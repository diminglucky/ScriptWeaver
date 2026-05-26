"""FastAPI integration tests for story-service run APIs."""
from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from src.services.story_service.core.services.creative_service import CreativeService, RunContext
from src.services.story_service.core.services.event_bus import EventBus
from src.services.story_service.core.services.run_registry import RunRegistry
from src.services.story_service.deps import get_creative_service, get_event_bus
from src.services.story_service.main import create_app
from src.shared.domain.events import CreativeEvent


class _Harness:
    def __init__(self, runner):
        self.bus = EventBus()
        self.runs = RunRegistry()
        self.service = CreativeService(
            registry=None,
            prompts=None,
            runs=self.runs,
            bus=self.bus,
            runner=runner,
        )
        self.app = create_app()
        self.app.dependency_overrides[get_creative_service] = lambda: self.service
        self.app.dependency_overrides[get_event_bus] = lambda: self.bus
        self.client = TestClient(self.app)

    def __enter__(self):
        self.client.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.client.__exit__(exc_type, exc, tb)


def test_health_endpoint():
    async def runner(**_):
        pass

    with _Harness(runner) as h:
        r = h.client.get("/v1/health")
        assert r.status_code == 200
        assert r.json()["service"] == "story"


def test_run_novel_status_and_sse_events():
    async def runner(*, ctx: RunContext, **_):
        ctx.bus.publish(CreativeEvent(type="token", run_id=ctx.run_id, payload={"text": "hello"}))

    with _Harness(runner) as h:
        started = h.client.post("/v1/projects/proj-1/novel:run", json={"requirement": "x"})
        assert started.status_code == 200
        run_id = started.json()["run_id"]

        with h.client.stream("GET", f"/v1/runs/{run_id}/events") as resp:
            assert resp.status_code == 200
            body = "".join(resp.iter_text())
        assert "event: creative" in body
        assert "run_started" in body
        assert "token" in body
        assert "succeeded" in body

        status = h.client.get(f"/v1/runs/{run_id}")
        assert status.status_code == 200
        assert status.json()["status"] == "succeeded"
        assert status.json()["project_id"] == "proj-1"


def test_character_design_route_uses_character_runner_kind():
    seen: list[str] = []

    async def runner(*, kind: str, **_):
        seen.append(kind)

    with _Harness(runner) as h:
        r = h.client.post("/v1/projects/proj-1/characters:design", json={"story_context": "x"})
        assert r.status_code == 200
        run_id = r.json()["run_id"]
        with h.client.stream("GET", f"/v1/runs/{run_id}/events") as resp:
            _ = "".join(resp.iter_text())
        assert seen == ["characters"]


def test_resume_route_unblocks_runner():
    async def runner(*, ctx: RunContext, **_):
        payload = await ctx.wait_resume("approve")
        ctx.bus.publish(CreativeEvent(type="token", run_id=ctx.run_id, payload={"payload": payload}))

    with _Harness(runner) as h:
        start = h.client.post("/v1/projects/p/novel:run", json={})
        run_id = start.json()["run_id"]
        resume = h.client.post(f"/v1/runs/{run_id}/resume", json={"decision": "approve", "note": "ok"})
        assert resume.status_code == 200
        with h.client.stream("GET", f"/v1/runs/{run_id}/events") as resp:
            body = "".join(resp.iter_text())
        assert "approve" in body
        assert "succeeded" in body


def test_cancel_route_marks_run_cancelled():
    async def runner(*, ctx: RunContext, **_):
        while not ctx.cancelled():
            await asyncio.sleep(0.01)
        raise asyncio.CancelledError()

    with _Harness(runner) as h:
        start = h.client.post("/v1/projects/p/novel:run", json={})
        run_id = start.json()["run_id"]
        cancel = h.client.post(f"/v1/runs/{run_id}/cancel")
        assert cancel.status_code == 200
        assert cancel.json()["cancelled"] is True
        with h.client.stream("GET", f"/v1/runs/{run_id}/events") as resp:
            body = "".join(resp.iter_text())
        assert "cancelled" in body


def test_unknown_run_uses_json_error_handler():
    async def runner(**_):
        pass

    with _Harness(runner) as h:
        r = h.client.get("/v1/runs/missing")
        assert r.status_code == 404
        assert r.json()["code"] == "not_found"
