"""
数据模型层 - 定义核心数据结构
"""

try:
    from .shot import Shot, ShotCamera, ShotCharacterDetail
    from .character import Character, CharacterAppearance, CharacterOutfit
    from .project import DirectorProject
except ImportError:
    from shot import Shot, ShotCamera, ShotCharacterDetail
    from character import Character, CharacterAppearance, CharacterOutfit
    from project import DirectorProject

__all__ = [
    'Shot',
    'ShotCamera',
    'ShotCharacterDetail',
    'Character',
    'CharacterAppearance',
    'CharacterOutfit',
    'DirectorProject',
]

