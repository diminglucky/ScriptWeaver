from __future__ import annotations

import unittest

from src.gui.helpers.story_templates import get_story_template


class StoryTemplatesTests(unittest.TestCase):
    def test_urban_power_requires_substantial_failure(self):
        template = get_story_template("urban_power")
        rules = "\n".join(template.get("section_rules", []))
        self.assertIn("实质失败", rules)
        self.assertIn("禁止一路顺风", rules)


if __name__ == "__main__":
    unittest.main()
