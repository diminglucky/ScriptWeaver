"""Tests for rag_service.core.splitters.split_text."""
from __future__ import annotations

import pytest

from src.services.rag_service.core.splitters import SplitChunk, split_text


def test_empty_input_returns_empty():
    assert split_text("") == []
    assert split_text("   \n\n  ") == []


def test_short_text_below_threshold_is_dropped():
    # < 20 chars after strip → filtered out per design.
    assert split_text("短句。") == []


def test_single_chunk_when_text_fits():
    text = "第一句话非常详细地描述了背景。" * 3  # ~ 60 chars
    out = split_text(text, chunk_size=200, overlap=20)
    assert len(out) == 1
    assert out[0].text.strip().startswith("第一句话")


def test_offsets_are_consistent_with_source():
    text = "句子A。句子B。句子C。" * 20  # forces multi-chunk
    chunks = split_text(text, chunk_size=40, overlap=8)
    assert len(chunks) >= 2
    for c in chunks:
        assert isinstance(c, SplitChunk)
        assert 0 <= c.start < c.end <= len(text)


def test_overlap_creates_continuity_across_chunks():
    text = "甲乙丙丁戊己庚辛壬癸。" * 30
    chunks = split_text(text, chunk_size=60, overlap=12)
    assert len(chunks) >= 2
    # The second chunk should begin with characters that appear at the tail
    # of the first chunk.
    head_of_second = chunks[1].text[:6]
    assert head_of_second and head_of_second in chunks[0].text


def test_invalid_overlap_raises():
    with pytest.raises(ValueError):
        split_text("xxxxxxxxxxxxxxxxxxxxxxxxxx", chunk_size=10, overlap=10)
    with pytest.raises(ValueError):
        split_text("xxxxxxxxxxxxxxxxxxxxxxxxxx", chunk_size=0, overlap=0)
