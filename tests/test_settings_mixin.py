import os
import unittest

from src.gui.mixins.settings_refactored import SettingsMixin


class _Var:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value


class _DummySettings(SettingsMixin):
    pass


class SettingsMixinResolveTaskApiTests(unittest.TestCase):
    def setUp(self):
        self.obj = _DummySettings()
        self.obj.model_routing = {}
        self.obj._model_routing_loaded = True
        self.obj.api_providers = {
            "DeepSeek": {"key": "", "base_url": "", "model": ""},
        }
        self.obj.api_presets = {}
        self.obj.settings_api_provider = _Var("DeepSeek")
        self.obj.api_preset = _Var("DeepSeek")

    def test_deepseek_legacy_env_fallback(self):
        os.environ["DEEPSEEK_API_KEY"] = "legacy-key"
        os.environ["DEEPSEEK_BASE_URL"] = "https://legacy.example/v1"
        os.environ["DEEPSEEK_MODEL"] = "legacy-model"
        try:
            resolved = self.obj._resolve_task_api("story_generate", fallback_provider="DeepSeek")
        finally:
            os.environ.pop("DEEPSEEK_API_KEY", None)
            os.environ.pop("DEEPSEEK_BASE_URL", None)
            os.environ.pop("DEEPSEEK_MODEL", None)

        self.assertEqual(resolved["provider"], "DeepSeek")
        self.assertEqual(resolved["key"], "legacy-key")
        self.assertEqual(resolved["base_url"], "https://legacy.example/v1")
        self.assertEqual(resolved["model"], "legacy-model")

    def test_provider_config_key_has_priority(self):
        self.obj.api_providers["DeepSeek"]["key"] = "provider-key"
        os.environ["DEEPSEEK_API_KEY"] = "legacy-key"
        try:
            resolved = self.obj._resolve_task_api("story_generate", fallback_provider="DeepSeek")
        finally:
            os.environ.pop("DEEPSEEK_API_KEY", None)

        self.assertEqual(resolved["key"], "provider-key")


if __name__ == "__main__":
    unittest.main()
