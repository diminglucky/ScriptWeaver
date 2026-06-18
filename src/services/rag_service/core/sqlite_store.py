"""SQLite metadata store, one per shard. See docs/technical_architecture.md.3.

The ``chunks`` table is the source of truth for retrievable chunk text and
ordering. The ``documents`` table is the source manifest used for incremental
sync, source lifecycle, and index previews. ChromaDB stores the vectors.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

_SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id   TEXT PRIMARY KEY,
    source_id  TEXT NOT NULL,
    path       TEXT NOT NULL,
    position   INTEGER NOT NULL DEFAULT 0,
    text       TEXT NOT NULL,
    kb_type    TEXT NOT NULL,
    project_id TEXT,
    tags_json  TEXT NOT NULL DEFAULT '[]',
    ordinal    INTEGER NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_chunks_source   ON chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_chunks_ordinal  ON chunks(ordinal);

CREATE TABLE IF NOT EXISTS documents (
    source_id           TEXT PRIMARY KEY,
    path                TEXT NOT NULL,
    content_hash        TEXT NOT NULL,
    mtime_ns            INTEGER NOT NULL DEFAULT 0,
    size_bytes          INTEGER NOT NULL DEFAULT 0,
    chunk_count         INTEGER NOT NULL DEFAULT 0,
    chunk_settings_json TEXT NOT NULL DEFAULT '{}',
    embedding_model     TEXT NOT NULL DEFAULT '',
    indexed_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_documents_path ON documents(path);
"""


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    raw = d.pop("tags_json", "[]")
    try:
        d["tags"] = json.loads(raw) if raw else []
    except json.JSONDecodeError:
        d["tags"] = []
    return d


