"""
Ableton リファレンス検索エンジン
device / hardware / release-notes / LOM / glossary / pattern を JSON-DB から検索する。
スコアリング: (名前一致×10) + (タグ一致×5) + (説明一致×3) + (カテゴリ一致×8) + (関連×2)
"""

import json
import re
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "data"

_device_db: dict | None = None
_hardware_db: dict | None = None
_release_notes_db: list | None = None
_lom_db: dict | None = None
_glossary_db: dict | None = None
_pattern_db: list | None = None
_manual_db: dict | None = None


def _load_json(filename: str) -> Any:
    return json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))


def _get_device_db() -> dict:
    global _device_db
    if _device_db is None:
        _device_db = _load_json("device-db.json")
    return _device_db


def _get_hardware_db() -> dict:
    global _hardware_db
    if _hardware_db is None:
        _hardware_db = _load_json("hardware-db.json")
    return _hardware_db


def _get_release_notes_db() -> list:
    global _release_notes_db
    if _release_notes_db is None:
        _release_notes_db = _load_json("release-notes-db.json")
    return _release_notes_db


def _get_lom_db() -> dict:
    global _lom_db
    if _lom_db is None:
        _lom_db = _load_json("lom-db.json")
    return _lom_db


def _get_glossary_db() -> dict:
    global _glossary_db
    if _glossary_db is None:
        _glossary_db = _load_json("glossary-db.json")
    return _glossary_db


def _get_pattern_db() -> list:
    global _pattern_db
    if _pattern_db is None:
        _pattern_db = _load_json("pattern-db.json")
    return _pattern_db


def _get_manual_db() -> dict:
    global _manual_db
    if _manual_db is None:
        try:
            _manual_db = _load_json("manual-db.json")
        except FileNotFoundError:
            _manual_db = {}
    return _manual_db


def _text_score(text: str | None, query: str) -> int:
    if not text:
        return 0
    lower = text.lower()
    if lower == query:
        return 10
    if lower.startswith(query):
        return 7
    if query in lower:
        return 3
    return 0


def _array_score(arr: list | None, query: str) -> int:
    if not arr or not isinstance(arr, list):
        return 0
    return max((_text_score(item, query) for item in arr if isinstance(item, str)), default=0)


def _tokenize(query: str) -> list[str]:
    return [t for t in re.split(r'[\s　,、]+', query.lower()) if t]


# --- Devices ---


def search_devices(
    query: str,
    type: str | None = None,
    available_on: str | None = None,
    max_results: int = 10,
) -> dict:
    """Live / Move / Push のデバイスを検索"""
    db = _get_device_db()
    tokens = _tokenize(query)
    results = []

    for name, dev in db.items():
        if type and dev.get("type") != type:
            continue
        if available_on and available_on not in (dev.get("available_on") or []):
            continue

        score = 0
        for token in tokens:
            score += _text_score(name, token) * 10
            score += _text_score(dev.get("category"), token) * 8
            score += _array_score(dev.get("tags"), token) * 5
            score += _array_score(dev.get("tags_ja"), token) * 5
            score += _text_score(dev.get("description"), token) * 3
            score += _text_score(dev.get("description_ja"), token) * 3
            score += _array_score(dev.get("related"), token) * 2

        if score > 0:
            results.append({"name": name, "score": score, **dev})

    results.sort(key=lambda x: x["score"], reverse=True)
    limited = results[:max_results]

    return {
        "query": query,
        "type": type or "all",
        "available_on": available_on or "all",
        "result_count": len(limited),
        "total_matches": len(results),
        "results": limited,
    }


def get_device_detail(name: str) -> dict | None:
    db = _get_device_db()
    if name in db:
        return {"name": name, **db[name]}
    lower = name.lower()
    for key, dev in db.items():
        if key.lower() == lower:
            return {"name": key, **dev}
    return None


