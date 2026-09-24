"""Single-image pipeline: translate + enhance + call image API + persist."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from src.services.image_service.api._helpers import render_payload
from src.shared.config.paths import get_repo_paths


def _enabled(name: str) -> bool:
    return (os.getenv(name, "") or "").strip().lower() in {"1", "true", "yes", "on"}


def _size_for_aspect_ratio(aspect_ratio: str) -> str:
    if aspect_ratio in {"9:16", "2:3", "portrait"}:
        return "1024x1536"
    if aspect_ratio in {"16:9", "3:2", "landscape"}:
        return "1536x1024"
    return "1024x1024"


class ImagePipeline:
    async def render_single(
        self,
        *,
        prompt: str,
        negative_prompt: str = "",
        aspect_ratio: str = "16:9",
        model_hint: str = "",
    ) -> dict:
        if _enabled("WSF_IMAGE_REAL"):
            return await self._render_openai_compatible(
                prompt=prompt,
                negative_prompt=negative_prompt,
                aspect_ratio=aspect_ratio,
                model_hint=model_hint,
            )
        return render_payload(prompt=prompt, aspect_ratio=aspect_ratio, model_hint=model_hint)

    async def _render_openai_compatible(
        self,
        *,
        prompt: str,
        negative_prompt: str,
        aspect_ratio: str,
        model_hint: str,
    ) -> dict:
        import asyncio

        from src.clients.image_client import OpenAIImageClient

        model = (
            (os.getenv("WSF_IMAGE_MODEL", "") or "").strip()
            or (model_hint or "").strip()
            or "gpt-image-1"
        )
        client = OpenAIImageClient(
            api_key=(os.getenv("WSF_IMAGE_API_KEY", "") or "").strip() or None,
            base_url=(os.getenv("WSF_IMAGE_BASE_URL", "") or "").strip() or None,
            model=model,
        )
        final_prompt = prompt
        if negative_prompt.strip():
            final_prompt = f"{prompt}\nAvoid: {negative_prompt.strip()}"
        images = await asyncio.to_thread(
            client.generate,
            final_prompt,
            size=_size_for_aspect_ratio(aspect_ratio),
            n=1,
        )
        if not images:
            raise RuntimeError("image provider returned no images")
        output_id = uuid.uuid4().hex
        output_dir = get_repo_paths().runtime_root / "generated_images"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{output_id}.png"
        await asyncio.to_thread(images[0].image.save, output_path)
        return {
            "image_id": output_id,
            "url": output_path.as_uri(),
            "path": str(output_path),
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "model_hint": model,
            "status": "succeeded",
        }
