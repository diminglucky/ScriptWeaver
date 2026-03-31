import unittest

from src.gui.mixins.story_modules.ui_builder import StoryUIBuilderMixin


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _Dummy(StoryUIBuilderMixin):
    pass


class StoryRagPostprocessTests(unittest.TestCase):
    def _make_obj(self):
        obj = _Dummy()
        obj.top_k = _Var(6)
        obj.rag_min_score = _Var(0.4)
        obj.story_template_key = _Var("urban_power")
        obj.story_template_strategy = _Var("shuffle")
        obj._story_creativity_nonce = "test-nonce"
        return obj

    def test_postprocess_filters_by_score_and_dedups(self):
        obj = self._make_obj()
        rows = [
            ("重复内容A", 0.61, ("a.txt", 0)),
            ("重复内容A", 0.59, ("a.txt", 1)),
            ("低分内容", 0.10, ("b.txt", 0)),
            ("有效内容B", 0.72, ("c.txt", 0)),
        ]
        out = obj._postprocess_rag_results(rows)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0][0], "重复内容A")
        self.assertEqual(out[1][0], "有效内容B")

    def test_postprocess_has_fallback_when_threshold_too_high(self):
        obj = self._make_obj()
        obj.rag_min_score.set(0.99)
        rows = [
            ("内容A", 0.50, ("a.txt", 0)),
            ("内容B", 0.45, ("b.txt", 0)),
            ("内容A", 0.44, ("a.txt", 1)),
        ]
        out = obj._postprocess_rag_results(rows)
        self.assertEqual(len(out), 2)

    def test_build_story_run_banner_contains_template_and_rag(self):
        obj = self._make_obj()
        banner = obj._build_story_run_banner(
            "写一个逆袭故事",
            "都市",
            [("内容A", 0.52, ("a.txt", 0)), ("内容B", 0.66, ("b.md", 1))],
        )
        self.assertIn("本次模版", banner)
        self.assertIn("RAG检索", banner)
        self.assertIn("a.txt", banner)


if __name__ == "__main__":
    unittest.main()

