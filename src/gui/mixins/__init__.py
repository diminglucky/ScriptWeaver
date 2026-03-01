"""Mixin exports with lazy imports to reduce import-time coupling."""

from importlib import import_module

__all__ = [
    "ProjectMixin",
    "StoryMixin",
    "ImageMixin",
    "DirectorMixin",
    "KbMixin",
    "ConfigMixin",
    "UiMixin",
    "SettingsMixin",
    "EnhancementsMixin",
    "KBEnhancementsMixin",
    "PerformanceMixin",
]

_EXPORTS = {
    "ProjectMixin": ".project_mixin",
    "StoryMixin": ".story_modules",
    "ImageMixin": ".image_modules",
    "DirectorMixin": ".director_mixin",
    "KbMixin": ".kb_mixin",
    "ConfigMixin": ".config_modules",
    "UiMixin": ".ui_mixin",
    "SettingsMixin": ".settings_refactored",
    "EnhancementsMixin": ".enhancements_refactored",
    "KBEnhancementsMixin": ".kb_enhancements",
    "PerformanceMixin": ".async_utils",
}


def __getattr__(name):
    module_path = _EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(module_path, __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value
