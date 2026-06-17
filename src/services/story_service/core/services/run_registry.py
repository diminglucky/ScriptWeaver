"""Per-process run registry with cancel + client-attach.

See docs/technical_architecture.md.3.
"""

from __future__ import annotations

import asyncio
from typing import Any


class RunRegistry:
    def __init__(self) -> None:
        self._events: dict[str, asyncio.Event] = {}
        self._clients: dict[str, list[Any]] = {}

    def register(self, run_id: str) -> asyncio.Event:
        ev = self._events.get(run_id) or asyncio.Event()
        self._events[run_id] = ev
        return ev

    def is_cancelled(self, run_id: str) -> bool:
        ev = self._events.get(run_id)
        return bool(ev and ev.is_set())

    def attach_client(self, run_id: str, client: Any) -> None:
        self._clients.setdefault(run_id, []).append(client)

    async def cancel(self, run_id: str) -> bool:
        ev = self._events.get(run_id)
        if not ev:
            return False
        ev.set()
        for client in self._clients.get(run_id, []):
            try:
                await client.aclose()
            except Exception:
                pass
        return True

    def finish(self, run_id: str) -> None:
        self._events.pop(run_id, None)
        self._clients.pop(run_id, None)
