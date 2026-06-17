"""RunRegistry cancel + client-attach. See docs/technical_architecture.md.3."""

from __future__ import annotations

import asyncio

from src.services.story_service.core.services.run_registry import RunRegistry


def test_register_and_cancel_marks_event():
    async def run():
        r = RunRegistry()
        ev = r.register("r1")
        assert not r.is_cancelled("r1")
        result = await r.cancel("r1")
        assert result is True
        assert ev.is_set()
        assert r.is_cancelled("r1")

    asyncio.run(run())


def test_cancel_unknown_run_returns_false():
    async def run():
        r = RunRegistry()
        assert await r.cancel("ghost") is False

    asyncio.run(run())


def test_finish_clears_state():
    async def run():
        r = RunRegistry()
        r.register("r1")
        r.finish("r1")
        assert not r.is_cancelled("r1")

    asyncio.run(run())


def test_attached_clients_are_aclosed_on_cancel():
    closed: list[str] = []

    class FakeClient:
        def __init__(self, label: str):
            self.label = label

        async def aclose(self):
            closed.append(self.label)

    async def run():
        r = RunRegistry()
        r.register("r1")
        r.attach_client("r1", FakeClient("x"))
        r.attach_client("r1", FakeClient("y"))
        await r.cancel("r1")

    asyncio.run(run())
    assert closed == ["x", "y"]


def test_attached_client_close_failure_does_not_break_cancel():
    class BadClient:
        async def aclose(self):
            raise RuntimeError("boom")

    async def run():
        r = RunRegistry()
        r.register("r1")
        r.attach_client("r1", BadClient())
        return await r.cancel("r1")

    assert asyncio.run(run()) is True
