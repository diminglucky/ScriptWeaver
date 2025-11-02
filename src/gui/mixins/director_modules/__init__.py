"""
导演模块 - 使用新架构的精简版本
"""
from .director_mixin import DirectorMixin
from .director_controller import DirectorController
from .models import Shot, Character, DirectorProject

# 服务类和配置类已迁移到统一位置
# 如需使用，请从以下位置导入：
# - 服务: from src.services.director import ...
# - 配置: from src.core.config_manager import ...

__all__ = [
    'DirectorMixin',
    'DirectorController',
    'Shot',
    'Character',
    'DirectorProject',
]
