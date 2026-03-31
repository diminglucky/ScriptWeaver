import unittest

from src.gui.helpers.story_templates import (
    DEFAULT_STORY_TEMPLATE_STRATEGY,
    normalize_story_template_strategy,
    resolve_story_template,
)


class StoryTemplateStrategyTests(unittest.TestCase):
    def test_normalize_strategy(self):
        self.assertEqual(normalize_story_template_strategy("fixed"), "fixed")
        self.assertEqual(normalize_story_template_strategy("ROTATE"), "rotate")
        self.assertEqual(normalize_story_template_strategy("invalid"), DEFAULT_STORY_TEMPLATE_STRATEGY)

    def test_resolve_fixed_returns_selected_template(self):
        profile = resolve_story_template("urban_power", "fixed", nonce="n1", requirement="逆袭", category="都市")
        self.assertEqual(profile.get("resolved_key"), "urban_power")
        self.assertEqual(profile.get("strategy"), "fixed")

    def test_resolve_rotate_is_deterministic_for_same_seed(self):
        p1 = resolve_story_template("urban_power", "rotate", nonce="n2", requirement="逆袭", category="都市")
        p2 = resolve_story_template("urban_power", "rotate", nonce="n2", requirement="逆袭", category="都市")
        self.assertEqual(p1.get("resolved_key"), p2.get("resolved_key"))
        self.assertEqual(p1.get("strategy"), "rotate")

    def test_resolve_shuffle_prefers_diversity(self):
        profile = resolve_story_template("urban_power", "shuffle", nonce="n3", requirement="逆袭", category="都市")
        self.assertEqual(profile.get("strategy"), "shuffle")
        self.assertNotEqual(profile.get("resolved_key"), "")


if __name__ == "__main__":
    unittest.main()

