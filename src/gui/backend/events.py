"""Decode an httpx streaming response into CreativeEvent objects.

See v2 plan §7.5.
"""

from __future__ import annotations

from typing import AsyncIterator

from src.shared.domain.events import CreativeEvent, deserialize_event


async def iter_events_from_response(response) -> AsyncIterator[CreativeEvent]:
    """Yield CreativeEvent objects parsed from an SSE `text/event-stream` body."""
    pending: list[str] = []
    async for raw_line in response.aiter_lines():
        if raw_line == "":
            if pending:
                data = "\n".join(line[5:].lstrip() for line in pending if line.startswith("data:"))
                pending = []
                if data:
                    try:
                        yield deserialize_event(data)
                    except Exception:
                        continue
            continue
        pending.append(raw_line)
