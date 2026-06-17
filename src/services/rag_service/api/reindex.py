"""Admin endpoints for RAG index metadata."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.services.rag_service.api.schemas import ManifestResponse
from src.services.rag_service.deps import get_index_hub

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.post("/manifest:rebuild")
async def rebuild_manifest(hub=Depends(get_index_hub)) -> dict:
    return hub.rebuild_manifest()


@router.get("/manifest", response_model=ManifestResponse)
async def manifest(hub=Depends(get_index_hub)) -> ManifestResponse:
    return ManifestResponse.model_validate(hub.manifest())
