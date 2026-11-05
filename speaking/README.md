# Eddy 口說 Chunks PWA

網址：https://eddychang0630.github.io/eddy-flashcards/speaking/

## 結構
- `index.html`：整個 App（版面、樣式、程式）
- `lessons/`：課程資料，每課一個檔案，格式見 `lessons/README.md`
- `manifest.json`、`sw.js`、圖示：PWA 安裝與離線用

## 課程管理
- 標題列點「▼」切換課程；預設是「📅 今日複習」，把所有課程到期的卡片混在一起
- 每課分兩種：🎬 影片課（按家族分組）、💬 問答句（按情境分組）
- 新增一課：在 `lessons/` 加檔案，並寫進 `lessons/index.js`

## 本機預覽
在這個資料夾執行 `python -m http.server 8000`，開 http://localhost:8000
（YouTube 內嵌播放器要用網址開才會動）

## 快捷鍵（電腦）
閃卡：Space 翻牌、P 播音、←/→ 切換、1 熟練、2 再練
跟讀 / 對話：Space 播放 / 停止
聽力抓塊：Space 播放、Enter 確認 / 下一題
