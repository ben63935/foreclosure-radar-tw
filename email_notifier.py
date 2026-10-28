#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日法拍多人分流訂閱篩選與真實寄信模組 (ForeclosureRadar TW)
1. 支援讀取加密保護之家人與成員收件名單 (ENC_MAIL:... 自動於記憶體內解密，公開庫零個資外洩)
2. 支援依每位家人各自訂閱的規則分流篩選 (CONFIRMED / PENDING / EXCLUDED)，寄發個人專屬日報
3. 透過站長設定於 GitHub Secrets 的 Gmail SMTP (SMTP_USER / SMTP_PASS) 自動寄送給所有訂閱家人
"""

import json
import os
import smtplib
import argparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta

TW_TZ = timezone(timedelta(hours=8))
EMAIL_CIPHER_KEY = "FR_TW_FAMILY_CIPHER_2026"

def decode_protected_email(encoded_str: str) -> str:
    if not encoded_str or encoded_str in ("GITHUB_SECRET_DEFAULT", "PROTECTED_BY_GITHUB_SECRETS"):
        return ""
    if not encoded_str.startswith("ENC_MAIL:"):
        return encoded_str.strip()
    try:
        hex_part = encoded_str[9:]
        raw_bytes = bytes.fromhex(hex_part)
        key_bytes = EMAIL_CIPHER_KEY.encode("utf-8")
        out_bytes = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(raw_bytes)])
        return out_bytes.decode("utf-8").strip()
    except Exception:
        return ""

def mask_email(email_str: str) -> str:
    if not email_str or "@" not in email_str:
        return "（由 GitHub Secrets 加密保護）"
    name, domain = email_str.split("@", 1)
    if len(name) <= 2:
        masked = name[0] + "***"
    else:
        masked = name[:2] + "***" + name[-1]
    return f"{masked}@{domain}"

def match_multi_locations(case: dict, loc_array: list) -> bool:
    if not loc_array:
        return True
    c_city = case.get("city", "")
    c_dist = case.get("district", "")
    for token in loc_array:
        token = str(token).strip()
        if not token or token == "ALL":
            return True
        if ":" in token:
            t_city, t_dist = [x.strip() for x in token.split(":", 1)]
            if c_city == t_city and (t_dist in ("*", "") or c_dist == t_dist):
                return True
        else:
            if c_city == token or c_dist == token or (c_city + c_dist) == token:
                return True
    return False

def evaluate_case_bucket(case: dict, rule: dict, show_demo: bool = True) -> tuple:
    if not show_demo and case.get("is_demo"):
        return ("EXCLUDED", ["隱藏示範樣本"])

    locs = rule.get("locations", [])
    if not match_multi_locations(case, locs):
        return ("EXCLUDED", ["地區不符"])

    max_price = rule.get("maxPrice") or rule.get("max_price_wan")
    if max_price is not None and float(case.get("reserve_price_wan", 0)) > float(max_price):
        return ("EXCLUDED", ["底價超過上限"])

    min_price = rule.get("minPrice") or rule.get("min_price_wan")
    if min_price is not None and float(case.get("reserve_price_wan", 0)) < float(min_price):
        return ("EXCLUDED", ["底價低於下限"])

    pending_reasons = []

    min_ping = rule.get("minPing") or rule.get("min_ping")
    if min_ping is not None and float(min_ping) > 0:
        area = case.get("area_total_ping")
        if area is None:
            pending_reasons.append("總建坪官方未載(待查)")
        elif float(area) < float(min_ping):
            return ("EXCLUDED", ["建坪低於下限"])

    max_age = rule.get("maxAge") or rule.get("max_age_years")
    if max_age is not None and float(max_age) >= 0:
        age = case.get("age_years")
        if age is None:
            pending_reasons.append("屋齡官方未載(待調謄本核實)")
        elif float(age) > float(max_age):
            return ("EXCLUDED", ["屋齡超過上限"])

    h_mode = rule.get("handover", "SAFE_AND_PENDING")
    h_status = case.get("handover_status", "點交條件不明(待查)")
    if h_mode == "STRICT_HANDOVER":
        if h_status != "點交":
            return ("EXCLUDED", ["非明確點交"])
    elif h_mode == "SAFE_AND_PENDING":
        if h_status == "不點交":
            return ("EXCLUDED", ["不點交排除"])
        if h_status in ("部分點交", "點交條件不明(待查)"):
            pending_reasons.append(f"點交狀態為「{h_status}」")

    if case.get("status") == "停拍/撤回":
        pending_reasons.append("最新公告為停拍/撤回")

    if pending_reasons:
        return ("PENDING", pending_reasons)
    return ("CONFIRMED", [])

def build_html_digest(member_name: str, masked_recipient: str, rules_count: int, confirmed_items: list, pending_items: list) -> str:
    now_str = datetime.now(TW_TZ).strftime("%Y-%m-%d %H:%M (Asia/Taipei)")
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 680px; margin: 0 auto; color: #1e293b;">
      <div style="background: #0f172a; color: #ffffff; padding: 20px 24px; border-radius: 12px 12px 0 0;">
        <h2 style="margin: 0; font-size: 19px;">法拍雷達 ForeclosureRadar TW｜每日專屬訂閱日報</h2>
        <p style="margin: 6px 0 0; font-size: 12px; color: #cbd5e1;">
          收件成員：{member_name} ({masked_recipient}) ｜ 適用規則：{rules_count} 組 ｜ 產出時間：{now_str}
        </p>
      </div>
      <div style="border: 1px solid #e2e8f0; border-top: none; padding: 20px 24px; border-radius: 0 0 12px 12px; background: #ffffff;">
        <h3 style="color: #065f46; margin-top: 0; font-size: 15px; border-bottom: 1px solid #d1fae5; padding-bottom: 8px;">
          ✅ 一、已確認符合您設定條件之案件 ({len(confirmed_items)} 筆)
        </h3>
    """
    if not confirmed_items:
        html += "<p style='font-size: 13px; color: #64748b;'>今日無完全符合條件之案件。</p>"
    for item in confirmed_items:
        c = item["case"]
        tag = "[示範樣本] " if c.get("is_demo") else "[真實公告] "
        src_url = c["sources"][0]["url"] if c.get("sources") else "https://aomp109.judicial.gov.tw/judbp/wkw/WHD1A02.htm"
        html += f"""
        <div style="padding: 12px; margin-bottom: 10px; background: #f0fdf4; border-left: 4px solid #16a34a; border-radius: 6px;">
          <div style="font-weight: bold; font-size: 14px; color: #0f172a;">
            {tag}[{c.get('city')}・{c.get('district')}] {c.get('address')} ({c.get('auction_round')}・{c.get('reserve_price_wan')}萬・{c.get('handover_status')})
          </div>
          <div style="font-size: 12px; color: #334155; margin-top: 4px;">
            案號：{c.get('case_id')} ({c.get('court')}) ｜ 建坪：<b>{c.get('area_total_ping') or '未載'} 坪</b> ｜
            屋齡：<b>{c.get('age_years') if c.get('age_years') is not None else '待查'} 年</b> ｜ 開標日：{c.get('auction_date_roc')}
          </div>
          <div style="font-size: 11px; color: #047857; margin-top: 4px;">
            命中規則：{item['rule_name']} ｜ <a href="{src_url}" style="color: #0284c7;">查看官方原始公告 ↗</a>
          </div>
        </div>
        """

    html += f"""
        <h3 style="color: #92400e; margin-top: 22px; font-size: 15px; border-bottom: 1px solid #fef3c7; padding-bottom: 8px;">
          ⚠️ 二、資訊不足待確認防漏清單 ({len(pending_items)} 筆 — 避免因缺屋齡或部分點交漏標)
        </h3>
    """
    if not pending_items:
        html += "<p style='font-size: 13px; color: #64748b;'>今日無待確認防漏案件。</p>"
    for item in pending_items:
        c = item["case"]
        tag = "[示範樣本] " if c.get("is_demo") else "[真實公告] "
        reasons_str = "、".join(item.get("reasons", []))
        html += f"""
        <div style="padding: 12px; margin-bottom: 10px; background: #fffbeb; border-left: 4px solid #f59e0b; border-radius: 6px;">
          <div style="font-weight: bold; font-size: 14px; color: #0f172a;">
            {tag}[{c.get('city')}・{c.get('district')}] {c.get('address')} ({c.get('auction_round')}・{c.get('reserve_price_wan')}萬・{c.get('handover_status')})
          </div>
          <div style="font-size: 12px; color: #78350f; margin-top: 4px;">
            建坪：{c.get('area_total_ping') or '未載'} 坪 ｜ 待查原因：<b>{reasons_str}</b>
          </div>
        </div>
        """

    html += """
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;"/>
        <p style="font-size: 11px; color: #64748b; line-height: 1.5;">
          【系統提示】標註為「示範樣本」之物件為系統預設功能測試資料，非實際待標案；投標前請務必以司法院、行政執行署與主辦銀行最新拍賣公告正本及第二類謄本為準。<br/>
          前往專屬法拍雷達控制台：<a href="https://ben63935.github.io/foreclosure-radar-tw/">https://ben63935.github.io/foreclosure-radar-tw/</a>
        </p>
      </div>
    </div>
    """
    return html

