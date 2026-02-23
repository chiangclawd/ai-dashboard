# 🤖 AI 每日儀表板

## 📍 位置
`/home/ubuntu/.openclaw/workspace/ai-dashboard/DASHBOARD.md`

## 🔄 自動更新
- **頻率：** 每天早上 8:00（cron）
- **內容：** 多來源 AI 新聞 RSS（The Verge、TechCrunch、MIT Technology Review、Ars Technica、AI Trends）+ RAG (arXiv / GitHub / Hugging Face)
- **語言：** 透過 Google Translate API 自動轉為繁體中文
- **流程：** `update_dashboard.sh` → `generate_dashboard.py`
  - 產出 `DASHBOARD.md` / `index.html`
  - 儲存歷史檔 `history/<date>.md`
  - 更新 `timeline.md`（時間軸摘要）

## 📂 文件結構
```
ai-dashboard/
├── DASHBOARD.md              # 主儀表板（Markdown）
├── index.html                # 發佈用 HTML 儀表板
├── generate_dashboard.py     # Python 產生器：抓 RSS、翻譯、整合 RAG、寫入歷史 & timeline
├── update_dashboard.sh       # Shell 包裝腳本（可給 cron 呼叫）
├── timeline.md               # 歷史時間軸（自動更新）
├── history/                  # 依日期歸檔的完整儀表板
├── rag_data/rag_data.json    # RAG 資料來源
└── rag_system/               # Cron / RAG wrapper（相容舊流程）
```

## 🎯 儀表板內容
- 🔥 頭條新聞（繁體中文摘要）
- 💼 產業動態
- 🧠 深度觀點
- 🤖 RAG 區塊（論文、開源專案、Hugging Face 趨勢）
- 🗂 主頁上提供「今日完整內容」與「歷史時間軸」連結

## 📝 手動操作

### 立即更新儀表板
```bash
cd /home/ubuntu/.openclaw/workspace/ai-dashboard
./update_dashboard.sh
```
完成後會同時刷新 DASHBOARD、HTML、history、timeline。日誌：`update.log`

### 查看最近輸出
```bash
tail -n 50 update.log
```

### 修改 RAG 資料
編輯 `rag_data/rag_data.json` 或撰寫新抓取腳本後覆蓋該檔。

## ⚙️ Cron 設定

設定每日 08:00 自動更新：
```bash
cd /home/ubuntu/.openclaw/workspace/ai-dashboard
./rag_system/setup_cron.sh
```
Cron log：`/home/ubuntu/.openclaw/workspace/ai-dashboard/cron.log`

## 🛠️ Troubleshooting
1. `update_dashboard.sh` exit code ≠ 0：查閱 `update.log`
2. 若 RSS 抓取失敗，腳本會記錄並改用最近文章。
3. 若翻譯 API 無回應，摘要會暫時以原文呈現並在日誌提示。

---
*由小管家 🤖 維護*
