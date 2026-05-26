"""Chinese-friendly text splitters with overlap. See v2 plan §4.2.

Produces `SplitChunk` instances that retain character offsets into the
original document so we can re-attach citations later.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Sentence terminators we are willing to break on. Order matters: the last
# entry (newline) is the lowest-priority separator we accept.
_TERMINATORS = "。！？!?.\n"
_SENTENCE_RE = re.compile(rf"[^{re.escape(_TERMINATORS)}]*[{re.escape(_TERMINATORS)}]+|[^{re.escape(_TERMINATORS)}]+$")


@dataclass
class SplitChunk:
    text: str
    start: int
    end: int


def _iter_sentences(text: str) -> list[tuple[int, int, str]]:
    """Yield ``(start, end, sentence)`` triples that tile the whole text."""
    out: list[tuple[int, int, str]] = []
    for m in _SENTENCE_RE.finditer(text):
        s, e = m.span()
        if e == s:
            continue
        out.append((s, e, text[s:e]))
    return out


def split_text(text: str, *, chunk_size: int = 600, overlap: int = 80) -> list[SplitChunk]:
    """Split ``text`` into ``SplitChunk`` instances.

    The splitter packs sentences greedily up to ``chunk_size`` characters,
    then continues the next chunk with the trailing ``overlap`` characters of
    the previous one preserved. Empty / whitespace-only text returns an
    empty list. Chunks shorter than ~20 chars after stripping are dropped to
    match the v1 behaviour and keep low-signal tails out of the index.
    """
    if not text or not text.strip():
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must satisfy 0 <= overlap < chunk_size")

    sentences = _iter_sentences(text)
    if not sentences:
        return []

    chunks: list[SplitChunk] = []
    cur_start = sentences[0][0]
    cur_end = cur_start
    cur_text_parts: list[str] = []

    def flush() -> None:
        nonlocal cur_start, cur_end, cur_text_parts
        body = "".join(cur_text_parts).strip()
        if len(body) > 20:
            chunks.append(SplitChunk(text=body, start=cur_start, end=cur_end))
        cur_text_parts = []

    for s, e, sent in sentences:
        sent_len = e - s
        cur_len = cur_end - cur_start
        if cur_len + sent_len > chunk_size and cur_text_parts:
            flush()
            # Re-seed next chunk with overlap drawn from the *original* text
            # so offsets stay aligned.
            if overlap > 0:
                back = min(overlap, cur_end - 0)
                new_start = max(0, cur_end - back)
                cur_start = new_start
                cur_end = cur_end
                cur_text_parts = [text[new_start:cur_end]]
            else:
                cur_start = s
                cur_end = s
                cur_text_parts = []
        if not cur_text_parts:
            cur_start = s
        cur_text_parts.append(sent)
        cur_end = e

    flush()
    return chunks