def send_gmail_smtp(smtp_user: str, smtp_pass: str, recipient: str, subject: str, html_body: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"ForeclosureRadar TW 法拍雷達 <{smtp_user}>"
    msg["To"] = recipient
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [recipient], msg.as_string())

def evaluate_for_member(member_id: str, rules: list, cases: list, show_demo: bool):
    confirmed_map = {}
    pending_map = {}
    confirmed_items = []
    pending_items = []
    member_rules_count = 0

    for r in rules:
        if not r.get("active", True):
            continue
        r_subs = r.get("subscribers") or ["ALL"]
        if "ALL" not in r_subs and member_id not in r_subs:
            continue
        member_rules_count += 1
        for c in cases:
            key = c.get("dedup_key")
            bucket, reasons = evaluate_case_bucket(c, r, show_demo=show_demo)
            if bucket == "CONFIRMED" and key not in confirmed_map:
                confirmed_map[key] = True
                confirmed_items.append({"case": c, "rule_name": r.get("name", "自訂規則")})
            elif bucket == "PENDING" and key not in pending_map and key not in confirmed_map:
                pending_map[key] = True
                pending_items.append({"case": c, "reasons": reasons, "rule_name": r.get("name", "自訂規則")})

    return member_rules_count, confirmed_items, pending_items

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="cases.json")
    parser.add_argument("--subscriptions", default="subscriptions.json")
    args = parser.parse_args()

    cases = []
    if os.path.exists(args.cases):
        try:
            with open(args.cases, "r", encoding="utf-8") as f:
                cases = json.load(f)
        except Exception as e:
            print(f"[Warn] Could not parse {args.cases}: {e}")

    sub_config = {}
    if os.path.exists(args.subscriptions):
        try:
            with open(args.subscriptions, "r", encoding="utf-8") as f:
                sub_config = json.load(f)
        except Exception as e:
            print(f"[Warn] Could not parse {args.subscriptions}: {e}")

    rules = sub_config.get("subscriptions", [])
    show_demo = sub_config.get("include_demo_in_email", True)
    raw_subscribers = sub_config.get("subscribers", [])

    default_secret_email = (os.environ.get("NOTIFY_EMAIL") or os.environ.get("SMTP_USER") or "").strip()
    smtp_user = (os.environ.get("SMTP_USER") or "").strip()
    smtp_pass = (os.environ.get("SMTP_PASS") or "").strip()

    # Build resolved recipient list
    resolved_members = []
    seen_emails = set()

    if not raw_subscribers:
        raw_subscribers = [{"id": "mem_owner", "name": "👑 站長主信箱", "email": "GITHUB_SECRET_DEFAULT", "active": True}]

    for m in raw_subscribers:
        if not m.get("active", True):
            continue
        mid = m.get("id", "mem_owner")
        mname = m.get("name", "家庭成員")
        raw_em = m.get("email", "")
        if raw_em in ("GITHUB_SECRET_DEFAULT", "PROTECTED_BY_GITHUB_SECRETS", ""):
            real_email = default_secret_email
        else:
            real_email = decode_protected_email(raw_em)

        if real_email and "@" in real_email and real_email.lower() not in seen_emails:
            seen_emails.add(real_email.lower())
            resolved_members.append({"id": mid, "name": mname, "email": real_email})
        elif mid == "mem_owner" and not real_email:
            resolved_members.append({"id": mid, "name": mname, "email": ""})

    preview_saved = False
    for mem in resolved_members:
        m_rules_cnt, conf_items, pend_items = evaluate_for_member(mem["id"], rules, cases, show_demo)
        masked_addr = mask_email(mem["email"])
        html_body = build_html_digest(mem["name"], masked_addr, m_rules_cnt, conf_items, pend_items)

        if not preview_saved:
            with open("latest_digest_preview.html", "w", encoding="utf-8") as f:
                f.write(html_body)
            preview_saved = True

        print(f"[Digest] 成員【{mem['name']}】({masked_addr})：適用 {m_rules_cnt} 組規則 -> 符合 {len(conf_items)} 筆，待查 {len(pend_items)} 筆")

        if smtp_user and smtp_pass and mem["email"] and m_rules_cnt > 0:
            subject = f"【法拍雷達日報・{mem['name']}】今日命中 {len(conf_items)} 筆符合案件 + {len(pend_items)} 筆待查防漏"
            try:
                send_gmail_smtp(smtp_user, smtp_pass, mem["email"], subject, html_body)
                print(f"[SUCCESS] 已成功寄送專屬法拍日報給【{mem['name']}】({masked_addr})！")
            except Exception as e:
                print(f"[SMTP Error] 寄送給 {masked_addr} 失敗，請檢查 SMTP_USER / SMTP_PASS：{e}")
        elif not (smtp_user and smtp_pass):
            print("[Notice] 尚未於 GitHub Secrets 設定 SMTP_USER 與 SMTP_PASS，已產出預覽檔 (Dry-run OK)。")
