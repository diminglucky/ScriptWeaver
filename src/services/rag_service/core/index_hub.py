"""Multi-shard ChromaDB vector index management.

`IndexHub` owns one :class:`Shard` per ``(kb_type, project_id?)`` tuple plus a
global ``manifest.json`` that records embedding model and schema version.
ChromaDB is the only vector backend; SQLite stores chunk text and metadata.
"""

from __future__ import annotations

import json
import logging
import math
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.services.rag_service.core.sqlite_store import SqliteStore

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
DEFAULT_PROJECT_SEGMENT = "_global"
VECTOR_BACKEND = "chroma"


@dataclass
class SearchHit:
    chunk_id: str
    score: float
    ordinal: int
    meta: dict


def _normalize_vector(vector: list[float] | tuple[float, ...]) -> list[float] | None:
    values = [float(x) for x in vector]
    norm = math.sqrt(sum(x * x for x in values))
    if norm <= 0:
        return None
    return [x / norm for x in values]


def _normalize_vectors(vectors: list[list[float]]) -> list[list[float]]:
    out: list[list[float]] = []
    for vector in vectors:
        normalized = _normalize_vector(vector)
        if normalized is None:
            normalized = [0.0 for _ in vector]
        out.append(normalized)
    return out


class Shard:
    """Owns a single ``(kb_type, project_id)`` Chroma collection + metadata store."""

    SQLITE_FILE = "meta.sqlite"

    def __init__(
        self,
        *,
        kb_type: str,
        project_id: str | None,
        root: Path,
        dim: int | None = None,
    ):
        self.kb_type = kb_type
        self.project_id = project_id
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._dim: int | None = dim
        self._lock = threading.RLock()
        self._store = SqliteStore(self.root / self.SQLITE_FILE)
        self._store.init()
        self._chroma_client: Any | None = None
        self._chroma_collection: Any | None = None
        self._init_chroma()

    @property
    def _uses_chroma(self) -> bool:
        return True

    def _init_chroma(self) -> None:
        import chromadb
        from chromadb.config import Settings

        chroma_root = self.root / "chroma"
        self._chroma_client = chromadb.PersistentClient(
            path=str(chroma_root),
            settings=Settings(anonymized_telemetry=False),
        )
        self._chroma_collection = self._chroma_client.get_or_create_collection(
            name="chunks",
            metadata={
                "kb_type": self.kb_type,
                "project_id": self.project_id or DEFAULT_PROJECT_SEGMENT,
                "hnsw:space": "cosine",
            },
        )

    @property
    def dim(self) -> int | None:
        return self._dim

    @property
    def store(self) -> SqliteStore:
        return self._store

    def close(self) -> None:
        self._chroma_collection = None
        client = self._chroma_client
        self._chroma_client = None
        if client is not None:
            try:
                system = getattr(client, "_system", None)
                stop = getattr(system, "stop", None)
                if callable(stop):
                    stop()
                clear_cache = getattr(client, "clear_system_cache", None)
                if callable(clear_cache):
                    clear_cache()
            except Exception as exc:
                logger.debug("failed to close chroma client for shard %s: %s", self.root, exc)
        self._store.close()

    def __len__(self) -> int:
        return self._store.count()

    def upsert(self, chunk_ids: list[str], vectors: list[list[float]], metadata: list[dict]) -> None:
        if not chunk_ids:
            return
        if not (len(chunk_ids) == len(metadata) == len(vectors)):
            raise ValueError("chunk_ids, vectors, metadata length mismatch")
        if any(not isinstance(v, list) or not v for v in vectors):
            raise ValueError("vectors must be non-empty lists")

        dim = len(vectors[0])
        if any(len(v) != dim for v in vectors):
            raise ValueError("all vectors must have the same dimension")

        with self._lock:
            if self._dim is None:
                self._dim = dim
            elif dim != self._dim:
                raise ValueError(f"vector dim mismatch: shard={self._dim}, batch={dim}")
            self._chroma_upsert(chunk_ids, _normalize_vectors(vectors), metadata)

    def _chroma_upsert(self, chunk_ids: list[str], vectors: list[list[float]], metadata: list[dict]) -> None:
        if self._chroma_collection is None:
            raise RuntimeError("Chroma collection is not initialised")

        existing = self._store.fetch_chunks(list(chunk_ids))
        if existing:
            self._chroma_collection.delete(ids=[row["chunk_id"] for row in existing])

        base = self._store.next_ordinal()
        rows = []
        docs = []
        metadatas = []
        for i, (cid, meta) in enumerate(zip(chunk_ids, metadata)):
            row = dict(meta)
            row["chunk_id"] = cid
            row.setdefault("kb_type", self.kb_type)
            row.setdefault("project_id", self.project_id)
            row["ordinal"] = base + i
            rows.append(row)
            docs.append(str(row.get("text", "")))
            metadatas.append({
                "source_id": str(row.get("source_id", "")),
                "path": str(row.get("path", "")),
                "position": int(row.get("position", 0)),
                "kb_type": str(row.get("kb_type", self.kb_type)),
                "project_id": str(row.get("project_id") or ""),
                "tags": ",".join(str(x) for x in row.get("tags", []) or []),
            })

        self._chroma_collection.upsert(
            ids=chunk_ids,
            embeddings=vectors,
            documents=docs,
            metadatas=metadatas,
        )
        if existing:
            placeholders = ",".join("?" * len(existing))
            self._store.conn.execute(
                f"DELETE FROM chunks WHERE chunk_id IN ({placeholders})",
                [row["chunk_id"] for row in existing],
            )
            self._store.conn.commit()
        self._store.upsert_chunks(rows)

    def delete_source(self, source_id: str) -> int:
        with self._lock:
            existing = self._store.fetch_source(source_id)
            if not existing:
                return 0
            if self._chroma_collection is None:
                raise RuntimeError("Chroma collection is not initialised")
            self._chroma_collection.delete(ids=[row["chunk_id"] for row in existing])
            ords = self._store.delete_source(source_id)
            return len(ords)

    def search(self, query_vec: list[float], *, top_k: int = 8) -> list[SearchHit]:
        if top_k <= 0 or len(self) == 0:
            return []
        q = _normalize_vector(query_vec)
        if q is None:
            return []
        if self._dim is not None and len(q) != self._dim:
            raise ValueError(f"query dim mismatch: shard={self._dim}, query={len(q)}")
        if self._dim is None:
            self._dim = len(q)
        if self._chroma_collection is None:
            raise RuntimeError("Chroma collection is not initialised")

        result = self._chroma_collection.query(
            query_embeddings=[q],
            n_results=top_k,
            include=["metadatas", "distances", "documents"],
        )
        ids = (result.get("ids") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        hits: list[SearchHit] = []
        for idx, cid in enumerate(ids):
            meta = dict(metadatas[idx] or {})
            stored = self._store.fetch_chunks([str(cid)])
            if stored:
                meta = stored[0]
            else:
                meta["chunk_id"] = cid
                meta["text"] = docs[idx] if idx < len(docs) else meta.get("text", "")
            raw_tags = str(meta.get("tags", "") or "")
            if isinstance(meta.get("tags"), str):
                meta["tags"] = [x for x in raw_tags.split(",") if x]
            if not meta.get("project_id"):
                meta["project_id"] = None
            distance = float(distances[idx]) if idx < len(distances) else 1.0
            score = max(0.0, 1.0 - distance)
            hits.append(SearchHit(chunk_id=str(cid), score=score, ordinal=int(meta.get("ordinal", idx)), meta=meta))
        return hits


class IndexHub:
    """Materialises Chroma-backed shards on disk under ``index_root/v2``."""

    MANIFEST_FILE = "manifest.json"

    def __init__(
        self,
        index_root: Path | None = None,
        *,
        embedding_model: str | None = None,
    ):
        if index_root is None:
            from src.shared.config.paths import get_repo_paths

            index_root = get_repo_paths().index_root
        self.index_root = Path(index_root) / "v2"
        self.index_root.mkdir(parents=True, exist_ok=True)
        self._shards: dict[tuple[str, str], Shard] = {}
        self._lock = threading.RLock()
        self._embedding_model = embedding_model

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

    def manifest(self) -> dict:
        path = self.index_root / self.MANIFEST_FILE
        if not path.exists():
            return {
                "schema_version": SCHEMA_VERSION,
                "embedding_model": self._embedding_model,
                "shards": [],
                "vector_backend": VECTOR_BACKEND,
            }
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def write_manifest(self, *, embedding_model: str | None = None) -> dict:
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "embedding_model": embedding_model or self._embedding_model,
            "vector_backend": VECTOR_BACKEND,
            "shards": [
                {
                    "kb_type": s.kb_type,
                    "project_id": s.project_id,
                    "count": len(s),
                    "dim": s.dim,
                    "backend": VECTOR_BACKEND,
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

    def rebuild_manifest(self) -> dict:
        manifest = self.write_manifest()
        return {"status": "completed", "manifest": manifest}
