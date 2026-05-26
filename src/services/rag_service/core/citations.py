"""Helpers that translate raw search hits → RetrievedContext payloads."""

from __future__ import annotations

from src.shared.domain.schemas import RetrievedContext, SourceRef


def pack_context(*, text: str, source_id: str, path: str, chunk_id: str, score: float,
                 kb_type: str = "reference", project_id: str | None = None,
                 reason: str = "", truncated: bool = False) -> RetrievedContext:
    return RetrievedContext(
        text=text,
        source=SourceRef(
            source_id=source_id,
            path=path,
            chunk_id=chunk_id,
            score=score,
            kb_type=kb_type,  # type: ignore[arg-type]
            project_id=project_id,
        ),
        reason=reason,
        truncated=truncated,
    )
