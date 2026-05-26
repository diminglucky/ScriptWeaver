"""Admin endpoints for legacy index migration. See v2 plan §11.4."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.services.rag_service.api.schemas import ManifestResponse
from src.services.rag_service.deps import get_index_hub

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.post("/reindex")
async def reindex(hub=Depends(get_index_hub)) -> dict:
    return hub.reindex_legacy()


@router.get("/manifest", response_model=ManifestResponse)
async def manifest(hub=Depends(get_index_hub)) -> ManifestResponse:
    return ManifestResponse.model_validate(hub.manifest())
