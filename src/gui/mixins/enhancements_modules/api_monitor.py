"""API status monitor extracted from enhancements mixin."""

import threading
import time
from datetime import datetime
from typing import Dict, Optional

import logging

logger = logging.getLogger(__name__)


class APIStatusMonitor:
    """Track API check results in memory."""

    def __init__(self):
        self.status_cache: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self.check_interval = 60
        self._running = False
        self._thread = None

    def check_api(self, name: str, base_url: str, api_key: str, model: str = None) -> Dict:
        from src.utils.text import try_chat_api

        start_time = time.time()
        try:
            ok, msg = try_chat_api(api_key, base_url, model or "test")
            latency = (time.time() - start_time) * 1000
            status = {
                "name": name,
                "status": "online" if ok else "error",
                "message": msg,
                "latency": latency,
                "last_check": datetime.now().isoformat(),
            }
        except Exception as e:
            status = {
                "name": name,
                "status": "error",
                "message": str(e),
                "latency": -1,
                "last_check": datetime.now().isoformat(),
            }

        with self._lock:
            self.status_cache[name] = status
        return status

    def get_status(self, name: str) -> Optional[Dict]:
        with self._lock:
            return self.status_cache.get(name)

    def get_all_status(self) -> Dict[str, Dict]:
        with self._lock:
            return dict(self.status_cache)


class APIMonitorMixin:
    """Mixin for async API health checks."""

    def _init_api_monitor(self):
        self.api_monitor = APIStatusMonitor()

    def check_api_status(self, name: str, base_url: str, api_key: str, model: str = None):
        def check():
            return self.api_monitor.check_api(name, base_url, api_key, model)

        def on_complete(result):
            self._update_api_status_display(result)

        if hasattr(self, "run_with_progress"):
            def worker():
                result = check()
                if hasattr(self, "after"):
                    self.after(0, lambda: on_complete(result))
                else:
                    on_complete(result)

            thread = threading.Thread(target=worker, daemon=True)
            thread.start()
        else:
            result = check()
            self._update_api_status_display(result)

    def _update_api_status_display(self, status: Dict):
        if not isinstance(status, dict):
            return

        name = str(status.get("name") or "API")
        state = str(status.get("status") or "unknown")
        message = str(status.get("message") or "")
        latency = status.get("latency")

        ok = state == "online"
        summary = f"{name} {'在线' if ok else '异常'}"
        if isinstance(latency, (int, float)) and latency >= 0:
            summary += f" ({latency:.0f} ms)"
        if message:
            summary += f": {message}"

        if hasattr(self, "status"):
            try:
                self.status.set(summary)
            except Exception as e:
                logger.debug("set status text failed: %s", e)

        if hasattr(self, "update_header_status"):
            try:
                self.update_header_status(
                    f"{name}{'可用' if ok else '不可用'}",
                    "✅" if ok else "❌",
                )
            except Exception as e:
                logger.debug("update header status failed: %s", e)
