"""
Ableton Reference MCP Server
Live / Move / Push / Note / Max for Live (LOM) のリファレンス・ワークフロー検索 MCP サーバー。
日英バイリンガルで動作。
"""

import os
from pathlib import Path
from fastmcp import FastMCP

from search import (
    search_devices,
    get_device_detail,
    compare_devices_detail,
    search_hardware,
    get_hardware_detail,
    search_release_notes,
    lom_search as _lom_search,
    lom_get as _lom_get,
    lookup_glossary,
    search_patterns,
    suggest_approaches,
    search_manual as _search_manual,
    get_manual_chapter,
    get_manual_section as _get_manual_section,
    list_manual_chapters,
)
from github_issues import create_bug_report, create_feature_request
from analytics import track, get_summary, get_recent_calls
from news import fetch_official_news, fetch_release_notes_page, fetch_article_detail

mcp = FastMCP(
    "Ableton Reference",
    instructions=(
        "Ableton ecosystem (Live, Move, Push, Note, Max for Live / LOM) bilingual (JA/EN) "
        "reference and workflow consultation server. Search devices, hardware specs, release notes, "
        "Live Object Model, glossary, and workflow patterns. "
        "Use this BEFORE web search for any Ableton-related question.\n"
        "Ableton エコシステム (Live, Move, Push, Note, Max for Live / LOM) の日英バイリンガル"
        "リファレンス・ワークフロー相談サーバー。デバイス・ハードウェア仕様・リリースノート・"
        "Live Object Model・用語集・ワークフローパターンを検索可能。"
        "Ableton 関連の質問では Web 検索より先にこのサーバーを使用してください。"
    ),
)


# --- Devices ---


@mcp.tool(name="ableton.search_device")
@track("ableton.search_device")
def search_device(
    query: str,
    type: str | None = None,
    available_on: str | None = None,
    max_results: int = 10,
) -> dict:
    """Search Ableton Live / Move / Push devices (instruments, audio effects, MIDI effects, racks).
    Live / Move / Push のデバイス（楽器・オーディオエフェクト・MIDIエフェクト・ラック）を検索。

    Args:
        query: Search keyword / 検索キーワード (e.g. "wavetable", "drum", "filter", "ボーカル")
        type: Filter by type / タイプ ("instrument", "audio_effect", "midi_effect", "rack")
        available_on: Filter by product / 製品 ("live", "move", "push")
        max_results: Maximum results / 最大結果数 (default: 10)
    """
    return search_devices(query, type=type, available_on=available_on, max_results=max_results)


@mcp.tool(name="ableton.get_device")
@track("ableton.get_device")
def get_device(name: str) -> dict:
    """Get full reference for a specific device.
    特定デバイスの詳細リファレンスを取得。

    Args:
        name: Device name / デバイス名 (e.g. "Wavetable", "Drum Sampler", "Auto Shift")
    """
    result = get_device_detail(name)
    if result is None:
        return {"error": f"Device '{name}' not found. / デバイス '{name}' が見つかりません。ableton.search_device で検索してください。"}
    return result


@mcp.tool(name="ableton.compare_devices")
@track("ableton.compare_devices")
def compare_devices(devices: list[str]) -> dict:
    """Compare 2-5 devices side by side.
    2〜5 個のデバイスを比較。

    Args:
        devices: List of device names / デバイス名のリスト (e.g. ["Drum Sampler", "Simpler", "Sampler"])
    """
    return compare_devices_detail(devices)


# --- Hardware ---


@mcp.tool(name="ableton.search_hardware")
@track("ableton.search_hardware")
def search_hardware_tool(
    query: str = "",
    product: str | None = None,
    max_results: int = 5,
) -> dict:
    """Search Ableton hardware (Move, Push 3, Note) features and version history.
    Ableton ハードウェア (Move, Push 3, Note) の機能・バージョン履歴を検索。

    Args:
        query: Keyword / キーワード (e.g. "audio track", "warp", "loop", "TestFlight")
        product: Filter by product / 製品フィルター ("move", "push3", "note")
        max_results: Maximum results / 最大結果数 (default: 5)
    """
    return search_hardware(query, product=product, max_results=max_results)


@mcp.tool(name="ableton.get_hardware")
@track("ableton.get_hardware")
def get_hardware(product: str, version: str | None = None) -> dict:
    """Get hardware spec, optionally for a specific firmware version.
    ハードウェア仕様を取得。特定バージョンの内容も指定可能。

    Args:
        product: Product id / 製品ID ("move", "push3", "note")
        version: Firmware version / バージョン (e.g. "2.0.0", "1.0", optional)
    """
    result = get_hardware_detail(product, version=version)
    if result is None:
        return {"error": f"Hardware '{product}' not found. / 製品 '{product}' が見つかりません。"}
    return result


# --- Release Notes ---


