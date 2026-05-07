"""
Live Reference Manual のデバイスインデックスからデバイス一覧を抽出する
ingest スクリプト（Phase 2: スケルトン）。

参照: https://www.ableton.com/en/manual/live-12/

注: 完全な ingest は Phase 2.5 で実装予定。
このスクリプトは TOC を取得して URL とデバイス名候補を列挙するまで。
詳細パラメータ抽出は Manual の各サブページを再取得する必要がある。

Usage:
    python scripts/ingest_devices.py             # TOC を表示
    python scripts/ingest_devices.py --write     # data/device-index.json を新規作成
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX_OUT = ROOT / "data" / "device-index.json"

INSTRUMENTS_TOC = "https://www.ableton.com/en/manual/live-instrument-reference/"
EFFECTS_TOC = "https://www.ableton.com/en/manual/live-audio-effect-reference/"
# TODO(Phase 2.5): Live 12 のマニュアル URL は SPA 構造に変わって TOC HTML から
# 直接 a 要素を抽出できない。Next.js __NEXT_DATA__ パース or sitemap.xml アプローチに切替予定。


def _fetch(url: str) -> str | None:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AbletonRefMCP/0.1",
            "Accept": "text/html",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[error] fetch failed: {url} -> {e}", file=sys.stderr)
        return None


_LINK_PATTERN = re.compile(
    r'<a[^>]+href="(/[a-z]{2}/manual/[^"#]+)"[^>]*>([^<]+)</a>',
    re.IGNORECASE,
)


def extract_device_links(html: str, base: str = "https://www.ableton.com") -> list[dict]:
    """TOC ページからデバイス見出し候補を抽出する。"""
    seen = set()
    out = []
    for m in _LINK_PATTERN.finditer(html):
        path, title = m.group(1), m.group(2).strip()
        if not title or len(title) < 3:
            continue
        url = base + path
        if url in seen:
            continue
        seen.add(url)
        out.append({"title": title, "url": url})
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="data/device-index.json に書き込む")
    args = parser.parse_args()

    result = {"instruments": [], "effects": []}

    for category, url in (("instruments", INSTRUMENTS_TOC), ("effects", EFFECTS_TOC)):
        print(f"[fetch] {category}: {url}")
        html = _fetch(url)
        if not html:
            continue
        links = extract_device_links(html)
        # ノイズ除去: 'manual/live-12' のような index 自身は除外
        links = [l for l in links if "instrument" in l["url"] or "effect" in l["url"] or "device" in l["url"]]
        print(f"  -> {len(links)} links")
        result[category] = links[:200]

    if args.write:
        INDEX_OUT.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"[wrote] {INDEX_OUT}")
    else:
        print("[dry-run] --write を付けると data/device-index.json を作成")
        for cat, links in result.items():
            print(f"  {cat}: {len(links)} entries")
            for l in links[:5]:
                print(f"    - {l['title']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
