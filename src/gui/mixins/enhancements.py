"""Legacy compatibility facade for enhancements mixin.

This module keeps the historical import path stable while delegating
implementations to extracted modules.
"""

from .enhancements_modules import (
    APIMonitorMixin,
    APIStatusMonitor,
    CacheManager,
    CacheMixin,
    ConfigExportMixin,
    HAS_CRYPTOGRAPHY,
    HistoryManager,
    HistoryMixin,
    KeyboardShortcuts,
    ProgressDialog,
    ProgressMixin,
    ProjectExportMixin,
    SecureConfigMixin,
    SecureKeyStorage,
    ShortcutsMixin,
)
from .enhancements_refactored import EnhancementsMixin

__all__ = [
    "HAS_CRYPTOGRAPHY",
    "ProgressDialog",
    "ProgressMixin",
    "KeyboardShortcuts",
    "ShortcutsMixin",
    "HistoryManager",
    "HistoryMixin",
    "SecureKeyStorage",
    "SecureConfigMixin",
    "APIStatusMonitor",
    "APIMonitorMixin",
    "ConfigExportMixin",
    "CacheManager",
    "CacheMixin",
    "ProjectExportMixin",
    "EnhancementsMixin",
]
