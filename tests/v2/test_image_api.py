from __future__ import annotations

import asyncio
from types import SimpleNamespace
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from src.services.image_service import deps
from src.services.image_service.core.services.image_pipeline import ImagePipeline
from src.services.image_service.core.services.publisher_service import PublisherService
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


def test_real_image_pipeline_opt_in_saves_provider_output(monkeypatch, tmp_path: Path):
    paths_module.get_repo_paths.cache_clear()
    monkeypatch.setenv("WSF_REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("WSF_IMAGE_REAL", "1")
    monkeypatch.setenv("WSF_IMAGE_MODEL", "image-model")

    class DummyImageClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def generate(self, prompt, *, size, n):
            image = Image.new("RGB", (2, 2), color=(10, 20, 30))
            return [SimpleNamespace(image=image, seed=None, provider="dummy", model="image-model")]

    monkeypatch.setattr("src.clients.image_client.OpenAIImageClient", DummyImageClient)
    try:
        result = asyncio.run(
            ImagePipeline().render_single(
                prompt="rainy night",
                aspect_ratio="16:9",
            )
        )
    finally:
        paths_module.get_repo_paths.cache_clear()

    assert result["status"] == "succeeded"
    assert result["url"].startswith("file://")
    assert Path(result["path"]).exists()
    assert Path(result["path"]).parent == tmp_path / ".runtime" / "generated_images"


def test_real_publisher_opt_in_uses_playwright_adapter(monkeypatch, tmp_path: Path):
    paths_module.get_repo_paths.cache_clear()
    monkeypatch.setenv("WSF_REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("WSF_ZHIHU_PUBLISH", "1")
    calls = []

    def fake_publish(title, content, headless=False, progress_callback=None):
        calls.append((title, content, headless))
        return True, "filled"

    monkeypatch.setattr(
        "src.gui.services.zhihu_publisher.publish_to_zhihu_sync",
        fake_publish,
    )
    try:
        result = asyncio.run(
            PublisherService().publish_to_zhihu(
                "p-real",
                title="标题",
                content="正文",
                headless=True,
            )
        )
    finally:
        paths_module.get_repo_paths.cache_clear()

    assert result["status"] == "succeeded"
    assert result["message"] == "filled"
    assert calls == [("标题", "正文", True)]
    assert (tmp_path / "projects" / "p-real" / "zhihu_last_result.json").exists()
