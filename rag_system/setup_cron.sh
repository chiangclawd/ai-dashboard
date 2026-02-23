#!/bin/bash
# Setup cron job for daily AI Dashboard update

WORKSPACE="/home/ubuntu/.openclaw/workspace"
SCRIPT_PATH="$WORKSPACE/ai-dashboard/update_dashboard.sh"
CRON_LOG="$WORKSPACE/ai-dashboard/cron.log"

(crontab -l 2>/dev/null | grep -v "$SCRIPT_PATH"; echo "0 8 * * * $SCRIPT_PATH >> $CRON_LOG 2>&1") | crontab -

echo "✅ 每日自動更新任務已設定"
echo "⏰ 執行時間：每天上午 8:00"
echo "📄 腳本路徑：$SCRIPT_PATH"
echo "📝 日誌檔案：$CRON_LOG"
