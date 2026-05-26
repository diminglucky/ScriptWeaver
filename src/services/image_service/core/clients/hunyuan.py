"""Hunyuan image client adapter.

To be reorganised on top of `src.clients.hunyuan_image_client` during Phase 6.
"""

from __future__ import annotations

from src.services.image_service.api._helpers import render_payload


class HunyuanImageAdapter:
    async def generate(self, prompt: str, **kwargs) -> dict:
        return render_payload(
            prompt=prompt,
            aspect_ratio=str(kwargs.get("aspect_ratio") or kwargs.get("resolution") or "1:1"),
            model_hint="hunyuan",
        )
