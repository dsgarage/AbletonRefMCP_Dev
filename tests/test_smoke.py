"""主要モジュールの import と最小動作確認"""

import sys
from pathlib import Path

# repo ルートを import path に追加（pytest は tests/ から実行される想定）
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_core_module_imports():
    import core  # noqa: F401
    assert core.mcp is not None


def test_search_functions_callable():
    from search import (
        search_devices,
        get_device_detail,
        compare_devices_detail,
        search_hardware,
        get_hardware_detail,
        search_release_notes,
        lom_search,
        lom_get,
        lookup_glossary,
        search_patterns,
        suggest_approaches,
    )
    assert callable(search_devices)
    assert callable(get_device_detail)
    assert callable(compare_devices_detail)
    assert callable(search_hardware)
    assert callable(get_hardware_detail)
    assert callable(search_release_notes)
    assert callable(lom_search)
    assert callable(lom_get)
    assert callable(lookup_glossary)
    assert callable(search_patterns)
    assert callable(suggest_approaches)


def test_search_devices_basic():
    from search import search_devices
    res = search_devices("sampler", max_results=5)
    assert res["result_count"] >= 1
    names = [r["name"] for r in res["results"]]
    assert any("Sampler" in n for n in names), names


def test_get_hardware_move_2_0():
    from search import get_hardware_detail
    res = get_hardware_detail("move", version="2.0.0")
    assert res is not None
    assert res["selected_version"]["audio_tracks_supported"] is True
    assert res["selected_version"]["audio_warping"] is True


def test_release_notes_filter_by_product():
    from search import search_release_notes
    res = search_release_notes(product="move")
    assert res["result_count"] >= 1
    products = {r["product"] for r in res["results"]}
    assert products == {"move"}


def test_lom_get_clip():
    from search import lom_get
    res = lom_get("Clip")
    assert res is not None
    assert res["parent"] == "ClipSlot"
    prop_names = [p["name"] for p in res.get("key_properties", [])]
    assert "warp_mode" in prop_names


def test_glossary_warp():
    from search import lookup_glossary
    res = lookup_glossary("warp")
    assert res is not None
    assert res["ja"] == "ワープ"
    assert "Beats" in res.get("modes", [])


def test_pattern_loop_audio_clip_top_hit():
    from search import search_patterns
    res = search_patterns("loop audio clip", product="move", max_results=3)
    assert res["result_count"] >= 1
    assert res["results"][0]["id"] == "move-loop-as-audio-clip"


def test_news_module_imports():
    from news import fetch_official_news, fetch_release_notes_page, fetch_article_detail
    assert callable(fetch_official_news)
    assert callable(fetch_release_notes_page)
    assert callable(fetch_article_detail)


def test_github_issues_module_imports():
    from github_issues import create_bug_report, create_feature_request, REPO
    assert callable(create_bug_report)
    assert callable(create_feature_request)
    assert REPO.startswith("dsgarage/")
