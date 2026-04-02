import json
import os
from pathlib import Path
import tempfile
import unittest

from src.gui.helpers.story_pipeline_profile import (
    build_emotion_arc_guidelines,
    build_memory_ledger_prompt,
    build_polish_prompt,
    build_quality_review_prompt,
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

        review_prompt = build_quality_review_prompt(
            requirement="职场逆袭",
            category="职场",
            section_title="被迫站队",
            preview="他盯着电梯门，迟迟不敢按下去。",
        )
        self.assertIn("仅返回 JSON", review_prompt)
        self.assertIn("realism", review_prompt)
        self.assertIn("章节标题：被迫站队", review_prompt)

        memory_prompt = build_memory_ledger_prompt(
            section_title="反转时刻",
            preview="他终于拿到了邮件证据。",
        )
        self.assertIn("记忆账本", memory_prompt)
        self.assertIn("summary", memory_prompt)

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


if __name__ == "__main__":
    unittest.main()

