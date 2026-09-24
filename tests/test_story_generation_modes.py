from __future__ import annotations

import unittest

from src.gui.helpers.story_generation_modes import (
    DEFAULT_STORY_GENERATION_MODE,
    get_story_generation_mode_settings,
)
from src.gui.mixins.story_modules.outline_section_utils_mixin import (
    OutlineSectionUtilsMixin,
)


class _Var:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class _Button:
    def __init__(self):
        self.state = None

    def config(self, **kwargs):
        self.state = kwargs.get("state", self.state)


class _Selector:
    def __init__(self):
        self.values = ()
        self.index = None

    def __setitem__(self, key, value):
        if key == "values":
            self.values = tuple(value)

    def current(self, index=None):
        if index is None:
            return self.index
        self.index = index


class _SimplePlanApp(OutlineSectionUtilsMixin):
    def __init__(self):
        self.parsed_sections = []
        self.target_chars = _Var(5400)
        self.section_selector = _Selector()
        self.btn_generate_section = _Button()
        self.btn_continue_next = _Button()
        self.status = _Var("")
        self.generated_content = "old"


class StoryGenerationModeTests(unittest.TestCase):
    def test_default_mode_is_lean(self):
        self.assertEqual(DEFAULT_STORY_GENERATION_MODE, "lean")

    def test_lean_keeps_quality_but_skips_optional_planning_ui(self):
        settings = get_story_generation_mode_settings("lean")
        self.assertTrue(settings["story_quality_review_enabled"])
        self.assertTrue(settings["story_auto_polish_enabled"])
        self.assertFalse(settings["story_global_overview_enabled"])
        self.assertFalse(settings["story_overview_before_generate"])
        self.assertFalse(settings["story_preview_before_apply"])

    def test_balanced_and_strict_enable_auto_polish(self):
        self.assertTrue(get_story_generation_mode_settings("balanced")["story_auto_polish_enabled"])
        self.assertTrue(get_story_generation_mode_settings("strict")["story_auto_polish_enabled"])

    def test_fast_disables_quality_review(self):
        self.assertFalse(get_story_generation_mode_settings("fast")["story_quality_review_enabled"])

    def test_simple_plan_creates_internal_chapters_without_outline_call(self):
        app = _SimplePlanApp()

        created = app._ensure_simple_story_plan("写一个三章悬疑故事")

        self.assertTrue(created)
        self.assertEqual(len(app.parsed_sections), 3)
        self.assertIn("1.", app.current_outline)
        self.assertEqual(app.chapter_blueprints, [])
        self.assertEqual(app.generated_content, "")
        self.assertEqual(app.section_selector.values[0], "1. 第1章 异常开场")


if __name__ == "__main__":
    unittest.main()
