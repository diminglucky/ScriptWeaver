"""Singleton wrapper around the sentence-transformers model.

See docs/technical_architecture.md.5. We delegate to `src.kb.model_cache.get_sentence_transformer`
so v1 and v2 share the same on-disk model cache.
"""

from __future__ import annotations

from typing import Any

DEFAULT_MODEL_NAME = "BAAI/bge-small-zh-v1.5"


class EmbeddingHub:
    """Holds at most one SentenceTransformer per model name."""

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        self.model_name = model_name
        self._model: Any | None = None

    def get(self) -> Any:
        if self._model is None:
            from src.kb.model_cache import get_sentence_transformer

            self._model = get_sentence_transformer(self.model_name)
        return self._model

    def encode(self, texts: list[str]) -> list[list[float]]:
        model = self.get()
        return model.encode(texts, normalize_embeddings=True).tolist()

    async def encode_async(self, texts: list[str]) -> list[list[float]]:
        import anyio

        return await anyio.to_thread.run_sync(self.encode, texts)