class SqliteStore:
    """Thin sqlite wrapper. Connection is lazily opened in :meth:`init`."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Lifecycle

    def init(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.executescript(_SCHEMA)
        conn.commit()
        self._conn = conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "SqliteStore":
        self.init()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("SqliteStore not initialised; call .init() first")
        return self._conn

    # ------------------------------------------------------------------
    # Writes

    def next_ordinal(self) -> int:
        cur = self.conn.execute("SELECT COALESCE(MAX(ordinal), -1) + 1 FROM chunks")
        return int(cur.fetchone()[0])

    def upsert_chunks(self, rows: Iterable[dict]) -> None:
        """Insert or replace chunk rows.

        Each row must contain ``chunk_id``, ``source_id``, ``path``,
        ``position``, ``text``, ``kb_type``, ``ordinal``; ``project_id`` and
        ``tags`` (list[str]) are optional.
        """
        payload = []
        for r in rows:
            payload.append((
                r["chunk_id"],
                r["source_id"],
                r["path"],
                int(r.get("position", 0)),
                r["text"],
                r["kb_type"],
                r.get("project_id"),
                json.dumps(list(r.get("tags") or []), ensure_ascii=False),
                int(r["ordinal"]),
            ))
        self.conn.executemany(
            """
            INSERT OR REPLACE INTO chunks
                (chunk_id, source_id, path, position, text, kb_type, project_id, tags_json, ordinal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            payload,
        )
        self.conn.commit()

    def delete_source(self, source_id: str) -> list[int]:
        """Delete all chunks for a source. Returns the removed ordinals."""
        cur = self.conn.execute(
            "SELECT ordinal FROM chunks WHERE source_id = ?", (source_id,)
        )
        ords = [int(row[0]) for row in cur.fetchall()]
        doc_cur = self.conn.execute(
            "SELECT 1 FROM documents WHERE source_id = ? LIMIT 1", (source_id,)
        )
        has_document = doc_cur.fetchone() is not None
        if ords or has_document:
            if ords:
                self.conn.execute("DELETE FROM chunks WHERE source_id = ?", (source_id,))
            if has_document:
                self.conn.execute("DELETE FROM documents WHERE source_id = ?", (source_id,))
            self.conn.commit()
        return ords

    def clear(self) -> int:
        """Delete all chunk metadata. Returns the removed row count."""
        removed = self.count()
        self.conn.execute("DELETE FROM chunks")
        self.conn.execute("DELETE FROM documents")
        self.conn.commit()
        return removed

    def upsert_documents(self, rows: Iterable[dict]) -> None:
        payload = []
        for row in rows:
            payload.append((
                row["source_id"],
                row["path"],
                row["content_hash"],
                int(row.get("mtime_ns", 0)),
                int(row.get("size_bytes", 0)),
                int(row.get("chunk_count", 0)),
                json.dumps(dict(row.get("chunk_settings") or {}), ensure_ascii=False, sort_keys=True),
                str(row.get("embedding_model", "")),
            ))
        if not payload:
            return
        self.conn.executemany(
            """
            INSERT OR REPLACE INTO documents
                (source_id, path, content_hash, mtime_ns, size_bytes, chunk_count,
                 chunk_settings_json, embedding_model, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            payload,
        )
        self.conn.commit()

    def reassign_ordinals(self, mapping: dict[int, int]) -> None:
        """Apply ``{old_ordinal: new_ordinal}`` updates atomically."""
        if not mapping:
            return
        # Two-phase: bump to a disjoint negative space first to dodge the
        # UNIQUE constraint on ordinal, then settle final values.
        items = list(mapping.items())
        tmp = [(-(i + 1), old) for i, (old, _) in enumerate(items)]
        self.conn.executemany("UPDATE chunks SET ordinal = ? WHERE ordinal = ?", tmp)
        final = [(new, -(i + 1)) for i, (_, new) in enumerate(items)]
        self.conn.executemany("UPDATE chunks SET ordinal = ? WHERE ordinal = ?", final)
        self.conn.commit()

    # ------------------------------------------------------------------
    # Reads

    def fetch_chunks(self, chunk_ids: list[str]) -> list[dict]:
        if not chunk_ids:
            return []
        placeholders = ",".join("?" * len(chunk_ids))
        cur = self.conn.execute(
            f"SELECT * FROM chunks WHERE chunk_id IN ({placeholders})", chunk_ids
        )
        return [_row_to_dict(r) for r in cur.fetchall()]

    def fetch_by_ordinals(self, ordinals: list[int]) -> dict[int, dict]:
        if not ordinals:
            return {}
        placeholders = ",".join("?" * len(ordinals))
        cur = self.conn.execute(
            f"SELECT * FROM chunks WHERE ordinal IN ({placeholders})", ordinals
        )
        return {int(row["ordinal"]): _row_to_dict(row) for row in cur.fetchall()}

    def fetch_source(self, source_id: str) -> list[dict]:
        cur = self.conn.execute(
            "SELECT * FROM chunks WHERE source_id = ? ORDER BY ordinal ASC", (source_id,)
        )
        return [_row_to_dict(row) for row in cur.fetchall()]

    def list_chunks(self) -> list[dict]:
        """Return all chunks ordered by insertion ordinal."""
        cur = self.conn.execute("SELECT * FROM chunks ORDER BY ordinal ASC")
        return [_row_to_dict(row) for row in cur.fetchall()]

    def fetch_documents(self, source_ids: list[str]) -> dict[str, dict]:
        if not source_ids:
            return {}
        placeholders = ",".join("?" * len(source_ids))
        cur = self.conn.execute(
            f"SELECT * FROM documents WHERE source_id IN ({placeholders})", source_ids
        )
        return {str(row["source_id"]): self._document_row_to_dict(row) for row in cur.fetchall()}

    def list_documents(self) -> list[dict]:
        cur = self.conn.execute("SELECT * FROM documents ORDER BY path ASC")
        return [self._document_row_to_dict(row) for row in cur.fetchall()]

    def _document_row_to_dict(self, row: sqlite3.Row) -> dict:
        data = dict(row)
        raw = data.pop("chunk_settings_json", "{}")
        try:
            data["chunk_settings"] = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data["chunk_settings"] = {}
        return data

    def count(self) -> int:
        cur = self.conn.execute("SELECT COUNT(*) FROM chunks")
        return int(cur.fetchone()[0])
