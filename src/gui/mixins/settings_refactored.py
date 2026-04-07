"""Refactored SettingsMixin entrypoint.

Behavior remains compatible while moving focused pieces out of
`settings_mixin.py` incrementally.
"""

from .settings_mixin import SettingsMixin as LegacySettingsMixin
from .settings_modules import (
    SettingsActionsMixin,
    SettingsModelFetchMixin,
    SettingsModelRoutingUIMixin,
    SettingsModelUtilsMixin,
    SettingsProviderUIMixin,
    SettingsRuntimeSyncMixin,
)


class SettingsMixin(
    SettingsActionsMixin,
    SettingsModelUtilsMixin,
    SettingsModelFetchMixin,
    SettingsModelRoutingUIMixin,
    SettingsProviderUIMixin,
    SettingsRuntimeSyncMixin,
    LegacySettingsMixin,
):
    """Compatibility wrapper for progressively refactored settings mixin."""
