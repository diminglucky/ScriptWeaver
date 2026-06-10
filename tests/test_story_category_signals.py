from __future__ import annotations

import sys
import types
import unittest

if "PIL" not in sys.modules:
    pil_mod = types.ModuleType("PIL")
    pil_mod.Image = types.SimpleNamespace()
    pil_mod.ImageDraw = types.SimpleNamespace()
    pil_mod.ImageFont = types.SimpleNamespace()
    sys.modules["PIL"] = pil_mod
    sys.modules["PIL.Image"] = pil_mod.Image
    sys.modules["PIL.ImageDraw"] = pil_mod.ImageDraw
    sys.modules["PIL.ImageFont"] = pil_mod.ImageFont

from src.gui.helpers.story_category_signals import (
    infer_story_category,
    normalize_story_category_label,
    score_story_category,
)


class StoryCategorySignalsTests(unittest.TestCase):
    def test_normalizes_horror_aliases(self):
        self.assertEqual(normalize_story_category_label("惊悚"), "心理惊悚")
        self.assertEqual(normalize_story_category_label("恐怖"), "心理惊悚")

    def test_infers_hidden_psychological_horror_signals(self):
        text = "合租屋里，门锁总在凌晨自己弹开，群聊里多出一条我没发过的语音，旧照片上的人少了我。"

        category, score = infer_story_category(text)

        self.assertEqual(category, "心理惊悚")
        self.assertGreaterEqual(score, 10)

    def test_scores_life_based_signals_for_psychological_horror(self):
        text = "陌生短信提醒我回家，监控里走廊多出一个影子，记忆却说那晚我一直在加班。"

        self.assertGreater(score_story_category(text, "心理惊悚"), 0)
        self.assertGreater(score_story_category(text, "心理惊悚"), score_story_category(text, "职场"))


if __name__ == "__main__":
    unittest.main()
