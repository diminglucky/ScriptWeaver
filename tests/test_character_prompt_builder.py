from __future__ import annotations

import unittest

from src.gui.helpers.character_prompt_builder import CharacterPromptBuilder


class CharacterPromptBuilderTests(unittest.TestCase):
    def test_extract_appearance_only_exists_and_filters(self):
        self.assertTrue(hasattr(CharacterPromptBuilder, "extract_appearance_only"))
        text = "背景是雨夜街道。外貌：黑发、深色眼睛、高个子，穿黑色风衣。动作：奔跑。"
        result = CharacterPromptBuilder.extract_appearance_only(text)
        self.assertIn("黑发", result)
        self.assertIn("风衣", result)
        self.assertNotIn("背景", result)

    def test_build_retry_prompt_returns_non_empty(self):
        prompt = CharacterPromptBuilder.build_retry_prompt(
            description="年轻男性，短发，黑色外套，面部有浅疤。",
            language="zh",
        )
        self.assertIsInstance(prompt, str)
        self.assertTrue(prompt.strip())


if __name__ == "__main__":
    unittest.main()
