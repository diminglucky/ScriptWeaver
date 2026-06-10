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

from src.gui.helpers.deep_horror_rules import (
    build_deep_horror_rules,
    should_apply_deep_horror_rules,
)
from src.gui.mixins.story_modules.prompt_builder_mixin import StoryPromptBuilderMixin


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


class _PromptHarness(StoryPromptBuilderMixin):
    def __init__(self):
        self.target_chars = _Var(2400)
        self.style = _Var("心理惊悚")
        self.story_memory_ledger = []


class DeepHorrorRulesTests(unittest.TestCase):
    def test_rules_trigger_for_horror_but_not_plain_realism(self):
        self.assertTrue(should_apply_deep_horror_rules("来自灵魂深处的恐怖"))
        self.assertTrue(should_apply_deep_horror_rules("悬疑惊悚"))
        self.assertFalse(should_apply_deep_horror_rules("职场成长"))

    def test_rules_reject_stale_horror_props(self):
        text = build_deep_horror_rules(
            stage="story",
            requirement="写一个更惊悚更恐怖的故事",
        )

        self.assertIn("熟悉生活突然不对劲", text)
        self.assertIn("灵魂深处的不安", text)
        self.assertIn("手术刀", text)
        self.assertIn("审讯室", text)
        self.assertIn("廉价道具", text)
        self.assertIn("家人避开某个称呼", text)

    def test_horror_prompt_includes_deep_horror_rules(self):
        prompt = _PromptHarness()._build_prompt(
            "写一个更惊悚更恐怖、来自灵魂深处的不安故事",
            contexts=[],
            category="悬疑",
            outline="",
        )

        self.assertIn("【深层惊悚与反套路恐怖】", prompt)
        self.assertIn("熟悉生活突然不对劲", prompt)
        self.assertIn("手术刀", prompt)
        self.assertIn("废弃医院", prompt)

    def test_non_horror_prompt_does_not_include_deep_horror_rules(self):
        app = _PromptHarness()
        app.style = _Var("克制现实")
        prompt = app._build_prompt(
            "写一个职场成长故事",
            contexts=[],
            category="职场",
            outline="",
        )

        self.assertNotIn("【深层惊悚与反套路恐怖】", prompt)

    def test_hidden_psychological_horror_requirement_triggers_alignment(self):
        app = _PromptHarness()
        block, effective_category, note = app._build_requirement_alignment_block(
            "合租屋里，门锁凌晨自己弹开，群聊里多出一条我没发过的语音，旧照片上的人少了我。",
            "职场",
            stage="story",
        )

        self.assertEqual(effective_category, "心理惊悚")
        self.assertIn("需求对齐锚点", block)
        self.assertIn("门锁", block)
        self.assertIn("群聊", block)
        self.assertIn("旧照片", block)
        self.assertTrue(note == "" or "心理惊悚" in note)


if __name__ == "__main__":
    unittest.main()