def compare_devices_detail(devices: list[str]) -> dict:
    if len(devices) < 2:
        return {"error": "比較には2つ以上のデバイス名が必要です。"}
    if len(devices) > 5:
        return {"error": "比較は最大5つまでです。"}

    found = []
    not_found = []
    for n in devices:
        d = get_device_detail(n)
        if d:
            found.append(d)
        else:
            not_found.append(n)

    if len(found) < 2:
        return {"error": "比較に必要な2つ以上のデバイスが見つかりません。", "not_found": not_found}

    types = {d.get("type") for d in found}
    categories = {d.get("category") for d in found}
    available = {tuple(d.get("available_on") or []) for d in found}

    comparison = {"devices": found, "shared_traits": [], "differences": []}
    if len(types) == 1:
        comparison["shared_traits"].append(f"同じタイプ: {types.pop()}")
    if len(categories) == 1:
        comparison["shared_traits"].append(f"同じカテゴリ: {categories.pop()}")
    if len(available) == 1:
        comparison["shared_traits"].append(f"同じ製品で利用可: {available.pop()}")

    if len(types) > 1:
        comparison["differences"].append({"aspect": "タイプ", "values": {d["name"]: d.get("type") for d in found}})
    if len(categories) > 1:
        comparison["differences"].append({"aspect": "カテゴリ", "values": {d["name"]: d.get("category") for d in found}})

    out = {"comparison": comparison, "device_count": len(found)}
    if not_found:
        out["not_found"] = not_found
    return out


# --- Hardware ---


def search_hardware(query: str, product: str | None = None, max_results: int = 5) -> dict:
    db = _get_hardware_db()
    tokens = _tokenize(query)
    results = []

    for prod_id, prod in db.items():
        if product and product != prod_id:
            continue

        score = 0
        for token in tokens:
            score += _text_score(prod_id, token) * 10
            score += _text_score(prod.get("name"), token) * 10
            score += _text_score(prod.get("category"), token) * 6
            score += _array_score(prod.get("tags"), token) * 5
            score += _array_score(prod.get("tags_ja"), token) * 5
            score += _text_score(prod.get("description"), token) * 3
            score += _text_score(prod.get("description_ja"), token) * 3
            for v_id, v in (prod.get("versions") or {}).items():
                score += _text_score(v.get("notes_ja"), token) * 2

        if score > 0 or product:
            results.append({"product": prod_id, "score": score, **prod})

    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    limited = results[:max_results]

    return {
        "query": query,
        "product": product or "all",
        "result_count": len(limited),
        "total_matches": len(results),
        "results": limited,
    }


def get_hardware_detail(product: str, version: str | None = None) -> dict | None:
    db = _get_hardware_db()
    prod = db.get(product) or db.get(product.lower())
    if not prod:
        return None
    out = {"product": product, **prod}
    if version:
        v = (prod.get("versions") or {}).get(version)
        if v:
            out["selected_version"] = {"version": version, **v}
        else:
            out["selected_version"] = None
            out["version_not_found"] = version
    return out


# --- Release notes ---


def search_release_notes(
    query: str | None = None,
    product: str | None = None,
    max_results: int = 10,
) -> dict:
    db = _get_release_notes_db()
    tokens = _tokenize(query) if query else []
    results = []

    for entry in db:
        if product and entry.get("product") != product:
            continue

        score = 0
        if tokens:
            for token in tokens:
                score += _text_score(entry.get("title_ja"), token) * 6
                score += _text_score(entry.get("version"), token) * 8
                for h in entry.get("highlights_ja") or []:
                    score += _text_score(h, token) * 3
            if score == 0:
                continue
        results.append({**entry, "score": score})

    if tokens:
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
    else:
        results.sort(key=lambda x: x.get("release_date", ""), reverse=True)

    limited = results[:max_results]
    return {
        "query": query or "",
        "product": product or "all",
        "result_count": len(limited),
        "total_matches": len(results),
        "results": limited,
    }


# --- LOM ---


def lom_search(query: str, max_results: int = 10) -> dict:
    db = _get_lom_db()
    tokens = _tokenize(query)
    results = []

    for name, cls in db.items():
        score = 0
        for token in tokens:
            score += _text_score(name, token) * 10
            score += _array_score(cls.get("aliases"), token) * 8
            score += _array_score(cls.get("tags"), token) * 5
            score += _array_score(cls.get("tags_ja"), token) * 5
            score += _text_score(cls.get("description"), token) * 3
            score += _text_score(cls.get("description_ja"), token) * 3
            for prop in cls.get("key_properties") or []:
                score += _text_score(prop.get("name"), token) * 4
            for m in cls.get("key_methods") or []:
                score += _text_score(m, token) * 4

        if score > 0:
            results.append({"name": name, "score": score, **cls})

    results.sort(key=lambda x: x["score"], reverse=True)
    limited = results[:max_results]

    return {
        "query": query,
        "result_count": len(limited),
        "total_matches": len(results),
        "results": limited,
    }


def lom_get(name: str) -> dict | None:
    db = _get_lom_db()
    if name in db:
        return {"name": name, **db[name]}
    lower = name.lower()
    for key, cls in db.items():
        if key.lower() == lower:
            return {"name": key, **cls}
        if lower in [a.lower() for a in (cls.get("aliases") or [])]:
            return {"name": key, **cls}
    return None


