#!/usr/bin/env python3
"""
Update HTML dashboard with RAG information (fixed version)
"""

import json
import datetime
import re

# 路徑設定
WORKSPACE = "/home/ubuntu/.openclaw/workspace"
DASHBOARD_DIR = f"{WORKSPACE}/ai-dashboard"
RAG_DATA_FILE = f"{DASHBOARD_DIR}/rag_data/rag_data.json"
HTML_FILE = f"{DASHBOARD_DIR}/index.html"

def load_rag_data():
    """載入 RAG 資料"""
    try:
        with open(RAG_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("RAG 資料檔案不存在")
        return None

def generate_rag_html_section():
    """生成 RAG HTML 區塊"""
    rag_data = load_rag_data()
    if not rag_data:
        return ""
    
    # 生成論文 HTML
    papers_html = ""
    for paper in rag_data.get('papers', [])[:3]:  # 只取前3篇
        papers_html += f'''
                        <li>
                            <strong><a href="{paper['url']}" target="_blank">{paper['title']}</a></strong>：{paper['abstract']}
                            <br><span class="source">來源：<a href="{paper['url']}" target="_blank">arXiv</a> • {paper['published_date']}</span>
                        </li>'''
    
    # 生成專案 HTML
    projects_html = ""
    for project in rag_data.get('projects', [])[:4]:  # 只取前4個
        projects_html += f'''
                        <li>
                            <strong><a href="{project['url']}" target="_blank">{project['name']}</a></strong>：{project['description']}
                            <br><span class="source">來源：<a href="{project['url']}" target="_blank">GitHub</a> • {project['last_updated']}</span>
                        </li>'''
    
    # 生成模型 HTML
    models_html = ""
    for model in rag_data.get('models', [])[:2]:  # 只取前2個
        models_html += f'''
                        <li>
                            <strong><a href="{model['url']}" target="_blank">{model['name']}</a></strong>：{model['description']}
                            <br><span class="source">來源：<a href="{model['url']}" target="_blank">Hugging Face</a></span>
                        </li>'''
    
    # 完整的 RAG 區塊
    rag_section = f'''
            <!-- RAG AI Agent Research -->
            <section class="dashboard-section">
                <h2>📅 {datetime.date.today().strftime("%Y-%m-%d")}</h2>
                <p class="date-subtitle">AI Agent 架構研究與開源專案 ({datetime.date.today().strftime("%Y-%m-%d")})</p>
                
                <div class="news-card">
                    <h3>📚 最新 AI Agent 論文</h3>
                    <ul>{papers_html}
                    </ul>
                </div>

                <div class="news-card">
                    <h3>💻 熱門開源專案</h3>
                    <ul>{projects_html}
                    </ul>
                </div>

                <div class="news-card">
                    <h3>🤗 Hugging Face 趨勢</h3>
                    <ul>{models_html}
                    </ul>
                </div>
            </section>
'''
    
    return rag_section

def update_html_file():
    """更新 HTML 檔案（修復重複問題）"""
    # 讀取現有的 HTML
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # 先移除任何現有的 RAG 區塊
    html_content = re.sub(r'\s*<!-- RAG AI Agent Research -->\s*<section class="dashboard-section">.*?</section>', '', html_content, flags=re.DOTALL)
    
    # 找到插入點（在 <main> 標籤後）
    main_pattern = r'(<main>\s*)'
    
    if re.search(main_pattern, html_content):
        # 插入新的 RAG 區塊
        rag_section = generate_rag_html_section()
        updated_content = re.sub(main_pattern, r'\1' + rag_section, html_content)
    else:
        # 如果找不到 <main>，就加在 body 的開頭
        body_pattern = r'(<body>\s*<div class="container">\s*)'
        rag_section = generate_rag_html_section()
        updated_content = re.sub(body_pattern, r'\1' + rag_section, html_content)
    
    # 寫回檔案
    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print("✅ HTML 儀表板已更新（已修復重複問題）")

if __name__ == "__main__":
    update_html_file()