import os
import unittest
from unittest.mock import patch

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

    def test_backend_runtime_is_disabled_by_default(self):
        obj = _DummyStartup()
        with patch.dict(os.environ, {}, clear=True):
            ModernApp._init_backend_runtime(obj)

        self.assertIsNone(obj.backend_supervisor)
        self.assertIsNone(obj.backend_client)

    def test_backend_runtime_starts_and_connects_when_enabled(self):
        calls = []

        class DummySupervisor:
            def __init__(self, project_root):
                calls.append(("init", project_root))

            def start_all(self, *, dev_mode=False):
                calls.append(("start", dev_mode))

            def shutdown(self):
                calls.append(("shutdown",))

        class DummyClient:
            @classmethod
            def from_runtime(cls):
                calls.append(("client",))
                return "client"

        obj = _DummyStartup()
        with patch.dict(os.environ, {"WSF_AUTOSTART": "1", "WSF_DEV": "1"}, clear=True), \
             patch("src.gui.backend.supervisor.ServiceSupervisor", DummySupervisor), \
             patch("src.gui.backend.client.BackendClient", DummyClient):
            ModernApp._init_backend_runtime(obj)

        self.assertIsInstance(obj.backend_supervisor, DummySupervisor)
        self.assertEqual(obj.backend_client, "client")
        self.assertEqual([call[0] for call in calls], ["init", "start", "client"])


if __name__ == "__main__":
    unittest.main()
