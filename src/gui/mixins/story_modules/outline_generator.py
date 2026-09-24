"""Story outline generator aggregator mixin."""

from src.clients.deepseek_client import DeepSeekClient  # backward-compat for tests/monkey-patching

from .lean_story_mixin import LeanStoryMixin
from .outline_section_utils_mixin import OutlineSectionUtilsMixin
from .story_infra import StoryInfraMixin


class OutlineGeneratorMixin(
    StoryInfraMixin,
    LeanStoryMixin,
    OutlineSectionUtilsMixin,
):
    """Compose lean chapter generation and parsing utilities."""

    pass
