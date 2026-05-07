"""アナリティクスモジュールのテスト"""

import os
import tempfile
import unittest

# テスト用DBパスを設定（本番DBを汚さない）
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["ANALYTICS_DB"] = _tmp.name

from analytics import record_call, get_summary, get_recent_calls, track


class TestRecordAndQuery(unittest.TestCase):
    def test_record_and_summary(self):
        record_call("maxref.search_object", {"query": "cycle~"}, "success", 5.2)
        record_call("maxref.search_object", {"query": "saw~"}, "success", 3.1)
        record_call("maxref.get_object", {"name": "metro"}, "error", 1.0)

        summary = get_summary(days=1)
        self.assertGreaterEqual(summary["total_calls"], 3)
        self.assertGreater(summary["avg_duration_ms"], 0)
        self.assertGreater(len(summary["by_tool"]), 0)

    def test_recent_calls(self):
        record_call("maxref.glossary", {"term": "test"}, "success", 1.0)
        recent = get_recent_calls(limit=10)
        self.assertGreater(len(recent), 0)
        self.assertIn("tool", recent[0])
        self.assertIn("timestamp", recent[0])

    def test_top_queries(self):
        record_call("maxref.search_object", {"query": "filter"}, "success", 2.0)
        record_call("maxref.search_object", {"query": "filter"}, "success", 2.0)
        record_call("maxref.search_object", {"query": "filter"}, "success", 2.0)

        summary = get_summary(days=1)
        top = summary["top_queries"]
        self.assertGreater(len(top), 0)

    def test_by_status(self):
        record_call("maxref.test", None, "success", 0.1)
        summary = get_summary(days=1)
        self.assertIn("success", summary["by_status"])


class TestTrackDecorator(unittest.TestCase):
    def test_decorator_records(self):
        @track("test.decorated")
        def my_func(x=1):
            return {"value": x}

        result = my_func(x=42)
        self.assertEqual(result["value"], 42)

        recent = get_recent_calls(limit=1)
        self.assertEqual(recent[0]["tool"], "test.decorated")

    def test_decorator_records_error(self):
        @track("test.error_func")
        def error_func():
            return {"error": "something wrong"}

        error_func()
        recent = get_recent_calls(limit=1)
        self.assertEqual(recent[0]["status"], "error")

    def test_decorator_records_exception(self):
        @track("test.exception_func")
        def exception_func():
            raise ValueError("boom")

        with self.assertRaises(ValueError):
            exception_func()

        recent = get_recent_calls(limit=1)
        self.assertEqual(recent[0]["tool"], "test.exception_func")
        self.assertEqual(recent[0]["status"], "exception")


class TestEdgeCases(unittest.TestCase):
    def test_empty_summary(self):
        # 9999日前のデータは存在しないが、エラーにならない
        summary = get_summary(days=0)
        self.assertIn("total_calls", summary)

    def test_record_without_params(self):
        record_call("maxref.glossary", None, "success", 0.5)
        recent = get_recent_calls(limit=1)
        self.assertIsNone(recent[0]["params"])


def tearDownModule():
    os.unlink(_tmp.name)


if __name__ == "__main__":
    unittest.main()
