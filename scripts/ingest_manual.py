"""
Ableton Live 12.x マニュアルを ableton.com から取り込むスクリプト。

調査結果（2026-05-08）:
- マニュアルは章単位で固定 URL: https://www.ableton.com/en/manual/<slug>/
- バージョン番号は URL に含まれず、常に最新の Live 12.x 版が返る
- ブラウザ向けは SPA で空 HTML が返るが、Googlebot UA で fetch すると
  SSR された完全な HTML が返ってくる
- <main> タグ内に h1 (章) / h2 (節 X.Y) / h3 (小節 X.Y.Z) / p (本文) で構造化済み
- sitemap-manual.xml に EN 36 章 / JA 36 章の URL リストがある

Usage:
    python scripts/ingest_manual.py                    # ドライラン (URL一覧と一部 fetch)
    python scripts/ingest_manual.py --write            # data/manual-db.json に書き込み (EN)
    python scripts/ingest_manual.py --write --lang ja  # 日本語版を取得
    python scripts/ingest_manual.py --slug clip-view   # 特定章のみ取得して表示
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
import urllib.error
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

SITEMAP_URL = "https://www.ableton.com/sitemap-manual.xml"

# Googlebot UA でアクセスすると SSR HTML が返ってくる
UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"


def _fetch(url: str, timeout: int = 30) -> str | None:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
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


def get_manual_urls(lang: str = "en") -> list[str]:
    xml = _fetch(SITEMAP_URL)
    if not xml:
        return []
    return re.findall(rf'https://www\.ableton\.com/{lang}/manual/[^<]+', xml)


def _strip_html(s: str) -> str:
    s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'\s+', ' ', s).strip()


# 章番号と本文を区別する正規表現
# 例: "8. Clip View" / "8.1 Clip View Layout" / "8.1.1 Clip Title Bar"
_NUMBERED_HEADING = re.compile(r'^\s*(\d+(?:\.\d+){0,3})\.?\s+(.+?)\s*$')


def parse_chapter(html: str, url: str, slug: str) -> dict | None:
    m = re.search(r'<main[^>]*>(.*?)</main>', html, re.DOTALL)
    if not m:
        return None
    main = m.group(1)

    # h1 = 章タイトル
    h1_m = re.search(r'<h1[^>]*>(.*?)</h1>', main, re.DOTALL)
    if not h1_m:
        return None
    h1_text = _strip_html(h1_m.group(1))
    h1_match = _NUMBERED_HEADING.match(h1_text)
    if h1_match:
        chapter_number = h1_match.group(1)
        chapter_title = h1_match.group(2)
    else:
        chapter_number = ""
        chapter_title = h1_text

    # 全ヘッダ + 段落をドキュメント順で抽出する
    pattern = re.compile(
        r'<(h[1-3]|p)\b[^>]*>(.*?)</\1>',
        re.DOTALL | re.IGNORECASE,
    )
    items = []
    for tag, raw in pattern.findall(main):
        text = _strip_html(raw)
        if not text:
            continue
        items.append((tag.lower(), text))

    # 構造化: h1 をルート、h2 = 節、h3 = 小節
    sections: list[dict] = []
    current_section: dict | None = None
    current_subsection: dict | None = None
    intro_paragraphs: list[str] = []

    def add_paragraph(text: str) -> None:
        if current_subsection is not None:
            current_subsection["paragraphs"].append(text)
        elif current_section is not None:
            current_section["paragraphs"].append(text)
        else:
            intro_paragraphs.append(text)

    for tag, text in items:
        if tag == "h1":
            continue  # 既に取得済み
        if tag == "h2":
            hm = _NUMBERED_HEADING.match(text)
            current_section = {
                "number": hm.group(1) if hm else "",
                "title": hm.group(2) if hm else text,
                "paragraphs": [],
                "subsections": [],
            }
            current_subsection = None
            sections.append(current_section)
        elif tag == "h3":
            hm = _NUMBERED_HEADING.match(text)
            current_subsection = {
                "number": hm.group(1) if hm else "",
                "title": hm.group(2) if hm else text,
                "paragraphs": [],
            }
            if current_section is None:
                # h2 なしで h3 が出てきたら h2 をダミー作成
                current_section = {
                    "number": "",
                    "title": "",
                    "paragraphs": [],
                    "subsections": [],
                }
                sections.append(current_section)
            current_section["subsections"].append(current_subsection)
        elif tag == "p":
            # サイト共通の marketing コピーを除外する
            if any(skip in text for skip in (
                "Summit for Music Makers",
                "fundamentals of music making",
                "synthesis using a web-based",
                "Creative Strategies for Electronic Producers",
            )):
                continue
            if len(text) < 4:
                continue
            add_paragraph(text)

    return {
        "slug": slug,
        "url": url,
        "chapter_number": chapter_number,
        "title": chapter_title,
        "intro_paragraphs": intro_paragraphs,
        "sections": sections,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", default="en", choices=["en", "ja", "de"])
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--slug", help="特定章のみ取得")
    parser.add_argument("--sleep", type=float, default=0.6, help="連続 fetch 間の秒数")
    args = parser.parse_args()

    if args.slug:
        url = f"https://www.ableton.com/{args.lang}/manual/{args.slug}/"
        html = _fetch(url)
        if not html:
            return 1
        chapter = parse_chapter(html, url, args.slug)
        if chapter is None:
            print("[error] parse failed", file=sys.stderr)
            return 1
        print(json.dumps(chapter, ensure_ascii=False, indent=2)[:3000])
        print(f"\n[summary] sections: {len(chapter['sections'])}, "
              f"intro paragraphs: {len(chapter['intro_paragraphs'])}")
        return 0

    urls = get_manual_urls(args.lang)
    print(f"[fetch sitemap] {len(urls)} chapters for lang={args.lang}")
    if not urls:
        return 1

    db: dict[str, dict] = {}
    for i, url in enumerate(urls, 1):
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        print(f"  [{i}/{len(urls)}] {slug}")
        html = _fetch(url)
        if not html:
            continue
        chapter = parse_chapter(html, url, slug)
        if chapter is None:
            print(f"    [warn] parse failed: {slug}")
            continue
        db[slug] = chapter
        time.sleep(args.sleep)

    sections_total = sum(len(c["sections"]) for c in db.values())
    paragraphs_total = sum(
        len(c["intro_paragraphs"])
        + sum(len(s["paragraphs"]) for s in c["sections"])
        + sum(len(ss["paragraphs"]) for s in c["sections"] for ss in s["subsections"])
        for c in db.values()
    )
    print(f"[summary] chapters: {len(db)} / sections: {sections_total} / "
          f"paragraphs: {paragraphs_total}")

    if args.write:
        out = DATA / f"manual-db{'' if args.lang == 'en' else '-' + args.lang}.json"
        out.write_text(
            json.dumps(db, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"[wrote] {out}")
    else:
        print("[dry-run] --write を付けると JSON を保存")

    return 0


if __name__ == "__main__":
    sys.exit(main())
