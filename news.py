"""
Ableton 公式サイト fetch モジュール (Phase 1: minimal HTML scraping)
ableton.com/blog や release-notes ページから最新記事タイトル・URL を抽出する。
Phase 2 で Next.js __NEXT_DATA__ 解析や Help Center 対応を強化予定。
"""

import re
import urllib.request
import urllib.error
import json
from html.parser import HTMLParser
from datetime import datetime


class SimpleTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "header", "footer"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "header", "footer"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            stripped = data.strip()
            if stripped:
                self.text_parts.append(stripped)

    def get_text(self) -> str:
        return "\n".join(self.text_parts)


def _strip_html(html_str) -> str:
    if not html_str:
        return ""
    if not isinstance(html_str, str):
        return str(html_str)
    extractor = SimpleTextExtractor()
    extractor.feed(html_str)
    return extractor.get_text()


def _fetch_url(url: str, timeout: int = 10) -> str | None:
    headers = {
        "User-Agent": "AbletonRefMCP/0.1 (+https://github.com/dsgarage/AbletonRefMCP_Dev)",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def _extract_next_data(html: str) -> dict | None:
    match = re.search(r'<script\s+id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


_BLOG_PATTERN = re.compile(
    r'<a[^>]+href="(/[a-z]{2}/blog/[^"#]+)"[^>]*>([^<]+)</a>',
    re.IGNORECASE,
)


def fetch_official_news(max_results: int = 5) -> dict:
    """ableton.com/blog から最新記事を取得 (Phase 1: HTML から a タグ抽出)。"""
    base = "https://www.ableton.com"
    html = _fetch_url(f"{base}/en/blog/")
    if not html:
        return {
            "error": "ableton.com/blog への接続に失敗しました。",
            "source": f"{base}/en/blog/",
        }

    seen = set()
    articles = []
    for m in _BLOG_PATTERN.finditer(html):
        path, title = m.group(1), m.group(2).strip()
        if not title or len(title) < 4:
            continue
        url = f"{base}{path}"
        if url in seen:
            continue
        seen.add(url)
        articles.append({"title": title, "url": url})
        if len(articles) >= max_results:
            break

    return {
        "source": f"{base}/en/blog/",
        "article_count": len(articles),
        "articles": articles,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "note": "Phase 1: HTML 抽出のみ。詳細は ableton.read_article でURL指定。",
    }


_RELEASE_NOTE_URLS = {
    "live": "https://www.ableton.com/en/release-notes/live-12/",
    "move": "https://www.ableton.com/en/release-notes/move-1/",
    "note": "https://www.ableton.com/en/release-notes/note/",
}


_VERSION_HEADING_PATTERN = re.compile(
    r'<h[2-4][^>]*>\s*([0-9][0-9.]*[a-z]*)\s*(?:\([^)]*\))?\s*</h[2-4]>',
    re.IGNORECASE,
)


def fetch_release_notes_page(product: str = "live", max_results: int = 10) -> dict:
    url = _RELEASE_NOTE_URLS.get(product.lower())
    if not url:
        return {
            "error": f"未対応の製品: {product}",
            "supported": list(_RELEASE_NOTE_URLS.keys()),
        }

    html = _fetch_url(url)
    if not html:
        return {"error": f"{url} への接続に失敗しました。", "source": url}

    versions = []
    for m in _VERSION_HEADING_PATTERN.finditer(html):
        v = m.group(1).strip(".")
        if v and v not in versions:
            versions.append(v)
        if len(versions) >= max_results:
            break

    return {
        "source": url,
        "product": product,
        "version_count": len(versions),
        "versions_found": versions,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "note": "Phase 1: バージョン番号のみ抽出。詳細はローカル release-notes-db.json (ableton.release_notes) を使用。",
    }


def fetch_article_detail(url: str) -> dict:
    if "ableton.com" not in url and "help.ableton.com" not in url:
        return {"error": "ableton.com / help.ableton.com の URL のみ対応。"}

    html = _fetch_url(url)
    if not html:
        return {"error": f"記事の取得に失敗しました: {url}"}

    next_data = _extract_next_data(html)
    if next_data:
        page_props = next_data.get("props", {}).get("pageProps", {})
        post = page_props.get("post") or page_props.get("article") or {}
        if isinstance(post, dict) and post.get("title"):
            content_text = _strip_html(post.get("content", ""))
            return {
                "url": url,
                "title": post.get("title", ""),
                "date": post.get("created_at") or post.get("published_at", ""),
                "content": content_text[:3000],
                "fetched_at": datetime.utcnow().isoformat() + "Z",
            }

    extractor = SimpleTextExtractor()
    extractor.feed(html)
    text = extractor.get_text()
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
    title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else ""
    content_lines = [l for l in text.split("\n") if len(l) > 30]

    return {
        "url": url,
        "title": title,
        "content": "\n".join(content_lines[:30])[:3000],
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "note": "Phase 1: HTML テキスト抽出のフォールバック。",
    }
