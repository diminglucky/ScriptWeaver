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
                "character_states": ["主角：已拿到邮件证据/知道上司威胁/手心发冷/不能公开求助"],
                "timeline_events": ["下午三点在会议室外收到匿名邮件", "下午三点半被迫站队"],
                "open_threads": ["邮件原始发件服务器未查清"],
            }
        ]


class StoryPromptContextTests(unittest.TestCase):
    def test_compressed_story_state_keeps_facts_hooks_and_rules(self):
        h = _Harness()
        text = h._build_compressed_story_state(
            1,
            "他推开会议室的门，发现所有人都在等他。",
        )
        self.assertIn("事实锁定", text)
        self.assertIn("人物关系与立场锁定", text)
        self.assertIn("未回收钩子队列", text)
        self.assertIn("匿名发件人", text)
        self.assertIn("邮件原始发件服务器", text)
        self.assertIn("下午三点在会议室外", text)
        self.assertIn("不得改写已发生事实", text)
        self.assertIn("章末新钩子必须改变下一章行动方案", text)

    def test_story_state_contract_locks_facts_relations_hooks_and_tail(self):
        h = _Harness()
        text = h._build_story_state_contract(
            1,
            "他推开会议室的门，发现所有人都在等他。",
        )

        self.assertIn("即时承接点", text)
        self.assertIn("本章第一场必须接住", text)
        self.assertIn("邮件证据暴露", text)
        self.assertIn("主角与上司公开决裂", text)
        self.assertIn("主角从观望转为反击", text)
        self.assertIn("匿名发件人的真实身份仍未揭开", text)
        self.assertIn("主角：已拿到邮件证据", text)
        self.assertIn("邮件原始发件服务器未查清", text)
        self.assertIn("下午三点半被迫站队", text)
        self.assertIn("新反转必须从上述事实", text)

    def test_story_memory_context_ignores_invalid_chapter_index_rows(self):
        h = _Harness()
        h.story_memory_ledger.insert(
            0,
            {
                "chapter_index": "not-a-number",
                "chapter_title": "坏数据",
                "summary": "这条旧数据不应打断上下文构建。",
            },
        )

        memory_text = h._build_story_memory_context(1)
        contract_text = h._build_story_state_contract(1, "他推开会议室的门。")
        transition_text = h._build_section_transition_context(1, "他推开会议室的门。")

        self.assertIn("旧账曝光", memory_text)
        self.assertIn("邮件证据暴露", contract_text)
        self.assertIn("上章事件摘要", transition_text)
        self.assertNotIn("坏数据", memory_text + contract_text + transition_text)

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
