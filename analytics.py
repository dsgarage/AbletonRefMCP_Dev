"""
API 利用状況トラッキング
SQLite ベースの軽量アナリティクス。ツール呼び出しを記録し、集計を提供する。
"""

import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from functools import wraps

DB_PATH = Path(os.environ.get("ANALYTICS_DB", Path(__file__).parent / "data" / "analytics.db"))

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """スレッドローカルなDB接続を取得"""
    if not hasattr(_local, "conn") or _local.conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _local.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _init_db(_local.conn)
    return _local.conn


def _init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tool_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_name TEXT NOT NULL,
            params TEXT,
            result_status TEXT DEFAULT 'success',
            duration_ms REAL,
            timestamp TEXT NOT NULL,
            date TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_tool_name ON tool_calls(tool_name);
        CREATE INDEX IF NOT EXISTS idx_date ON tool_calls(date);
        CREATE INDEX IF NOT EXISTS idx_timestamp ON tool_calls(timestamp);
    """)
    conn.commit()


def record_call(
    tool_name: str,
    params: dict | None = None,
    result_status: str = "success",
    duration_ms: float = 0,
) -> None:
    """ツール呼び出しを記録"""
    conn = _get_conn()
    now = datetime.now(timezone.utc)
    conn.execute(
        "INSERT INTO tool_calls (tool_name, params, result_status, duration_ms, timestamp, date) VALUES (?, ?, ?, ?, ?, ?)",
        (
            tool_name,
            json.dumps(params, ensure_ascii=False) if params else None,
            result_status,
            duration_ms,
            now.isoformat(),
            now.strftime("%Y-%m-%d"),
        ),
    )
    conn.commit()


def track(tool_name: str):
    """ツール関数をラップして自動的に呼び出しを記録するデコレータ"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.monotonic()
            status = "success"
            try:
                result = func(*args, **kwargs)
                if isinstance(result, dict) and "error" in result:
                    status = "error"
                return result
            except Exception:
                status = "exception"
                raise
            finally:
                duration = (time.monotonic() - start) * 1000
                try:
                    record_call(tool_name, kwargs or None, status, duration)
                except Exception:
                    pass  # アナリティクスの失敗でツール実行を妨げない
        return wrapper
    return decorator


def get_summary(days: int = 30) -> dict:
    """利用状況サマリーを取得"""
    conn = _get_conn()

    # 全体統計
    row = conn.execute(
        "SELECT COUNT(*) as total, AVG(duration_ms) as avg_ms FROM tool_calls WHERE date >= date('now', ?)",
        (f"-{days} days",),
    ).fetchone()
    total_calls = row["total"]
    avg_duration = round(row["avg_ms"] or 0, 1)

    # ツール別呼び出し数
    tool_rows = conn.execute(
        """SELECT tool_name, COUNT(*) as count, AVG(duration_ms) as avg_ms,
                  SUM(CASE WHEN result_status = 'error' THEN 1 ELSE 0 END) as errors
           FROM tool_calls WHERE date >= date('now', ?)
           GROUP BY tool_name ORDER BY count DESC""",
        (f"-{days} days",),
    ).fetchall()
    by_tool = [
        {
            "tool": r["tool_name"],
            "count": r["count"],
            "avg_ms": round(r["avg_ms"] or 0, 1),
            "errors": r["errors"],
        }
        for r in tool_rows
    ]

    # 日別推移
    daily_rows = conn.execute(
        """SELECT date, COUNT(*) as count
           FROM tool_calls WHERE date >= date('now', ?)
           GROUP BY date ORDER BY date""",
        (f"-{days} days",),
    ).fetchall()
    daily = [{"date": r["date"], "count": r["count"]} for r in daily_rows]

    # ステータス別
    status_rows = conn.execute(
        """SELECT result_status, COUNT(*) as count
           FROM tool_calls WHERE date >= date('now', ?)
           GROUP BY result_status""",
        (f"-{days} days",),
    ).fetchall()
    by_status = {r["result_status"]: r["count"] for r in status_rows}

    # 人気検索クエリ（search_* 系のパラメータから）
    query_rows = conn.execute(
        """SELECT params FROM tool_calls
           WHERE tool_name LIKE 'ableton.search_%'
              OR tool_name LIKE 'ableton.lom_search'
              OR tool_name LIKE 'ableton.glossary'
              OR tool_name LIKE 'ableton.release_notes'
           AND params IS NOT NULL AND date >= date('now', ?)
           ORDER BY timestamp DESC LIMIT 100""",
        (f"-{days} days",),
    ).fetchall()
    query_counts: dict[str, int] = {}
    for r in query_rows:
        try:
            p = json.loads(r["params"])
            q = p.get("query", "")
            if q:
                query_counts[q] = query_counts.get(q, 0) + 1
        except (json.JSONDecodeError, TypeError):
            pass
    top_queries = sorted(query_counts.items(), key=lambda x: x[1], reverse=True)[:20]

    return {
        "period_days": days,
        "total_calls": total_calls,
        "avg_duration_ms": avg_duration,
        "by_tool": by_tool,
        "daily": daily,
        "by_status": by_status,
        "top_queries": [{"query": q, "count": c} for q, c in top_queries],
    }


def get_recent_calls(limit: int = 50) -> list[dict]:
    """直近の呼び出し履歴を取得"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT tool_name, params, result_status, duration_ms, timestamp FROM tool_calls ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [
        {
            "tool": r["tool_name"],
            "params": json.loads(r["params"]) if r["params"] else None,
            "status": r["result_status"],
            "duration_ms": round(r["duration_ms"] or 0, 1),
            "timestamp": r["timestamp"],
        }
        for r in rows
    ]
