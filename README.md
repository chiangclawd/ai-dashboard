# 🤖 AI 每日儀表板

## 📍 位置
`/home/ubuntu/.openclaw/workspace/ai-dashboard/DASHBOARD.md`

## 🔄 自動更新
- **頻率：** 每天早上 8:00（cron）
- **內容：** RSS AI 新聞 + RAG (arXiv / GitHub / Hugging Face) 摘要
- **方式：** `update_dashboard.sh` 執行 `generate_dashboard.py` 自動產出 Markdown 與 HTML

## 📂 文件結構
```
ai-dashboard/
├── DASHBOARD.md              # 主儀表板（Markdown）
├── index.html                # 發佈用 HTML 儀表板
├── generate_dashboard.py     # Python 產生器：抓 RSS、整合 RAG
├── update_dashboard.sh       # Shell 包裝腳本（提供日誌、錯誤處理）
├── rag_data/rag_data.json    # RAG 資料來源
├── rag_system/               # Cron / RAG utilities
└── README.md
```

## 🎯 儀表板內容
- 🔥 頭條新聞（The Verge / TechCrunch RSS）
- 💼 產業動態
- 🧠 深度觀點
- 🤖 RAG 區塊（論文、開源專案、Hugging Face 趨勢）

## 📝 手動操作

### 立即更新儀表板
```bash
cd /home/ubuntu/.openclaw/workspace/ai-dashboard
./update_dashboard.sh
```
日誌輸出：`update.log`

### 查看最近輸出
```bash
tail -n 50 update.log
```

### 修改 RAG 資料
直接編輯 `rag_data/rag_data.json` 或撰寫新抓取腳本後覆蓋該檔。

## ⚙️ Cron 設定

設定每日 08:00 自動更新：
```bash
cd /home/ubuntu/.openclaw/workspace/ai-dashboard
./rag_system/setup_cron.sh
```
Cron log：`/home/ubuntu/.openclaw/workspace/ai-dashboard/cron.log`

## 🛠️ Troubleshooting
1. `update_dashboard.sh` exit code ≠ 0：查閱 `update.log`
2. 若 RSS 抓取失敗，腳本會落回最近文章，並在日誌記錄。
3. 若 RAG 檔案缺失，僅跳過該區塊，不影響新聞更新。

---
*由小管家 🤖 維護*
