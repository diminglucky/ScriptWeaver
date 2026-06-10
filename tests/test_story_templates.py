from __future__ import annotations

import unittest

from src.gui.helpers.story_templates import get_story_template


class StoryTemplatesTests(unittest.TestCase):
    def test_urban_power_requires_substantial_failure(self):
        template = get_story_template("urban_power")
        rules = "\n".join(template.get("section_rules", []))
        self.assertIn("实质失败", rules)
        self.assertIn("禁止一路顺风", rules)

    def test_suspense_thriller_prefers_psychological_dread(self):
        template = get_story_template("suspense_thriller")
        combined = "\n".join(
            str(item)
            for key in (
                "description",
                "outline_focus",
                "outline_rules",
                "story_focus",
                "story_rules",
                "section_rules",
                "story_system_prompt",
            )
            for item in (
                template.get(key, [])
                if isinstance(template.get(key, []), list)
                else [template.get(key, "")]
            )
        )

        self.assertIn("心理侵入", combined)
        self.assertIn("日常异化", combined)
        self.assertIn("熟悉生活", combined)
        self.assertIn("手术刀", combined)
        self.assertIn("审讯室", combined)
        self.assertIn("禁止", combined)


if __name__ == "__main__":
    unittest.main()
