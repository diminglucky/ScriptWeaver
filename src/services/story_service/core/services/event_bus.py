"""SSE event bus: per run_id queue + buffered history for reconnects.

See docs/technical_architecture.md.5.
"""

from __future__ import annotations

import asyncio
from collections import deque
from typing import AsyncIterator, Deque

from src.shared.domain.events import CreativeEvent

_MAX_BUFFER = 500


_TERMINAL = {"succeeded", "failed", "cancelled"}


class EventBus:
    def __init__(self, *, max_buffer: int = _MAX_BUFFER) -> None:
        self._queues: dict[str, asyncio.Queue[CreativeEvent]] = {}
        self._buffers: dict[str, Deque[CreativeEvent]] = {}
        self._terminal: dict[str, CreativeEvent] = {}
        self._max_buffer = max_buffer

    def publish(self, ev: CreativeEvent) -> None:
        ev.stamp()
        if ev.type in _TERMINAL:
            self._terminal[ev.run_id] = ev
        else:
            buf = self._buffers.setdefault(ev.run_id, deque(maxlen=self._max_buffer))
            buf.append(ev)
        q = self._queues.get(ev.run_id)
        if q is not None:
            q.put_nowait(ev)

    async def subscribe(self, run_id: str) -> AsyncIterator[CreativeEvent]:
        q: asyncio.Queue[CreativeEvent] = asyncio.Queue()
        self._queues[run_id] = q
        try:
            for ev in list(self._buffers.get(run_id, ())):
                yield ev
            term = self._terminal.get(run_id)
            if term is not None:
                yield term
                return
            while True:
                ev = await q.get()
                yield ev
                if ev.type in _TERMINAL:
                    return
        finally:
            self._queues.pop(run_id, None)

    def drop(self, run_id: str) -> None:
        self._buffers.pop(run_id, None)
        self._queues.pop(run_id, None)
        self._terminal.pop(run_id, None)
