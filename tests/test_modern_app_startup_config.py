import unittest

from src.gui.modern_app import ModernApp


class _DummyStartup:
    def __init__(self):
        self.calls = []

    def _load_api_config_from_file(self):
        self.calls.append("load_file")
        self._api_config_from_file_loaded = True

    def _auto_load_api_config(self):
        self.calls.append("load_env")

    def _auto_load_story_api_selection(self):
        self.calls.append("load_story_api")

    def _auto_restore_last_project_on_startup(self):
        self.calls.append("restore_project")


class ModernAppStartupConfigTests(unittest.TestCase):
    def test_startup_loads_file_when_not_loaded(self):
        obj = _DummyStartup()
        ModernApp._startup_load_configs(obj)
        self.assertEqual(obj.calls, ["load_file", "load_env", "load_story_api", "restore_project"])

    def test_startup_skips_file_when_already_loaded(self):
        obj = _DummyStartup()
        obj._api_config_from_file_loaded = True
        ModernApp._startup_load_configs(obj)
        self.assertEqual(obj.calls, ["load_env", "load_story_api", "restore_project"])


if __name__ == "__main__":
    unittest.main()
