"""
~/.claude.json の `ableton-ref-mcp` エントリの URL を切り替えるユーティリティ。

Usage:
    # localhost (Phase 1 dev)
    python scripts/switch_mcp_url.py http://localhost:8001/mcp

    # Railway 直接
    python scripts/switch_mcp_url.py https://abletonrefmcp-production.up.railway.app/mcp

    # Cloudflare Workers プロキシ経由 (MaxRefMCP と同パターン)
    python scripts/switch_mcp_url.py https://mcp-proxy.tsukasansan-utt.workers.dev/ableton/mcp

    # 現状確認のみ
    python scripts/switch_mcp_url.py --show
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CONFIG_PATH = Path.home() / ".claude.json"
KEY = "ableton-ref-mcp"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?", help="新しい MCP URL")
    parser.add_argument("--show", action="store_true", help="現在の URL を表示するだけ")
    parser.add_argument("--no-backup", action="store_true", help="バックアップを取らない")
    args = parser.parse_args()

    if not CONFIG_PATH.exists():
        print(f"[error] {CONFIG_PATH} が存在しません。", file=sys.stderr)
        return 1

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    servers = config.setdefault("mcpServers", {})
    current = servers.get(KEY, {}).get("url")

    if args.show or args.url is None:
        print(f"current {KEY} url: {current}")
        return 0

    new_url = args.url
    if new_url == current:
        print(f"既に {new_url} に設定済みです。変更なし。")
        return 0

    if not args.no_backup:
        backup = CONFIG_PATH.with_suffix(".json.bak-ableton-ref")
        backup.write_bytes(CONFIG_PATH.read_bytes())
        print(f"backup: {backup}")

    servers[KEY] = {"type": "http", "url": new_url}
    CONFIG_PATH.write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"{KEY} url: {current} -> {new_url}")
    print("Claude Code を再起動すると新しい URL が反映されます。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
