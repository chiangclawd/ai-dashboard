#!/usr/bin/env python3
"""AI Daily Dashboard generator with Traditional Chinese summaries."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import escape, unescape
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlencode
from urllib.request import Request, urlopen

WORKSPACE = Path("/home/ubuntu/.openclaw/workspace/ai-dashboard")
DASHBOARD_MD = WORKSPACE / "DASHBOARD.md"
DASHBOARD_HTML = WORKSPACE / "index.html"
RAG_DATA_FILE = WORKSPACE / "rag_data" / "rag_data.json"
LOG_FILE = WORKSPACE / "update.log"

ATOM_NS = "{http://www.w3.org/2005/Atom}"
USER_AGENT = "Mozilla/5.0 (AI-Dashboard-Aggregator)"
TRANSLATE_ENDPOINT = "https://translate.googleapis.com/translate_a/single"
LOOKBACK_HOURS = 36
MIN_ARTICLES = 6
SUMMARY_LIMIT = 400

RSS_SOURCES = [
    {"name": "The Verge · AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"},
    {"name": "TechCrunch · Artificial Intelligence", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "MIT Technology Review · AI", "url": "https://www.technologyreview.com/feed/?category_name=artificial-intelligence"},
    {"name": "Ars Technica · AI", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab"},
    {"name": "AI Trends", "url": "https://www.aitrends.com/feed/"},
]

# ---------------------------------------------------------------------------

def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(f"[{timestamp}] {message}\n")

def http_get(url: str, timeout: int = 20) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()

def strip_html(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def node_text(element, tag: str) -> str:
    value = element.findtext(tag)
    if value:
        return value.strip()
    value = element.findtext(ATOM_NS + tag)
    if value:
        return value.strip()
    return ""

def translate_to_traditional(text: str) -> str:
    if not text:
        return ""
    params = urlencode({
        "client": "gtx",
        "sl": "auto",
        "tl": "zh-TW",
        "dt": "t",
        "q": text[:SUMMARY_LIMIT],
    })
    url = f"{TRANSLATE_ENDPOINT}?{params}"
    try:
        raw = http_get(url, timeout=15)
        data = json.loads(raw.decode("utf-8"))
        translated = "".join(segment[0] for segment in data[0])
        return translated.strip()
    except Exception as exc:
        log(f"⚠️ 翻譯失敗（使用原文）：{exc}")
        return text

@dataclass
class Article:
    title: str
    link: str
    source: str
    published: datetime
    summary: str

    def to_markdown(self) -> str:
        date_str = self.published.strftime("%Y-%m-%d %H:%M %Z")
        return (
            f"- **[{self.title}]({self.link})**  _{self.source} · {date_str}_  \n"
            f"  {self.summary}"
        )

    def to_html(self) -> str:
        date_str = self.published.strftime("%Y-%m-%d %H:%M %Z")
        return (
            "<li>"
            f"<strong><a href=\"{escape(self.link)}\" target=\"_blank\">{escape(self.title)}</a></strong><br>"
            f"<span class=\"source\">{escape(self.source)} · {date_str}</span>"
            f"<p>{escape(self.summary)}</p>"
            "</li>"
        )

# ---------------------------------------------------------------------------

def parse_feed(data: bytes, source: str) -> List[Article]:
    import xml.etree.ElementTree as ET

    articles: List[Article] = []
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        log(f"❌ 無法解析 {source} RSS：{exc}")
        return articles

    items = root.findall(".//item")
    if not items:
        items = root.findall(f".//{ATOM_NS}entry")

    for item in items:
        title = node_text(item, "title")
        link = node_text(item, "link")
        if not link:
            link_el = item.find("link") or item.find(ATOM_NS + "link")
            if link_el is not None:
                link = (link_el.get("href") or link_el.text or "").strip()
        pub_date_raw = node_text(item, "pubDate") or node_text(item, "updated")
        summary_raw = node_text(item, "description") or node_text(item, "summary")
        summary_clean = strip_html(summary_raw)[:SUMMARY_LIMIT]
        summary = translate_to_traditional(summary_clean)

        if not title or not link:
            continue

        try:
            pub_dt = parsedate_to_datetime(pub_date_raw)
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
            else:
                pub_dt = pub_dt.astimezone(timezone.utc)
        except Exception:
            pub_dt = datetime.now(timezone.utc)

        articles.append(Article(title=title, link=link, source=source, published=pub_dt, summary=summary))
    return articles

def collect_news() -> List[Article]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    aggregated: List[Article] = []
    for source in RSS_SOURCES:
        try:
            data = http_get(source["url"])
            parsed = parse_feed(data, source["name"])
            recent = [a for a in parsed if a.published >= cutoff]
            if not recent:
                recent = sorted(parsed, key=lambda a: a.published, reverse=True)[:2]
            aggregated.extend(recent)
            log(f"✅ {source['name']} 抓到 {len(recent)} 則")
        except Exception as exc:
            log(f"❌ 無法抓取 {source['name']}：{exc}")
    aggregated.sort(key=lambda a: a.published, reverse=True)
    return aggregated

def split_sections(articles: List[Article]) -> Dict[str, List[Article]]:
    if not articles:
        return {"headlines": [], "industry": [], "highlights": []}
    return {
        "headlines": articles[:2],
        "industry": articles[2:6],
        "highlights": articles[6:8],
    }

# ---------------------------------------------------------------------------

def load_rag() -> Dict[str, Any]:
    if not RAG_DATA_FILE.exists():
        log("⚠️ 找不到 RAG 資料，略過該區塊")
        return {}
    with RAG_DATA_FILE.open("r", encoding="utf-8") as fh:
        return json.load(fh)

def render_rag_markdown(rag: Dict[str, Any]) -> str:
    if not rag:
        return ""
    lines: List[str] = ["## 🤖 RAG 資訊", "", "### 📚 最新 AI Agent 論文", ""]
    for paper in rag.get("papers", [])[:3]:
        lines.append(f"- **[{paper['title']}]({paper['url']})**  ")
        lines.append(f"  {paper.get('abstract', '').strip()}")
        lines.append("")
    lines.append("### 💻 熱門開源專案\n")
    for project in rag.get("projects", [])[:4]:
        lines.append(f"- **[{project['name']}]({project['url']})**  ")
        lines.append(f"  {project.get('description', '').strip()}")
        lines.append("")
    lines.append("### 🤗 Hugging Face 趨勢\n")
    for model in rag.get("models", [])[:2]:
        lines.append(f"- **[{model['name']}]({model['url']})**  ")
        lines.append(f"  {model.get('description', '').strip()}")
        lines.append("")
    return "\n".join(lines).strip()

def render_rag_html(rag: Dict[str, Any], today: str) -> str:
    if not rag:
        return ""

    def build(items: List[Dict[str, Any]], keys: tuple[str, str, str], limit: int) -> str:
        html_items = []
        for item in items[:limit]:
            title = escape(str(item.get(keys[0], "")))
            url = escape(str(item.get(keys[1], "")))
            desc = escape(str(item.get(keys[2], "")))
            html_items.append(f"<li><strong><a href=\"{url}\" target=\"_blank\">{title}</a></strong><p>{desc}</p></li>")
        return "".join(html_items)

    return f"""
            <section class=\"dashboard-section\">
                <h2>📚 AI Agent 研究 & RAG 資訊</h2>
                <p class=\"date-subtitle\">更新：{today}</p>
                <div class=\"news-card\">
                    <h3>最新論文</h3>
                    <ul>
                        {build(rag.get('papers', []), ('title', 'url', 'abstract'), 3)}
                    </ul>
                </div>
                <div class=\"news-card\">
                    <h3>熱門開源專案</h3>
                    <ul>
                        {build(rag.get('projects', []), ('name', 'url', 'description'), 4)}
                    </ul>
                </div>
                <div class=\"news-card\">
                    <h3>Hugging Face 趨勢</h3>
                    <ul>
                        {build(rag.get('models', []), ('name', 'url', 'description'), 2)}
                    </ul>
                </div>
            </section>
        """

# ---------------------------------------------------------------------------

def render_markdown(sections: Dict[str, List[Article]], rag: Dict[str, Any]) -> str:
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    updated = now.strftime("%Y-%m-%d %H:%M")

    parts: List[str] = [
        "# 🤖 AI 每日儀表板",
        "",
        f"## 📅 {today}",
        "",
        f"### 📰 昨日 AI 大事件 ({yesterday})",
        "",
        f"_最後更新：{updated}_",
        "",
        "---",
        "",
        "## 🔥 頭條新聞",
        "",
    ]

    headlines = sections.get("headlines", [])
    parts.extend(a.to_markdown() for a in headlines) if headlines else parts.append("_（暫無資料）_")
    parts.append("")

    parts.append("## 💼 產業動態\n")
    industry = sections.get("industry", [])
    parts.extend(a.to_markdown() for a in industry) if industry else parts.append("_（暫無資料）_")
    parts.append("")

    parts.append("## 🧠 深度觀點\n")
    highlights = sections.get("highlights", [])
    parts.extend(a.to_markdown() for a in highlights) if highlights else parts.append("_（暫無資料）_")
    parts.append("")

    rag_block = render_rag_markdown(rag)
    if rag_block:
        parts.append(rag_block)
        parts.append("")

    parts.extend([
        "---",
        "",
        "## ⚙️ 設定狀態",
        "",
        "- ✅ 儀表板自動生成",
        "- ✅ 多來源 RSS + RAG 資料整合",
        f"- 📍 位置：`{DASHBOARD_MD}`",
        "",
        "## 🔄 更新 schedule",
        "",
        "- **頻率**：每天上午 8:00",
        "- **涵蓋**：前 24~36 小時 AI 新聞 + RAG 資訊",
        "",
        "---",
        "",
        "*由小管家 🤖 自動生成*",
    ])

    return "\n".join(parts)

def render_html(sections: Dict[str, List[Article]], rag: Dict[str, Any]) -> str:
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    updated = now.strftime("%Y-%m-%d %H:%M")

    def render_list(items: List[Article]) -> str:
        if not items:
            return '<p class="empty">目前沒有資料</p>'
        return "<ul>" + "".join(article.to_html() for article in items) + "</ul>"

    rag_section = render_rag_html(rag, today)

    return f"""<!DOCTYPE html>
