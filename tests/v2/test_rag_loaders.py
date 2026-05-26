"""Tests for rag_service.core.loaders.load_document."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.services.rag_service.core.loaders import (
    SUPPORTED_EXTENSIONS,
    load_document,
)


def test_load_txt_file(tmp_path: Path):
    p = tmp_path / "a.txt"
    p.write_text("Hello\r\n\r\n\r\nWorld\u3000中文", encoding="utf-8")
    doc = load_document(p)
    assert doc.mime == "text/plain"
    assert doc.path == str(p)
    # clean_text normalises CRLF, collapses 3+ blank lines, replaces ideographic space.
    assert "\r" not in doc.text
    assert "\n\n\n" not in doc.text
    assert "\u3000" not in doc.text
    assert "Hello" in doc.text and "World" in doc.text


def test_load_markdown_returns_markdown_mime(tmp_path: Path):
    p = tmp_path / "note.md"
    p.write_text("# Title\n\nbody", encoding="utf-8")
    assert load_document(p).mime == "text/markdown"


def test_load_missing_file_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_document(tmp_path / "nope.txt")


def test_load_unsupported_extension_raises(tmp_path: Path):
    p = tmp_path / "weird.bin"
    p.write_text("xxx", encoding="utf-8")
    with pytest.raises(ValueError):
        load_document(p)


def test_supported_extensions_covers_common_kinds():
    for ext in (".txt", ".md", ".docx", ".pdf"):
        assert ext in SUPPORTED_EXTENSIONS
