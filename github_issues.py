"""
GitHub Issue 作成モジュール (AbletonRefMCP_Dev 専用)
"""

import json
import os
import urllib.request
import urllib.error

REPO = os.environ.get("ABLETON_REF_MCP_REPO", "dsgarage/AbletonRefMCP_Dev")


def _get_github_token() -> str | None:
    return os.environ.get("GITHUB_TOKEN")


def _create_github_issue(title: str, body: str, labels: list[str]) -> dict:
    token = _get_github_token()
    if not token:
        return {
            "error": "GITHUB_TOKEN 環境変数が設定されていません。",
            "fallback": {
                "repo": REPO,
                "title": title,
                "body": body,
                "labels": labels,
                "manual_url": f"https://github.com/{REPO}/issues/new",
            },
        }

    url = f"https://api.github.com/repos/{REPO}/issues"
    payload = json.dumps({
        "title": title,
        "body": body,
        "labels": labels,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {
                "success": True,
                "issue_number": data["number"],
                "url": data["html_url"],
                "repo": REPO,
                "title": data["title"],
            }
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        return {
            "error": f"GitHub API エラー: {e.code} {e.reason}",
            "detail": error_body,
            "repo": REPO,
        }


def create_bug_report(
    title: str,
    description: str,
    steps_to_reproduce: str | None = None,
    expected: str | None = None,
    actual: str | None = None,
    target_repo: str | None = None,  # 互換性のため残す（無視）
) -> dict:
    body_parts = [
        "## バグ報告\n",
        f"### 概要\n{description}\n",
    ]
    if steps_to_reproduce:
        body_parts.append(f"### 再現手順\n{steps_to_reproduce}\n")
    if expected:
        body_parts.append(f"### 期待される動作\n{expected}\n")
    if actual:
        body_parts.append(f"### 実際の動作\n{actual}\n")
    body_parts.append(f"\n---\n*リポジトリ: `{REPO}`*")
    return _create_github_issue(f"[Bug] {title}", "\n".join(body_parts), ["bug"])


def create_feature_request(
    title: str,
    description: str,
    use_case: str | None = None,
    target_repo: str | None = None,  # 互換性のため残す（無視）
) -> dict:
    body_parts = [
        "## 機能リクエスト\n",
        f"### 概要\n{description}\n",
    ]
    if use_case:
        body_parts.append(f"### ユースケース\n{use_case}\n")
    body_parts.append(f"\n---\n*リポジトリ: `{REPO}`*")
    return _create_github_issue(f"[Feature] {title}", "\n".join(body_parts), ["enhancement"])
