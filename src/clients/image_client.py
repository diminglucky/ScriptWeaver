from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from io import BytesIO
from typing import List, Optional, Tuple

from PIL import Image
from openai import OpenAI


@dataclass
class ImageResult:
    image: Image.Image
    seed: Optional[int]
    provider: str
    model: str


class OpenAIImageClient:
    """Minimal OpenAI image client using images.generate.

    Note: OpenAI does not expose a stable seed for perfect determinism. We keep
    the parameter for a unified interface; the backend may ignore it.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "gpt-image-1", timeout_seconds: int = 120) -> None:
        key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not key:
            raise RuntimeError("Missing OPENAI_API_KEY for image generation")
        self.client = OpenAI(api_key=key, base_url=base_url, timeout=timeout_seconds)
        self.model = model

    def generate(self, prompt: str, *, seed: Optional[int] = None, size: str = "1024x1024", n: int = 1) -> List[ImageResult]:
        resp = self.client.images.generate(model=self.model, prompt=prompt, size=size, n=n)
        results: List[ImageResult] = []
        for d in resp.data:
            b64 = d.b64_json
            img_bytes = base64.b64decode(b64)
            img = Image.open(BytesIO(img_bytes)).convert("RGB")
            results.append(ImageResult(image=img, seed=seed, provider="openai", model=self.model))
        return results

    def generate_with_reference(self, prompt: str, reference_image_path: str, *, size: str = "1024x1024") -> List[ImageResult]:
        """Create images guided by a reference image (identity consistency).

        This uses the images.edits API with the reference image and prompt.
        If the backend ignores edits for the chosen model, we gracefully fall
        back to plain generation.
        """
        try:
            with open(reference_image_path, "rb") as f:
                resp = self.client.images.edits(model=self.model, image=f, prompt=prompt, size=size)
            results: List[ImageResult] = []
            for d in resp.data:
                b64 = d.b64_json
                img_bytes = base64.b64decode(b64)
                img = Image.open(BytesIO(img_bytes)).convert("RGB")
                results.append(ImageResult(image=img, seed=None, provider="openai", model=self.model))
            return results
        except Exception:
            # Fallback to pure text prompt if edits unsupported
            return self.generate(prompt=prompt, size=size, n=1)


