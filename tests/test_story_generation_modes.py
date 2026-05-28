from __future__ import annotations

import unittest

from src.gui.helpers.story_generation_modes import get_story_generation_mode_settings


class StoryGenerationModeTests(unittest.TestCase):
    def test_balanced_and_strict_enable_auto_polish(self):
        self.assertTrue(get_story_generation_mode_settings("balanced")["story_auto_polish_enabled"])
        self.assertTrue(get_story_generation_mode_settings("strict")["story_auto_polish_enabled"])

    def test_fast_disables_quality_review(self):
        self.assertFalse(get_story_generation_mode_settings("fast")["story_quality_review_enabled"])


if __name__ == "__main__":
    unittest.main()
