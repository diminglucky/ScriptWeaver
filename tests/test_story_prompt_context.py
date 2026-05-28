from __future__ import annotations

import unittest

from src.gui.mixins.story_modules.prompt_context_mixin import StoryPromptContextMixin


class _Harness(StoryPromptContextMixin):
    def __init__(self):
        self.story_memory_ledger = [
            {
                "chapter_index": 0,
                "chapter_title": "旧账曝光",
                "summary": "主角拿到邮件证据后被迫站队。",
                "plot_points": ["邮件证据暴露", "上司开始威胁主角"],
                "relation_changes": ["主角与上司公开决裂"],
                "unresolved_hooks": ["匿名发件人的真实身份仍未揭开"],
                "state_shift": "主角从观望转为反击",
            }
        ]


class StoryPromptContextTests(unittest.TestCase):
    def test_compressed_story_state_keeps_facts_hooks_and_rules(self):
        h = _Harness()
        text = h._build_compressed_story_state(
            1,
            "他推开会议室的门，发现所有人都在等他。",
        )
        self.assertIn("已发生事实", text)
        self.assertIn("人物关系", text)
        self.assertIn("未回收钩子", text)
        self.assertIn("匿名发件人", text)
        self.assertIn("不得重置人物状态", text)
        self.assertIn("更高风险的新钩子", text)

    def test_story_skill_pack_contains_core_skills(self):
        h = _Harness()
        text = h._build_story_skill_pack()
        self.assertIn("写作 Skills", text)
        self.assertIn("危机阶梯", text)
        self.assertIn("钩子接力", text)
        self.assertIn("反转合法性", text)
        self.assertIn("逻辑锁链", text)


if __name__ == "__main__":
    unittest.main()
