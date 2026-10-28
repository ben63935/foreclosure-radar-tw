# 免安裝 Git！純網頁上傳專案結構說明 (扁平化單層包)

這個壓縮包裡面的所有檔案都是「純單層檔案」，完全沒有子資料夾：
1. `index.html` (前端主程式網頁)
2. `scraper_pipeline.py` (法拍爬蟲與資料清洗)
3. `email_notifier.py` (每日 Email 日報寄送)
4. `requirements.txt` (Python 套件清單)
5. `schema.json` (統一資料結構規範)

## 為什麼直接拖曳資料夾會被忽略？
GitHub 網頁的「Choose your files」彈出視窗只允許選取「檔案」；但如果你用滑鼠在電腦裡「框選整個資料夾」直接拖進瀏覽器，某些瀏覽器（或點選按鈕時）不支援資料夾上傳。

## 兩種最簡單的解法：

### 解法 A：在 GitHub 網頁上「直接建立資料夾與工作流」（最推薦，只需建一次）
GitHub Actions 的排程設定檔必須放在 `.github/workflows/` 資料夾內：
1. 在您的 GitHub 儲存庫頁面，點擊 **「Add file」→「Create new file」**。
2. 在檔名框輸入：
   `.github/workflows/daily_sync.yml`
   （當您輸入 `/` 時，GitHub 就會自動為您建立 `.github` 與 `workflows` 這兩層資料夾！）
3. 把壓縮包中 `daily_sync.yml` 的文字貼進去，滑到最下面點擊 **Commit changes**。
4. 接著回到根目錄，點擊 **Add file → Upload files**，把剩餘的 `index.html`、`scraper_pipeline.py`、`email_notifier.py`、`requirements.txt` 直接全選拖進去即可！

### 解法 B：電腦安裝「GitHub Desktop」(免費圖形化軟體，全自動同步資料夾)
如果您不想在網頁手動建立，強烈推薦下載官方的 **[GitHub Desktop](https://desktop.github.com/)**（免費無廣告）：
1. 下載並登入您的 GitHub 帳號。
2. 點選 `File` → `Clone Repository` 把您建好的儲存庫下載到電腦。
3. 把整包解壓縮出來的資料夾與檔案直接複製貼進去。
4. 回到 GitHub Desktop 軟體，左下角按一下 **Commit to main**，再按右上角 **Push origin**，不到 3 秒鐘所有多層資料夾與設定檔就全自動上傳完成了！
