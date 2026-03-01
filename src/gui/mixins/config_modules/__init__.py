"""Config mixin exports with lazy composition."""

__all__ = ["ConfigMixin"]


def __getattr__(name):
    if name != "ConfigMixin":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from .api_config import APIConfigMixin
    from .preset_manager import PresetManagerMixin

    class ConfigMixin(
        APIConfigMixin,
        PresetManagerMixin,
    ):
        """Config feature mixin."""

    globals()["ConfigMixin"] = ConfigMixin
    return ConfigMixin
