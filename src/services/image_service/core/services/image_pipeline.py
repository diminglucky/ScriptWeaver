"""Single-image pipeline: translate + enhance + call image API + persist."""

from __future__ import annotations

from src.services.image_service.api._helpers import render_payload


class ImagePipeline:
    async def render_single(
        self,
        *,
        prompt: str,
        negative_prompt: str = "",
        aspect_ratio: str = "16:9",
        model_hint: str = "",
    ) -> dict:
        return render_payload(prompt=prompt, aspect_ratio=aspect_ratio, model_hint=model_hint)
