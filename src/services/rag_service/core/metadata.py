"""DocumentMeta + ChunkMeta. See v2 plan §4.2 / §4.4."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass
class DocumentMeta:
    source_id: str
    path: str
    kb_type: str
    project_id: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class ChunkMeta:
    chunk_id: str
    source_id: str
    text: str
    position: int
    extra: dict = field(default_factory=dict)


def compute_chunk_id(source_id: str, normalized_text: str) -> str:
    """Stable chunk id per v2 plan §4.4: sha1(source_id ":" text[:512])[:16]."""
    payload = f"{source_id}:{normalized_text[:512]}".encode("utf-8")
    return hashlib.sha1(payload).hexdigest()[:16]
