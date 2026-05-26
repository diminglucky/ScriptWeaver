"""EventBus subscribe + buffer + auto-close. See v2 plan §8.5."""

from __future__ import annotations

import asyncio

from src.services.story_service.core.services.event_bus import EventBus
from src.shared.domain.events import CreativeEvent


def test_subscribe_replays_buffered_events():
    bus = EventBus()
    bus.publish(CreativeEvent(type="run_started", run_id="r1"))
    bus.publish(CreativeEvent(type="node_started", run_id="r1", node="x"))
    bus.publish(CreativeEvent(type="succeeded", run_id="r1"))

    async def consume():
        out = []
        async for ev in bus.subscribe("r1"):
            out.append(ev.type)
        return out

    out = asyncio.run(consume())
    assert out == ["run_started", "node_started", "succeeded"]


def test_subscribe_terminates_on_terminal_event():
    bus = EventBus()
    bus.publish(CreativeEvent(type="failed", run_id="r2"))
    # Should not hang.
    out = asyncio.run(_collect(bus, "r2"))
    assert out == ["failed"]


def test_buffer_capped_to_max():
    bus = EventBus(max_buffer=3)
    for i in range(5):
        bus.publish(CreativeEvent(type="token", run_id="r3", payload={"i": i}))
    bus.publish(CreativeEvent(type="succeeded", run_id="r3"))

    async def consume():
        out = []
        async for ev in bus.subscribe("r3"):
            out.append(ev.type)
        return out

    out = asyncio.run(consume())
    # 3 token frames retained + final succeeded = 4 total.
    assert out.count("token") == 3
    assert out[-1] == "succeeded"


def test_drop_clears_buffer():
    bus = EventBus()
    bus.publish(CreativeEvent(type="run_started", run_id="r4"))
    bus.drop("r4")
    bus.publish(CreativeEvent(type="succeeded", run_id="r4"))

    async def consume():
        out = []
        async for ev in bus.subscribe("r4"):
            out.append(ev.type)
        return out

    assert asyncio.run(consume()) == ["succeeded"]


async def _collect(bus: EventBus, run_id: str) -> list[str]:
    out = []
    async for ev in bus.subscribe(run_id):
        out.append(ev.type)
    return out
