"""Stable chunk_id hashing. See docs/technical_architecture.md.4."""

from __future__ import annotations

from src.services.rag_service.core.metadata import (
    ChunkMeta,
    DocumentMeta,
    compute_chunk_id,
)


def test_chunk_id_is_deterministic():
    a = compute_chunk_id("source-1", "hello world")
    b = compute_chunk_id("source-1", "hello world")
    assert a == b


def test_chunk_id_differs_for_different_source():
    a = compute_chunk_id("source-1", "hello")
    b = compute_chunk_id("source-2", "hello")
    assert a != b


def test_chunk_id_truncates_long_text_consistently():
    long1 = "x" * 600
    long2 = "x" * 512 + "different-tail"
    # Implementation truncates to first 512 chars 鈫?ids should match.
    assert compute_chunk_id("s", long1) == compute_chunk_id("s", long2)


def test_chunk_id_length_is_16_hex():
    cid = compute_chunk_id("s", "abc")
    assert len(cid) == 16
    int(cid, 16)  # raises if not hex


def test_document_meta_defaults():
    doc = DocumentMeta(source_id="s", path="p", kb_type="reference")
    assert doc.tags == []
    assert doc.project_id is None


def test_chunk_meta_extra_independent_per_instance():
    a = ChunkMeta(chunk_id="a", source_id="s", text="t", position=0)
    b = ChunkMeta(chunk_id="b", source_id="s", text="t", position=1)
    a.extra["k"] = 1
    assert b.extra == {}
