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

    def test_extract_pure_story_filters_rag_runtime_lines(self):
        text = (
            "🎭 本次模版：知乎现实故事（策略：固定模版）\n"
            "🔎 RAG检索：命中 3 条（阈值≥0.12）\n"
            "  1. story_a.md（score=0.873）\n"
            "  2. story_b.txt（score=0.764）\n\n"
            "这是第一段正文。\n"
            "这是第二段正文。"
        )
        pure = StoryExtractor.extract_pure_story(text)
        self.assertIn("这是第一段正文。", pure)
        self.assertIn("这是第二段正文。", pure)
        self.assertNotIn("RAG检索", pure)
        self.assertNotIn("score=", pure)

    def test_sanitize_for_publish_removes_control_chars(self):
        text = "这是正文\u200b第一段。\n这是正文第二段。\x07"
        cleaned = StoryExtractor.sanitize_for_publish(text)
        self.assertIn("这是正文第一段。", cleaned)
        self.assertIn("这是正文第二段。", cleaned)
        self.assertNotIn("\u200b", cleaned)
        self.assertNotIn("\x07", cleaned)

    def test_sanitize_for_publish_removes_index_runtime_noises(self):
        text = (
            "No text-like files found under /tmp/data\n"
            "未找到索引，是否现在根据当前数据目录自动构建？\n"
            "🧭 题材纠偏：检测到需求更偏“校园”\n"
            "对齐检查提示：章节标题过于通用\n"
            "正在构建索引...\n"
            "这是正文第一段。\n"
            "这是正文第二段。"
        )
        cleaned = StoryExtractor.sanitize_for_publish(text)
        self.assertIn("这是正文第一段。", cleaned)
        self.assertIn("这是正文第二段。", cleaned)
        self.assertNotIn("No text-like files found under", cleaned)
        self.assertNotIn("未找到索引", cleaned)
        self.assertNotIn("题材纠偏", cleaned)
        self.assertNotIn("对齐检查提示", cleaned)
        self.assertNotIn("正在构建索引", cleaned)

    def test_sanitize_for_zhihu_publish_neutralizes_mentions_but_keeps_email(self):
        text = (
            "正文第一段。\n"
            "@张三 你说得对。\n"
            "邮箱: test.user@example.com\n"
            "他说：@李四 继续。\n"
            "他说@王五，后来沉默。"
        )
        cleaned = StoryExtractor.sanitize_for_zhihu_publish(text)
        self.assertIn("＠张三", cleaned)
        self.assertIn("＠李四", cleaned)
        self.assertIn("他说＠王五", cleaned)
        self.assertIn("test.user@example.com", cleaned)
        self.assertNotIn("@张三", cleaned)
        self.assertNotIn("@李四", cleaned)

    def test_extract_pure_story_keeps_numbered_lines_after_story_started(self):
        text = (
            "这是第一段正文。\n"
            "1. 证据清单。\n"
            "第二段正文。"
        )
        pure = StoryExtractor.extract_pure_story(text)
        self.assertIn("1. 证据清单。", pure)


if __name__ == "__main__":
    unittest.main()
