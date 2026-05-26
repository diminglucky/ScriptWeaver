"""Custom image-API client driven by `custom_image_api_presets.json`.

To be ported from `src.clients.image_client` during Phase 6.
"""

from __future__ import annotations

from src.services.image_service.api._helpers import render_payload


class CustomImageAdapter:
    def __init__(self, *, preset_name: str):
        self.preset_name = preset_name

    async def generate(self, prompt: str, **kwargs) -> dict:
        return render_payload(
            prompt=prompt,
            aspect_ratio=str(kwargs.get("aspect_ratio") or kwargs.get("size") or "16:9"),
            model_hint=self.preset_name,
        )
