"""FastAPI integration tests for rag-service HTTP routes."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.services.rag_service.deps import get_embedding_hub, get_index_hub, get_retriever
from src.services.rag_service.main import create_app
from src.services.rag_service.core.index_hub import IndexHub
from src.services.rag_service.core.retrievers import CreativeRetriever


class _FakeEmbedder:
    model_name = "fake"

    async def encode_async(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def _vec(self, text: str) -> list[float]:
        t = text.lower()
        if "dragon" in t or "龙" in t:
            return [1.0, 0.0, 0.0]
        if "style" in t or "风格" in t:
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]


def _client(tmp_path: Path) -> tuple[TestClient, IndexHub]:
    hub = IndexHub(index_root=tmp_path, embedding_model="fake")
    embedder = _FakeEmbedder()
    app = create_app()
    app.dependency_overrides[get_index_hub] = lambda: hub
    app.dependency_overrides[get_embedding_hub] = lambda: embedder
    app.dependency_overrides[get_retriever] = lambda: CreativeRetriever(hub=hub, embedder=embedder)
    return TestClient(app), hub


def test_health_endpoint(tmp_path: Path):
    client, hub = _client(tmp_path)
    try:
        r = client.get("/v1/health")
        assert r.status_code == 200
        assert r.json()["service"] == "rag"
    finally:
        hub.close()


def test_ingest_search_delete_reference_roundtrip(tmp_path: Path):
    client, hub = _client(tmp_path)
    try:
        payload = {
            "documents": [
                {
                    "source_id": "book-1",
                    "path": "/kb/book-1.txt",
                    "text": "Dragon lore. The red dragon guards the mountain treasure. " * 3,
                    "tags": ["lore"],
                },
                {
                    "source_id": "style-1",
                    "path": "/kb/style-1.txt",
                    "text": "Style note. Use concise sentences and cinematic images. " * 3,
                    "tags": ["style"],
                },
            ],
            "chunk_size": 200,
            "overlap": 20,
            "overlap_paragraphs": 1,
        }
        ingest = client.post("/v1/kb/reference/documents", json=payload)
        assert ingest.status_code == 200
        assert ingest.json()["ingested"] == 2
        assert ingest.json()["chunks"] >= 2
        docs = hub.shard("reference").store.fetch_documents(["book-1", "style-1"])
        assert set(docs) == {"book-1", "style-1"}
        assert docs["book-1"]["path"] == "/kb/book-1.txt"
        assert docs["book-1"]["chunk_count"] >= 1
        assert docs["book-1"]["chunk_settings"] == {
            "max_chars": 200,
            "overlap": 20,
            "overlap_paragraphs": 1,
            "paragraphs_per_chunk": 4,
        }
        assert docs["book-1"]["embedding_model"] == "fake"
        assert docs["book-1"]["size_bytes"] > 0

        search = client.post(
            "/v1/kb/reference/search",
            json={"query": "dragon", "top_k": 3, "min_score": 0.1},
        )
        assert search.status_code == 200
        results = search.json()["results"]
        assert results
        assert results[0]["source"]["source_id"] == "book-1"
        assert "Dragon" in results[0]["text"]

        delete = client.delete("/v1/kb/reference/documents/book-1")
        assert delete.status_code == 200
        assert delete.json()["removed"] >= 1
        assert hub.shard("reference").store.fetch_documents(["book-1"]) == {}

        after = client.post(
            "/v1/kb/reference/search",
            json={"query": "dragon", "top_k": 3, "min_score": 0.1},
        )
        assert after.status_code == 200
        assert all(r["source"]["source_id"] != "book-1" for r in after.json()["results"])
    finally:
        hub.close()


def test_ingest_replaces_same_source_chunks(tmp_path: Path):
    client, hub = _client(tmp_path)
    try:
        first = client.post(
            "/v1/kb/reference/documents",
            json={
                "documents": [{
                    "source_id": "book-1",
                    "path": "/kb/book-1.txt",
                    "text": "Dragon old lore. " * 8,
                    "tags": ["lore"],
                }],
                "chunk_size": 80,
                "overlap": 10,
                "overlap_paragraphs": 0,
            },
        )
        assert first.status_code == 200

        second = client.post(
            "/v1/kb/reference/documents",
            json={
                "documents": [{
                    "source_id": "book-1",
                    "path": "/kb/book-1.txt",
                    "text": "Style replacement note. " * 8,
                    "tags": ["style"],
                }],
                "chunk_size": 80,
                "overlap": 10,
                "overlap_paragraphs": 0,
            },
        )
        assert second.status_code == 200
        rows = hub.shard("reference").store.list_chunks()
        docs = hub.shard("reference").store.fetch_documents(["book-1"])
        assert {row["source_id"] for row in rows} == {"book-1"}
        assert all("old lore" not in row["text"] for row in rows)
        assert any("replacement" in row["text"] for row in rows)
        assert docs["book-1"]["chunk_count"] == len(rows)
        assert docs["book-1"]["content_hash"]
        assert docs["book-1"]["chunk_settings"]["paragraphs_per_chunk"] == 4
    finally:
        hub.close()


def test_ingest_invalid_chunk_window_returns_422(tmp_path: Path):
    client, hub = _client(tmp_path)
    try:
        response = client.post(
            "/v1/kb/reference/documents",
            json={
                "documents": [{
                    "source_id": "book-1",
                    "path": "/kb/book-1.txt",
                    "text": "Dragon lore. " * 8,
                    "tags": ["lore"],
                }],
                "chunk_size": 50,
                "overlap": 50,
            },
        )
        assert response.status_code == 422
    finally:
        hub.close()


def test_ingest_duplicate_source_id_returns_422(tmp_path: Path):
    client, hub = _client(tmp_path)
    try:
        response = client.post(
            "/v1/kb/reference/documents",
            json={
                "documents": [
                    {
                        "source_id": "book-1",
                        "path": "/kb/book-a.txt",
                        "text": "Dragon first version. " * 8,
                    },
                    {
                        "source_id": "book-1",
                        "path": "/kb/book-b.txt",
                        "text": "Dragon second version. " * 8,
                    },
                ],
            },
        )
        assert response.status_code == 422
    finally:
        hub.close()


def test_ingest_counts_only_chunkable_documents(tmp_path: Path):
    client, hub = _client(tmp_path)
    try:
        response = client.post(
            "/v1/kb/reference/documents",
            json={
                "documents": [
                    {
                        "source_id": "too-short",
                        "path": "/kb/too-short.txt",
                        "text": "short",
                    },
                    {
                        "source_id": "book-1",
                        "path": "/kb/book-1.txt",
                        "text": "Dragon usable reference. " * 8,
                    },
                ],
                "chunk_size": 120,
                "overlap": 20,
                "overlap_paragraphs": 0,
            },
        )
        assert response.status_code == 200
        assert response.json()["ingested"] == 1
        docs = hub.shard("reference").store.fetch_documents(["too-short", "book-1"])
        assert set(docs) == {"book-1"}
    finally:
        hub.close()


def test_project_memory_crud_and_search_is_project_scoped(tmp_path: Path):
    client, hub = _client(tmp_path)
    try:
        write = client.post(
            "/v1/projects/proj-a/memory",
            json={"entries": [{"source_id": "m1", "text": "Dragon memory for project A. " * 3, "tags": ["continuity"]}]},
        )
        assert write.status_code == 200
        assert write.json()["entries"][0]["source_id"] == "m1"
        write_2 = client.post(
            "/v1/projects/proj-a/memory",
            json={"entries": [{"source_id": "m2", "text": "Second dragon memory for project A. " * 3, "tags": ["continuity"]}]},
        )
        assert write_2.status_code == 200

        listed = client.get("/v1/projects/proj-a/memory")
        assert listed.status_code == 200
        assert [e["source_id"] for e in listed.json()["entries"]] == ["m1", "m2"]

        found = client.post(
            "/v1/kb/project_memory/search",
            json={"query": "dragon", "project_id": "proj-a", "top_k": 2, "min_score": 0.1},
        )
        assert found.status_code == 200
        assert found.json()["results"][0]["source"]["project_id"] == "proj-a"

        isolated = client.post(
            "/v1/kb/project_memory/search",
            json={"query": "dragon", "project_id": "proj-b", "top_k": 2, "min_score": 0.1},
        )
        assert isolated.status_code == 200
        assert isolated.json()["results"] == []

        cleared = client.delete("/v1/projects/proj-a/memory")
        assert cleared.status_code == 200
        assert cleared.json()["removed"] == 2
        assert client.get("/v1/projects/proj-a/memory").json()["entries"] == []
    finally:
        hub.close()


def test_project_memory_replaces_same_source(tmp_path: Path):
    client, hub = _client(tmp_path)
    try:
        first = client.post(
            "/v1/projects/proj-a/memory",
            json={"entries": [{"source_id": "chapter-1", "text": "Old dragon memory. " * 3, "tags": ["continuity"]}]},
        )
        assert first.status_code == 200
        second = client.post(
            "/v1/projects/proj-a/memory",
            json={"entries": [{"source_id": "chapter-1", "text": "Fresh style memory. " * 3, "tags": ["continuity"]}]},
        )
        assert second.status_code == 200
        listed = client.get("/v1/projects/proj-a/memory")
        entries = listed.json()["entries"]
        assert len(entries) == 1
        assert entries[0]["source_id"] == "chapter-1"
        assert "Fresh style memory" in entries[0]["text"]
    finally:
        hub.close()


def test_manifest_endpoint(tmp_path: Path):
    client, hub = _client(tmp_path)
    try:
        hub.write_manifest()
        r = client.get("/v1/admin/manifest")
        assert r.status_code == 200
        body = r.json()
        assert body["schema_version"] == 1
        assert body["embedding_model"] == "fake"
        assert body["vector_backend"] == "chroma"
        assert isinstance(body["shards"], list)
    finally:
        hub.close()


def test_creative_error_handler_for_bad_kb_type(tmp_path: Path):
    client, hub = _client(tmp_path)
    try:
        r = client.post("/v1/kb/unknown/search", json={"query": "x"})
        assert r.status_code == 500
        assert r.json()["code"] == "creative_error"
        assert r.json()["detail"]["kb_type"] == "unknown"
    finally:
        hub.close()
