"""Mixin模块聚合"""

from .project_mixin import ProjectMixin
from .story_mixin import StoryMixin
from .image_mixin import ImageMixin
from .kb_mixin import KbMixin
from .config_mixin import ConfigMixin
from .ui_mixin import UiMixin

__all__ = [
	"ProjectMixin",
	"StoryMixin",
	"ImageMixin",
	"KbMixin",
	"ConfigMixin",
	"UiMixin",
]