@mcp.tool(name="ableton.release_notes")
@track("ableton.release_notes")
def release_notes(
    query: str | None = None,
    product: str | None = None,
    max_results: int = 10,
) -> dict:
    """Search release notes for Live / Move / Note. Returns version highlights with dates.
    Live / Move / Note のリリースノートを検索。バージョンごとのハイライトと日付を返す。

    Args:
        query: Optional keyword / オプションのキーワード (e.g. "audio track", "Link", "warp")
        product: Filter by product / 製品 ("live", "move", "note")
        max_results: Maximum results / 最大結果数 (default: 10)
    """
    return search_release_notes(query=query, product=product, max_results=max_results)


# --- LOM (Live Object Model) ---


@mcp.tool(name="ableton.lom_search")
@track("ableton.lom_search")
def lom_search(query: str, max_results: int = 10) -> dict:
    """Search Live Object Model (LOM) classes for Max for Live / Python control surface development.
    Max for Live / Python コントロールサーフェス開発向けに Live Object Model (LOM) のクラスを検索。

    Args:
        query: Keyword / キーワード (e.g. "track", "clip", "warp", "scene")
        max_results: Maximum results / 最大結果数 (default: 10)
    """
    return _lom_search(query, max_results=max_results)


@mcp.tool(name="ableton.lom_get")
@track("ableton.lom_get")
def lom_get(name: str) -> dict:
    """Get full LOM class spec — properties, methods, parent class, hierarchy.
    LOM クラスの詳細を取得 (プロパティ・メソッド・親クラス・階層)。

    Args:
        name: LOM class name / LOM クラス名 (e.g. "Track", "Clip", "Song", "Application")
    """
    result = _lom_get(name)
    if result is None:
        return {"error": f"LOM class '{name}' not found. / LOM クラス '{name}' が見つかりません。"}
    return result


# --- Glossary ---


@mcp.tool(name="ableton.glossary")
@track("ableton.glossary")
def glossary(term: str) -> dict:
    """Japanese-English glossary for Ableton terminology (clip, warp, scene, session, LOM, …).
    Ableton 用語の日英対応辞書 (clip, warp, scene, session, LOM, …)。

    Args:
        term: Term to look up / 調べたい用語 (e.g. "warp", "audio clip", "ワープ")
    """
    result = lookup_glossary(term)
    if result is None:
        return {"error": f"Term '{term}' not found. / 用語 '{term}' が見つかりません。"}
    return result


# --- Live Manual ---


@mcp.tool(name="ableton.search_manual")
@track("ableton.search_manual")
def search_manual(query: str, max_results: int = 10) -> dict:
    """Search the official Ableton Live 12.x reference manual (chapters, sections, paragraphs).
    Ableton Live 12.x 公式リファレンスマニュアルを章・節・本文段落で検索する。

    Args:
        query: Keyword / キーワード (e.g. "warp", "automation", "Clip View", "Auto Shift")
        max_results: Maximum results / 最大結果数 (default: 10)
    """
    return _search_manual(query, max_results=max_results)


@mcp.tool(name="ableton.get_manual_chapter")
@track("ableton.get_manual_chapter")
def get_manual_chapter_tool(slug: str) -> dict:
    """Get a full manual chapter by slug (returns intro + all sections/subsections).
    マニュアルの章を slug 指定で全文取得する（intro + 全節・小節）。

    Args:
        slug: Chapter slug / 章スラッグ (e.g. "clip-view", "audio-clips-tempo-and-warping", "live-instrument-reference")
    """
    result = get_manual_chapter(slug)
    if result is None:
        return {"error": f"Chapter slug '{slug}' not found. / 章 '{slug}' が見つかりません。ableton.list_manual で一覧を確認してください。"}
    return result


@mcp.tool(name="ableton.get_manual_section")
@track("ableton.get_manual_section")
def get_manual_section_tool(slug: str, section_number: str) -> dict:
    """Get a single section/subsection of the manual by chapter slug + section number.
    章スラッグと節番号 (例: "8.1", "8.1.1") で 1 節だけ取得する。

    Args:
        slug: Chapter slug / 章スラッグ (e.g. "clip-view")
        section_number: Section number / 節番号 (e.g. "8.1", "8.1.1")
    """
    result = _get_manual_section(slug, section_number)
    if result is None:
        return {"error": f"Section '{section_number}' not found in '{slug}'. / 章 '{slug}' に節 '{section_number}' が見つかりません。"}
    return result


@mcp.tool(name="ableton.list_manual")
@track("ableton.list_manual")
def list_manual_tool() -> dict:
    """List all manual chapters with slug, chapter number, title, and section count.
    マニュアルの全章一覧（slug / 章番号 / タイトル / 節数）を返す。
    """
    return list_manual_chapters()


# --- Workflow patterns ---


