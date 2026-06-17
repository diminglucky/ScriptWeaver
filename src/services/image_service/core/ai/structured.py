"""Re-export of structured-output helper from story-service.

See docs/technical_architecture.md.7 / 搂6.3.
"""

from __future__ import annotations

from src.services.story_service.core.ai.structured import AttemptStats, invoke_structured

__all__ = ["AttemptStats", "invoke_structured"]
