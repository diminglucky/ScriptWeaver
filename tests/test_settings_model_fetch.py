import unittest
from unittest.mock import patch
import types

from src.gui.mixins.settings_modules.model_fetch import SettingsModelFetchMixin
from src.gui.mixins.settings_modules.model_utils import SettingsModelUtilsMixin


class _Var:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _Dummy(SettingsModelUtilsMixin, SettingsModelFetchMixin):
    def __init__(self):
        self.api_providers = {"DeepSeek": {"models": [], "key": "", "base_url": ""}}
        self.settings_api_provider = _Var("DeepSeek")
        self.settings_model_var = _Var("")
        self.settings_combo_model = {}
        self.model_route_vars = {}
        self._model_fetching = set()

    def _ui(self, func, *args, **kwargs):
        return func(*args, **kwargs)


class _Resp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _ImmediateThread:
    def __init__(self, target=None, daemon=None):
        self._target = target

    def start(self):
        if self._target:
            self._target()


class SettingsModelFetchTests(unittest.TestCase):
    def test_fetch_models_from_api_parses_and_dedup(self):
        fake_requests = types.SimpleNamespace(
            get=lambda *args, **kwargs: _Resp(200, {"data": [{"id": "m1"}, {"name": "m2"}, {"id": "m1"}]})
        )
        obj = _Dummy()
        with patch.dict("sys.modules", {"requests": fake_requests}):
            models, err = obj._fetch_models_from_api("k", "https://example.com/v1")
            self.assertIsNone(err)
            self.assertEqual(models, ["m1", "m2"])

    @patch("src.gui.mixins.settings_modules.model_fetch.threading.Thread", _ImmediateThread)
    def test_refresh_models_for_provider_updates_state_and_ui(self):
        obj = _Dummy()
        obj._fetch_models_from_api = lambda api_key, base_url: (["deepseek-chat"], None)

        obj._refresh_models_for_provider("DeepSeek", "k1", "https://example.com/v1")

        self.assertEqual(obj.api_providers["DeepSeek"]["models"], ["deepseek-chat"])
        self.assertEqual(obj.api_providers["DeepSeek"]["key"], "k1")
        self.assertEqual(obj.api_providers["DeepSeek"]["base_url"], "https://example.com/v1")
        self.assertEqual(obj.settings_combo_model["values"], ["🔵 文本 deepseek-chat"])
        self.assertEqual(obj.settings_model_var.get(), "🔵 文本 deepseek-chat")


if __name__ == "__main__":
    unittest.main()
