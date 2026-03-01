import unittest
from unittest.mock import patch

from src.gui.mixins.settings_modules.model_routing_ui import SettingsModelRoutingUIMixin
from src.gui.mixins.settings_modules.model_utils import SettingsModelUtilsMixin


class _Var:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _Log:
    def __init__(self):
        self.lines = []

    def insert(self, *_args):
        self.lines.append(_args[-1])

    def see(self, *_args):
        return None


class _Dummy(SettingsModelUtilsMixin, SettingsModelRoutingUIMixin):
    def __init__(self):
        self.api_providers = {"DeepSeek": {"models": ["deepseek-chat"], "key": "k", "base_url": "u"}}
        self.api_presets = {}
        self.settings_api_provider = _Var("DeepSeek")
        self.settings_api_key = _Var("k")
        self.settings_base_url = _Var("u")
        self.model_route_vars = {
            "story_generate": {
                "provider_var": _Var("DeepSeek"),
                "model_var": _Var(""),
                "combo_model": {},
                "task_key": "story_generate",
            }
        }
        self.settings_log = _Log()
        self.model_routing = {}
        self._model_routing_loaded = False
        self.saved = False
        self.refreshed = []

    def _refresh_models_for_provider(self, provider, key, base_url, log_to_settings=False):
        self.refreshed.append((provider, key, base_url, log_to_settings))

    def _ensure_model_routing_loaded(self):
        return None

    def _get_task_route(self, task_key):
        return {"provider": "DeepSeek", "model": "deepseek-chat"} if task_key == "story_generate" else {}

    def _save_model_routing_to_file(self):
        self.saved = True


class SettingsModelRoutingUITests(unittest.TestCase):
    def test_on_route_provider_change_sets_decorated_default(self):
        obj = _Dummy()
        obj._on_route_provider_change("story_generate")
        self.assertEqual(obj.model_route_vars["story_generate"]["combo_model"]["values"], ["🔵 文本 deepseek-chat"])
        self.assertEqual(obj.model_route_vars["story_generate"]["model_var"].get(), "🔵 文本 deepseek-chat")

    def test_on_route_provider_change_refresh_when_empty_models(self):
        obj = _Dummy()
        obj.api_providers["DeepSeek"]["models"] = []
        obj._on_route_provider_change("story_generate")
        self.assertEqual(obj.refreshed, [("DeepSeek", "k", "u", False)])

    def test_load_model_routing_to_ui(self):
        obj = _Dummy()
        obj._load_model_routing_to_ui()
        self.assertEqual(obj.model_route_vars["story_generate"]["provider_var"].get(), "DeepSeek")
        self.assertEqual(obj.model_route_vars["story_generate"]["model_var"].get(), "🔵 文本 deepseek-chat")

    @patch("src.gui.mixins.settings_modules.model_routing_ui.messagebox.showinfo")
    def test_save_model_routing_settings(self, _mock_info):
        obj = _Dummy()
        obj.model_route_vars["story_generate"]["model_var"].set("🔵 文本 deepseek-chat")
        obj._save_model_routing_settings()
        self.assertTrue(obj.saved)
        self.assertTrue(obj._model_routing_loaded)
        self.assertEqual(obj.model_routing["story_generate"]["provider"], "DeepSeek")
        self.assertEqual(obj.model_routing["story_generate"]["model"], "deepseek-chat")


if __name__ == "__main__":
    unittest.main()
