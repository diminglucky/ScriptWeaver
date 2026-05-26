"""Tests for story_service.core.services.creative_service.CreativeService."""
from __future__ import annotations

import asyncio

import pytest

from src.services.story_service.core.services.creative_service import (
    CreativeService,
    RunContext,
)
from src.services.story_service.core.services.event_bus import EventBus
from src.services.story_service.core.services.run_registry import RunRegistry
from src.shared.domain.errors import CreativeError, NotFound


def _make_service(runner):
    return CreativeService(
        registry=None,
        prompts=None,
        runs=RunRegistry(),
        bus=EventBus(),
        runner=runner,
    )


def _collect(bus: EventBus, run_id: str):
    async def consume():
        out: list = []
        async for ev in bus.subscribe(run_id):
            out.append(ev)
        return out
    return consume()


def test_start_novel_runs_runner_and_emits_terminal_event():
    seen = {}

    async def runner(*, kind, project_id, run_id, request, ctx):
        seen.update(kind=kind, project_id=project_id, request=request)

    svc = _make_service(runner)

    async def go():
        run_id = await svc.start_novel("proj-1", {"requirement": "go"})
        events = await _collect(svc.bus, run_id)
        return run_id, events

    run_id, events = asyncio.run(go())
    types = [e.type for e in events]
    assert types[0] == "run_started"
    assert types[-1] == "succeeded"
    assert seen == {"kind": "novel", "project_id": "proj-1", "request": {"requirement": "go"}}


def test_runner_exception_emits_failed_event():
    async def runner(**_):
        raise CreativeError("boom", detail={"why": "test"})

    svc = _make_service(runner)

    async def go():
        run_id = await svc.start_novel("proj-1", {})
        events = await _collect(svc.bus, run_id)
        return run_id, events

    run_id, events = asyncio.run(go())
    terminal = events[-1]
    assert terminal.type == "failed"
    assert terminal.payload["code"] == "creative_error"
    assert terminal.payload["detail"] == {"why": "test"}
    status = asyncio.run(svc.get_status(run_id))
    assert status["status"] == "failed" and status["error"] == "boom"


def test_runner_unexpected_exception_emits_failed():
    async def runner(**_):
        raise RuntimeError("kaboom")

    svc = _make_service(runner)

    async def go():
        run_id = await svc.start_novel("p", {})
        events = await _collect(svc.bus, run_id)
        return run_id, events

    _, events = asyncio.run(go())
    assert events[-1].type == "failed"
    assert "kaboom" in events[-1].payload["message"]


def test_cancel_sets_cancel_event_and_emits_cancelled():
    async def runner(*, ctx: RunContext, **_):
        # wait until cancelled
        while not ctx.cancelled():
            await asyncio.sleep(0.01)
        raise asyncio.CancelledError()

    svc = _make_service(runner)

    async def go():
        run_id = await svc.start_novel("p", {})
        # Let runner start
        await asyncio.sleep(0.02)
        ok = await svc.cancel(run_id)
        assert ok is True
        events = await _collect(svc.bus, run_id)
        return events

    events = asyncio.run(go())
    assert events[-1].type == "cancelled"


def test_resume_signals_runner_decision():
    decisions: list = []

    async def runner(*, ctx: RunContext, **_):
        payload = await ctx.wait_resume("approve")
        decisions.append(payload)

    svc = _make_service(runner)

    async def go():
        run_id = await svc.start_novel("p", {})
        await asyncio.sleep(0.02)
        await svc.resume(run_id, {"decision": "approve", "edits": {"tone": "darker"}})
        events = await _collect(svc.bus, run_id)
        return events

    events = asyncio.run(go())
    assert events[-1].type == "succeeded"
    assert decisions == [{"decision": "approve", "edits": {"tone": "darker"}}]


def test_resume_unknown_run_raises_not_found():
    svc = _make_service(lambda **_: None)
    with pytest.raises(NotFound):
        asyncio.run(svc.resume("missing", {"decision": "x"}))


def test_get_status_unknown_run_raises_not_found():
    svc = _make_service(lambda **_: None)
    with pytest.raises(NotFound):
        asyncio.run(svc.get_status("missing"))


def test_missing_runner_raises_creative_error():
    svc = CreativeService(registry=None, prompts=None, runs=RunRegistry(), bus=EventBus(), runner=None)
    with pytest.raises(CreativeError):
        asyncio.run(svc.start_novel("p", {}))
