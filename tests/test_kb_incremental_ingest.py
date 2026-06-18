from __future__ import annotations

from pathlib import Path

from src.kb.ingest import IngestConfig, KnowledgeBaseIngestor

TEXT_V1 = (
    "The first reference paragraph gives the system enough material to build a chunk.\n\n"
    "The second paragraph keeps continuity and makes the document useful for retrieval."
)
TEXT_V2 = (
    "The first reference paragraph has been rewritten with new details for the index.\n\n"
    "The second paragraph keeps continuity and makes the document useful for retrieval.\n\n"
    "The third paragraph is newly added and should force a source-level replacement."
)
TEXT_NEW = "A newly added reference document with enough detail to become an indexed chunk."


class _FakeStore:
    def __init__(self) -> None:
        self.docs: dict[str, dict] = {}
        self.chunks: dict[str, list[dict]] = {}

    def fetch_documents(self, source_ids: list[str]) -> dict[str, dict]:
        return {source_id: self.docs[source_id] for source_id in source_ids if source_id in self.docs}

    def list_documents(self) -> list[dict]:
        return list(self.docs.values())

    def upsert_documents(self, rows: list[dict]) -> None:
        for row in rows:
            self.docs[row["source_id"]] = dict(row)


class _FakeShard:
    def __init__(self) -> None:
        self.store = _FakeStore()
        self.clear_calls = 0
        self.upsert_calls = 0
        self.replace_calls = 0
        self.deleted_sources: list[str] = []

    def clear(self) -> int:
        removed = sum(len(rows) for rows in self.store.chunks.values())
        self.store.chunks.clear()
        self.store.docs.clear()
        self.clear_calls += 1
        return removed

    def upsert(self, chunk_ids: list[str], vectors: list[list[float]], metadata: list[dict]) -> None:
        self.upsert_calls += 1
        self._store_chunks(metadata)

    def replace_sources(self, chunk_ids: list[str], vectors: list[list[float]], metadata: list[dict]) -> int:
        self.replace_calls += 1
        removed = 0
        for source_id in {row["source_id"] for row in metadata}:
            removed += self.delete_source(source_id)
        self._store_chunks(metadata)
        return removed

    def delete_source(self, source_id: str) -> int:
        rows = self.store.chunks.pop(source_id, [])
        self.store.docs.pop(source_id, None)
        self.deleted_sources.append(source_id)
        return len(rows)

    def _store_chunks(self, metadata: list[dict]) -> None:
        for row in metadata:
            self.store.chunks.setdefault(row["source_id"], []).append(dict(row))


class _FakeHub:
    def __init__(self, *args, **kwargs) -> None:
        self.fake_shard = _FakeShard()
        self.manifest_writes = 0
        self.closed = False

    def shard(self, kb_type: str, project_id: str | None = None) -> _FakeShard:
        return self.fake_shard

    def write_manifest(self) -> None:
        self.manifest_writes += 1

    def close(self) -> None:
        self.closed = True


class _FakeEmbeddingHub:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text) or 1), 1.0] for text in texts]


def _patch_ingest_backends(monkeypatch, hub: _FakeHub) -> None:
    monkeypatch.setattr("src.kb.ingest._load_kb_backends", lambda: True)
    monkeypatch.setattr("src.kb.ingest.EmbeddingHub", _FakeEmbeddingHub)
    monkeypatch.setattr("src.kb.ingest.IndexHub", lambda *args, **kwargs: hub)


def test_incremental_ingest_skips_unchanged_document(tmp_path: Path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    (data / "a.txt").write_text(TEXT_V1, encoding="utf-8")
    hub = _FakeHub()
    _patch_ingest_backends(monkeypatch, hub)

    full = KnowledgeBaseIngestor(IngestConfig(data_root=data, index_dir=tmp_path / "index")).build()
    assert full.indexed == 1
    assert hub.fake_shard.upsert_calls == 1

    inc = KnowledgeBaseIngestor(
        IngestConfig(data_root=data, index_dir=tmp_path / "index", rebuild=False)
    ).build()
    assert inc.skipped == 1
    assert inc.indexed == 0
    assert inc.updated == 0
    assert hub.fake_shard.replace_calls == 0
    assert hub.manifest_writes == 2


def test_incremental_ingest_replaces_changed_document(tmp_path: Path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    source = data / "a.txt"
    source.write_text(TEXT_V1, encoding="utf-8")
    hub = _FakeHub()
    _patch_ingest_backends(monkeypatch, hub)

    KnowledgeBaseIngestor(IngestConfig(data_root=data, index_dir=tmp_path / "index")).build()
    source.write_text(TEXT_V2, encoding="utf-8")

    inc = KnowledgeBaseIngestor(
        IngestConfig(data_root=data, index_dir=tmp_path / "index", rebuild=False)
    ).build()
    assert inc.updated == 1
    assert inc.chunk_count > 0
    assert hub.fake_shard.replace_calls == 1
    assert str(source) in hub.fake_shard.deleted_sources


def test_incremental_ingest_prunes_deleted_document(tmp_path: Path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    source = data / "a.txt"
    source.write_text(TEXT_V1, encoding="utf-8")
    hub = _FakeHub()
    _patch_ingest_backends(monkeypatch, hub)

    KnowledgeBaseIngestor(IngestConfig(data_root=data, index_dir=tmp_path / "index")).build()
    source.unlink()
    (data / "b.txt").write_text(TEXT_NEW, encoding="utf-8")

    inc = KnowledgeBaseIngestor(
        IngestConfig(data_root=data, index_dir=tmp_path / "index", rebuild=False)
    ).build()
    assert inc.removed > 0
    assert str(source) in hub.fake_shard.deleted_sources
