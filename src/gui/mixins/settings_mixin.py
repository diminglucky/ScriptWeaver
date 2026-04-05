"""Unified settings mixin assembled from focused sub-mixins."""

from __future__ import annotations

from tkinter import messagebox  # Backward compatibility for existing patches/tests.

from .settings_modules.api_config_persistence_mixin import SettingsApiConfigPersistenceMixin
from .settings_modules.api_test_mixin import SettingsApiTestMixin
from .settings_modules.page_actions_mixin import SettingsPageActionsMixin
from .settings_modules.page_layout_mixin import SettingsPageLayoutMixin
from .settings_modules.quick_switch_mixin import SettingsQuickSwitchMixin
from .settings_modules.routing_provider_mixin import SettingsRoutingProviderMixin
from .settings_modules.story_env_mixin import SettingsStoryEnvMixin
from .settings_modules.story_template_mixin import SettingsStoryTemplateMixin


class SettingsMixin(
    SettingsPageLayoutMixin,
    SettingsPageActionsMixin,
    SettingsStoryTemplateMixin,
    SettingsQuickSwitchMixin,
    SettingsStoryEnvMixin,
    SettingsApiTestMixin,
    SettingsApiConfigPersistenceMixin,
    SettingsRoutingProviderMixin,
):
    """Unified settings page behaviors."""

    pass
