import json
import os
from pathlib import Path
import tempfile
import unittest

from src.gui.helpers.story_prompt_profile import (
    get_outline_core_requirements_text,
    get_outline_output_example_text,
    get_section_intro_text,
    get_section_reminder_text,
    get_section_writing_spec_text,
    get_story_intro_text,
    get_story_reminder_text,
    get_story_writing_spec_text,
    reload_story_prompt_profile,
)


class StoryPromptProfileTests(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("STORY_PROMPT_PROFILE_FILE", None)
        reload_story_prompt_profile()

    def test_default_profile_contains_key_sections(self):
        self.assertIn("章节列表", get_outline_output_example_text())
        core = get_outline_core_requirements_text(
            suggested_sections="4-6",
            chapter_title_min_len=4,
            chapter_title_max_len=12,
        )
        self.assertIn("4-6", core)
        self.assertIn("4-12", core)
        self.assertIn("长篇中文故事", get_story_intro_text())
        self.assertIn("不要写标题", get_story_writing_spec_text())
        self.assertIn("至少 1200 字", get_story_reminder_text(min_chars=1200))
        self.assertIn("第 2/8", get_section_intro_text(section_no=2, total_sections=8))
        self.assertIn("前文", get_section_writing_spec_text())
        self.assertIn("800 字", get_section_reminder_text(min_chars=800))

    def test_custom_profile_file_overrides_defaults(self):
        custom = {
            "outline": {
                "intro": "请先规划目录再写正文。",
                "core_requirements": ["输出 {suggested_sections} 个标题。"],
            },
            "story": {
                "intro": "你是获奖作家，请完成长篇。",
                "writing_spec_lines": ["句子要短促有力。"],
                "reminder_template": "最少写到 {min_chars} 字。",
            },
            "section": {
                "intro_template": "继续第 {section_no}/{total_sections} 段。",
                "writing_spec_lines": ["本节必须推进冲突。"],
                "reminder_template": "本节至少 {min_chars} 字。",
            },
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "story_prompt_profile.json"
            path.write_text(json.dumps(custom, ensure_ascii=False), encoding="utf-8")
            os.environ["STORY_PROMPT_PROFILE_FILE"] = str(path)
            reload_story_prompt_profile()

            core = get_outline_core_requirements_text(
                suggested_sections="3-4",
                chapter_title_min_len=4,
                chapter_title_max_len=10,
            )
            self.assertIn("3-4", core)
            self.assertIn("你是获奖作家", get_story_intro_text())
            self.assertIn("句子要短促有力", get_story_writing_spec_text())
            self.assertIn("最少写到 900 字", get_story_reminder_text(min_chars=900))
            self.assertIn("继续第 1/3 段", get_section_intro_text(section_no=1, total_sections=3))
            self.assertIn("推进冲突", get_section_writing_spec_text())
            self.assertIn("本节至少 600 字", get_section_reminder_text(min_chars=600))


if __name__ == "__main__":
    unittest.main()
