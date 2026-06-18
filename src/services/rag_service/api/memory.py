"""project_memory CRUD. See docs/technical_architecture.md.7 / 搂7.3."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.services.rag_service.api.schemas import (
    DeleteResponse,
    MemoryEntryOut,
    MemoryListResponse,
    MemoryWriteRequest,
)
from src.services.rag_service.core.metadata import compute_chunk_id
from src.services.rag_service.deps import get_embedding_hub, get_index_hub

router = APIRouter(prefix="/v1/projects", tags=["memory"])


@router.post("/{project_id}/memory", response_model=MemoryListResponse)
async def write_memory(
    project_id: str,
    body: MemoryWriteRequest,
    hub=Depends(get_index_hub),
    embedder=Depends(get_embedding_hub),
) -> MemoryListResponse:
    shard = hub.shard("project_memory", project_id)
    chunk_ids: list[str] = []
    metas: list[dict] = []
    for i, entry in enumerate(body.entries):
        cid = compute_chunk_id(entry.source_id, entry.text)
        chunk_ids.append(cid)
        metas.append({
            "source_id": entry.source_id,
            "path": f"memory://{project_id}/{entry.source_id}",
            "position": i,
            "text": entry.text,
            "kb_type": "project_memory",
            "project_id": project_id,
            "tags": list(entry.tags),
        })
    if chunk_ids:
        vecs = await embedder.encode_async([m["text"] for m in metas])
        shard.replace_sources(chunk_ids, vecs, metas)
    return MemoryListResponse(entries=[
        MemoryEntryOut(
            chunk_id=cid,
            source_id=meta["source_id"],
            text=meta["text"],
            tags=meta["tags"],
        )
        for cid, meta in zip(chunk_ids, metas)
    ])


@router.get("/{project_id}/memory", response_model=MemoryListResponse)
async def list_memory(project_id: str, hub=Depends(get_index_hub)) -> MemoryListResponse:
    shard = hub.shard("project_memory", project_id)
    rows = shard.store.list_chunks()
    entries = [
        MemoryEntryOut(
            chunk_id=row["chunk_id"],
            source_id=row["source_id"],
            text=row["text"],
            tags=row.get("tags") or [],
        )
        for row in rows
    ]
    return MemoryListResponse(entries=entries)


@router.delete("/{project_id}/memory", response_model=DeleteResponse)
async def clear_memory(project_id: str, hub=Depends(get_index_hub)) -> DeleteResponse:
    shard = hub.shard("project_memory", project_id)
    removed = 0
    rows = shard.store.list_chunks()
    for source_id in sorted({row["source_id"] for row in rows}):
        removed += shard.delete_source(source_id)
    return DeleteResponse(removed=removed)
