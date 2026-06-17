"""Document ingestion / deletion for a single knowledge-base shard.

Endpoints:
    POST   /v1/kb/{kb_type}/documents
    DELETE /v1/kb/{kb_type}/documents/{source_id}

See docs/technical_architecture.md.3.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.services.rag_service.api.schemas import (
    DeleteResponse,
    IngestRequest,
    IngestResponse,
)
from src.services.rag_service.core.metadata import compute_chunk_id
from src.services.rag_service.core.splitters import split_text
from src.services.rag_service.deps import get_embedding_hub, get_index_hub
from src.shared.domain.errors import CreativeError

router = APIRouter(prefix="/v1/kb", tags=["kb"])

_VALID_KB = {"reference", "project_memory", "style_corpus"}


def _check_kb_type(kb_type: str) -> None:
    if kb_type not in _VALID_KB:
        raise CreativeError(f"unknown kb_type: {kb_type}", detail={"kb_type": kb_type})


@router.post("/{kb_type}/documents", response_model=IngestResponse)
async def ingest_documents(
    kb_type: str,
    body: IngestRequest,
    hub=Depends(get_index_hub),
    embedder=Depends(get_embedding_hub),
) -> IngestResponse:
    _check_kb_type(kb_type)

    chunk_ids: list[str] = []
    metas: list[dict] = []

    project_id_for_shard: str | None = None
    for doc in body.documents:
        chunks = split_text(
            doc.text,
            chunk_size=body.chunk_size,
            overlap=body.overlap,
            overlap_paragraphs=body.overlap_paragraphs,
        )
        if not chunks:
            continue
        if kb_type == "project_memory":
            # All entries in a project_memory ingest call must target the
            # same project so we can pin the shard.
            if project_id_for_shard is None:
                project_id_for_shard = doc.project_id
            elif doc.project_id != project_id_for_shard:
                raise CreativeError("project_memory ingest must be scoped to one project_id")
        for pos, ch in enumerate(chunks):
            cid = compute_chunk_id(doc.source_id, ch.text)
            chunk_ids.append(cid)
            metas.append({
                "source_id": doc.source_id,
                "path": doc.path,
                "position": pos,
                "text": ch.text,
                "kb_type": kb_type,
                "project_id": doc.project_id,
                "tags": list(doc.tags),
            })
    if not chunk_ids:
        return IngestResponse(ingested=0, chunks=0, shard=f"{kb_type}/{project_id_for_shard or '_global'}")

    # Single embed call to amortise model load.
    vecs = await embedder.encode_async([m["text"] for m in metas])
    shard = hub.shard(kb_type, project_id_for_shard if kb_type == "project_memory" else None)
    shard.upsert(chunk_ids, vecs, metas)

    return IngestResponse(
        ingested=len(body.documents),
        chunks=len(chunk_ids),
        shard=f"{kb_type}/{project_id_for_shard or '_global'}",
    )


@router.delete("/{kb_type}/documents/{source_id}", response_model=DeleteResponse)
async def delete_document(
    kb_type: str,
    source_id: str,
    project_id: str | None = None,
    hub=Depends(get_index_hub),
) -> DeleteResponse:
    _check_kb_type(kb_type)
    target_project = project_id if kb_type == "project_memory" else None
    shard = hub.shard(kb_type, target_project)
    removed = shard.delete_source(source_id)
    return DeleteResponse(removed=removed)
