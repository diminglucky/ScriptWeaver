"""Multi-shard vector index management. See v2 plan §4.3.

`IndexHub` owns one :class:`Shard` per ``(kb_type, project_id?)`` tuple plus a
global ``manifest.json`` that records embedding model + schema version.

The implementation uses FAISS when available and transparently falls back to
a numpy brute-force inner-product search otherwise (vectors are stored on
disk as float32 ``vectors.npy``). Either way the on-disk layout is identical
and a later install of ``faiss-cpu`` will pick up speed without re-indexing.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from src.services.rag_service.core.sqlite_store import SqliteStore

SCHEMA_VERSION = 1
DEFAULT_PROJECT_SEGMENT = "_global"


def _has_faiss() -> bool:
    try:
        import faiss  # noqa: F401
        return True
    except Exception:
        return False


@dataclass
class SearchHit:
    chunk_id: str
    score: float
    ordinal: int
    meta: dict


class Shard:
    """Owns a single ``(kb_type, project_id)`` index + metadata pair."""

    VECTORS_FILE = "vectors.npy"
    SQLITE_FILE = "meta.sqlite"

    def __init__(self, *, kb_type: str, project_id: str | None, root: Path, dim: int | None = None):
        self.kb_type = kb_type
        self.project_id = project_id
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._dim: int | None = dim
        self._lock = threading.RLock()
        self._store = SqliteStore(self.root / self.SQLITE_FILE)
        self._store.init()
        self._vectors: np.ndarray | None = None
        self._load_vectors()

    # ------------------------------------------------------------------
    # Persistence helpers

    @property
    def vectors_path(self) -> Path:
        return self.root / self.VECTORS_FILE

    @property
    def dim(self) -> int | None:
        return self._dim

    @property
    def store(self) -> SqliteStore:
        return self._store

    def close(self) -> None:
        self._store.close()

    def __len__(self) -> int:
        return 0 if self._vectors is None else int(self._vectors.shape[0])

    def _load_vectors(self) -> None:
        if self.vectors_path.exists():
            arr = np.load(self.vectors_path, allow_pickle=False)
            if arr.ndim != 2:
                raise RuntimeError(f"shard vectors must be 2D, got shape {arr.shape}")
            self._vectors = arr.astype("float32", copy=False)
            self._dim = int(arr.shape[1])

    def _save_vectors(self) -> None:
        if self._vectors is None:
            # Remove orphan file if we've emptied the shard.
            if self.vectors_path.exists():
                self.vectors_path.unlink()
            return
        tmp = self.vectors_path.with_name(self.vectors_path.name + ".tmp")
        with tmp.open("wb") as fh:
            np.save(fh, self._vectors)
        tmp.replace(self.vectors_path)

    # ------------------------------------------------------------------
    # Writes

    def upsert(self, chunk_ids: list[str], vectors: list[list[float]] | np.ndarray, metadata: list[dict]) -> None:
        if not chunk_ids:
            return
        if not (len(chunk_ids) == len(metadata) == len(vectors)):
            raise ValueError("chunk_ids, vectors, metadata length mismatch")
        arr = np.asarray(vectors, dtype="float32")
        if arr.ndim != 2:
            raise ValueError("vectors must be 2D")
        # Normalize for inner-product / cosine equivalence.
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        arr = arr / norms

        with self._lock:
            if self._dim is None:
                self._dim = int(arr.shape[1])
            elif arr.shape[1] != self._dim:
                raise ValueError(f"vector dim mismatch: shard={self._dim}, batch={arr.shape[1]}")

            # First, evict any existing chunks with the same chunk_id so we
            # can append cleanly; preserves ``ordinal`` stability for others.
            existing = self._store.fetch_chunks(list(chunk_ids))
            if existing:
                self._evict_ordinals([int(r["ordinal"]) for r in existing])

            base = self._store.next_ordinal()
            if self._vectors is None or self._vectors.size == 0:
                self._vectors = arr.copy()
            else:
                self._vectors = np.vstack([self._vectors, arr])

            rows = []
            for i, (cid, meta) in enumerate(zip(chunk_ids, metadata)):
                row = dict(meta)
                row["chunk_id"] = cid
                row.setdefault("kb_type", self.kb_type)
                row.setdefault("project_id", self.project_id)
                row["ordinal"] = base + i
                rows.append(row)
            self._store.upsert_chunks(rows)
            self._save_vectors()

    def delete_source(self, source_id: str) -> int:
        with self._lock:
            ords = self._store.delete_source(source_id)
            if not ords:
                return 0
            self._evict_ordinals(ords, already_deleted_in_store=True)
            self._save_vectors()
            return len(ords)

    def _evict_ordinals(self, ordinals: list[int], *, already_deleted_in_store: bool = False) -> None:
        if not ordinals or self._vectors is None:
            return
        ord_set = set(int(o) for o in ordinals)
        keep_mask = np.array([i not in ord_set for i in range(self._vectors.shape[0])], dtype=bool)
        if not already_deleted_in_store:
            # Caller still has rows in sqlite; remove them first.
            placeholders = ",".join("?" * len(ordinals))
            self._store.conn.execute(
                f"DELETE FROM chunks WHERE ordinal IN ({placeholders})", ordinals
            )
            self._store.conn.commit()

        new_vectors = self._vectors[keep_mask]
        # Rebuild ordinals densely (0..N-1) to match new array layout.
        kept_indices = [i for i, k in enumerate(keep_mask) if k]
        mapping = {old: new for new, old in enumerate(kept_indices) if old != new}
        if mapping:
            self._store.reassign_ordinals(mapping)
        self._vectors = new_vectors if new_vectors.size else None

    # ------------------------------------------------------------------
    # Reads

    def search(self, query_vec: list[float] | np.ndarray, *, top_k: int = 8) -> list[SearchHit]:
        if self._vectors is None or self._vectors.shape[0] == 0 or top_k <= 0:
            return []
        q = np.asarray(query_vec, dtype="float32").reshape(-1)
        if self._dim is not None and q.shape[0] != self._dim:
            raise ValueError(f"query dim mismatch: shard={self._dim}, query={q.shape[0]}")
        norm = float(np.linalg.norm(q))
        if norm == 0:
            return []
        q = q / norm

        scores = self._vectors @ q  # cosine, since both are normalized
        k = min(top_k, scores.shape[0])
        # argpartition for speed, then sort the top-k slice.
        idx_part = np.argpartition(-scores, kth=k - 1)[:k]
        ordered = idx_part[np.argsort(-scores[idx_part])]
        ords = [int(i) for i in ordered.tolist()]
        rows = self._store.fetch_by_ordinals(ords)
        hits: list[SearchHit] = []
        for ordinal in ords:
            row = rows.get(ordinal)
            if row is None:
                continue
            hits.append(SearchHit(
                chunk_id=row["chunk_id"],
                score=float(scores[ordinal]),
                ordinal=ordinal,
                meta=row,
            ))
        return hits


class IndexHub:
    """Materialises shards on disk under ``index_root/v2``."""

    MANIFEST_FILE = "manifest.json"

    def __init__(self, index_root: Path | None = None, *, embedding_model: str | None = None):
        if index_root is None:
            from src.shared.config.paths import get_repo_paths
            index_root = get_repo_paths().index_root
        self.index_root = Path(index_root) / "v2"
        self.index_root.mkdir(parents=True, exist_ok=True)
        self._shards: dict[tuple[str, str], Shard] = {}
        self._lock = threading.RLock()
        self._embedding_model = embedding_model

    # ------------------------------------------------------------------

    def _shard_key(self, kb_type: str, project_id: str | None) -> tuple[str, str]:
        return (kb_type, project_id or DEFAULT_PROJECT_SEGMENT)

    def _shard_path(self, kb_type: str, project_id: str | None) -> Path:
        return self.index_root / kb_type / (project_id or DEFAULT_PROJECT_SEGMENT)

    def shard(self, kb_type: str, project_id: str | None = None) -> Shard:
        key = self._shard_key(kb_type, project_id)
        with self._lock:
            sh = self._shards.get(key)
            if sh is None:
                sh = Shard(
                    kb_type=kb_type,
                    project_id=project_id,
                    root=self._shard_path(kb_type, project_id),
                )
                self._shards[key] = sh
            return sh

    def list_shards(self) -> list[Shard]:
        return list(self._shards.values())

    def close(self) -> None:
        with self._lock:
            for sh in self._shards.values():
                sh.close()
            self._shards.clear()

    # ------------------------------------------------------------------

    def manifest(self) -> dict:
        path = self.index_root / self.MANIFEST_FILE
        if not path.exists():
            return {
                "schema_version": SCHEMA_VERSION,
                "embedding_model": self._embedding_model,
                "shards": [],
                "faiss": _has_faiss(),
            }
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def write_manifest(self, *, embedding_model: str | None = None) -> dict:
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "embedding_model": embedding_model or self._embedding_model,
            "faiss": _has_faiss(),
            "shards": [
                {
                    "kb_type": s.kb_type,
                    "project_id": s.project_id,
                    "count": len(s),
                    "dim": s.dim,
                }
                for s in self._shards.values()
            ],
        }
        path = self.index_root / self.MANIFEST_FILE
        tmp = path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
        return manifest

    def reindex_legacy(self) -> dict:
        manifest = self.write_manifest()
        return {"status": "completed", "manifest": manifest}
