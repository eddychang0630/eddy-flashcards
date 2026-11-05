# Eddy 口說 Chunks PWA

## 檔案
- `index.html`：整個 App（版面、樣式、程式）
- `data.js`：教材資料（由 `../chunks_data.json` 轉成）
- `manifest.json`、`sw.js`、`icon-*.png`、`apple-touch-icon.png`：PWA 安裝與離線用

## 本機預覽
直接雙擊 `index.html` 就能看筆記、閃卡、跟讀、測驗。
YouTube 內嵌播放器需要用網址開（file:// 會被 YouTube 擋），可以在這個資料夾執行：
    python -m http.server 8000
然後開 http://localhost:8000

## 部署到 GitHub Pages（建議放在 eddy-flashcards 底下的 /speaking/）
1. （已部署）eddy-flashcards repo 的 `speaking/` 資料夾就是這份 App
2. commit + push
3. 網址：https://eddychang0630.github.io/eddy-flashcards/speaking/
4. iPhone / iPad：Safari 開網址 → 分享 → 加入主畫面

## 更新教材
改完 `chunks_data.json` 後，重新產生 data.js：
    python -c "import json;d=json.load(open('../chunks_data.json',encoding='utf-8'));open('data.js','w',encoding='utf-8').write('window.CHUNKS_DATA = '+json.dumps(d,ensure_ascii=False,indent=1)+';\n')"
並把 `sw.js` 裡的 `CACHE_NAME` 版本號 +1。

## 快捷鍵（電腦）
閃卡：Space 翻牌、P 播音、←/→ 切換、1 熟練、2 再練
跟讀 / 對話：Space 播放 / 停止
聽力抓塊：Space 播放、Enter 確認 / 下一題
