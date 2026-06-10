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

from src.gui.helpers.zhihu_hook_rules import (
    build_zhihu_hook_opening_rules,
    build_zhihu_section_opening_rules,
)
from src.gui.mixins.story_modules.prompt_builder_mixin import StoryPromptBuilderMixin


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


class _PromptHarness(StoryPromptBuilderMixin):
    def __init__(self):
        self.target_chars = _Var(1800)
        self.style = _Var("知乎回答体")
        self.story_memory_ledger = []


class ZhihuHookRulesTests(unittest.TestCase):
    def test_story_opening_rules_are_specific_and_front_loaded(self):
        text = build_zhihu_hook_opening_rules(first_section=True)

        self.assertIn("第一句必须直接抛出强钩子", text)
        self.assertIn("反常事实", text)
        self.assertIn("前 150 字禁止写天气", text)
        self.assertIn("前 300 字必须完成", text)

    def test_later_section_rules_preserve_continuity_without_soft_restart(self):
        text = build_zhihu_section_opening_rules(section_index=2)

        self.assertIn("承接上章最后一个动作", text)
        self.assertIn("禁止用", text)
        self.assertIn("前 120 字必须同时做到", text)

    def test_full_story_prompt_includes_hook_rules(self):
        prompt = _PromptHarness()._build_prompt(
            "写一个知乎风悬疑故事",
            contexts=[],
            category="悬疑",
            outline="",
        )

        self.assertIn("【知乎强钩子开头】", prompt)
        self.assertIn("前 150 字禁止写天气", prompt)
        self.assertIn("前 300 字必须完成", prompt)

    def test_first_section_prompt_includes_hook_rules(self):
        prompt = _PromptHarness()._build_section_prompt(
            section={"title": "死亡通知", "items": ["主角收到自己的死亡通知"]},
            section_index=0,
            total_sections=3,
            previous_content="",
            requirement="写一个知乎风悬疑故事",
            contexts=[],
            category="悬疑",
            style_part="知乎回答体",
            target_chars_per_section=1200,
        )

        self.assertIn("【知乎强钩子开头】", prompt)
        self.assertIn("第一句必须直接抛出强钩子", prompt)
        self.assertIn("前 300 字必须完成", prompt)


if __name__ == "__main__":
    unittest.main()
