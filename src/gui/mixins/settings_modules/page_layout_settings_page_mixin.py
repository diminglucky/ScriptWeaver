"""Top-level settings page container layout."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ...theme import Theme


class SettingsPageLayoutSettingsPageMixin:
    """Build the root settings page and tab containers."""
    def _build_settings_page(self) -> None:
        """构建统一设置页面"""
        # 使用分区标签页，让设置结构更清晰
        container = tk.Frame(self.page_settings, bg=Theme.BG_SECONDARY)
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        settings_notebook = ttk.Notebook(container)
        settings_notebook.pack(fill="both", expand=True)

        api_tab = self._make_scroll_tab(settings_notebook, "API 配置")
        routing_tab = self._make_scroll_tab(settings_notebook, "模型路由")
        data_tab = self._make_scroll_tab(settings_notebook, "知识库 & 参数")
        advanced_tab = self._make_scroll_tab(settings_notebook, "高级")
        
        self._build_data_kb_and_params_tab(data_tab)
        self._build_api_settings_tab(api_tab)
        self._build_model_routing_tab(routing_tab)
        self._build_advanced_settings_tab(advanced_tab)

        # 加载当前配置
        self._load_settings_values()

