import os
import unittest

from src.gui.mixins.settings_modules.model_utils import SettingsModelUtilsMixin
from src.gui.mixins.settings_modules.runtime_sync import SettingsRuntimeSyncMixin


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

    def get(self):
        return self._value


class _Dummy(SettingsModelUtilsMixin, SettingsRuntimeSyncMixin):
    def __init__(self):
        self.settings_img_provider = _Var("Img")
        self.settings_img_api_key = _Entry("k")
        self.settings_img_base_url = _Entry("u")
        self.settings_img_model_var = _Var("🖼️ 图像 flux")

        self.img_api_key = _Var("")
        self.img_base_url = _Var("")
        self.img_model = _Var("")
        self.img_api_type = _Var("")

        self.img_api_providers = {"Img": {"provider": "openai", "key": "k", "base_url": "u", "model": "flux"}}
        self.img_api_presets = {}

    def _get_current_img_model(self):
        return "flux"


class SettingsRuntimeSyncTests(unittest.TestCase):
    def test_sync_img_runtime_from_settings(self):
        obj = _Dummy()
        obj._sync_img_runtime_from_settings("Img")
        self.assertEqual(obj.img_api_key.get(), "k")
        self.assertEqual(obj.img_base_url.get(), "u")
        self.assertEqual(obj.img_model.get(), "flux")
        self.assertEqual(obj.img_api_type.get(), "openai")

    def test_sync_img_runtime_from_config(self):
        obj = _Dummy()
        obj.img_api_key.set("")
        obj.img_base_url.set("")
        obj.img_model.set("")
        obj._sync_img_runtime_from_config("Img")
        self.assertEqual(obj.img_api_key.get(), "k")
        self.assertEqual(obj.img_base_url.get(), "u")
        self.assertEqual(obj.img_model.get(), "flux")
        self.assertEqual(obj.img_api_type.get(), "openai")

    def test_sync_img_runtime_from_config_uses_env(self):
        obj = _Dummy()
        os.environ["IMAGE_GEN_API"] = "Img"
        try:
            obj.img_api_key.set("")
            obj._sync_img_runtime_from_config()
            self.assertEqual(obj.img_api_key.get(), "k")
        finally:
            os.environ.pop("IMAGE_GEN_API", None)


if __name__ == "__main__":
    unittest.main()
