"""Settings page layout aggregator mixin."""

from __future__ import annotations

from .page_layout_advanced_mixin import SettingsPageLayoutAdvancedMixin
from .page_layout_api_mixin import SettingsPageLayoutApiMixin
from .page_layout_base_mixin import SettingsPageLayoutBaseMixin
from .page_layout_data_mixin import SettingsPageLayoutDataMixin
from .page_layout_routing_mixin import SettingsPageLayoutRoutingMixin
from .page_layout_settings_page_mixin import SettingsPageLayoutSettingsPageMixin


class SettingsPageLayoutMixin(
    SettingsPageLayoutBaseMixin,
    SettingsPageLayoutDataMixin,
    SettingsPageLayoutSettingsPageMixin,
    SettingsPageLayoutApiMixin,
    SettingsPageLayoutRoutingMixin,
    SettingsPageLayoutAdvancedMixin,
):
    """Compose all settings-page layout builders."""

    pass
