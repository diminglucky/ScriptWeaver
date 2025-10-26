"""
配置管理模块
"""

try:
    from .config_manager import ConfigManager, APIConfig
except ImportError:
    from config_manager import ConfigManager, APIConfig

__all__ = ['ConfigManager', 'APIConfig']

