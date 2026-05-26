"""POST /v1/images:generate — synchronous single-image generation.

See v2 plan §7.4.
"""

from __future__ import annotations

from fastapi import APIRouter

from src.services.image_service.api._helpers import render_payload

router = APIRouter(prefix="/v1/images", tags=["images"])


@router.post(":generate")
async def generate_image(body: dict) -> dict:
    return render_payload(
        prompt=str(body.get("prompt") or ""),
        aspect_ratio=str(body.get("aspect_ratio") or "16:9"),
        model_hint=str(body.get("model_hint") or ""),
    )
