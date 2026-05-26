"""Tests for story_service.core.workflows.checkpoint."""
from __future__ import annotations

import time
from pathlib import Path

from src.services.story_service.core.workflows.checkpoint import (
    LocalCheckpointer,
    build_checkpointer,
    cleanup_expired,
)


def test_save_load_roundtrip(tmp_path: Path):
    with LocalCheckpointer(tmp_path / "cp.sqlite") as cp:
        cp.save("t1", {"step": 1, "data": [1, 2, 3]})
        assert cp.load("t1") == {"step": 1, "data": [1, 2, 3]}
        cp.save("t1", {"step": 2})
        assert cp.load("t1") == {"step": 2}


def test_list_and_delete(tmp_path: Path):
    with LocalCheckpointer(tmp_path / "cp.sqlite") as cp:
        cp.save("a", {}, now=1.0)
        cp.save("b", {}, now=2.0)
        cp.save("c", {}, now=3.0)
        assert cp.list_threads() == ["c", "b", "a"]
        assert cp.delete("b") is True
        assert cp.delete("missing") is False
        assert cp.list_threads() == ["c", "a"]


def test_load_missing_returns_none(tmp_path: Path):
    with LocalCheckpointer(tmp_path / "cp.sqlite") as cp:
        assert cp.load("nope") is None


def test_build_checkpointer_creates_under_project(tmp_path: Path):
    cp = build_checkpointer("proj-1", projects_root=tmp_path)
    try:
        cp.save("t1", {"x": 1})
        expected = tmp_path / "proj-1" / "checkpoints.sqlite"
        assert expected.exists()
    finally:
        cp.close()


def test_cleanup_expired_removes_old(tmp_path: Path):
    db = tmp_path / "cp.sqlite"
    with LocalCheckpointer(db) as cp:
        now = time.time()
        cp.save("old", {}, now=now - 31 * 86400)
        cp.save("fresh", {}, now=now - 1)
    removed = cleanup_expired(db, retention_days=30, now=now)
    assert removed == 1
    with LocalCheckpointer(db) as cp2:
        assert cp2.list_threads() == ["fresh"]


def test_cleanup_expired_missing_file_is_no_op(tmp_path: Path):
    assert cleanup_expired(tmp_path / "absent.sqlite") == 0
