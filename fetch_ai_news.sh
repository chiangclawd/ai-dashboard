#!/bin/bash
# AI Daily Dashboard - News Fetcher
# 每天自動抓取 AI 相關新聞並更新儀表板

WORKSPACE="/home/clawd/.openclaw/workspace"
DASHBOARD_DIR="$WORKSPACE/ai-dashboard"
NEWS_FILE="$DASHBOARD_DIR/daily_news.md"
DATE=$(date +"%Y-%m-%d")
YESTERDAY=$(date -d "yesterday" +"%Y-%m-%d")

# 創建或更新新聞文件
cat > "$NEWS_FILE" << EOF
# 🤖 AI 每日儀表板 - $DATE

## 📰 昨日 AI 大事件 ($YESTERDAY)

_最後更新：$(date +"%Y-%m-%d %H:%M")_

---

EOF

echo "✅ AI 新聞儀表板已初始化：$NEWS_FILE"
echo "📅 日期：$DATE"
echo "📆 涵蓋：$YESTERDAY"
