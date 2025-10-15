"""Config功能模块"""

from .api_config import APIConfigMixin
from .preset_manager import PresetManagerMixin


class ConfigMixin(
    APIConfigMixin,
    PresetManagerMixin,
):
    """Config功能完整Mixin"""
    pass


__all__ = ['ConfigMixin']
