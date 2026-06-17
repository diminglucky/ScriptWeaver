"""POST /v1/kb/{kb_type}/search. See docs/technical_architecture.md.6 / 搂7.3."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.services.rag_service.api.schemas import SearchRequest, SearchResponse
from src.services.rag_service.deps import get_retriever
from src.shared.domain.errors import CreativeError

router = APIRouter(prefix="/v1/kb", tags=["kb"])

_VALID_KB = {"reference", "project_memory", "style_corpus"}


@router.post("/{kb_type}/search", response_model=SearchResponse)
async def search(
    kb_type: str,
    body: SearchRequest,
    retriever=Depends(get_retriever),
) -> SearchResponse:
    if kb_type not in _VALID_KB:
        raise CreativeError(f"unknown kb_type: {kb_type}", detail={"kb_type": kb_type})
    kb_types = body.kb_types or [kb_type]  # type: ignore[list-item]
    if kb_type not in kb_types:
        kb_types = [kb_type]
    results = await retriever.retrieve(
        body.query,
        kb_types=kb_types,
        project_id=body.project_id,
        top_k=body.top_k,
        min_score=body.min_score,
        tags=body.tags,
    )
    return SearchResponse(results=results)
