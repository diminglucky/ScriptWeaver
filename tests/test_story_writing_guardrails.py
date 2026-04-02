import json
import os
from pathlib import Path
import tempfile
import unittest

from src.gui.helpers.story_writing_guardrails import (
    build_non_ai_writing_guardrails,
    build_outline_title_guardrails,
    get_article_title_limits,
    get_chapter_title_limits,
    normalize_article_title,
    normalize_chapter_title,
    reload_story_guardrails,
)


class StoryWritingGuardrailsTests(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("STORY_GUARDRAILS_FILE", None)
        reload_story_guardrails()

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

    def test_custom_guardrails_file_overrides_defaults(self):
        custom = {
            "non_ai": {
                "banned_phrases": ["综上所述", "由此可见"],
                "guardrail_lines": ["禁止模板口吻（如：{banned_phrases}）。"],
            },
            "outline_title": {
                "chapter_title_min_len": 5,
                "chapter_title_max_len": 9,
                "guardrail_lines": [
                    "章节标题控制在 {chapter_title_min_len}-{chapter_title_max_len} 个汉字。"
                ],
            },
            "article_title": {
                "min_len": 10,
                "max_len": 16,
            },
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "guardrails.json"
            path.write_text(json.dumps(custom, ensure_ascii=False), encoding="utf-8")
            os.environ["STORY_GUARDRAILS_FILE"] = str(path)
            reload_story_guardrails()

            text = build_non_ai_writing_guardrails()
            self.assertIn("综上所述", text)
            self.assertIn("由此可见", text)

            outline_text = build_outline_title_guardrails()
            self.assertIn("5-9", outline_text)
            self.assertEqual(get_chapter_title_limits(), (5, 9))
            self.assertEqual(get_article_title_limits(), (10, 16))

            chapter_title = normalize_chapter_title("这个标题明显太长了需要被裁剪")
            self.assertLessEqual(len(chapter_title), 9)

            article_title = normalize_article_title("标题：这是一条非常非常非常长的标题文本用于测试长度")
            self.assertLessEqual(len(article_title), 16)


if __name__ == "__main__":
    unittest.main()
