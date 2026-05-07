"""
コミュニティデータ検索エンジン（Phase 2 用スタブ）
Discord / X からのデータを検索する。
"""


def search_community(query: str, source: str = "all", max_results: int = 5) -> dict:
    """コミュニティ知見を検索（Phase 2 で実装）"""
    return {
        "query": query,
        "source": source,
        "result_count": 0,
        "results": [],
        "message": "コミュニティ検索は Phase 2 で実装予定です。",
    }
