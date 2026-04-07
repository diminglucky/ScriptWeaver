"""Unified settings mixin assembled from focused sub-mixins."""

from __future__ import annotations

from tkinter import messagebox  # Backward compatibility for existing patches/tests.

from .settings_modules import (
    SettingsActionsMixin,
    SettingsApiConfigPersistenceMixin,
    SettingsApiTestMixin,
    SettingsModelFetchMixin,
    SettingsModelRoutingUIMixin,
    SettingsModelUtilsMixin,
    SettingsPageActionsMixin,
    SettingsPageLayoutMixin,
    SettingsProviderUIMixin,
    SettingsQuickSwitchMixin,
    SettingsRoutingProviderMixin,
    SettingsRuntimeSyncMixin,
    SettingsStoryEnvMixin,
    SettingsStoryTemplateMixin,
)


class SettingsMixin(
    SettingsActionsMixin,
    SettingsModelUtilsMixin,
    SettingsModelFetchMixin,
    SettingsModelRoutingUIMixin,
    SettingsProviderUIMixin,
    SettingsRuntimeSyncMixin,
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
