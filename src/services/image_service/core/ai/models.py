"""Re-exports the shared ModelRegistry. image-service only consumes image_*
and director_script_generate tasks. See docs/technical_architecture.md.2.
"""

from __future__ import annotations

from src.services.story_service.core.ai.models import ModelRegistry

__all__ = ["ModelRegistry"]