# --- Glossary ---


def lookup_glossary(term: str) -> dict | None:
    db = _get_glossary_db()
    lower = term.lower().replace(" ", "_")

    if lower in db:
        return {"term": lower, **db[lower]}

    for key, entry in db.items():
        if entry.get("ja", "").lower() == term.lower():
            return {"term": key, **entry}
        if term.lower() in [a.lower() for a in (entry.get("aliases") or [])]:
            return {"term": key, **entry}

    matches = []
    for key, entry in db.items():
        score = 0
        score += _text_score(key, lower) * 10
        score += _text_score(entry.get("ja"), term.lower()) * 10
        score += _text_score(entry.get("description"), term.lower()) * 3
        score += _text_score(entry.get("description_ja"), term.lower()) * 3
        score += _array_score(entry.get("aliases"), term.lower()) * 5
        if score > 0:
            matches.append({"term": key, "score": score, **entry})

    if matches:
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[0]
    return None


# --- Patterns / Workflows ---


def search_patterns(
    query: str,
    product: str | None = None,
    max_results: int = 5,
) -> dict:
    db = _get_pattern_db()
    tokens = _tokenize(query)
    results = []

    for pattern in db:
        if product and product not in (pattern.get("applicable_products") or []):
            continue

        score = 0
        for token in tokens:
            score += _text_score(pattern.get("name"), token) * 10
            score += _text_score(pattern.get("name_en"), token) * 10
            score += _text_score(pattern.get("description"), token) * 5
            score += _text_score(pattern.get("description_en"), token) * 5
            score += _array_score(pattern.get("tags"), token) * 8
            score += _array_score(pattern.get("tags_ja"), token) * 8
            score += _array_score(pattern.get("related_devices"), token) * 3
            score += _array_score(pattern.get("related_terms"), token) * 3

        if score > 0:
            results.append({**pattern, "score": score})

    results.sort(key=lambda x: x["score"], reverse=True)
    limited = results[:max_results]

    return {
        "query": query,
        "product": product or "all",
        "result_count": len(limited),
        "total_matches": len(results),
        "results": limited,
    }


# --- Manual (Live 12.x reference manual) ---


def search_manual(query: str, max_results: int = 10) -> dict:
    """章タイトル・節タイトル・本文段落を検索する"""
    db = _get_manual_db()
    tokens = _tokenize(query)
    if not tokens or not db:
        return {"query": query, "result_count": 0, "total_matches": 0, "results": []}

    hits: list[dict] = []
    for slug, chapter in db.items():
        ch_title = chapter.get("title", "")
        ch_num = chapter.get("chapter_number", "")
        # 章タイトル
        ch_score = sum(_text_score(ch_title, t) * 8 for t in tokens)
        if ch_score > 0:
            hits.append({
                "slug": slug,
                "chapter_number": ch_num,
                "chapter_title": ch_title,
                "section_number": ch_num,
                "section_title": ch_title,
                "match": "chapter_title",
                "score": ch_score,
                "snippet": (chapter.get("intro_paragraphs") or [""])[0][:200],
            })

        # 節
        for sec in chapter.get("sections", []):
            sec_score = sum(
                _text_score(sec.get("title", ""), t) * 6
                for t in tokens
            )
            if sec_score > 0:
                hits.append({
                    "slug": slug,
                    "chapter_number": ch_num,
                    "chapter_title": ch_title,
                    "section_number": sec.get("number", ""),
                    "section_title": sec.get("title", ""),
                    "match": "section_title",
                    "score": sec_score,
                    "snippet": (sec.get("paragraphs") or [""])[0][:200],
                })

            # 節の本文
            for p in sec.get("paragraphs", []):
                p_score = sum(_text_score(p, t) * 2 for t in tokens)
                if p_score > 0:
                    hits.append({
                        "slug": slug,
                        "chapter_number": ch_num,
                        "chapter_title": ch_title,
                        "section_number": sec.get("number", ""),
                        "section_title": sec.get("title", ""),
                        "match": "paragraph",
                        "score": p_score,
                        "snippet": p[:240],
                    })

            # 小節
            for sub in sec.get("subsections", []):
                sub_score = sum(
                    _text_score(sub.get("title", ""), t) * 5
                    for t in tokens
                )
                if sub_score > 0:
                    hits.append({
                        "slug": slug,
                        "chapter_number": ch_num,
                        "chapter_title": ch_title,
                        "section_number": sub.get("number", ""),
                        "section_title": sub.get("title", ""),
                        "match": "subsection_title",
                        "score": sub_score,
                        "snippet": (sub.get("paragraphs") or [""])[0][:200],
                    })
                for p in sub.get("paragraphs", []):
                    p_score = sum(_text_score(p, t) * 2 for t in tokens)
                    if p_score > 0:
                        hits.append({
                            "slug": slug,
                            "chapter_number": ch_num,
                            "chapter_title": ch_title,
                            "section_number": sub.get("number", ""),
                            "section_title": sub.get("title", ""),
                            "match": "paragraph",
                            "score": p_score,
                            "snippet": p[:240],
                        })

        # intro_paragraphs
        for p in chapter.get("intro_paragraphs", []):
            p_score = sum(_text_score(p, t) * 2 for t in tokens)
            if p_score > 0:
                hits.append({
                    "slug": slug,
                    "chapter_number": ch_num,
                    "chapter_title": ch_title,
                    "section_number": ch_num,
                    "section_title": ch_title,
                    "match": "intro_paragraph",
                    "score": p_score,
                    "snippet": p[:240],
                })

    hits.sort(key=lambda x: x["score"], reverse=True)
    return {
        "query": query,
        "result_count": min(len(hits), max_results),
        "total_matches": len(hits),
        "results": hits[:max_results],
    }


