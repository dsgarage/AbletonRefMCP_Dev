"""MaxRefMCP 検索エンジンのテスト"""

import unittest
from search import (
    search_objects,
    get_object_detail,
    search_patterns,
    search_packages,
    lookup_glossary,
    compare_objects_detail,
    suggest_approaches,
    explain_connection_detail,
    check_rnbo_compatibility,
    _text_score,
    _array_score,
    _tokenize,
)


class TestTextScore(unittest.TestCase):
    def test_exact_match(self):
        self.assertEqual(_text_score("cycle~", "cycle~"), 10)

    def test_prefix_match(self):
        self.assertEqual(_text_score("cycle~", "cyc"), 7)

    def test_partial_match(self):
        self.assertEqual(_text_score("A sine wave oscillator", "sine"), 3)

    def test_no_match(self):
        self.assertEqual(_text_score("cycle~", "metro"), 0)

    def test_none_input(self):
        self.assertEqual(_text_score(None, "test"), 0)

    def test_case_insensitive(self):
        self.assertEqual(_text_score("Cycle~", "cycle~"), 10)


class TestArrayScore(unittest.TestCase):
    def test_match_in_array(self):
        self.assertGreater(_array_score(["oscillator", "sine"], "sine"), 0)

    def test_no_match(self):
        self.assertEqual(_array_score(["oscillator", "sine"], "filter"), 0)

    def test_none_array(self):
        self.assertEqual(_array_score(None, "test"), 0)

    def test_empty_array(self):
        self.assertEqual(_array_score([], "test"), 0)


class TestTokenize(unittest.TestCase):
    def test_space_split(self):
        self.assertEqual(_tokenize("sine wave"), ["sine", "wave"])

    def test_comma_split(self):
        self.assertEqual(_tokenize("sine,wave"), ["sine", "wave"])

    def test_japanese_comma(self):
        self.assertEqual(_tokenize("サイン、ウェーブ"), ["サイン", "ウェーブ"])

    def test_empty(self):
        self.assertEqual(_tokenize(""), [])

    def test_lowercase(self):
        self.assertEqual(_tokenize("Cycle~"), ["cycle~"])


class TestSearchObjects(unittest.TestCase):
    def test_basic_search(self):
        result = search_objects("cycle~")
        self.assertGreater(result["result_count"], 0)
        self.assertEqual(result["results"][0]["name"], "cycle~")

    def test_domain_filter(self):
        result = search_objects("oscillator", domain="msp")
        for r in result["results"]:
            self.assertEqual(r["domain"], "msp")

    def test_no_results(self):
        result = search_objects("xyznonexistent12345")
        self.assertEqual(result["result_count"], 0)

    def test_japanese_search(self):
        result = search_objects("オシレーター")
        self.assertGreater(result["result_count"], 0)

    def test_max_results(self):
        result = search_objects("filter", max_results=3)
        self.assertLessEqual(result["result_count"], 3)


class TestGetObjectDetail(unittest.TestCase):
    def test_exact_name(self):
        result = get_object_detail("cycle~")
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "cycle~")
        self.assertIn("inlets", result)
        self.assertIn("outlets", result)

    def test_case_insensitive(self):
        result = get_object_detail("CYCLE~")
        self.assertIsNotNone(result)

    def test_not_found(self):
        result = get_object_detail("nonexistent_object_xyz")
        self.assertIsNone(result)


class TestSearchPatterns(unittest.TestCase):
    def test_synth_search(self):
        result = search_patterns("シンセサイザー")
        self.assertGreater(result["result_count"], 0)

    def test_domain_filter(self):
        result = search_patterns("effect", domain="msp")
        for r in result["results"]:
            self.assertEqual(r.get("domain"), "msp")


class TestSearchPackages(unittest.TestCase):
    def test_basic_search(self):
        result = search_packages("audio")
        self.assertGreater(result["result_count"], 0)


class TestGlossary(unittest.TestCase):
    def test_english_term(self):
        result = lookup_glossary("signal")
        self.assertIsNotNone(result)

    def test_japanese_term(self):
        result = lookup_glossary("シグナル")
        self.assertIsNotNone(result)

    def test_not_found(self):
        result = lookup_glossary("xyznonexistent")
        self.assertIsNone(result)


class TestCompareObjects(unittest.TestCase):
    def test_compare_two(self):
        result = compare_objects_detail(["cycle~", "saw~"])
        self.assertIn("comparison", result)
        self.assertEqual(result["object_count"], 2)
        self.assertEqual(len(result["comparison"]["objects"]), 2)

    def test_too_few(self):
        result = compare_objects_detail(["cycle~"])
        self.assertIn("error", result)

    def test_too_many(self):
        result = compare_objects_detail(["a", "b", "c", "d", "e", "f"])
        self.assertIn("error", result)

    def test_not_found_object(self):
        result = compare_objects_detail(["cycle~", "nonexistent_xyz"])
        # cycle~ は見つかるが1つだけなのでエラー
        self.assertIn("error", result)

    def test_shared_traits(self):
        result = compare_objects_detail(["cycle~", "saw~"])
        # 両方MSPドメインなので共通点がある
        self.assertGreater(len(result["comparison"]["shared_traits"]), 0)


class TestSuggestApproach(unittest.TestCase):
    def test_basic_suggestion(self):
        result = suggest_approaches("synth")
        self.assertGreater(result["approach_count"], 0)

    def test_with_constraints(self):
        result = suggest_approaches("シンセ", constraints=["RNBO互換"])
        self.assertIn("RNBO互換オブジェクトのみ使用", result["constraint_notes"])

    def test_no_match(self):
        result = suggest_approaches("xyznonexistent")
        # カスタム構成が少なくとも提案されうる
        self.assertIsInstance(result["approaches"], list)


class TestExplainConnection(unittest.TestCase):
    def test_signal_connection(self):
        result = explain_connection_detail("cycle~", "ezdac~")
        self.assertNotIn("error", result)
        self.assertIn("possible_connections", result)

    def test_source_not_found(self):
        result = explain_connection_detail("nonexistent_xyz", "ezdac~")
        self.assertIn("error", result)

    def test_dest_not_found(self):
        result = explain_connection_detail("cycle~", "nonexistent_xyz")
        self.assertIn("error", result)

    def test_recommended_connection(self):
        result = explain_connection_detail("cycle~", "ezdac~")
        if result.get("possible_connections"):
            self.assertIsNotNone(result.get("recommended"))


class TestRnboCompatibility(unittest.TestCase):
    def test_compatible_object(self):
        result = check_rnbo_compatibility(["cycle~"])
        self.assertIn("summary", result)
        # cycle~ はRNBO互換のはず
        total = result["summary"]["compatible"] + result["summary"]["incompatible"] + result["summary"]["unknown"]
        self.assertEqual(total, 1)

    def test_empty_list(self):
        result = check_rnbo_compatibility([])
        self.assertIn("error", result)

    def test_unknown_object(self):
        result = check_rnbo_compatibility(["nonexistent_xyz"])
        self.assertEqual(result["summary"]["unknown"], 1)

    def test_multiple_objects(self):
        result = check_rnbo_compatibility(["cycle~", "saw~", "metro"])
        self.assertEqual(result["summary"]["total"], 3)


if __name__ == "__main__":
    unittest.main()
