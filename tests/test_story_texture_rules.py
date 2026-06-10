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

from src.gui.helpers.story_texture_rules import build_story_texture_rules
from src.gui.mixins.story_modules.prompt_builder_mixin import StoryPromptBuilderMixin


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


class _PromptHarness(StoryPromptBuilderMixin):
    def __init__(self):
        self.target_chars = _Var(2200)
        self.style = _Var("知乎回答体")
        self.story_memory_ledger = []


class StoryTextureRulesTests(unittest.TestCase):
    def test_texture_rules_push_lived_in_detail_and_momentum(self):
        text = build_story_texture_rules(stage="story")

        self.assertIn("亲历者", text)
        self.assertIn("可验证细节", text)
        self.assertIn("每 4-6 段必须推进一次新信息", text)
        self.assertIn("对话要有潜台词", text)
        self.assertIn("真实代价", text)

    def test_full_story_prompt_includes_texture_rules(self):
        prompt = _PromptHarness()._build_prompt(
            "写一个真实细腻、开头很抓人的知乎风故事",
            contexts=[],
            category="现实",
            outline="",
        )

        self.assertIn("【真实细腻与吸引力】", prompt)
        self.assertIn("关键场景至少落到时间、地点、空间位置", prompt)
        self.assertIn("每 4-6 段必须推进一次新信息", prompt)

    def test_section_prompt_includes_texture_rules(self):
        prompt = _PromptHarness()._build_section_prompt(
            section={"title": "旧聊天记录", "items": ["主角发现一条被删掉的聊天记录"]},
            section_index=1,
            total_sections=3,
            previous_content="他把手机扣在桌上，屏幕还亮着。",
            requirement="写一个真实细腻、开头很抓人的知乎风故事",
            contexts=[],
            category="现实",
            style_part="知乎回答体",
            target_chars_per_section=1200,
        )

        self.assertIn("【真实细腻与吸引力】", prompt)
        self.assertIn("本章必须像一个亲历者", prompt)
        self.assertIn("真实代价", prompt)


if __name__ == "__main__":
    unittest.main()
