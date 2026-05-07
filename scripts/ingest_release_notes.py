"""
ableton.com のリリースノートページから全バージョンを抽出して
data/release-notes-db.json に統合する ingest スクリプト。

Usage:
    python scripts/ingest_release_notes.py            # ドライラン (差分のみ表示)
    python scripts/ingest_release_notes.py --write    # 実際に JSON を上書き
    python scripts/ingest_release_notes.py --product move

対応製品:
    live (https://www.ableton.com/en/release-notes/live-12/)
    move (https://www.ableton.com/en/release-notes/move-1/)
    note (https://www.ableton.com/en/release-notes/note/)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
import urllib.error
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "release-notes-db.json"

PRODUCT_URLS = {
    "live": "https://www.ableton.com/en/release-notes/live-12/",
    "move": "https://www.ableton.com/en/release-notes/move-1/",
    "note": "https://www.ableton.com/en/release-notes/note/",
}


def _fetch(url: str, timeout: int = 15) -> str | None:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AbletonRefMCP/0.1 (+https://github.com/dsgarage/AbletonRefMCP_Dev)",
            "Accept": "text/html",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"[error] fetch failed: {url} -> {e}", file=sys.stderr)
        return None


_VERSION_H2 = re.compile(
    r'<h2[^>]*>\s*(?:Live\s+|Move\s+|Note\s+)?(\d+\.\d+(?:\.\d+)?[a-z]?)\s*'
    r'(?:\(([^)]*)\))?\s*</h2>',
    re.IGNORECASE,
)


class _SectionExtractor(HTMLParser):
    """h2 で section を区切り、各 section 内の text を集める。"""

    def __init__(self):
        super().__init__()
        self.sections: list[dict] = []
        self._current: dict | None = None
        self._capture_h2 = False
        self._capture_h3 = False
        self._capture_li = False
        self._capture_p = False
        self._buf: list[str] = []
        self._skip = False

    def _flush(self, target_key: str) -> None:
        text = "".join(self._buf).strip()
        self._buf = []
        if text and self._current is not None:
            self._current.setdefault(target_key, []).append(text)

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer"):
            self._skip = True
            return
        if tag == "h2":
            if self._current:
                self.sections.append(self._current)
            self._current = {"h2_raw": "", "h3": [], "li": [], "p": []}
            self._capture_h2 = True
        elif tag == "h3":
            self._capture_h3 = True
        elif tag == "li":
            self._capture_li = True
        elif tag == "p":
            self._capture_p = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer"):
            self._skip = False
            return
        if tag == "h2" and self._capture_h2:
            self._current["h2_raw"] = "".join(self._buf).strip()
            self._buf = []
            self._capture_h2 = False
        elif tag == "h3" and self._capture_h3:
            self._flush("h3")
            self._capture_h3 = False
        elif tag == "li" and self._capture_li:
            self._flush("li")
            self._capture_li = False
        elif tag == "p" and self._capture_p:
            self._flush("p")
            self._capture_p = False

    def handle_data(self, data):
        if self._skip:
            return
        if self._capture_h2 or self._capture_h3 or self._capture_li or self._capture_p:
            self._buf.append(data)

    def close(self):
        super().close()
        if self._current:
            self.sections.append(self._current)


def parse_release_notes(html: str, product: str) -> list[dict]:
    extractor = _SectionExtractor()
    extractor.feed(html)
    extractor.close()

    out = []
    for sec in extractor.sections:
        h2 = sec.get("h2_raw", "").strip()
        m = re.match(r'(?:Live\s+|Move\s+|Note\s+)?(\d+\.\d+(?:\.\d+)?[a-z]?)', h2, re.IGNORECASE)
        if not m:
            continue
        version = m.group(1)
        highlights = sec.get("h3", []) + sec.get("li", [])
        # 重複除去・空除去・短すぎる項目除外
        seen = set()
        cleaned = []
        for h in highlights:
            h = re.sub(r'\s+', ' ', h).strip()
            if len(h) < 4 or h in seen:
                continue
            seen.add(h)
            cleaned.append(h)
        out.append({
            "product": product,
            "version": version,
            "release_date": "",
            "channel": "stable",
            "title_ja": f"{product.title()} {version}",
            "highlights_ja": cleaned[:30],
            "url": PRODUCT_URLS[product],
        })
    return out


def merge(existing: list[dict], new_entries: list[dict]) -> tuple[list[dict], list[dict]]:
    """既存 DB と新規取得をマージ。同 product+version は既存を残し新規 highlights を補完。
    戻り値: (新しい DB, 新規追加されたエントリのリスト)
    """
    by_key = {(e["product"], e["version"]): e for e in existing}
    added: list[dict] = []
    for n in new_entries:
        key = (n["product"], n["version"])
        if key not in by_key:
            by_key[key] = n
            added.append(n)
        else:
            # 既存に highlights_ja_extra として追加（既存の手書き翻訳は壊さない）
            existing_entry = by_key[key]
            existing_highlights = set(existing_entry.get("highlights_ja", []))
            extras = [h for h in n.get("highlights_ja", []) if h not in existing_highlights]
            if extras:
                existing_entry.setdefault("highlights_en_ingested", []).extend(extras)

    merged = sorted(by_key.values(), key=lambda e: (e.get("product", ""), e.get("version", "")), reverse=True)
    return merged, added


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", choices=list(PRODUCT_URLS.keys()) + ["all"], default="all")
    parser.add_argument("--write", action="store_true", help="JSON を実書き込みする")
    args = parser.parse_args()

    products = list(PRODUCT_URLS.keys()) if args.product == "all" else [args.product]

    existing = json.loads(DB_PATH.read_text(encoding="utf-8"))
    new_total: list[dict] = []
    for prod in products:
        url = PRODUCT_URLS[prod]
        print(f"[fetch] {prod}: {url}")
        html = _fetch(url)
        if not html:
            continue
        parsed = parse_release_notes(html, prod)
        print(f"  -> parsed {len(parsed)} versions")
        new_total.extend(parsed)

    merged, added = merge(existing, new_total)
    print(f"[summary] new entries: {len(added)} / total in DB: {len(merged)}")
    for a in added:
        print(f"  + {a['product']} {a['version']} ({len(a.get('highlights_ja', []))} hl)")

    if args.write:
        DB_PATH.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"[wrote] {DB_PATH}")
    else:
        print("[dry-run] --write を付けると JSON を上書き")

    return 0


if __name__ == "__main__":
    sys.exit(main())
