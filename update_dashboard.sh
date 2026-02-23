#!/bin/bash
# AI Dashboard orchestrator
# Fetches news + updates Markdown/HTML via Python generator

set -euo pipefail

WORKSPACE="/home/ubuntu/.openclaw/workspace/ai-dashboard"
LOG_FILE="$WORKSPACE/update.log"
SCRIPT="$WORKSPACE/generate_dashboard.py"

if [ ! -f "$SCRIPT" ]; then
  echo "找不到 $SCRIPT" >&2
  exit 1
fi

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
mkdir -p "$WORKSPACE"
echo "[$TIMESTAMP] 開始執行 update_dashboard.sh" >> "$LOG_FILE"

if python3 "$SCRIPT" >> "$LOG_FILE" 2>&1; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 儀表板生成完成" >> "$LOG_FILE"
  echo "✅ AI 儀表板已更新"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 儀表板生成失敗" >> "$LOG_FILE"
  echo "❌ AI 儀表板更新失敗，詳見 $LOG_FILE" >&2
  exit 1
fi
