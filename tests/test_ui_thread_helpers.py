import threading
import unittest
from unittest.mock import Mock, patch

from src.gui.mixins.enhancements_modules.api_monitor import APIMonitorMixin
from src.gui.mixins.ui_mixin import UiMixin


class _DummyUi(UiMixin):
    def __init__(self):
        self.after_calls = 0
        self.header_calls = []

    def after(self, delay, callback):
        self.after_calls += 1
        callback()

    def update_header_status(self, text, icon, color=None):
        self.header_calls.append((text, icon, color))


class _DummyMonitor(APIMonitorMixin):
    def __init__(self):
        self.updated = []
        self.after_calls = 0
        self.api_monitor = Mock()

    def after(self, delay, callback):
        self.after_calls += 1
        callback()

    def _update_api_status_display(self, status):
        self.updated.append(status)


class UiThreadHelperTests(unittest.TestCase):
    def test_ui_direct_call_main_thread(self):
        obj = _DummyUi()
        out = obj._ui(lambda x: x + 1, 1)
        self.assertEqual(out, 2)
        self.assertEqual(obj.after_calls, 0)

    def test_ui_call_from_worker_thread_uses_after(self):
        obj = _DummyUi()
        box = {}

        def worker():
            box["value"] = obj._ui(lambda: "ok")

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        t.join(timeout=5)

        self.assertEqual(box.get("value"), "ok")
        self.assertEqual(obj.after_calls, 1)

    def test_ui_get_returns_value(self):
        obj = _DummyUi()
        self.assertEqual(obj._ui_get(lambda: "v"), "v")

    def test_header_status_wrapper(self):
        obj = _DummyUi()
        obj._header_status("ok", "✅")
        self.assertEqual(obj.header_calls, [("ok", "✅", None)])


class ApiMonitorThreadingTests(unittest.TestCase):
    def test_check_api_status_schedules_ui_update_when_async(self):
        obj = _DummyMonitor()
        obj.run_with_progress = Mock()
        result = {"name": "ds", "status": "online"}
        obj.api_monitor.check_api.return_value = result

        with patch("src.gui.mixins.enhancements_modules.api_monitor.threading.Thread") as thread_cls:
            thread_instance = thread_cls.return_value
            thread_instance.start.side_effect = lambda: None

            obj.check_api_status("ds", "https://x", "k", "m")

            worker = thread_cls.call_args.kwargs["target"]
            worker()

        self.assertEqual(obj.updated, [result])
        self.assertGreaterEqual(obj.after_calls, 1)


if __name__ == "__main__":
    unittest.main()
