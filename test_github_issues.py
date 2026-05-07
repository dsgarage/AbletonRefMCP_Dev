"""GitHub Issue 振り分けロジックのテスト"""

import unittest
from github_issues import _classify_repo, create_bug_report, create_feature_request


class TestClassifyRepo(unittest.TestCase):
    # MaxMCP に振り分けられるべきケース
    def test_patcher_operation(self):
        self.assertEqual(_classify_repo("パッチが作れない", "max.object.create がタイムアウトする"), "maxmcp")

    def test_websocket(self):
        self.assertEqual(_classify_repo("WebSocket接続エラー", "クライアントが接続できない"), "maxmcp")

    def test_dsp_issue(self):
        self.assertEqual(_classify_repo("DSPがオンにならない", "audio.toggle が反応しない"), "maxmcp")

    def test_ableton(self):
        self.assertEqual(_classify_repo("Ableton連携", "Live のトラック操作ができない"), "maxmcp")

    def test_layout(self):
        self.assertEqual(_classify_repo("レイアウトが崩れる", "align で位置がずれる"), "maxmcp")

    def test_skill(self):
        self.assertEqual(_classify_repo("/max-synth が動かない", "スキル実行時にエラー"), "maxmcp")

    # MaxRefMCP に振り分けられるべきケース
    def test_search(self):
        self.assertEqual(_classify_repo("検索結果がおかしい", "maxref.search_object の結果が不正"), "maxrefmcp")

    def test_glossary(self):
        self.assertEqual(_classify_repo("用語が見つからない", "glossary で signal が出ない"), "maxrefmcp")

    def test_compare(self):
        self.assertEqual(_classify_repo("比較機能の改善", "compare でタグも比較してほしい"), "maxrefmcp")

    def test_database(self):
        self.assertEqual(_classify_repo("object-db にオブジェクトがない", "データベースに ring~ がない"), "maxrefmcp")

    def test_deploy(self):
        self.assertEqual(_classify_repo("Railway デプロイ失敗", "デプロイ時にエラー"), "maxrefmcp")

    def test_reference(self):
        self.assertEqual(_classify_repo("リファレンスが不正確", "cycle~ の説明が間違っている"), "maxrefmcp")

    # 曖昧なケース → デフォルトは maxmcp
    def test_ambiguous(self):
        result = _classify_repo("バグがある", "なんかおかしい")
        self.assertEqual(result, "maxmcp")

    # max.* プレフィックスで MaxMCP と判定
    def test_max_prefix(self):
        self.assertEqual(_classify_repo("エラー", "max.object.create で失敗"), "maxmcp")

    # maxref.* プレフィックスで MaxRefMCP と判定
    def test_maxref_prefix(self):
        self.assertEqual(_classify_repo("エラー", "maxref.get_object が空を返す"), "maxrefmcp")


class TestCreateBugReport(unittest.TestCase):
    def test_without_token(self):
        """GITHUB_TOKEN がない場合はフォールバック"""
        import os
        old = os.environ.pop("GITHUB_TOKEN", None)
        try:
            result = create_bug_report(
                title="テストバグ",
                description="テスト用",
            )
            self.assertIn("error", result)
            self.assertIn("fallback", result)
            self.assertIn("manual_url", result["fallback"])
        finally:
            if old:
                os.environ["GITHUB_TOKEN"] = old

    def test_explicit_repo(self):
        """明示的にリポジトリを指定"""
        import os
        old = os.environ.pop("GITHUB_TOKEN", None)
        try:
            result = create_bug_report(
                title="テスト",
                description="テスト",
                target_repo="maxrefmcp",
            )
            self.assertEqual(result["fallback"]["repo"], "dsgarage/MaxRefMCP")
        finally:
            if old:
                os.environ["GITHUB_TOKEN"] = old


class TestCreateFeatureRequest(unittest.TestCase):
    def test_without_token(self):
        import os
        old = os.environ.pop("GITHUB_TOKEN", None)
        try:
            result = create_feature_request(
                title="新機能",
                description="グリッチエフェクトのパターン追加",
            )
            self.assertIn("error", result)
            self.assertIn("fallback", result)
        finally:
            if old:
                os.environ["GITHUB_TOKEN"] = old

    def test_auto_routing_to_maxmcp(self):
        """パッチ構築系はMaxMCPに振り分け"""
        import os
        old = os.environ.pop("GITHUB_TOKEN", None)
        try:
            result = create_feature_request(
                title="新しいスキル追加",
                description="グリッチエフェクトのパッチ構築スキルが欲しい",
            )
            self.assertEqual(result["fallback"]["repo"], "dsgarage/MaxMCP-dev")
        finally:
            if old:
                os.environ["GITHUB_TOKEN"] = old

    def test_auto_routing_to_maxrefmcp(self):
        """リファレンス系はMaxRefMCPに振り分け"""
        import os
        old = os.environ.pop("GITHUB_TOKEN", None)
        try:
            result = create_feature_request(
                title="データベースにオブジェクト追加",
                description="object-db にring~のリファレンスを追加してほしい",
            )
            self.assertEqual(result["fallback"]["repo"], "dsgarage/MaxRefMCP")
        finally:
            if old:
                os.environ["GITHUB_TOKEN"] = old


if __name__ == "__main__":
    unittest.main()
