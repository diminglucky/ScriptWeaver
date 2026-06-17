"""RunHandle: wraps run_id + SSE iterator + cancel.

See docs/technical_architecture.md.2.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Awaitable, Callable

from src.shared.domain.events import CreativeEvent


@dataclass
class RunHandle:
    run_id: str
    _events_factory: Callable[[], AsyncIterator[CreativeEvent]]
    _cancel: Callable[[], Awaitable[None]]
    _wait: Callable[[], Awaitable[dict]]

    async def events(self) -> AsyncIterator[CreativeEvent]:
        async for ev in self._events_factory():
            yield ev

    async def cancel(self) -> None:
        await self._cancel()

    async def wait(self) -> dict:
        return await self._wait()
