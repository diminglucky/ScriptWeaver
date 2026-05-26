from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.services.image_service import deps
from src.services.image_service.main import create_app
from src.shared.config import paths as paths_module


def _client(monkeypatch, tmp_path: Path) -> TestClient:
    monkeypatch.setenv("WSF_REPO_ROOT", str(tmp_path))
    paths_module.get_repo_paths.cache_clear()
    for name in ("get_run_registry", "get_event_bus", "get_image_pipeline", "get_character_pipeline", "get_shot_pipeline", "get_publisher_service"):
        getattr(deps, name).cache_clear()
    return TestClient(create_app())


def _drain_events(client: TestClient, run_id: str) -> str:
    with client.stream("GET", f"/v1/runs/{run_id}/events") as resp:
        assert resp.status_code == 200
        return "".join(resp.iter_text())


def test_image_prompt_generation_persists_and_lists_shots(monkeypatch, tmp_path: Path):
    with _client(monkeypatch, tmp_path) as client:
        started = client.post("/v1/projects/p-img/image-prompts:generate", json={"scene": "雨夜", "prompt": "rainy night"})
        assert started.status_code == 200
        body = _drain_events(client, started.json()["run_id"])
        assert "succeeded" in body

        shots = client.get("/v1/projects/p-img/shots")
        assert shots.status_code == 200
        assert shots.json()["shots"][0]["shot_id"] == "shot-001"

        rendered = client.post("/v1/projects/p-img/shots/shot-001:render", json={})
        assert rendered.status_code == 200
        assert rendered.json()["status"] == "succeeded"
        assert rendered.json()["prompt"] == "rainy night"

        missing = client.post("/v1/projects/p-img/shots/missing:render", json={})
        assert missing.status_code == 404
        assert missing.json()["code"] == "not_found"


def test_batch_character_director_publish_runs_and_reads(monkeypatch, tmp_path: Path):
    with _client(monkeypatch, tmp_path) as client:
        client.post("/v1/projects/p-img/image-prompts:generate", json={"prompt": "a"})

        for path in (
            "/v1/projects/p-img/shots:batch",
            "/v1/projects/p-img/characters/林夏/turnaround",
            "/v1/projects/p-img/characters/林夏/photo",
            "/v1/projects/p-img/director:script",
            "/v1/projects/p-img/zhihu:publish",
        ):
            resp = client.post(path, json={"title": "标题"})
            assert resp.status_code == 200
            assert "run_id" in resp.json()
            assert "succeeded" in _drain_events(client, resp.json()["run_id"])

        script = client.get("/v1/projects/p-img/director/script")
        assert script.status_code == 200
        assert script.json()["title"] == "标题"

        publish = client.get("/v1/projects/p-img/zhihu/last-result")
        assert publish.status_code == 200
        assert publish.json()["status"] == "dry_run"


def test_single_image_and_cancel_unknown_run(monkeypatch, tmp_path: Path):
    with _client(monkeypatch, tmp_path) as client:
        image = client.post("/v1/images:generate", json={"prompt": "x", "aspect_ratio": "1:1"})
        assert image.status_code == 200
        assert image.json()["url"].startswith("generated://image/")
        assert image.json()["aspect_ratio"] == "1:1"

        cancel = client.post("/v1/runs/missing/cancel")
        assert cancel.status_code == 200
        assert cancel.json() == {"run_id": "missing", "cancelled": False}
