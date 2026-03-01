import unittest
from unittest.mock import patch

from src.gui.mixins.settings_modules.settings_actions import SettingsActionsMixin


class _Dummy(SettingsActionsMixin):
    def __init__(self):
        self.calls = []

    def export_config(self, include_keys=False):
        self.calls.append(("export_config", include_keys))

    def clear_cache(self):
        self.calls.append(("clear_cache",))

    def _update_cache_size(self):
        self.calls.append(("update_cache_size",))

    def _load_api_config_from_file(self):
        self.calls.append(("load_api_config",))

    def _ensure_model_routing_loaded(self):
        self.calls.append(("ensure_model_routing",))

    def _on_settings_provider_change(self):
        self.calls.append(("story_provider_change",))

    def _on_settings_img_provider_change(self):
        self.calls.append(("img_provider_change",))

    def _load_model_routing_to_ui(self):
        self.calls.append(("load_routing_ui",))

    def _load_quick_api_switch(self):
        self.calls.append(("load_quick_switch",))


class _DummyNoEnhancements(SettingsActionsMixin):
    def _update_cache_size(self):
        pass

    def _on_settings_provider_change(self):
        pass

    def _on_settings_img_provider_change(self):
        pass


class SettingsActionsTests(unittest.TestCase):
    @patch("src.gui.mixins.settings_modules.settings_actions.messagebox.askyesno", return_value=True)
    def test_export_with_keys(self, _mock_ask):
        obj = _Dummy()
        obj._export_config_with_keys()
        self.assertIn(("export_config", True), obj.calls)

    @patch("src.gui.mixins.settings_modules.settings_actions.messagebox.askyesno", return_value=True)
    def test_clear_cache_ui(self, _mock_ask):
        obj = _Dummy()
        obj._clear_cache_ui()
        self.assertEqual(obj.calls, [("clear_cache",), ("update_cache_size",)])

    @patch("src.gui.mixins.settings_modules.settings_actions.messagebox.showwarning")
    def test_import_config_ui_warns_when_unavailable(self, mock_warn):
        obj = _DummyNoEnhancements()
        obj._import_config_ui()
        mock_warn.assert_called_once()

    @patch("src.gui.mixins.settings_modules.settings_actions.messagebox.showwarning")
    def test_export_config_ui_warns_when_unavailable(self, mock_warn):
        obj = _DummyNoEnhancements()
        obj._export_config_ui()
        mock_warn.assert_called_once()

    @patch("src.gui.mixins.settings_modules.settings_actions.messagebox.showwarning")
    def test_clear_cache_ui_warns_when_unavailable(self, mock_warn):
        obj = _DummyNoEnhancements()
        obj._clear_cache_ui()
        mock_warn.assert_called_once()

    def test_load_settings_values_calls_hooks(self):
        obj = _Dummy()
        obj._load_settings_values()
        self.assertEqual(
            obj.calls,
            [
                ("load_api_config",),
                ("ensure_model_routing",),
                ("story_provider_change",),
                ("img_provider_change",),
                ("load_routing_ui",),
                ("load_quick_switch",),
            ],
        )


if __name__ == "__main__":
    unittest.main()
