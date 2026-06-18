"""Tests for rag_service.core.index_hub: Chroma Shard + IndexHub end-to-end."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.rag_service.core.index_hub import (
    DEFAULT_PROJECT_SEGMENT,
    IndexHub,
    SCHEMA_VERSION,
    Shard,
)


pytest.importorskip("chromadb")


def _v(*xs: float) -> list[float]:
    return list(xs)


def _meta(chunk_id: str, source_id: str, **extra) -> dict:
    base = {
        "source_id": source_id,
        "path": f"/{source_id}.txt",
        "position": 0,
        "text": f"text-{chunk_id}",
    }
    base.update(extra)
    return base


def test_shard_upsert_and_search(tmp_path: Path):
    sh = Shard(kb_type="reference", project_id=None, root=tmp_path)
    try:
        sh.upsert(
            chunk_ids=["c1", "c2", "c3"],
            vectors=[_v(1, 0, 0), _v(0, 1, 0), _v(0, 0, 1)],
            metadata=[_meta("c1", "s1"), _meta("c2", "s1"), _meta("c3", "s2")],
        )
        assert len(sh) == 3
        assert sh.dim == 3
        hits = sh.search([0.95, 0.05, 0], top_k=2)
        assert hits[0].chunk_id == "c1"
        assert hits[0].score > hits[1].score
    finally:
        sh.close()


def test_shard_persists_across_reopen(tmp_path: Path):
    sh = Shard(kb_type="reference", project_id=None, root=tmp_path)
    sh.upsert(["c1"], [_v(1, 0)], [_meta("c1", "s1")])
    sh.close()

    sh2 = Shard(kb_type="reference", project_id=None, root=tmp_path)
    try:
        assert len(sh2) == 1
        hits = sh2.search([1, 0], top_k=1)
        assert hits and hits[0].chunk_id == "c1"
    finally:
        sh2.close()


def test_shard_delete_source_removes_from_chroma_and_metadata(tmp_path: Path):
    sh = Shard(kb_type="reference", project_id=None, root=tmp_path)
    try:
        sh.upsert(
            ["c1", "c2", "c3"],
            [_v(1, 0), _v(0, 1), _v(1, 1)],
            [_meta("c1", "s1"), _meta("c2", "s1"), _meta("c3", "s2")],
        )
        removed = sh.delete_source("s1")
        assert removed == 2
        assert len(sh) == 1
        hits = sh.search([1, 1], top_k=3)
        assert [hit.chunk_id for hit in hits] == ["c3"]
    finally:
        sh.close()


def test_shard_upsert_replaces_existing_chunk_id(tmp_path: Path):
    sh = Shard(kb_type="reference", project_id=None, root=tmp_path)
    try:
        sh.upsert(["c1"], [_v(1, 0)], [_meta("c1", "s1", text="v1")])
        sh.upsert(["c1"], [_v(0, 1)], [_meta("c1", "s1", text="v2")])
        assert len(sh) == 1
        hits = sh.search([0, 1], top_k=1)
        assert hits[0].chunk_id == "c1"
        assert hits[0].meta["text"] == "v2"
    finally:
        sh.close()


def test_shard_replace_sources_removes_stale_chunks(tmp_path: Path):
    sh = Shard(kb_type="reference", project_id=None, root=tmp_path)
    try:
        sh.upsert(
            ["old-1", "old-2", "keep"],
            [_v(1, 0), _v(1, 0), _v(0, 1)],
            [_meta("old-1", "s1"), _meta("old-2", "s1"), _meta("keep", "s2")],
        )
        removed = sh.replace_sources(["new-1"], [_v(1, 0)], [_meta("new-1", "s1", text="fresh")])
        assert removed == 2
        rows = sh.store.list_chunks()
        assert {row["chunk_id"] for row in rows} == {"new-1", "keep"}
        hits = sh.search([1, 0], top_k=5)
        assert "old-1" not in [hit.chunk_id for hit in hits]
        assert hits[0].chunk_id == "new-1"
    finally:
        sh.close()


def test_shard_replace_sources_validates_dim_before_delete(tmp_path: Path):
    sh = Shard(kb_type="reference", project_id=None, root=tmp_path)
    try:
        sh.upsert(["old"], [_v(1, 0)], [_meta("old", "s1")])
        with pytest.raises(ValueError):
            sh.replace_sources(["new"], [_v(1, 0, 0)], [_meta("new", "s1")])
        assert [row["chunk_id"] for row in sh.store.list_chunks()] == ["old"]
    finally:
        sh.close()


def test_shard_clear_removes_vectors_and_metadata(tmp_path: Path):
    sh = Shard(kb_type="reference", project_id=None, root=tmp_path)
    try:
        sh.upsert(["c1", "c2"], [_v(1, 0), _v(0, 1)], [_meta("c1", "s1"), _meta("c2", "s2")])
        assert sh.clear() == 2
        assert len(sh) == 0
        assert sh.search([1, 0], top_k=2) == []
    finally:
        sh.close()


def test_shard_dim_mismatch_raises(tmp_path: Path):
    sh = Shard(kb_type="reference", project_id=None, root=tmp_path)
    try:
        sh.upsert(["c1"], [_v(1, 0, 0)], [_meta("c1", "s1")])
        with pytest.raises(ValueError):
            sh.upsert(["c2"], [_v(1, 0)], [_meta("c2", "s1")])
        with pytest.raises(ValueError):
            sh.search([1, 0], top_k=1)
    finally:
        sh.close()


def test_shard_zero_query_returns_empty(tmp_path: Path):
    sh = Shard(kb_type="reference", project_id=None, root=tmp_path)
    try:
        sh.upsert(["c1"], [_v(1, 0)], [_meta("c1", "s1")])
        assert sh.search([0, 0], top_k=3) == []
    finally:
        sh.close()


def test_shard_multiple_upserts_keep_distinct_ordinals(tmp_path: Path):
    sh = Shard(kb_type="reference", project_id=None, root=tmp_path)
    try:
        sh.upsert(["c1"], [_v(1, 0)], [_meta("c1", "s1")])
        sh.upsert(["c2"], [_v(0, 1)], [_meta("c2", "s2")])
        rows = sh.store.list_chunks()
        assert [row["chunk_id"] for row in rows] == ["c1", "c2"]
        assert [row["ordinal"] for row in rows] == [0, 1]
    finally:
        sh.close()


def test_index_hub_shard_isolation(tmp_path: Path):
    hub = IndexHub(index_root=tmp_path)
    try:
        s_ref = hub.shard("reference")
        s_proj = hub.shard("project_memory", "proj-1")
        assert s_ref is hub.shard("reference")
        assert s_ref is not s_proj
        ref_path = tmp_path / "v2" / "reference" / DEFAULT_PROJECT_SEGMENT
        proj_path = tmp_path / "v2" / "project_memory" / "proj-1"
        assert ref_path.exists() and proj_path.exists()
    finally:
        hub.close()


def test_index_hub_manifest_write_and_read(tmp_path: Path):
    hub = IndexHub(index_root=tmp_path, embedding_model="test-model")
    try:
        sh = hub.shard("reference")
        sh.upsert(["c1"], [_v(1, 0)], [_meta("c1", "s1")])
        manifest = hub.write_manifest()
        assert manifest["schema_version"] == SCHEMA_VERSION
        assert manifest["embedding_model"] == "test-model"
        assert manifest["vector_backend"] == "chroma"
        assert manifest["shards"][0]["backend"] == "chroma"
        assert manifest["shards"][0]["count"] == 1
        on_disk = json.loads((tmp_path / "v2" / IndexHub.MANIFEST_FILE).read_text("utf-8"))
        assert on_disk == manifest
        assert hub.manifest() == manifest
    finally:
        hub.close()
