"""Tests for rag_service.core.sqlite_store.SqliteStore."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.services.rag_service.core.sqlite_store import SqliteStore


def _row(chunk_id: str, source_id: str, ordinal: int, **kw) -> dict:
    base = {
        "chunk_id": chunk_id,
        "source_id": source_id,
        "path": kw.pop("path", f"/data/{source_id}.txt"),
        "position": kw.pop("position", 0),
        "text": kw.pop("text", f"text-{chunk_id}"),
        "kb_type": kw.pop("kb_type", "reference"),
        "project_id": kw.pop("project_id", None),
        "tags": kw.pop("tags", []),
        "ordinal": ordinal,
    }
    base.update(kw)
    return base


def test_init_creates_schema(tmp_path: Path):
    store = SqliteStore(tmp_path / "meta.sqlite")
    store.init()
    try:
        assert store.count() == 0
        assert store.next_ordinal() == 0
    finally:
        store.close()


def test_upsert_and_fetch_roundtrip(tmp_path: Path):
    with SqliteStore(tmp_path / "m.sqlite") as store:
        store.upsert_chunks([
            _row("c1", "s1", 0, tags=["chinese", "novel"]),
            _row("c2", "s1", 1, position=1),
        ])
        assert store.count() == 2
        rows = store.fetch_chunks(["c1", "c2"])
        assert sorted(r["chunk_id"] for r in rows) == ["c1", "c2"]
        c1 = next(r for r in rows if r["chunk_id"] == "c1")
        assert c1["tags"] == ["chinese", "novel"]
        assert c1["source_id"] == "s1"


def test_upsert_replaces_existing_row(tmp_path: Path):
    with SqliteStore(tmp_path / "m.sqlite") as store:
        store.upsert_chunks([_row("c1", "s1", 0, text="v1")])
        store.upsert_chunks([_row("c1", "s1", 0, text="v2")])
        rows = store.fetch_chunks(["c1"])
        assert len(rows) == 1 and rows[0]["text"] == "v2"


def test_delete_source_returns_ordinals(tmp_path: Path):
    with SqliteStore(tmp_path / "m.sqlite") as store:
        store.upsert_chunks([
            _row("c1", "s1", 0),
            _row("c2", "s1", 1),
            _row("c3", "s2", 2),
        ])
        ords = store.delete_source("s1")
        assert sorted(ords) == [0, 1]
        assert store.count() == 1
        assert store.delete_source("missing") == []


def test_fetch_by_ordinals(tmp_path: Path):
    with SqliteStore(tmp_path / "m.sqlite") as store:
        store.upsert_chunks([
            _row("c1", "s1", 0),
            _row("c2", "s1", 1),
        ])
        out = store.fetch_by_ordinals([0, 1, 99])
        assert set(out.keys()) == {0, 1}
        assert out[0]["chunk_id"] == "c1"


def test_fetch_source_returns_ordered_rows(tmp_path: Path):
    with SqliteStore(tmp_path / "m.sqlite") as store:
        store.upsert_chunks([
            _row("c1", "s1", 0),
            _row("c2", "s2", 1),
            _row("c3", "s1", 2),
        ])
        rows = store.fetch_source("s1")
        assert [row["chunk_id"] for row in rows] == ["c1", "c3"]
        assert store.fetch_source("missing") == []


def test_reassign_ordinals_handles_collisions(tmp_path: Path):
    with SqliteStore(tmp_path / "m.sqlite") as store:
        store.upsert_chunks([
            _row("c1", "s1", 0),
            _row("c2", "s1", 1),
            _row("c3", "s1", 2),
        ])
        # Compaction-style remap: free ordinal 1 first, then shift 2→1.
        store.conn.execute("DELETE FROM chunks WHERE ordinal = 1")
        store.conn.commit()
        store.reassign_ordinals({2: 1})
        rows = store.fetch_by_ordinals([0, 1])
        assert rows[1]["chunk_id"] == "c3"


def test_conn_property_requires_init(tmp_path: Path):
    store = SqliteStore(tmp_path / "m.sqlite")
    with pytest.raises(RuntimeError):
        _ = store.conn
