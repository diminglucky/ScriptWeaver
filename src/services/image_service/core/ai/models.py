"""Re-exports the shared ModelRegistry. image-service only consumes image_*
and director_script_generate tasks. See v2 plan §6.2.
"""

from __future__ import annotations

from src.services.story_service.core.ai.models import ModelRegistry

__all__ = ["ModelRegistry"]
