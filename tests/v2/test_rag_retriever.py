"""Tests for CreativeRetriever multi-shard merge + filtering."""
from __future__ import annotations

import asyncio
from pathlib import Path

from src.services.rag_service.core.index_hub import IndexHub
from src.services.rag_service.core.retrievers import CreativeRetriever


class _FakeEmbedder:
    """Deterministic embedder that maps queries to a unit basis vector."""

    def __init__(self, mapping: dict[str, list[float]]):
        self._mapping = mapping

    async def encode_async(self, texts: list[str]) -> list[list[float]]:
        return [self._mapping[t] for t in texts]


def _seed(hub: IndexHub) -> None:
    ref = hub.shard("reference")
    ref.upsert(
        chunk_ids=["ref-1", "ref-2"],
        vectors=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        metadata=[
            {"source_id": "book", "path": "/r/book.txt", "text": "reference-A", "tags": ["lore"]},
            {"source_id": "book", "path": "/r/book.txt", "text": "reference-B", "tags": ["style"]},
        ],
    )
    mem = hub.shard("project_memory", "proj-1")
    mem.upsert(
        chunk_ids=["mem-1"],
        vectors=[[1.0, 0.0, 0.0]],
        metadata=[
            {"source_id": "mem", "path": "memory://proj-1", "text": "project-memo"},
        ],
    )


def test_retriever_merges_shards_and_sorts_by_score(tmp_path: Path):
    hub = IndexHub(index_root=tmp_path)
    try:
        _seed(hub)
        retriever = CreativeRetriever(
            hub=hub,
            embedder=_FakeEmbedder({"q": [1.0, 0.0, 0.0]}),
        )
        out = asyncio.run(retriever.retrieve(
            "q", kb_types=["reference", "project_memory"], project_id="proj-1", top_k=3,
        ))
        assert [c.text for c in out[:2]] == ["reference-A", "project-memo"]
        assert out[0].source.score >= out[1].source.score
        # kb_type is preserved per chunk.
        kb_types = {c.source.kb_type for c in out}
        assert kb_types == {"reference", "project_memory"}
    finally:
        hub.close()


def test_project_memory_isolation(tmp_path: Path):
    hub = IndexHub(index_root=tmp_path)
    try:
        _seed(hub)
        retriever = CreativeRetriever(
            hub=hub, embedder=_FakeEmbedder({"q": [1.0, 0.0, 0.0]}),
        )
        # Asking for project 'other' must NOT see proj-1 memories.
        out = asyncio.run(retriever.retrieve(
            "q", kb_types=["project_memory"], project_id="other", top_k=5,
        ))
        assert out == []
    finally:
        hub.close()


def test_min_score_filter(tmp_path: Path):
    hub = IndexHub(index_root=tmp_path)
    try:
        _seed(hub)
        retriever = CreativeRetriever(
            hub=hub, embedder=_FakeEmbedder({"q": [1.0, 0.0, 0.0]}),
        )
        # ref-2 sits orthogonal to the query → score ~0; should be dropped.
        out = asyncio.run(retriever.retrieve(
            "q", kb_types=["reference"], project_id=None, top_k=5, min_score=0.5,
        ))
        assert [c.text for c in out] == ["reference-A"]
    finally:
        hub.close()


def test_tag_filter_requires_all_tags(tmp_path: Path):
    hub = IndexHub(index_root=tmp_path)
    try:
        _seed(hub)
        retriever = CreativeRetriever(
            hub=hub, embedder=_FakeEmbedder({"q": [0.0, 1.0, 0.0]}),
        )
        out = asyncio.run(retriever.retrieve(
            "q", kb_types=["reference"], project_id=None, top_k=5, tags=["style"],
        ))
        assert [c.text for c in out] == ["reference-B"]
        # A tag that no chunk carries → empty.
        out2 = asyncio.run(retriever.retrieve(
            "q", kb_types=["reference"], project_id=None, top_k=5, tags=["missing"],
        ))
        assert out2 == []
    finally:
        hub.close()


def test_empty_query_returns_nothing(tmp_path: Path):
    hub = IndexHub(index_root=tmp_path)
    try:
        _seed(hub)
        retriever = CreativeRetriever(
            hub=hub, embedder=_FakeEmbedder({}),
        )
        out = asyncio.run(retriever.retrieve(
            "   ", kb_types=["reference"], project_id=None, top_k=3,
        ))
        assert out == []
    finally:
        hub.close()