<html lang=\"zh-TW\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>AI 每日儀表板</title>
    <link rel=\"stylesheet\" href=\"style.css\">
    <link href=\"https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700&display=swap\" rel=\"stylesheet\">
</head>
<body>
    <div class=\"container\">
        <header>
            <h1>🤖 AI 每日儀表板</h1>
            <p class=\"subtitle\">追蹤最新 AI 發展 · 每日自動更新</p>
            <div class=\"last-updated\">最後更新：{updated}</div>
        </header>
        <main>
            <section class=\"dashboard-section\">
                <h2>📅 {today}</h2>
                <p class=\"date-subtitle\">昨日 AI 大事件</p>
                <div class=\"news-card\">
                    <h3>🔥 頭條新聞</h3>
                    {render_list(sections.get('headlines', []))}
                </div>
                <div class=\"news-card\">
                    <h3>💼 產業動態</h3>
                    {render_list(sections.get('industry', []))}
                </div>
                <div class=\"news-card\">
                    <h3>🧠 深度觀點</h3>
                    {render_list(sections.get('highlights', []))}
                </div>
            </section>
            {rag_section}
            <section class=\"automation-info\">
                <h3>⚙️ 自動化狀態</h3>
                <div class=\"status-grid\">
                    <div class=\"status-item\"><span class=\"status-icon\">✅</span>RSS 聚合</div>
                    <div class=\"status-item\"><span class=\"status-icon\">✅</span>RAG 整合</div>
                    <div class=\"status-item\"><span class=\"status-icon\">✅</span>每日 08:00 定時更新</div>
                </div>
            </section>
        </main>
        <footer>
            <p>由小管家 🤖 自動維護 • Firebird 的 AWS 雲端管家</p>
        </footer>
    </div>
</body>
</html>
"""

# ---------------------------------------------------------------------------

def main() -> None:
    log("▶️ 開始生成儀表板")
    articles = collect_news()
    if len(articles) < MIN_ARTICLES:
        log(f"⚠️ 文章數不足 ({len(articles)} < {MIN_ARTICLES})，仍使用現有資料生成")
    sections = split_sections(articles)
    rag = load_rag()

    DASHBOARD_MD.write_text(render_markdown(sections, rag), encoding="utf-8")
    log("📝 已寫入 DASHBOARD.md")

    DASHBOARD_HTML.write_text(render_html(sections, rag), encoding="utf-8")
    log("🕸️ 已寫入 index.html")

    log("✅ 儀表板更新完成")
    print("Dashboard updated successfully.")


if __name__ == "__main__":
    main()
