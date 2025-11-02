"""Story功能模块"""

from .ui_builder import StoryUIBuilderMixin
from .outline_generator import OutlineGeneratorMixin
from .story_generator import StoryGeneratorMixin
from .config_handler import StoryConfigMixin
from .zhihu_publisher_mixin import ZhihuPublisherMixin
from .input_cache import InputCacheMixin


class StoryMixin(
    StoryUIBuilderMixin,
    OutlineGeneratorMixin,
    StoryGeneratorMixin,
    StoryConfigMixin,
    ZhihuPublisherMixin,
    InputCacheMixin,
):
    """Story功能完整Mixin"""
    pass


__all__ = ['StoryMixin']
