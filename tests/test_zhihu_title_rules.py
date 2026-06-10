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

from src.gui.helpers.zhihu_title_rules import build_zhihu_title_prompt


class ZhihuTitleRulesTests(unittest.TestCase):
    def test_title_prompt_requires_candidates_and_specific_hook(self):
        prompt = build_zhihu_title_prompt(
            story_summary="男主收到自己的死亡通知，镜子里的人先开口。",
            min_len=14,
            max_len=30,
            banned_phrase_preview="总的来说 / 不难发现",
        )

        self.assertIn("8 个候选标题", prompt)
        self.assertIn("反常事实", prompt)
        self.assertIn("具体钩子", prompt)
        self.assertIn("只输出最终标题", prompt)
        self.assertIn("14-30字", prompt)


if __name__ == "__main__":
    unittest.main()
