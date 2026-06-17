"""Per-project checkpoint store. See docs/technical_architecture.md.10 / 搂11.5.

Phase 2 ships a stdlib-sqlite implementation good enough for thread-level
save/load/list/delete plus retention cleanup. Phase 3 will plug LangGraph's
``SqliteSaver`` in via the same factory; in the meantime tests can exercise
the lifecycle without depending on LangGraph being installed.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from src.shared.config.paths import get_repo_paths
from src.shared.domain.project_paths import ProjectPaths

_SCHEMA = """
CREATE TABLE IF NOT EXISTS threads (
    thread_id  TEXT PRIMARY KEY,
    state_json TEXT NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_threads_updated ON threads(updated_at);
"""


class LocalCheckpointer:
    """Minimal sqlite-backed thread state store."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn

    def save(self, thread_id: str, state: dict, *, now: float | None = None) -> None:
        ts = float(now if now is not None else time.time())
        self._conn.execute(
            "INSERT OR REPLACE INTO threads (thread_id, state_json, updated_at) VALUES (?, ?, ?)",
            (thread_id, json.dumps(state, ensure_ascii=False), ts),
        )
        self._conn.commit()

    def load(self, thread_id: str) -> dict | None:
        cur = self._conn.execute(
            "SELECT state_json FROM threads WHERE thread_id = ?", (thread_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return json.loads(row["state_json"])

    def list_threads(self) -> list[str]:
        cur = self._conn.execute("SELECT thread_id FROM threads ORDER BY updated_at DESC")
        return [r["thread_id"] for r in cur.fetchall()]

    def delete(self, thread_id: str) -> bool:
        cur = self._conn.execute("DELETE FROM threads WHERE thread_id = ?", (thread_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "LocalCheckpointer":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def build_checkpointer(project_id: str, *, projects_root: Path | None = None) -> LocalCheckpointer:
    """Return a checkpointer bound to ``projects/<id>/checkpoints.sqlite``."""
    root = projects_root or get_repo_paths().projects_root
    pp = ProjectPaths(root, project_id)
    pp.ensure_dirs()
    return LocalCheckpointer(pp.checkpoints_sqlite)


def cleanup_expired(checkpoints_path: Path, *, retention_days: int = 30, now: float | None = None) -> int:
    """Delete checkpoint threads older than ``retention_days``.

    Returns the number of rows removed. Missing files are tolerated and yield 0.
    """
    if not Path(checkpoints_path).exists():
        return 0
    cutoff = float(now if now is not None else time.time()) - retention_days * 86400.0
    conn = sqlite3.connect(checkpoints_path)
    try:
        cur = conn.execute("DELETE FROM threads WHERE updated_at < ?", (cutoff,))
        conn.commit()
        return int(cur.rowcount)
    finally:
        conn.close()
