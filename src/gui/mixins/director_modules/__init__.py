"""
导演模块 - 使用新架构的精简版本
"""

from .director_mixin import DirectorMixin
from .director_controller import DirectorController
from .models import Shot, Character, DirectorProject
from .services import (
    PromptBuilderService,
    ImageGeneratorService,
    ShotManagerService,
    CharacterService
)
from .config import ConfigManager, APIConfig

__all__ = [
    'DirectorMixin',
    'DirectorController',
    'Shot',
    'Character',
    'DirectorProject',
    'PromptBuilderService',
    'ImageGeneratorService',
    'ShotManagerService',
    'CharacterService',
    'ConfigManager',
    'APIConfig',
]
