"""GET /v1/health for story-service."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/v1", tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "story",
        "version": "2.0.0",
        "models_loaded": False,
    }
