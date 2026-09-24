import unittest

from src.gui.mixins.enhancements_modules.shortcuts import KeyboardShortcuts, ShortcutsMixin


class KeyboardShortcutsNormalizeTests(unittest.TestCase):
    def test_normalize_invalid_root_object_falls_back_to_defaults(self):
        normalized = KeyboardShortcuts._normalize_shortcuts_config(["bad"])  # type: ignore[arg-type]
        self.assertEqual(normalized, KeyboardShortcuts.DEFAULT_SHORTCUTS)

    def test_normalize_keeps_defaults_and_applies_valid_overrides(self):
        normalized = KeyboardShortcuts._normalize_shortcuts_config(
            {
                "<Control-n>": ["new_project_alt", "New Project Alt"],
                "<Control-x>": ["custom_action", "Custom Action"],
                "<Control-bad-1>": ["only_action"],
                "<Control-bad-2>": "bad",
            }
        )
        self.assertEqual(normalized["<Control-n>"], ("new_project_alt", "New Project Alt"))
        self.assertEqual(normalized["<Control-x>"], ("custom_action", "Custom Action"))
        self.assertEqual(normalized["<Control-o>"], KeyboardShortcuts.DEFAULT_SHORTCUTS["<Control-o>"])
        self.assertNotIn("<Control-bad-1>", normalized)
        self.assertNotIn("<Control-bad-2>", normalized)


class ShortcutActionTests(unittest.TestCase):
    def test_generate_story_shortcut_prefers_one_click_generation(self):
        calls = []

        class Dummy(ShortcutsMixin):
            def on_generate(self):
                calls.append("single")

            def on_auto_generate_all(self):
                calls.append("auto")

        Dummy()._shortcut_generate_story()

        self.assertEqual(calls, ["auto"])

    def test_generate_story_shortcut_falls_back_to_single_generation(self):
        calls = []

        class Dummy(ShortcutsMixin):
            def on_generate(self):
                calls.append("single")

        Dummy()._shortcut_generate_story()

        self.assertEqual(calls, ["single"])


if __name__ == "__main__":
    unittest.main()
