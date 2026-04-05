"""Story prompt builder aggregator mixin."""

from __future__ import annotations

from .prompt_alignment_mixin import StoryPromptAlignmentMixin
from .prompt_context_mixin import StoryPromptContextMixin
from .prompt_generation_mixin import StoryPromptGenerationMixin
from .prompt_model_loading_mixin import StoryPromptModelLoadingMixin


class StoryPromptBuilderMixin(
    StoryPromptAlignmentMixin,
    StoryPromptContextMixin,
    StoryPromptGenerationMixin,
    StoryPromptModelLoadingMixin,
):
    """Compose all story prompt helper mixins."""

    pass
