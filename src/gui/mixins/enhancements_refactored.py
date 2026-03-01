"""Refactored EnhancementsMixin entrypoint.

This file keeps behavior compatible while allowing incremental extraction of
subsystems from `enhancements.py`.
"""

from tkinter import messagebox

from .enhancements_modules import (
    APIMonitorMixin,
    CacheMixin,
    ConfigExportMixin,
    HistoryMixin,
    ProgressMixin,
    ProjectExportMixin,
    SecureConfigMixin,
    ShortcutsMixin,
)


class EnhancementsMixin(
    ProgressMixin,
    ShortcutsMixin,
    HistoryMixin,
    SecureConfigMixin,
    APIMonitorMixin,
    ConfigExportMixin,
    CacheMixin,
    ProjectExportMixin,
):
    """Compatibility wrapper for progressively refactored enhancements."""

    def _init_enhancements(self):
        self._init_history()
        self._init_secure_storage()
        self._init_api_monitor()
        self._init_cache()
        self.after(100, self._setup_shortcuts)

    def _refresh_theme(self):
        messagebox.showinfo("提示", "主题已切换，部分更改需要重启应用后生效")
