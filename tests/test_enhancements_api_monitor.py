import unittest
from unittest.mock import patch

from src.gui.mixins.enhancements_modules.api_monitor import APIMonitorMixin
from src.gui.mixins.enhancements_modules.api_monitor import APIStatusMonitor


class _Var:
    def __init__(self, value=""):
        self.value = value

    def set(self, value):
        self.value = value


class _DummyMonitorDisplay(APIMonitorMixin):
    def __init__(self):
        self.status = _Var("")
        self.header_calls = []

    def update_header_status(self, text, icon):
        self.header_calls.append((text, icon))


class APIStatusMonitorTests(unittest.TestCase):
    @patch("src.utils.text.try_chat_api", return_value=(True, "ok"))
    def test_check_api_online(self, _mock_try_chat_api):
        monitor = APIStatusMonitor()
        result = monitor.check_api("ds", "https://example.com/v1", "k", "m")
        self.assertEqual(result["name"], "ds")
        self.assertEqual(result["status"], "online")
        self.assertEqual(result["message"], "ok")
        self.assertGreaterEqual(result["latency"], 0)
        self.assertIsNotNone(monitor.get_status("ds"))

    @patch("src.utils.text.try_chat_api", side_effect=RuntimeError("boom"))
    def test_check_api_error(self, _mock_try_chat_api):
        monitor = APIStatusMonitor()
        result = monitor.check_api("ds", "https://example.com/v1", "k", "m")
        self.assertEqual(result["status"], "error")
        self.assertIn("boom", result["message"])
        self.assertEqual(result["latency"], -1)

    def test_update_api_status_display_online(self):
        obj = _DummyMonitorDisplay()
        obj._update_api_status_display(
            {
                "name": "ds",
                "status": "online",
                "message": "ok",
                "latency": 12.7,
            }
        )
        self.assertIn("在线", obj.status.value)
        self.assertIn("ms", obj.status.value)
        self.assertEqual(obj.header_calls[-1], ("ds可用", "✅"))

    def test_update_api_status_display_error(self):
        obj = _DummyMonitorDisplay()
        obj._update_api_status_display(
            {
                "name": "ds",
                "status": "error",
                "message": "fail",
                "latency": -1,
            }
        )
        self.assertIn("异常", obj.status.value)
        self.assertIn("fail", obj.status.value)
        self.assertEqual(obj.header_calls[-1], ("ds不可用", "❌"))


if __name__ == "__main__":
    unittest.main()
