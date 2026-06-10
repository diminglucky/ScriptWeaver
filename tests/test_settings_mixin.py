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

    def test_unconfigured_route_falls_back_to_selected_provider(self):
        self.obj.model_routing = {
            "story_generate": {"provider": "Custom", "model": "custom-model"},
        }
        self.obj.api_providers = {
            "Custom": {"key": "", "base_url": "", "models": ["custom-model"]},
            "DeepSeek": {"key": "deepseek-key", "base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
        }
        self.obj.api_presets = {
            "DeepSeek": {"key": "deepseek-key", "base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
        }

        resolved = self.obj._resolve_task_api("story_generate", fallback_provider="DeepSeek")

        self.assertEqual(resolved["provider"], "DeepSeek")
        self.assertEqual(resolved["key"], "deepseek-key")
        self.assertEqual(resolved["base_url"], "https://api.deepseek.com")
        self.assertEqual(resolved["model"], "deepseek-chat")

    def test_story_provider_env_fallback(self):
        self.obj.api_providers["DeepSeek"] = {"key": "", "base_url": "", "model": ""}
        os.environ["STORY_DeepSeek_KEY"] = "story-env-key"
        os.environ["STORY_DeepSeek_BASE_URL"] = "https://story-env.example"
        os.environ["STORY_DeepSeek_MODEL"] = "story-env-model"
        try:
            resolved = self.obj._resolve_task_api("story_generate", fallback_provider="DeepSeek")
        finally:
            os.environ.pop("STORY_DeepSeek_KEY", None)
            os.environ.pop("STORY_DeepSeek_BASE_URL", None)
            os.environ.pop("STORY_DeepSeek_MODEL", None)

        self.assertEqual(resolved["key"], "story-env-key")
        self.assertEqual(resolved["base_url"], "https://story-env.example")
        self.assertEqual(resolved["model"], "story-env-model")


if __name__ == "__main__":
    unittest.main()
