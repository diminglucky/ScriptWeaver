import unittest

from src.gui.mixins.settings_modules.model_utils import SettingsModelUtilsMixin


class _Dummy(SettingsModelUtilsMixin):
    pass


class SettingsModelUtilsTests(unittest.TestCase):
    def setUp(self):
        self.obj = _Dummy()

    def test_strip_model_label(self):
        self.assertEqual(self.obj._strip_model_label("🔵 文本 deepseek-chat"), "deepseek-chat")
        self.assertEqual(self.obj._strip_model_label("🖼️ 图像 flux"), "flux")
        self.assertEqual(self.obj._strip_model_label("  图片  sdxl  "), "sdxl")

    def test_decorate_model_value(self):
        self.assertEqual(self.obj._decorate_model_value("deepseek-chat", "text"), "🔵 文本 deepseek-chat")
        self.assertEqual(self.obj._decorate_model_value("flux", "image"), "🖼️ 图像 flux")

    def test_decorate_model_list(self):
        result = self.obj._decorate_model_list(["m1", " ", "m2"], "text")
        self.assertEqual(result, ["🔵 文本 m1", "🔵 文本 m2"])

    def test_models_need_refresh(self):
        self.assertTrue(self.obj._models_need_refresh([]))
        self.assertTrue(self.obj._models_need_refresh(["default"]))
        self.assertFalse(self.obj._models_need_refresh(["m1"]))


if __name__ == "__main__":
    unittest.main()
