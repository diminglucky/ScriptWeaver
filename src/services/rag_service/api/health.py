"""GET /v1/health for rag-service. See v2 plan §14.5."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/v1", tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "rag",
        "version": "2.0.0",
        "models_loaded": False,  # to be set true once EmbeddingHub warmup completes
    }
