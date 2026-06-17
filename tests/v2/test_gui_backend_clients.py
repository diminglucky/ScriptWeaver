"""Tests for GUI backend HTTP clients."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from src.gui.backend.errors import error_from_payload
from src.gui.backend.image_client import ImageClient
from src.gui.backend.rag_client import RagClient
from src.gui.backend.story_client import StoryClient
from src.shared.domain.errors import NotFound


def test_error_from_payload_accepts_direct_and_nested_envelopes():
    direct = error_from_payload({"code": "not_found", "message": "missing", "detail": {"x": 1}})
    nested = error_from_payload({"error": {"code": "not_found", "message": "missing", "detail": {}}})
    assert isinstance(direct, NotFound)
    assert isinstance(nested, NotFound)
    assert direct.detail == {"x": 1}


def test_rag_client_ingest_search_memory(monkeypatch):
    calls = []

    async def fake_request_json(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if url.endswith("/search"):
            return {"results": [{
                "text": "ctx",
                "source": {"source_id": "s", "path": "p", "chunk_id": "c", "score": 0.9},
            }]}
        if url.endswith("/memory") and method == "GET":
            return {"entries": []}
        return {"ok": True}

    monkeypatch.setattr("src.gui.backend.rag_client.request_json", fake_request_json)
    c = RagClient(base_url="http://rag/", token="tok")

    async def go():
        await c.ingest("reference", {"documents": []})
        found = await c.search("reference", "q", top_k=2)
        mem = await c.list_memory("p1")
        await c.write_memory("p1", [{"source_id": "m", "text": "x"}])
        await c.clear_memory("p1")
        await c.rebuild_manifest()
        await c.manifest()
        return found, mem

    found, mem = asyncio.run(go())
    assert found[0].text == "ctx"
    assert mem == {"entries": []}
    assert calls[0][0] == "POST" and calls[0][1] == "http://rag/v1/kb/reference/documents"
    assert calls[1][2]["json"]["top_k"] == 2
    assert calls[-2][1] == "http://rag/v1/admin/manifest:rebuild"
    assert calls[-1][1] == "http://rag/v1/admin/manifest"


def test_story_client_run_handle_and_routes(monkeypatch):
    calls = []

    async def fake_request_json(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if url.endswith("novel:run"):
            return {"run_id": "r1"}
        if url.endswith("/runs/r1") and method == "GET":
            return {"run_id": "r1", "status": "succeeded"}
        return {"ok": True}

    monkeypatch.setattr("src.gui.backend.story_client.request_json", fake_request_json)
    c = StoryClient(base_url="http://story", token="tok")

    async def go():
        h = await c.generate_novel("p1", {"requirement": "x"})
        await h.cancel()
        status = await h.wait()
        await c.resume("r1", {"decision": "approve"})
        await c.get_routing()
        await c.update_routing({"x": 1})
        return h.run_id, status

    run_id, status = asyncio.run(go())
    assert run_id == "r1"
    assert status["status"] == "succeeded"
    assert calls[0][1] == "http://story/v1/projects/p1/novel:run"
    assert ("POST", "http://story/v1/runs/r1/cancel") == (calls[1][0], calls[1][1])
    assert calls[-1][0] == "PUT" and calls[-1][1] == "http://story/v1/routing"


def test_image_client_routes(monkeypatch):
    calls = []

    async def fake_request_json(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if ":generate" in url or ":batch" in url or ":script" in url or ":publish" in url or url.endswith("/photo"):
            return {"run_id": "irun", "url": "x"}
        if url.endswith("/shots"):
            return {"shots": []}
        return {"ok": True}

    monkeypatch.setattr("src.gui.backend.image_client.request_json", fake_request_json)
    c = ImageClient(base_url="http://image", token="tok")

    async def go():
        h1 = await c.generate_shot_prompts("p", {})
        h2 = await c.render_shots_batch("p")
        h3 = await c.generate_character_photo("p", "Alice")
        await c.list_shots("p")
        single = await c.render_single({"prompt": "x"})
        h4 = await c.director_script("p", {})
        h5 = await c.publish_zhihu("p", {})
        return [h1.run_id, h2.run_id, h3.run_id, h4.run_id, h5.run_id], single

    run_ids, single = asyncio.run(go())
    assert run_ids == ["irun"] * 5
    assert single["url"] == "x"
    urls = [c[1] for c in calls]
    assert "http://image/v1/projects/p/image-prompts:generate" in urls
    assert "http://image/v1/projects/p/shots:batch" in urls
    assert "http://image/v1/images:generate" in urls
