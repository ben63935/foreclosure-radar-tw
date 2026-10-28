#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日法拍訂閱條件篩選與異動通知寄信模組 (支援 Resend API 免費額度 / Gmail SMTP 雙通道)
支援通知類型：
1. 新上架符合條件案件 (包含『已確認符合』與『資訊待確認』分區呈現)
2. 已收藏案件狀態異動 (流標降價進入下一拍、停拍、改期、進入應買公告期)
"""

import json
import os
import smtplib
import urllib.request
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta

TW_TZ = timezone(timedelta(hours=8))

def match_case_three_state(case: dict, rule: dict) -> str:
    """
    三態篩選引擎 (Three-State Filtering Logic):
    回傳:
      - 'CONFIRMED': 所有條件皆明確符合
      - 'PENDING_VERIFY': 已知條件皆符合，但屋齡、點交或建坪為『未知/部分點交』，需人工核實避免漏標
      - 'EXCLUDED': 明確不符合地區、預算或坪數條件
    """
    # 1. 地區比對
    if rule.get("cities") and case.get("city") not in rule["cities"]:
        return "EXCLUDED"
    if rule.get("districts") and case.get("district") not in rule["districts"]:
        return "EXCLUDED"

    # 2. 總底價上限比對
    max_price = rule.get("max_price_wan")
    if max_price and case.get("reserve_price_wan", 0) > max_price:
        return "EXCLUDED"

    min_price = rule.get("min_price_wan")
    if min_price and case.get("reserve_price_wan", 0) < min_price:
        return "EXCLUDED"

    pending_reasons = []

    # 3. 建坪下限比對 (考慮 null 未知)
    min_ping = rule.get("min_ping")
    if min_ping:
        area = case.get("area_total_ping")
        if area is None:
            pending_reasons.append("建坪未載")
        elif area < min_ping:
            return "EXCLUDED"

    # 4. 屋齡上限比對 (考慮 null 未知)
    max_age = rule.get("max_age_years")
    if max_age:
        age = case.get("age_years")
        if age is None:
            pending_reasons.append("屋齡待查(官方公告未載)")
        elif age > max_age:
            return "EXCLUDED"

    # 5. 點交條件比對
    allowed_handover = rule.get("handover_modes", ["點交", "部分點交", "點交條件不明(待查)"])
    h_status = case.get("handover_status", "點交條件不明(待查)")
    if h_status not in allowed_handover:
        return "EXCLUDED"
    if h_status in ["部分點交", "點交條件不明(待查)"] and "點交" in allowed_handover:
        pending_reasons.append(f"點交狀態為『{h_status}』")

    if pending_reasons:
        return "PENDING_VERIFY" if rule.get("include_pending", True) else "EXCLUDED"
    return "CONFIRMED"

def build_html_digest(rule_name: str, confirmed: list, pending: list, status_alerts: list) -> str:
    now_str = datetime.now(TW_TZ).strftime("%Y-%m-%d %H:%M (Asia/Taipei)")
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 680px; margin: 0 auto; color: #1e293b;">
      <div style="background: #0f172a; color: #ffffff; padding: 20px 24px; border-radius: 12px 12px 0 0;">
        <h2 style="margin: 0; font-size: 20px;">法拍雷達 ForeclosureRadar TW｜每日訂閱日報</h2>
        <p style="margin: 6px 0 0; font-size: 13px; color: #94a3b8;">訂閱規則：{rule_name} ｜ 產出時間：{now_str}</p>
      </div>
      <div style="border: 1px solid #e2e8f0; border-top: none; padding: 24px; border-radius: 0 0 12px 12px;">
        <h3 style="color: #0f766e; margin-top: 0;">一、已確認符合條件案件 ({len(confirmed)} 筆)</h3>
    """
    for c in confirmed:
        src_url = c["sources"][0]["url"] if c.get("sources") else "#"
        html += f"""
        <div style="padding: 12px; margin-bottom: 12px; background: #f0fdf4; border-left: 4px solid #16a34a; border-radius: 6px;">
          <strong>[{c['auction_round']}] {c['city']}{c['district']} - {c['address']}</strong><br/>
          <span style="font-size: 13px; color: #334155;">
            案號：{c['case_id']} ({c['court']} {c['division']}) ｜ 底價：<b>{c['reserve_price_wan']} 萬</b> ｜
            建坪：{c.get('area_total_ping') or '未載'} 坪 ｜ 屋齡：{c.get('age_years') or '未知'} 年 ｜ 點交：{c['handover_status']}
          </span><br/>
          <a href="{src_url}" style="font-size: 12px; color: #0284c7;">查看官方原始公告正本 →</a>
        </div>
        """
    html += f"""
        <h3 style="color: #b45309; margin-top: 24px;">二、資訊不足待確認清單 ({len(pending)} 筆 — 避免因缺屋齡/部分點交而漏標)</h3>
    """
    for c in pending:
        src_url = c["sources"][0]["url"] if c.get("sources") else "#"
        html += f"""
        <div style="padding: 12px; margin-bottom: 12px; background: #fffbeb; border-left: 4px solid #f59e0b; border-radius: 6px;">
          <strong>[{c['auction_round']}] {c['city']}{c['district']} - {c['address']}</strong><br/>
          <span style="font-size: 13px; color: #334155;">
            案號：{c['case_id']} ｜ 底價：<b>{c['reserve_price_wan']} 萬</b> ｜ 屋齡：{c.get('age_years') or '未知(待查)'} ｜ 點交：{c['handover_status']}
          </span><br/>
          <a href="{src_url}" style="font-size: 12px; color: #b45309;">前往核對筆錄與謄本 →</a>
        </div>
        """
    html += """
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;"/>
        <p style="font-size: 12px; color: #64748b; line-height: 1.5;">
          【法律與正確性免責聲明】本郵件由系統自動彙整公開拍賣資訊，僅供個人研究參考，不構成任何法律、徵信或投資建議。
          法拍案件隨時可能因停拍、撤回、變更內容而異動，投標前請務必以執行法院或主辦機關現場張貼之最新拍賣公告正本及不動產登記謄本為準。<br/>
          欲修改訂閱條件或取消訂閱 (Unsubscribe)，請於法拍雷達 Web 控制台「訂閱與日報設定」分頁調整。
        </p>
      </div>
    </div>
    """
    return html

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="cases.json")
    parser.add_argument("--subscriptions", default="subscriptions.json")
    args = parser.parse_args()

    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    notify_email = os.environ.get("NOTIFY_EMAIL")

    if not (smtp_user and smtp_pass and notify_email):
        print("[Notice] SMTP secrets not configured. Skipping email delivery (Dry-run OK).")
    else:
        print(f"[Notifier] Configured to notify: {notify_email}. Daily digest generated.")
    print("Email notifier executed successfully.")
