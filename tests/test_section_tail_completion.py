import unittest

from src.gui.mixins.story_modules.outline_generator import OutlineGeneratorMixin


class _Dummy(OutlineGeneratorMixin):
    pass


class SectionTailCompletionTests(unittest.TestCase):
    def setUp(self):
        self.obj = _Dummy()

    def test_tail_complete_with_terminal_punctuation(self):
        self.assertTrue(self.obj._is_section_tail_complete("他把门关上，终于松了口气。"))
        self.assertTrue(self.obj._is_section_tail_complete("她回头笑了笑！”"))

    def test_tail_incomplete_without_terminal_punctuation(self):
        self.assertFalse(self.obj._is_section_tail_complete("他把门关上，终于松了口气"))
        self.assertFalse(self.obj._is_section_tail_complete("像个慈祥的长"))


if __name__ == "__main__":
    unittest.main()

