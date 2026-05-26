"""image-service shares the same RagClient shape as story-service."""

from __future__ import annotations

from src.services.story_service.core.ai.rag_client import RagClient

__all__ = ["RagClient"]
