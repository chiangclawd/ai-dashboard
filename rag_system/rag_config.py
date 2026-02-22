#!/usr/bin/env python3
"""
RAG System Configuration for AI Dashboard
使用 OpenClaw 內建功能實現 RAG 系統
"""

import os
import json
from datetime import datetime, timedelta

# 設定檔路徑
WORKSPACE = "/home/clawd/.openclaw/workspace"
AI_DASHBOARD_DIR = os.path.join(WORKSPACE, "ai-dashboard")
RAG_DATA_DIR = os.path.join(AI_DASHBOARD_DIR, "rag_data")
MEMORY_DIR = os.path.join(WORKSPACE, "memory")

# 創建必要目錄
os.makedirs(RAG_DATA_DIR, exist_ok=True)
os.makedirs(MEMORY_DIR, exist_ok=True)

# 搜尋設定
SEARCH_CONFIG = {
    "arxiv_queries": [
        "AI agent architecture",
        "large language model agents", 
        "autonomous AI systems",
        "multi-agent systems",
        "AI reasoning frameworks"
    ],
    "github_queries": [
        "AI agent framework",
        "LLM agent open source",
        "autonomous agent system",
        "AI agent toolkit",
        "multi-agent collaboration"
    ],
    "huggingface_queries": [
        "AI agent models",
        "agent-based LLM",
        "autonomous AI models"
    ]
}

# 更新頻率設定
UPDATE_CONFIG = {
    "frequency_hours": 24,  # 每24小時更新一次
    "last_update_file": os.path.join(RAG_DATA_DIR, "last_update.txt"),
    "data_file": os.path.join(RAG_DATA_DIR, "rag_data.json")
}

def get_last_update_time():
    """獲取上次更新時間"""
    try:
        with open(UPDATE_CONFIG["last_update_file"], "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def set_last_update_time():
    """設定上次更新時間"""
    with open(UPDATE_CONFIG["last_update_file"], "w") as f:
        f.write(datetime.now().isoformat())

def should_update():
    """檢查是否需要更新"""
    last_update = get_last_update_time()
    if not last_update:
        return True
    
    last_update_time = datetime.fromisoformat(last_update)
    hours_since_update = (datetime.now() - last_update_time).total_seconds() / 3600
    return hours_since_update >= UPDATE_CONFIG["frequency_hours"]

def save_rag_data(data):
    """儲存 RAG 資料"""
    with open(UPDATE_CONFIG["data_file"], "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_rag_data():
    """載入 RAG 資料"""
    try:
        with open(UPDATE_CONFIG["data_file"], "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"papers": [], "projects": [], "models": []}

if __name__ == "__main__":
    print("RAG 系統設定已載入")
    print(f"工作目錄: {WORKSPACE}")
    print(f"RAG 資料目錄: {RAG_DATA_DIR}")
    print(f"是否需要更新: {should_update()}")