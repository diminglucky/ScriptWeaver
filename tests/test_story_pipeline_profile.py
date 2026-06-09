import json
import os
from pathlib import Path
import tempfile
import unittest

from src.gui.helpers.story_pipeline_profile import (
    build_emotion_arc_guidelines,
    build_memory_ledger_prompt,
    build_polish_prompt,
    build_plot_contract_guidelines,
    build_quality_review_prompt,
    build_section_transition_guidelines,
    build_structure_rewrite_prompt,
    get_polish_fallback_fix,
    reload_story_pipeline_profile,
)


class StoryPipelineProfileTests(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("STORY_PIPELINE_PROFILE_FILE", None)
        reload_story_pipeline_profile()

    def test_default_profile_builders_return_expected_keywords(self):
        story_emotion = build_emotion_arc_guidelines(stage="story")
        self.assertIn("情绪", story_emotion)
        self.assertIn("压力递增", story_emotion)
        self.assertIn("不可逆选择", story_emotion)

        review_prompt = build_quality_review_prompt(
            requirement="职场逆袭",
            category="职场",
            section_title="被迫站队",
            preview="他盯着电梯门，迟迟不敢按下去。",
            continuity_contract="【事实锁定】\n- 邮件证据已经暴露，不能重新发现。",
            scene_card_contract="【本章目标】当众证明证据被调包。\n【场景链】场景1：目标/提交证据；阻力/文件被换；行动/追问编号；结果/锁定嫌疑；新问题/谁提前知道。",
        )
        self.assertIn("仅返回 JSON", review_prompt)
        self.assertIn("realism", review_prompt)
        self.assertIn("continuity", review_prompt)
        self.assertIn("escalation", review_prompt)
        self.assertIn("hook_density", review_prompt)
        self.assertIn("不可逆事件", review_prompt)
        self.assertIn("故事状态合同", review_prompt)
        self.assertIn("邮件证据已经暴露", review_prompt)
        self.assertIn("continuity/coherence 必须低于7", review_prompt)
        self.assertIn("本章场景执行卡", review_prompt)
        self.assertIn("当众证明证据被调包", review_prompt)
        self.assertIn("escalation/hook_density/coherence 必须低于7", review_prompt)
        self.assertIn("章节标题：被迫站队", review_prompt)

        transition_rules = build_section_transition_guidelines()
        self.assertIn("承接", transition_rules)
        self.assertIn("接力升级", transition_rules)
        self.assertIn("禁止空降", transition_rules)

        plot_contract = build_plot_contract_guidelines()
        self.assertIn("剧情任务", plot_contract)
        self.assertIn("场景", plot_contract)
        self.assertIn("因果推进", plot_contract)

        memory_prompt = build_memory_ledger_prompt(
            section_title="反转时刻",
            preview="他终于拿到了邮件证据。",
        )
        self.assertIn("记忆账本", memory_prompt)
        self.assertIn("summary", memory_prompt)
        self.assertIn("unresolved_hooks", memory_prompt)
        self.assertIn("character_states", memory_prompt)
        self.assertIn("timeline_events", memory_prompt)
        self.assertIn("open_threads", memory_prompt)
        self.assertIn("当前立场/知道的信息", memory_prompt)
        self.assertIn("不可逆事件", memory_prompt)

        polish_prompt = build_polish_prompt(
            section_title="反转时刻",
            section_content="他站在雨里，手心全是冷汗。",
            fix_goal="修复衔接生硬",
            target_low=600,
            target_high=900,
            current_chars=420,
            previous_tail="他推门离开时，没有回头。",
            continuity_context="【记忆账本】\n- 第1章《旧账》摘要：他拿到关键证据。",
        )
        self.assertIn("连贯性资料", polish_prompt)
        self.assertIn("上章收束句", polish_prompt)
        self.assertIn("记忆账本", polish_prompt)
        self.assertIn("危机升级", polish_prompt)
        self.assertIn("钩子接力", polish_prompt)

        rewrite_prompt = build_structure_rewrite_prompt(
            section_title="反转时刻",
            section_content="他站在雨里，想了很多。",
            fix_goal="补足冲突与代价",
            target_low=700,
            target_high=1000,
            current_chars=300,
            previous_tail="他推门离开时，没有回头。",
            continuity_context="【记忆账本】\n- 第1章《旧账》摘要：他拿到关键证据。",
            section_overview_plan="【核心事件】他必须当众交出证据，却发现证据被调包。",
            event_promise="证据被调包，主角失去唯一筹码",
        )
        self.assertIn("剧情重构版", rewrite_prompt)
        self.assertIn("本章剧情任务书", rewrite_prompt)
        self.assertIn("证据被调包", rewrite_prompt)

    def test_custom_profile_file_overrides_prompt_sections(self):
        custom = {
            "emotion_arc": {
                "story_lines": ["必须体现压抑到释放的情绪曲线。"],
            },
            "quality_review": {
                "rules": ["issues 至少2条；", "禁止任何解释文本；"],
            },
            "polish": {
                "fallback_fix": "重点修复情绪不连贯",
                "rules": [
                    "优先修复：{fix_goal}；",
                    "字数控制在 {target_low}-{target_high}（当前{current_chars}）。",
                ],
            },
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "profile.json"
            path.write_text(json.dumps(custom, ensure_ascii=False), encoding="utf-8")
            os.environ["STORY_PIPELINE_PROFILE_FILE"] = str(path)
            reload_story_pipeline_profile()

            story_emotion = build_emotion_arc_guidelines(stage="story")
            self.assertIn("压抑到释放", story_emotion)

            review_prompt = build_quality_review_prompt(
                requirement="都市情感",
                category="都市",
                section_title="雨夜对峙",
                preview="她握紧伞柄，没有回头。",
            )
            self.assertIn("issues 至少2条", review_prompt)
            self.assertIn("禁止任何解释文本", review_prompt)

            self.assertEqual(get_polish_fallback_fix(), "重点修复情绪不连贯")
            polish_prompt = build_polish_prompt(
                section_title="雨夜对峙",
                section_content="她握紧伞柄，没有回头。",
                fix_goal=get_polish_fallback_fix(),
                target_low=800,
                target_high=1100,
                current_chars=350,
            )
            self.assertIn("重点修复情绪不连贯", polish_prompt)
            self.assertIn("800-1100", polish_prompt)

            rewrite_prompt = build_structure_rewrite_prompt(
                section_title="雨夜对峙",
                section_content="她握紧伞柄，没有回头。",
                fix_goal="结构弱",
                target_low=800,
                target_high=1100,
                current_chars=350,
            )
            self.assertIn("剧情重构版", rewrite_prompt)


if __name__ == "__main__":
    unittest.main()
