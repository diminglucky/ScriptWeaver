"""Chinese-friendly paragraph-aware text splitters."""

from __future__ import annotations

import re
from dataclasses import dataclass

_TERMINATORS = "。！？!?；;.\n"
_SENTENCE_RE = re.compile(rf"[^{re.escape(_TERMINATORS)}]*[{re.escape(_TERMINATORS)}]+|[^{re.escape(_TERMINATORS)}]+$")


@dataclass
class SplitChunk:
    text: str
    start: int
    end: int


def _iter_paragraphs(text: str) -> list[tuple[int, int, str]]:
    """Return non-empty paragraphs with original offsets."""
    paragraphs: list[tuple[int, int, str]] = []
    for match in re.finditer(r"[^\r\n]+", text):
        start, end = match.span()
        raw = text[start:end]
        body = raw.strip()
        if not body:
            continue
        leading = len(raw) - len(raw.lstrip())
        trailing = len(raw.rstrip())
        paragraphs.append((start + leading, start + trailing, body))
    return paragraphs


def _iter_sentences(text: str) -> list[tuple[int, int, str]]:
    """Yield ``(start, end, sentence)`` triples that tile the whole text."""
    out: list[tuple[int, int, str]] = []
    for m in _SENTENCE_RE.finditer(text):
        s, e = m.span()
        if e == s:
            continue
        out.append((s, e, text[s:e]))
    return out


def _split_long_paragraph(start: int, paragraph: str, *, chunk_size: int) -> list[tuple[int, int, str]]:
    """Split a paragraph by sentence only when the paragraph is too large."""
    pieces: list[tuple[int, int, str]] = []
    current_start: int | None = None
    current_end = start
    parts: list[str] = []
    for sent_start, sent_end, sent in _iter_sentences(paragraph):
        abs_start = start + sent_start
        abs_end = start + sent_end
        base_start = current_start if current_start is not None else abs_start
        if parts and (current_end - base_start) + len(sent) > chunk_size:
            body = "".join(parts).strip()
            if body:
                pieces.append((base_start, current_end, body))
            current_start = abs_start
            parts = []
        if current_start is None:
            current_start = abs_start
        parts.append(sent)
        current_end = abs_end
    body = "".join(parts).strip()
    if body and current_start is not None:
        pieces.append((current_start, current_end, body))
    return pieces


def split_text(
    text: str,
    *,
    chunk_size: int = 600,
    overlap: int = 80,
    overlap_paragraphs: int = 1,
) -> list[SplitChunk]:
    """Split ``text`` into paragraph-aware chunks.

    Non-empty lines are treated as prose paragraphs. Paragraphs are packed up
    to ``chunk_size`` and the next chunk carries ``overlap_paragraphs`` from
    the previous chunk. Overlong paragraphs fall back to sentence splitting.
    """
    if not text or not text.strip():
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must satisfy 0 <= overlap < chunk_size")
    if overlap_paragraphs < 0:
        raise ValueError("overlap_paragraphs must be non-negative")

    paragraphs = _iter_paragraphs(text)
    if not paragraphs:
        return []
    units: list[tuple[int, int, str]] = []
    for start, end, paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            units.extend(_split_long_paragraph(start, paragraph, chunk_size=chunk_size))
        else:
            units.append((start, end, paragraph))

    chunks: list[SplitChunk] = []
    cur_units: list[tuple[int, int, str]] = []

    def flush() -> None:
        nonlocal cur_units
        if not cur_units:
            return
        body = "\n\n".join(unit[2].strip() for unit in cur_units).strip()
        if len(body) > 20:
            chunks.append(SplitChunk(text=body, start=cur_units[0][0], end=cur_units[-1][1]))
        cur_units = []

    for unit in units:
        unit_len = len(unit[2])
        current_len = len("\n\n".join(u[2] for u in cur_units)) if cur_units else 0
        if cur_units and current_len + 2 + unit_len > chunk_size:
            prev_units = cur_units[:]
            flush()
            if overlap_paragraphs:
                cur_units = prev_units[-overlap_paragraphs:]
            elif overlap > 0 and prev_units:
                last = prev_units[-1]
                fallback_start = max(last[0], last[1] - overlap)
                cur_units = [(fallback_start, last[1], text[fallback_start:last[1]].strip())]
        cur_units.append(unit)

    flush()
    return chunks
