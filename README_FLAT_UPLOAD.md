# ForeclosureRadar TW 升級版上傳包說明 (v5)

本壓縮包已整合以下 4 項重大修正與新功能：
1. **修正 Email 日報預覽動態過濾 Bug**：右側 Email 預覽現在 100% 依據左側設定的訂閱條件（地區、850萬內、30坪+、20年內）即時動態篩選，不會再出現不符條件的靜態範本。
2. **新增「🔒 網站管理員安全鎖 + 網頁直接設定發信」**：在「🔔 條件訂閱 & Email 日報」分頁輸入您的 GitHub Personal Access Token 解鎖後，即可直接在網頁修改條件與收件 Email，一鍵寫入 GitHub `subscriptions.json` 並立即觸發寄送測試信（外人無金鑰無法盜用發信）。
3. **整合 GitHub Models 免費 AI (GPT-4o / GPT-4o-mini) 初步調查**：在「🕵️ 案件深度調查 & AI 匯出」分頁，可一鍵免費呼叫 GitHub 官方提供的 GPT-4o 模型針對案件執行第一階段產權與筆錄陷阱預審，並自動併入匯出 JSON/Prompt。
4. **資料真實性標示與示範樣本開關**：將內建 10 筆功能測試樣本清楚標註「🧪 示範樣本」，並提供「顯示/隱藏內建示範樣本」開關與自動讀取 `cases.json` 機制。

## 如何更新至您的 GitHub 倉庫：
1. 解壓縮本壓縮包。
2. 在您的 GitHub 倉庫 `ben63935/foreclosure-radar-tw` 點擊 **Add file → Upload files**。
3. 將解壓縮後的 `index.html`, `scraper_pipeline.py`, `email_notifier.py`, `subscriptions.json`, `cases.json`, `requirements.txt` 拖曳上傳，點擊下方 **Commit changes** 覆蓋更新。
4. 若要更新 `.github/workflows/daily_sync.yml`（新增免費 AI `models: read` 權限），點進倉庫內的 `.github/workflows/daily_sync.yml` 貼上新版 `daily_sync.yml` 內容即可。
