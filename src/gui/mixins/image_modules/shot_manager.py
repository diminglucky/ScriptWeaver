"""Shot manager aggregator mixin."""

from __future__ import annotations

from src.clients.deepseek_client import DeepSeekClient  # backward-compat for tests/monkey-patching

from .character_auto_select_mixin import ShotCharacterAutoSelectMixin
from .director_package_mixin import DirectorPackageMixin
from .shot_batch_mixin import ShotBatchMixin
from .shot_prompt_mixin import ShotPromptMixin


class ShotManagerMixin(
    DirectorPackageMixin,
    ShotCharacterAutoSelectMixin,
    ShotPromptMixin,
    ShotBatchMixin,
):
    """Compose shot extraction, prompt generation and batch generation workflows."""

    pass
