"""
help.ableton.com (Zendesk Help Center) から記事を取得する ingest スクリプト
（Phase 2: スケルトン）。

Help Center は Zendesk なので公開 API が利用可能:
    GET https://help.ableton.com/api/v2/help_center/categories.json
    GET https://help.ableton.com/api/v2/help_center/sections.json
    GET https://help.ableton.com/api/v2/help_center/articles.json?per_page=100

ただし WebFetch / cURL では一部 User-Agent や Cookie が要求されることがある。
本スクリプトは最初に categories を取得し、Move 関連カテゴリの section と article 一覧を
JSON ダンプするところまで実装。本文の構造化抽出は Phase 2.5 で。

Usage:
    python scripts/ingest_help_center.py                 # ドライラン
    python scripts/ingest_help_center.py --write         # data/help-center-index.json を作成
    python scripts/ingest_help_center.py --search Move   # タイトルに 'Move' を含む article を表示
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX_OUT = ROOT / "data" / "help-center-index.json"

API_BASE = "https://help.ableton.com/api/v2/help_center"


def _api(path: str, params: dict | None = None) -> dict | None:
    url = f"{API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; AbletonRefMCP/0.1)",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[error] api failed: {url} -> {e}", file=sys.stderr)
        return None


def fetch_articles(per_page: int = 100, max_pages: int = 5) -> list[dict]:
    out = []
    for page in range(1, max_pages + 1):
        data = _api("/articles.json", {"per_page": per_page, "page": page})
        if not data:
            break
        articles = data.get("articles", [])
        if not articles:
            break
        out.extend(articles)
        if not data.get("next_page"):
            break
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--search", help="title フィルタ")
    parser.add_argument("--max-pages", type=int, default=5)
    args = parser.parse_args()

    print(f"[fetch] categories")
    cats = _api("/categories.json")
    if cats is None:
        print("[error] Help Center API への接続に失敗しました。", file=sys.stderr)
        return 1
    categories = cats.get("categories", [])
    print(f"  -> {len(categories)} categories")
    for c in categories[:10]:
        print(f"    - id={c['id']}: {c['name']}")

    print(f"[fetch] articles (max_pages={args.max_pages})")
    articles = fetch_articles(max_pages=args.max_pages)
    print(f"  -> {len(articles)} articles")

    if args.search:
        q = args.search.lower()
        filtered = [a for a in articles if q in (a.get("title") or "").lower()]
        print(f"[search '{args.search}'] {len(filtered)} hit")
        for a in filtered[:20]:
            print(f"  - {a.get('title')} ({a.get('html_url')})")

    if args.write:
        index = {
            "categories": [{"id": c["id"], "name": c["name"]} for c in categories],
            "articles": [
                {
                    "id": a["id"],
                    "title": a.get("title"),
                    "url": a.get("html_url"),
                    "section_id": a.get("section_id"),
                    "updated_at": a.get("updated_at"),
                }
                for a in articles
            ],
        }
        INDEX_OUT.write_text(
            json.dumps(index, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"[wrote] {INDEX_OUT}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