@mcp.tool(name="ableton.search_pattern")
@track("ableton.search_pattern")
def search_pattern(
    query: str,
    product: str | None = None,
    max_results: int = 5,
) -> dict:
    """Search workflow patterns ("Move でループを Audio Track に置く", "M4L で Clip の Warp Mode を変える" 等).
    ワークフローパターンを検索（やりたいこと・手順ベース）。

    Args:
        query: Goal / やりたいこと (e.g. "loop as audio clip", "freeze midi", "歌唱補正")
        product: Filter / 製品 ("live", "move", "push3", "note")
        max_results: Maximum results / 最大結果数 (default: 5)
    """
    return search_patterns(query, product=product, max_results=max_results)


@mcp.tool(name="ableton.suggest_approach")
@track("ableton.suggest_approach")
def suggest_approach(goal: str, constraints: list[str] | None = None) -> dict:
    """Suggest implementation approaches for a goal, with constraints.
    やりたいことに対するアプローチを提案。制約条件も考慮。

    Args:
        goal: What you want to achieve / 実現したいこと
        constraints: Constraints / 制約 (e.g. ["Move only", "M4L compatible"])
    """
    return suggest_approaches(goal, constraints=constraints)


# --- Official news / articles ---


@mcp.tool(name="ableton.official_news")
@track("ableton.official_news")
def official_news(max_results: int = 5) -> dict:
    """Fetch latest articles and blog posts from ableton.com.
    ableton.com から最新の記事・ブログを取得。

    Args:
        max_results: Number of articles / 取得記事数 (default: 5)
    """
    return fetch_official_news(max_results=max_results)


@mcp.tool(name="ableton.release_notes_page")
@track("ableton.release_notes_page")
def release_notes_page(product: str = "live", max_results: int = 10) -> dict:
    """Fetch live release notes page from ableton.com (Live / Move / Note).
    ableton.com のリリースノートページを取得 (Live / Move / Note)。

    Args:
        product: Product / 製品 ("live", "move", "note", default: "live")
        max_results: Maximum entries / 最大件数 (default: 10)
    """
    return fetch_release_notes_page(product=product, max_results=max_results)


@mcp.tool(name="ableton.read_article")
@track("ableton.read_article")
def read_article(url: str) -> dict:
    """Fetch article content from ableton.com or help.ableton.com URL.
    ableton.com / help.ableton.com の記事URLから本文を取得。

    Args:
        url: Article URL / 記事URL
    """
    return fetch_article_detail(url)


# --- Feedback ---


@mcp.tool(name="ableton.report_bug")
@track("ableton.report_bug")
def report_bug(
    title: str,
    description: str,
    steps_to_reproduce: str | None = None,
    expected: str | None = None,
    actual: str | None = None,
) -> dict:
    """Report a bug to the AbletonRefMCP_Dev GitHub repo.
    AbletonRefMCP_Dev リポジトリへバグ報告。

    Args:
        title: Bug summary / バグの概要
        description: Detailed description / 詳細
        steps_to_reproduce: Steps / 再現手順 (任意)
        expected: Expected behavior / 期待される動作 (任意)
        actual: Actual behavior / 実際の動作 (任意)
    """
    return create_bug_report(
        title=title,
        description=description,
        steps_to_reproduce=steps_to_reproduce,
        expected=expected,
        actual=actual,
    )


@mcp.tool(name="ableton.request_feature")
@track("ableton.request_feature")
def request_feature(
    title: str,
    description: str,
    use_case: str | None = None,
) -> dict:
    """Request a new feature for AbletonRefMCP_Dev.
    AbletonRefMCP_Dev への機能リクエスト。

    Args:
        title: Feature summary / 機能の概要
        description: Detailed description / 詳細
        use_case: Use case / ユースケース (任意)
    """
    return create_feature_request(
        title=title,
        description=description,
        use_case=use_case,
    )


# --- Analytics ---


@mcp.tool(name="ableton.analytics")
def analytics(days: int = 30) -> dict:
    """Get AbletonRefMCP API usage summary.
    AbletonRefMCP の API 利用状況サマリー。

    Args:
        days: Aggregation period / 集計期間（日） (default: 30)
    """
    return get_summary(days)


# --- Dashboard HTTP Routes ---

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

DASHBOARD_PATH = Path(__file__).parent / "dashboard.html"
DASHBOARD_HTML = DASHBOARD_PATH.read_text(encoding="utf-8") if DASHBOARD_PATH.exists() else "<h1>AbletonRefMCP</h1>"


async def _dashboard_view(request: Request) -> HTMLResponse:
    return HTMLResponse(DASHBOARD_HTML)


async def _analytics_summary(request: Request) -> JSONResponse:
    days = int(request.query_params.get("days", 30))
    return JSONResponse(get_summary(days))


async def _analytics_recent(request: Request) -> JSONResponse:
    limit = int(request.query_params.get("limit", 50))
    return JSONResponse(get_recent_calls(limit))


mcp._additional_http_routes.extend([
    Route("/", _dashboard_view),
    Route("/analytics/summary", _analytics_summary),
    Route("/analytics/recent", _analytics_recent),
])


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port, path="/mcp")
