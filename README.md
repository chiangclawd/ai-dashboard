# 🤖 AI 每日儀表板

## 📍 位置
`/home/ubuntu/.openclaw/workspace/ai-dashboard/DASHBOARD.md`

## 🔄 自動更新
- **頻率：** 每天早上 8:00
- **內容：** 整理前一天（24 小時內）的 AI 相關大事件
- **方式：** cron 定時任務自動執行

## 📂 文件結構
```
ai-dashboard/
├── DASHBOARD.md          # 主儀表板文件（每日更新）
├── update_dashboard.sh   # 更新腳本
├── update.log            # 更新日誌
└── README.md             # 本說明文件
```

## 🎯 儀表板內容
- 🔥 頭條新聞 - 重要 AI 新聞
- 📊 技術進展 - 新模型、新技術
- 💼 產業動態 - 公司、投資、併購
- 🧪 研究論文 - 重要學術發表
- 📈 趨勢觀察 - 產業趨勢分析

## 📝 手動操作

### 立即更新儀表板
對小管家說：「更新 AI 儀表板」

### 查看更新日誌
```bash
cat ~/ai-dashboard/update.log
```

### 自訂關注領域
編輯 `DASHBOARD.md` 或在 USER.md 中添加偏好設定

## ⚙️ Cron 設定
```bash
# 查看定時任務
crontab -l

# 編輯定時任務
crontab -e
```

## 🛠️ 故障排除

### 儀表板沒有更新？
1. 檢查 cron 狀態：`crontab -l`
2. 查看日誌：`cat ~/ai-dashboard/update.log`
3. 手動執行：`~/ai-dashboard/update_dashboard.sh`

### 想變更更新時間？
編輯 crontab：
```bash
crontab -e
```
修改第一欄（分鐘）和第二欄（小時）

---

*由小管家 🤖 維護*
