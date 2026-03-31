from __future__ import annotations

import unittest

from src.gui.helpers.story_creativity import build_story_creativity_block
from src.gui.helpers.story_creativity import normalize_story_creativity_mode


class StoryCreativityTests(unittest.TestCase):
    def test_normalize_mode(self):
        self.assertEqual(normalize_story_creativity_mode("stable"), "stable")
        self.assertEqual(normalize_story_creativity_mode("WILD"), "wild")
        self.assertEqual(normalize_story_creativity_mode("unknown"), "blend")

    def test_stable_mode_returns_empty_block(self):
        block = build_story_creativity_block(
            "stable",
            requirement="写一个创业故事",
            category="职场",
            style_hint="快节奏",
            stage="story",
        )
        self.assertEqual(block, "")

    def test_blend_mode_has_signature_and_constraints(self):
        block = build_story_creativity_block(
            "blend",
            requirement="写一个创业故事",
            category="职场",
            style_hint="快节奏",
            stage="outline",
            nonce="seed-001",
            primary_template_key="zhihu_realistic",
        )
        self.assertIn("创意签名", block)
        self.assertIn("结构扰动建议", block)
        self.assertIn("目录层面要显式体现", block)
        self.assertIn("跨模版融合", block)


if __name__ == "__main__":
    unittest.main()
