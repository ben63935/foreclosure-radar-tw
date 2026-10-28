# 台灣跨平台法拍屋、金拍屋、銀拍屋智慧搜尋與盡職調查系統 (ForeclosureRadar TW)

本專案整合 **司法院法拍屋、台灣金服(金拍屋)、合作金庫(銀拍/法拍)、臺灣銀行、法務部行政執行署、內政部不動產資訊平台** 以及 **104法拍網、優室法拍** 等 8 大管道，提供：
1. **三態容錯篩選引擎**：區分「已確認符合」、「資訊不足待確認（如官方公告未載屋齡或部分點交）」與「已確認排除」，杜絕因欄位缺失而漏掉好物件。
2. **跨平台唯一去重與拍賣歷程時間軸**：以 `法院代碼_年度_案號_標別` 建立唯一鍵，合併同案一拍、二拍、三拍與應買歷程，並自動標示官方與民間平台之欄位差異。
3. **多組自訂條件訂閱 & 每日 Email 日報**：內建預設條件（如桃園自住 850 萬內、新北點交宅、苗栗低總價透天）與收藏案件異動追蹤（流標降價、停拍、改期、應買到期提醒）。
4. **單案件三級證據力深度調查工作台 & AI Prompt 一鍵匯出**：針對選定案件提供「已確認事實 / 待查證線索 / 無法自動取得需人工核實」三級檢核表，並支援一鍵匯出結構化 JSON、Markdown 報告與 **Deep Research AI 分析專用 Prompt**。

---

## 免費部署與自動排程步驟 (GitHub Pages / Cloudflare Pages + GitHub Actions)

### 步驟 1：上傳至 GitHub 儲存庫 (透過網頁直接上傳，免安裝指令工具)
1. 登入您的 GitHub 帳號，建立一個新的公開或私有 Repository（例如 `foreclosure-radar-tw`）。
2. 點選頁面上的 **Add file → Upload files**，將本壓縮包解壓縮後的所有檔案直接拖曳上傳至網頁，點選 **Commit changes**。

### 步驟 2：開啟免費前端網站託管 (二選一)
- **方案 A：GitHub Pages (最簡單)**
  進入 Repository 的 `Settings` → `Pages`，在 `Build and deployment` 選擇 `Deploy from a branch` (`main` 分支 `/root` 目錄)，儲存後即可獲得免費網址。
- **方案 B：Cloudflare Pages (全球 CDN 加速)**
  登入 Cloudflare Dashboard → `Workers & Pages` → `Create application` → `Pages` → `Connect to Git`，選擇剛才建立的 GitHub Repo，直接點選 `Save and Deploy` 即可免費上線，之後每次爬蟲更新資料皆會自動重新部署。

### 步驟 3：設定每日自動篩選與免費 Email 通知 (GitHub Actions Secrets)
1. 前往 [Resend](https://resend.com/) 申請免費帳號（每月免費 3,000 封額度），或使用 Gmail 應用程式密碼。
2. 在 GitHub Repository 點選 `Settings` → `Secrets and variables` → `Actions` → `New repository secret`，新增：
   - `RESEND_API_KEY`：您的 Resend API 金鑰（或設定 `SMTP_USER` / `SMTP_PASS`）
   - `NOTIFY_EMAIL`：您要接收每日法拍日報與異動通知的個人信箱
3. 系統將於每日台灣時間 `07:30` 自動執行 `.github/workflows/daily_foreclosure_sync.yml`，您也可以隨時到 `Actions` 分頁點選 **Run workflow** 手動立即觸發。

---

## 法律合規與免責聲明
- 本系統優先使用政府開放資料與合法公開頁面，並嚴格遵守速率限制（每日僅低頻同步一次），不進行高併發爬取，亦不暴力破解任何 CAPTCHA 圖形驗證碼。
- 所有案件資訊皆附帶原始公告連結與抓取時間戳；法拍案件隨時可能停拍、撤回或變更，**投標前請務必以各執行法院及拍賣機關公告正本與最新地政謄本為準**。
