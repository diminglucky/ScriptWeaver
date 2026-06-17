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
    text = "\n\n".join([
        "第一段介绍人物的处境和不能说出口的秘密。" * 2,
        "第二段让人物接到一条陌生短信。" * 2,
        "第三段揭示门锁没有坏却总是自动反锁。" * 2,
        "第四段把旧照片和错位记忆联系起来。" * 2,
    ])
    chunks = split_text(text, chunk_size=70, overlap=12, overlap_paragraphs=1)
    assert len(chunks) >= 2
    first_paragraph_of_second = chunks[1].text.split("\n\n", 1)[0]
    assert first_paragraph_of_second in chunks[0].text


def test_paragraph_boundaries_are_preserved_when_possible():
    text = "第一段有完整语义。" * 3 + "\n\n" + "第二段是另一场戏。" * 3
    chunks = split_text(text, chunk_size=200, overlap=20)
    assert len(chunks) == 1
    assert "\n\n" in chunks[0].text


def test_invalid_overlap_raises():
    with pytest.raises(ValueError):
        split_text("xxxxxxxxxxxxxxxxxxxxxxxxxx", chunk_size=10, overlap=10)
    with pytest.raises(ValueError):
        split_text("xxxxxxxxxxxxxxxxxxxxxxxxxx", chunk_size=0, overlap=0)


def test_single_newline_lines_are_treated_as_paragraphs():
    text = "\n".join([
        "alpha paragraph has enough detail to be indexed",
        "beta paragraph has enough detail to be indexed",
        "gamma paragraph has enough detail to be indexed",
    ])
    chunks = split_text(text, chunk_size=95, overlap=10, overlap_paragraphs=1)
    assert len(chunks) >= 2
    assert chunks[0].text.split("\n\n") == [
        "alpha paragraph has enough detail to be indexed",
        "beta paragraph has enough detail to be indexed",
    ]
    assert chunks[1].text.startswith("beta paragraph")
