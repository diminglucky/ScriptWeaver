from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.services.story_service.core.services.project_store import ProjectStore
from src.services.story_service.core.workflows.runner import WorkflowRunner
from src.services.story_service.deps import get_model_registry
from src.services.story_service.main import create_app
from src.shared.config import paths as paths_module
from src.shared.config.keyfile import KeyVault
from src.shared.config.presets import PresetsConfig
from src.shared.config.routing import RouteEntry, RoutingConfig
from src.services.story_service.core.ai.models import ModelRegistry


def _reset_paths(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WSF_REPO_ROOT", str(tmp_path))
    paths_module.get_repo_paths.cache_clear()


def test_project_endpoints_round_trip(monkeypatch, tmp_path: Path):
    _reset_paths(monkeypatch, tmp_path)
    app = create_app()
    with TestClient(app) as client:
        created = client.post("/v1/projects", json={
            "project_id": "p-api",
            "requirement": "雨夜秘密",
            "genre": "悬疑",
            "style": "克制",
            "target_chars": 1000,
        })
        assert created.status_code == 200
        assert created.json()["project_id"] == "p-api"

        store = ProjectStore("p-api")
        store.save_final_story("正文")

        listing = client.get("/v1/projects")
        assert listing.status_code == 200
        assert listing.json()["projects"][0]["project_id"] == "p-api"

        meta = client.get("/v1/projects/p-api")
        assert meta.status_code == 200
        assert meta.json()["has_storybible"] is True
        assert meta.json()["has_story"] is True

        bible = client.get("/v1/projects/p-api/storybible")
        assert bible.status_code == 200
        assert bible.json()["requirement"] == "雨夜秘密"

        chapters = client.get("/v1/projects/p-api/chapters")
        assert chapters.status_code == 200
        assert chapters.json() == {"chapters": []}

        story = client.get("/v1/projects/p-api/story")
        assert story.status_code == 200
        assert story.json() == {"text": "正文"}

        missing = client.get("/v1/projects/missing")
        assert missing.status_code == 404
        assert missing.json()["code"] == "not_found"


def test_models_and_routing_endpoints(monkeypatch, tmp_path: Path):
    _reset_paths(monkeypatch, tmp_path)
    registry = ModelRegistry(
        routing=RoutingConfig(by_task={"story_generate": RouteEntry(provider="fake", model="fake-chat")}),
        presets=PresetsConfig(),
        vault=KeyVault(),
    )
    app = create_app()
    app.dependency_overrides[get_model_registry] = lambda: registry
    with TestClient(app) as client:
        models = client.get("/v1/models")
        assert models.status_code == 200
        assert models.json()["providers"] == ["fake"]

        routing = client.get("/v1/routing")
        assert routing.status_code == 200
        assert routing.json()["routes"]["story_generate"]["model"] == "fake-chat"

        updated = client.put("/v1/routing", json={
            "routes": {"story_generate": {"provider": "fake", "model": "m2", "temperature": 0.3}}
        })
        assert updated.status_code == 200
        assert updated.json()["routes"]["story_generate"]["temperature"] == 0.3
        saved = json.loads((tmp_path / "custom_model_routing.json").read_text(encoding="utf-8"))
        assert saved["routes"]["story_generate"]["model"] == "m2"


def test_review_endpoint_resumes_run():
    seen: list[dict] = []

    class _Service:
        async def resume(self, run_id: str, patch: dict) -> None:
            seen.append({"run_id": run_id, "patch": patch})

    from src.services.story_service.deps import get_creative_service

    app = create_app()
    app.dependency_overrides[get_creative_service] = lambda: _Service()
    with TestClient(app) as client:
        resp = client.post("/v1/runs/r1/review", json={"decision": "approve", "note": "ok"})
        assert resp.status_code == 200
        assert resp.json()["reviewed"] is True
        assert seen == [{"run_id": "r1", "patch": {"decision": "approve", "note": "ok"}}]


def test_workflow_runner_persists_novel(monkeypatch, tmp_path: Path):
    _reset_paths(monkeypatch, tmp_path)

    class _Bus:
        def __init__(self):
            self.events = []

        def publish(self, ev):
            self.events.append(ev)

    class _Ctx:
        def __init__(self):
            self.bus = _Bus()

    runner = WorkflowRunner(
        registry=ModelRegistry(routing=RoutingConfig(), presets=PresetsConfig(), vault=KeyVault()),
        prompts=None,
        rag_client=None,
    )
    ctx = _Ctx()
    asyncio.run(runner(kind="novel", project_id="p-runner", run_id="r", request={
        "requirement": "默认模型故事",
        "chapter_count": 2,
    }, ctx=ctx))

    store = ProjectStore("p-runner")
    assert store.load_storybible().requirement == "默认模型故事"
    assert len(store.list_chapters()) == 2
    assert store.load_final_story()
    assert ctx.bus.events[0].type == "node_started"
    assert ctx.bus.events[-1].type == "node_finished"


def test_default_story_api_runs_workflow_and_persists_project(monkeypatch, tmp_path: Path):
    _reset_paths(monkeypatch, tmp_path)

    from src.services.story_service import deps

    for name in (
        "get_model_registry",
        "get_prompt_library",
        "get_run_registry",
        "get_event_bus",
        "get_rag_client",
        "get_workflow_runner",
        "get_creative_service",
    ):
        getattr(deps, name).cache_clear()

    app = create_app()
    with TestClient(app) as client:
        started = client.post("/v1/projects/p-default/novel:run", json={
            "requirement": "默认 API 工作流",
            "chapter_count": 2,
            "use_rag": False,
        })
        assert started.status_code == 200
        run_id = started.json()["run_id"]
        with client.stream("GET", f"/v1/runs/{run_id}/events") as resp:
            body = "".join(resp.iter_text())
        assert "succeeded" in body

        status = client.get(f"/v1/runs/{run_id}")
        assert status.status_code == 200
        assert status.json()["status"] == "succeeded"

        bible = client.get("/v1/projects/p-default/storybible")
        assert bible.status_code == 200
        assert bible.json()["requirement"] == "默认 API 工作流"

        chapters = client.get("/v1/projects/p-default/chapters")
        assert chapters.status_code == 200
        assert len(chapters.json()["chapters"]) == 2

        story = client.get("/v1/projects/p-default/story")
        assert story.status_code == 200
        assert story.json()["text"]
