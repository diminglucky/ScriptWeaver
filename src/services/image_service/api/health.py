"""GET /v1/health for image-service."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/v1", tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "image",
        "version": "2.0.0",
        "playwright_available": False,  # detected at startup in Phase 6
    }
