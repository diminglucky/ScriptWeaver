"""CreativeRetriever: query multiple shards and merge results.

See v2 plan §4.3 / §4.6.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from src.services.rag_service.core.citations import pack_context
from src.shared.domain.schemas import RetrievedContext

if TYPE_CHECKING:
    from src.services.rag_service.core.index_hub import IndexHub


class _Embedder(Protocol):
    async def encode_async(self, texts: list[str]) -> list[list[float]]:
        ...


class CreativeRetriever:
    """Embeds the query once, fans out across shards, merges by score."""

    def __init__(self, *, hub: "IndexHub", embedder: _Embedder):
        self.hub = hub
        self.embedder = embedder

    async def retrieve(
        self,
        query: str,
        *,
        kb_types: list[str],
        project_id: str | None,
        top_k: int = 8,
        min_score: float = 0.0,
        tags: list[str] | None = None,
    ) -> list[RetrievedContext]:
        if not query or not query.strip():
            return []
        if not kb_types:
            return []

        vecs = await self.embedder.encode_async([query])
        if not vecs:
            return []
        qvec = vecs[0]

        wanted_tags = set(tags or [])
        # Over-fetch per shard so we have headroom after merge + filtering.
        per_shard_k = max(top_k * 2, top_k)

        merged: list[tuple[float, dict, str]] = []
        for kb_type in kb_types:
            target_project = project_id if kb_type == "project_memory" else None
            shard = self.hub.shard(kb_type, target_project)
            if len(shard) == 0:
                continue
            try:
                hits = shard.search(qvec, top_k=per_shard_k)
            except ValueError:
                # Dim mismatch (e.g. legacy shard, swapped embedding model).
                continue
            for hit in hits:
                if hit.score < min_score:
                    continue
                row_tags = set(hit.meta.get("tags") or [])
                if wanted_tags and not wanted_tags.issubset(row_tags):
                    continue
                merged.append((hit.score, hit.meta, kb_type))

        merged.sort(key=lambda t: t[0], reverse=True)
        out: list[RetrievedContext] = []
        for score, row, kb_type in merged[:top_k]:
            out.append(pack_context(
                text=row["text"],
                source_id=row["source_id"],
                path=row.get("path", ""),
                chunk_id=row["chunk_id"],
                score=float(score),
                kb_type=kb_type,
                project_id=row.get("project_id"),
            ))
        return out
