"""Backward-compatible re-export.

All settings mixins are now unified in settings_mixin.py.
This file only exists so existing ``from .settings_refactored import SettingsMixin``
imports continue to work.
"""

from .settings_mixin import SettingsMixin  # noqa: F401
