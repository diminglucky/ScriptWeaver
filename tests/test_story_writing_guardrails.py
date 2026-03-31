import unittest

from src.gui.helpers.story_writing_guardrails import (
    build_non_ai_writing_guardrails,
    build_outline_title_guardrails,
    normalize_article_title,
    normalize_chapter_title,
)


class StoryWritingGuardrailsTests(unittest.TestCase):
    def test_build_non_ai_guardrails_contains_key_phrases(self):
        text = build_non_ai_writing_guardrails()
        self.assertIn("首先", text)
        self.assertIn("可验证细节", text)

    def test_build_outline_guardrails_contains_length_rule(self):
        text = build_outline_title_guardrails()
        self.assertIn("4-12", text)

    def test_normalize_chapter_title_strips_prefix_and_clamps(self):
        title = normalize_chapter_title("1. 在雨夜里被迫签下终身竞业协议后他开始反击")
        self.assertFalse(title.startswith("1."))
        self.assertLessEqual(len(title), 12)
        self.assertTrue(title)

    def test_normalize_article_title_strips_noise_and_clamps(self):
        title = normalize_article_title("标题：\"这场同学会之后，我才知道她离婚是假的，但我的升职也没了\"")
        self.assertNotIn("标题", title)
        self.assertLessEqual(len(title), 20)
        self.assertTrue(title)


if __name__ == "__main__":
    unittest.main()