def get_manual_chapter(slug: str) -> dict | None:
    db = _get_manual_db()
    return db.get(slug)


def get_manual_section(slug: str, section_number: str) -> dict | None:
    chapter = get_manual_chapter(slug)
    if not chapter:
        return None
    for sec in chapter.get("sections", []):
        if sec.get("number") == section_number:
            return {
                "slug": slug,
                "chapter_number": chapter.get("chapter_number"),
                "chapter_title": chapter.get("title"),
                "section": sec,
            }
        for sub in sec.get("subsections", []):
            if sub.get("number") == section_number:
                return {
                    "slug": slug,
                    "chapter_number": chapter.get("chapter_number"),
                    "chapter_title": chapter.get("title"),
                    "section_number": sec.get("number"),
                    "section_title": sec.get("title"),
                    "subsection": sub,
                }
    return None


def list_manual_chapters() -> dict:
    db = _get_manual_db()
    out = []
    for slug, c in db.items():
        out.append({
            "slug": slug,
            "chapter_number": c.get("chapter_number"),
            "title": c.get("title"),
            "section_count": len(c.get("sections", [])),
            "url": c.get("url"),
        })

    def sort_key(x):
        n = x.get("chapter_number") or "99"
        try:
            return float(n)
        except ValueError:
            return 99.0

    out.sort(key=sort_key)
    return {"chapter_count": len(out), "chapters": out}


# --- Suggestion (minimal Phase 1 stub) ---


def suggest_approaches(goal: str, constraints: list[str] | None = None) -> dict:
    pattern_results = search_patterns(goal, max_results=5)
    matched_patterns = pattern_results.get("results", [])

    device_results = search_devices(goal, max_results=8)
    matched_devices = device_results.get("results", [])

    constraint_notes = []
    if constraints:
        for c in constraints:
            cl = c.lower()
            if "move" in cl:
                constraint_notes.append("Move ハードウェア上での動作を考慮")
                matched_devices = [d for d in matched_devices if "move" in (d.get("available_on") or [])]
            if "m4l" in cl or "max for live" in cl:
                constraint_notes.append("Max for Live 環境を前提")
            if "live" in cl and "move" not in cl:
                constraint_notes.append("Live 12 デスクトップを前提")

    approaches = []
    for p in matched_patterns:
        approaches.append({
            "name": p.get("name") or p.get("name_en"),
            "description": p.get("description") or p.get("description_en"),
            "applicable_products": p.get("applicable_products"),
            "min_version": p.get("min_version"),
            "steps_ja": p.get("steps_ja"),
            "relevance_score": p.get("score", 0),
        })

    if matched_devices and len(approaches) < 3:
        names = [d["name"] for d in matched_devices[:5]]
        approaches.append({
            "name": "デバイス組合せ案",
            "description": f"関連デバイス（{', '.join(names[:3])}等）を組み合わせて構築",
            "devices": names,
            "relevance_score": 0,
        })

    return {
        "goal": goal,
        "constraints": constraints or [],
        "constraint_notes": constraint_notes,
        "approach_count": len(approaches),
        "approaches": approaches,
        "related_devices": [
            {"name": d["name"], "type": d.get("type"), "description_ja": d.get("description_ja")}
            for d in matched_devices[:6]
        ],
    }
