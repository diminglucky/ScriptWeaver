import unittest

from src.utils.story_extractor import StoryExtractor


class StoryExtractorTests(unittest.TestCase):
    def test_extract_pure_story_filters_outline_and_runtime_markers(self):
        text = (
            "🎭 本次模版：知乎现实故事（策略：固定模版）\n\n"
            "生成目录中...\n\n"
            "目录（共3章，预估字数≈1200字）\n\n"
            "1. 开场冲突\n"
            "2. 危机升级\n"
            "3. 最终反转\n\n"
            "==================================================\n"
            "【第 1/3 章：开场冲突】\n\n"
            "第一段正文。\n\n"
            "第二段正文。\n\n"
            "✅ 第 1 章完成！本章字数：456 字\n"
            "⏳ 准备生成下一章...\n"
            "==================================================\n"
            "【第 2/3 章：危机升级】\n\n"
            "第三段正文。"
        )
        pure = StoryExtractor.extract_pure_story(text)
        self.assertIn("第一段正文。", pure)
        self.assertIn("第二段正文。", pure)
        self.assertIn("第三段正文。", pure)
        self.assertNotIn("目录（共3章", pure)
        self.assertNotIn("【第 1/3 章", pure)
        self.assertNotIn("准备生成下一章", pure)

    def test_get_story_preview(self):
        text = "目录\n1. A\n2. B\n\n======\n\n这是正文第一句。这是正文第二句。这是正文第三句。"
        preview = StoryExtractor.get_story_preview(text, max_length=15)
        self.assertTrue(preview)
        self.assertNotIn("目录", preview)


if __name__ == "__main__":
    unittest.main()

