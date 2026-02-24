#!/usr/bin/env python3
"""AI Daily Dashboard generator with Traditional Chinese summaries and history archive."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
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
HISTORY_DIR = WORKSPACE / "history"
TIMELINE_FILE = WORKSPACE / "timeline.md"
TIMELINE_JSON = WORKSPACE / "timeline.json"
TIMELINE_UI_LIMIT = 7
TIMELINE_STORE_LIMIT = 90

ATOM_NS = "{http://www.w3.org/2005/Atom}"
USER_AGENT = "Mozilla/5.0 (AI-Dashboard-Aggregator)"
TRANSLATE_ENDPOINT = "https://translate.googleapis.com/translate_a/single"
LOOKBACK_HOURS = 36
MIN_ARTICLES = 6
SUMMARY_LIMIT = 400

RSS_SOURCES = [
    {"name": "VentureBeat · AI", "url": "https://venturebeat.com/category/ai/feed/"},
    {"name": "TechCrunch · Artificial Intelligence", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "MIT Technology Review · AI", "url": "https://www.technologyreview.com/feed/?category_name=artificial-intelligence"},
    {"name": "ScienceDaily · AI", "url": "https://www.sciencedaily.com/rss/computers_math/artificial_intelligence.xml"},
    {"name": "AI Trends", "url": "https://www.aitrends.com/feed/"},
]


# ---------------------------------------------------------------------------
# Helpers
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
        translated = "".join(segment[0] for segment in data[0] if segment[0])
        return translated.strip()
    except Exception as exc:  # pragma: no cover
        log(f"⚠️ 翻譯失敗（改用原文）：{exc}")
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
# Aggregation
# ---------------------------------------------------------------------------

def parse_feed(data: bytes, source: str) -> List[Article]:
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
        summary = translate_to_traditional(strip_html(summary_raw))

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
# RAG handling
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


def _build_list(items: List[Dict[str, Any]], keys: tuple[str, str, str], limit: int) -> str:
    entries = []
    for item in items[:limit]:
        title = escape(str(item.get(keys[0], "")))
        url = escape(str(item.get(keys[1], "")))
        desc = escape(str(item.get(keys[2], "")))
        entries.append(f"<li><strong><a href=\"{url}\" target=\"_blank\">{title}</a></strong><p>{desc}</p></li>")
    return "".join(entries)


def render_rag_html(rag: Dict[str, Any], today: str) -> str:
    if not rag:
        return ""
    return f"""
            <section class=\"dashboard-section\">
                <h2>📚 AI Agent 研究 & RAG 資訊</h2>
                <p class=\"date-subtitle\">更新：{today}</p>
                <div class=\"news-card\">
                    <h3>最新論文</h3>
                    <ul>
                        {_build_list(rag.get('papers', []), ('title', 'url', 'abstract'), 3)}
                    </ul>
                </div>
                <div class=\"news-card\">
                    <h3>熱門開源專案</h3>
                    <ul>
                        {_build_list(rag.get('projects', []), ('name', 'url', 'description'), 4)}
                    </ul>
                </div>
                <div class=\"news-card\">
                    <h3>Hugging Face 趨勢</h3>
                    <ul>
                        {_build_list(rag.get('models', []), ('name', 'url', 'description'), 2)}
                    </ul>
                </div>
            </section>
        """
def render_timeline_html(entries: List[Dict[str, Any]]) -> str:
    if not entries:
        return ""
    cards = []
    for entry in entries:
        date = escape(entry.get("date", ""))
        updated = escape(entry.get("updated", ""))
        link = escape(entry.get("link", "")) or "#"
        def join(items):
            return " / ".join(items) if items else "（無資料）"
        cards.append(f"""
                <div class="timeline-card">
                    <div class="timeline-date">{date}</div>
                    <div class="timeline-updated">更新：{updated}</div>
                    <ul>
                        <li><strong>🔥 頭條</strong><span>{escape(join(entry.get('headlines') or []))}</span></li>
                        <li><strong>💼 產業</strong><span>{escape(join(entry.get('industry') or []))}</span></li>
                        <li><strong>🧠 深度</strong><span>{escape(join(entry.get('highlights') or []))}</span></li>
                    </ul>
                    <a class="timeline-link" href="{link}" target="_blank">查看完整內容 →</a>
                </div>
        """)
    cards_html = "".join(cards)
    return f"""
            <section class="timeline-section">
                <h2>🗂 歷史時間軸概觀</h2>
                <p class="date-subtitle">最近 {len(entries)} 天</p>
                <div class="timeline-cards">
                    {cards_html}
                </div>
            </section>
        """





# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_markdown(sections: Dict[str, List[Article]], rag: Dict[str, Any], today: str, yesterday: str, updated: str) -> str:
    lines: List[str] = [
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
    if headlines:
        lines.extend(article.to_markdown() for article in headlines)
    else:
        lines.append("_（暫無資料）_")
    lines.append("")

    lines.append("## 💼 產業動態\n")
    industry = sections.get("industry", [])
    if industry:
        lines.extend(article.to_markdown() for article in industry)
    else:
        lines.append("_（暫無資料）_")
    lines.append("")

    lines.append("## 🧠 深度觀點\n")
    highlights = sections.get("highlights", [])
    if highlights:
        lines.extend(article.to_markdown() for article in highlights)
    else:
        lines.append("_（暫無資料）_")
    lines.append("")

    rag_block = render_rag_markdown(rag)
    if rag_block:
        lines.append(rag_block)
        lines.append("")

    lines.extend([
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

    return "\n".join(lines)


def render_html(sections: Dict[str, List[Article]], rag: Dict[str, Any], today: str, updated: str, timeline_entries: List[Dict[str, Any]]) -> str:
    def render_list(items: List[Article]) -> str:
        if not items:
            return '<p class="empty">目前沒有資料</p>'
        return "<ul>" + "".join(article.to_html() for article in items) + "</ul>"

    history_link = f"history/{today}.md"
    rag_section = render_rag_html(rag, today)
    timeline_section = render_timeline_html(timeline_entries)

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
            <div class=\"quick-links\">
                <a href=\"{history_link}\" target=\"_blank\">🗂 今日完整內容</a>
                <a href=\"timeline.md\" target=\"_blank\">📜 歷史時間軸</a>
            </div>
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
            {timeline_section}
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
# History & timeline helpers
# ---------------------------------------------------------------------------

def save_history(markdown: str, date: str) -> Path:
    HISTORY_DIR.mkdir(exist_ok=True)
    path = HISTORY_DIR / f"{date}.md"
    path.write_text(markdown, encoding="utf-8")
    log(f"🗂️ 歷史儀表板已保存：{path}")
    return path





def update_timeline(date: str, updated: str, sections: Dict[str, List[Article]]) -> List[Dict[str, Any]]:
    def collect_titles(key: str, limit: int = 2) -> List[str]:
        return [article.title for article in sections.get(key, [])[:limit]]

    def join_titles(items: List[str]) -> str:
        return " / ".join(items) if items else "（無資料）"

    link = f"history/{date}.md"
    entry_lines = [
        f"## {date}",
        f"- 🕒 更新時間：{updated}",
        f"- 🔥 頭條：{join_titles(collect_titles('headlines'))}",
        f"- 💼 產業：{join_titles(collect_titles('industry'))}",
        f"- 🧠 深度：{join_titles(collect_titles('highlights'))}",
        f"- 📄 [完整內容]({link})",
        "",
    ]
    entry = "\n".join(entry_lines)

    if TIMELINE_FILE.exists():
        existing = TIMELINE_FILE.read_text(encoding="utf-8")
    else:
        existing = "# AI 儀表板時間軸\n\n"

    if not existing.startswith("# AI 儀表板時間軸"):
        header = "# AI 儀表板時間軸\n\n"
        body = existing.strip()
    else:
        header, _, body = existing.partition("\n\n")
        if not header:
            header = "# AI 儀表板時間軸"

    pattern = re.compile(rf"## {re.escape(date)}.*?(?=\n## |\Z)", re.S)
    body = re.sub(pattern, "", body).strip()

    new_body = entry + ("\n" + body if body else "")
    TIMELINE_FILE.write_text(header + "\n\n" + new_body.strip() + "\n", encoding="utf-8")
    log("🧭 timeline.md 已更新")

    entry_data = {
        "date": date,
        "updated": updated,
        "headlines": collect_titles('headlines'),
        "industry": collect_titles('industry'),
        "highlights": collect_titles('highlights'),
        "link": link,
    }
    return _update_timeline_json(entry_data)



def _load_timeline_json() -> List[Dict[str, Any]]:
    if TIMELINE_JSON.exists():
        try:
            with TIMELINE_JSON.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except json.JSONDecodeError:
            return []
    return []


def _update_timeline_json(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = [item for item in _load_timeline_json() if item.get("date") != entry.get("date")]
    data.insert(0, entry)
    if len(data) > TIMELINE_STORE_LIMIT:
        data = data[:TIMELINE_STORE_LIMIT]
    TIMELINE_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data[:TIMELINE_UI_LIMIT]


def load_timeline_entries(limit: int = TIMELINE_UI_LIMIT) -> List[Dict[str, Any]]:
    data = _load_timeline_json()
    return data[:limit] if limit else data



# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    log("▶️ 開始生成儀表板")
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    updated = now.strftime("%Y-%m-%d %H:%M")

    articles = collect_news()
    if len(articles) < MIN_ARTICLES:
        log(f"⚠️ 文章數不足 ({len(articles)} < {MIN_ARTICLES})，仍使用現有資料生成")
    sections = split_sections(articles)
    rag = load_rag()

    markdown = render_markdown(sections, rag, today, yesterday, updated)
    DASHBOARD_MD.write_text(markdown, encoding="utf-8")
    log("📝 已寫入 DASHBOARD.md")

    save_history(markdown, today)
    timeline_entries = update_timeline(today, updated, sections)
    if not timeline_entries:
        timeline_entries = load_timeline_entries()

    html = render_html(sections, rag, today, updated, timeline_entries)
    DASHBOARD_HTML.write_text(html, encoding="utf-8")
    log("🕸️ 已寫入 index.html")

    log("✅ 儀表板更新完成")
    print("Dashboard updated successfully.")


if __name__ == "__main__":
    main()
