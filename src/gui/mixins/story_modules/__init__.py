"""Story功能模块"""

from .ui_builder import StoryUIBuilderMixin
from .outline_generator import OutlineGeneratorMixin
from .story_generator import StoryGeneratorMixin
from .config_handler import StoryConfigMixin


class StoryMixin(
    StoryUIBuilderMixin,
    OutlineGeneratorMixin,
    StoryGeneratorMixin,
    StoryConfigMixin,
):
    """Story功能完整Mixin"""
    pass


__all__ = ['StoryMixin']
