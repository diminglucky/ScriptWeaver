from __future__ import annotations

import unittest

from src.gui.helpers.story_templates import get_story_template, resolve_story_template


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

    def test_default_template_adapts_to_suspense_request(self):
        resolved = resolve_story_template(
            "zhihu_realistic",
            "fixed",
            requirement="写一个收到死亡通知的灵异悬疑故事",
            category="悬疑",
        )

        self.assertEqual(resolved["key"], "suspense_thriller")
        self.assertEqual(resolved["base_key"], "suspense_thriller")

    def test_explicit_non_default_template_is_preserved(self):
        resolved = resolve_story_template(
            "urban_power",
            "fixed",
            requirement="写一个悬疑故事里的逆袭主角",
            category="悬疑",
        )

        self.assertEqual(resolved["key"], "urban_power")


if __name__ == "__main__":
    unittest.main()
