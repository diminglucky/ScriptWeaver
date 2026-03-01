import unittest

from src.gui.mixins.settings_modules.model_utils import SettingsModelUtilsMixin
from src.gui.mixins.settings_modules.provider_ui import SettingsProviderUIMixin


class _Var:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _Entry:
    def __init__(self, value=""):
        self._value = value
        self.show = "*"

    def get(self):
        return self._value

    def delete(self, _a, _b):
        self._value = ""

    def insert(self, _a, value):
        self._value = value

    def config(self, **kwargs):
        if "show" in kwargs:
            self.show = kwargs["show"]


class _Combo(dict):
    def update(self):
        return None


class _Dummy(SettingsModelUtilsMixin, SettingsProviderUIMixin):
    def __init__(self):
        self.api_providers = {"DeepSeek": {"models": ["deepseek-chat"], "base_url": "u1", "key": "k1"}}
        self.img_api_providers = {"Img": {"models": ["flux"], "base_url": "u2", "key": "k2"}}
        self.api_presets = {}
        self.img_api_presets = {}

        self.settings_api_provider = _Var("DeepSeek")
        self.settings_img_provider = _Var("Img")
        self.settings_model_var = _Var("")
        self.settings_img_model_var = _Var("")
        self.settings_combo_model = _Combo()
        self.settings_combo_img_model = _Combo()
        self.settings_base_url = _Entry()
        self.settings_api_key = _Entry()
        self.settings_img_base_url = _Entry()
        self.settings_img_api_key = _Entry()
        self.settings_custom_model = _Entry()
        self.settings_img_custom_model = _Entry()
        self.show_key_var = _Var(False)
        self.show_img_key_var = _Var(False)
        self.synced_img_provider = None

    def _models_need_refresh(self, models):
        return not bool(models)

    def _refresh_models_for_provider(self, provider, key, base_url, log_to_settings=False):
        self.refreshed = (provider, key, base_url, log_to_settings)

    def _sync_img_runtime_from_settings(self, provider_name=None):
        self.synced_img_provider = provider_name


class SettingsProviderUITests(unittest.TestCase):
    def test_is_custom_provider_aliases(self):
        self.assertTrue(SettingsProviderUIMixin._is_custom_provider("Custom"))
        self.assertTrue(SettingsProviderUIMixin._is_custom_provider("自定义"))
        self.assertTrue(SettingsProviderUIMixin._is_custom_provider("閼奉亜鐣炬稊?"))
        self.assertFalse(SettingsProviderUIMixin._is_custom_provider("DeepSeek"))

    def test_on_settings_provider_change(self):
        obj = _Dummy()
        obj._on_settings_provider_change()
        self.assertEqual(obj.settings_combo_model["values"], ["🔵 文本 deepseek-chat"])
        self.assertEqual(obj.settings_model_var.get(), "🔵 文本 deepseek-chat")
        self.assertEqual(obj.settings_base_url.get(), "u1")
        self.assertEqual(obj.settings_api_key.get(), "k1")

    def test_on_settings_img_provider_change(self):
        obj = _Dummy()
        obj._on_settings_img_provider_change()
        self.assertEqual(obj.settings_combo_img_model["values"], ["🖼️ 图像 flux"])
        self.assertEqual(obj.settings_img_model_var.get(), "🖼️ 图像 flux")
        self.assertEqual(obj.settings_img_base_url.get(), "u2")
        self.assertEqual(obj.settings_img_api_key.get(), "k2")
        self.assertEqual(obj.synced_img_provider, "Img")

    def test_toggle_visibility(self):
        obj = _Dummy()
        obj.show_key_var.set(True)
        obj._toggle_key_visibility()
        self.assertEqual(obj.settings_api_key.show, "")
        obj.show_key_var.set(False)
        obj._toggle_key_visibility()
        self.assertEqual(obj.settings_api_key.show, "*")

    def test_get_current_models(self):
        obj = _Dummy()
        obj.settings_model_var.set("🔵 文本 deepseek-chat")
        self.assertEqual(obj._get_current_story_model(), "deepseek-chat")
        obj.settings_img_model_var.set("🖼️ 图像 flux")
        self.assertEqual(obj._get_current_img_model(), "flux")


if __name__ == "__main__":
    unittest.main()
