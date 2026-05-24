"""Base UI helpers for settings page layout.

Also includes settings-page container and advanced-tab builders
(previously in separate tiny files).
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk

from ...theme import Theme

logger = logging.getLogger(__name__)


class SettingsPageLayoutBaseMixin:
    """Shared low-level layout helpers for settings tabs."""
    def _fix_entry_colors(self, entry_widget):
        """
        修复Entry组件的颜色问题，防止焦点时变成白底白字
        使用短时守护重试，避免长期高频轮询带来的性能负担
        """
        def _apply_dark_colors():
            try:
                entry_widget.config(
                    bg=Theme.BG_TERTIARY, 
                    fg=Theme.TEXT_PRIMARY,
                    insertbackground=Theme.TEXT_PRIMARY,
                    selectbackground=Theme.PRIMARY,
                    selectforeground=Theme.TEXT_PRIMARY,
                    disabledbackground=Theme.BG_TERTIARY,
                    disabledforeground=Theme.TEXT_DISABLED,
                    readonlybackground=Theme.BG_TERTIARY
                )
            except Exception:
                pass  # UI config may fail during widget teardown

        def _cancel_guard(_event=None):
            job = getattr(entry_widget, "_dark_guard_job", None)
            try:
                if job:
                    entry_widget.after_cancel(job)
            except Exception:
                pass  # timer may already be cancelled
            entry_widget._dark_guard_job = None

        def _schedule_guard(retries: int = 10):
            _cancel_guard()
            if retries <= 0:
                return

            def _tick(left: int):
                try:
                    if not entry_widget.winfo_exists():
                        entry_widget._dark_guard_job = None
                        return
                    current_bg = str(entry_widget.cget("bg"))
                    if current_bg != Theme.BG_TERTIARY:
                        _apply_dark_colors()
                    if left > 1:
                        entry_widget._dark_guard_job = entry_widget.after(200, lambda: _tick(left - 1))
                    else:
                        entry_widget._dark_guard_job = None
                except Exception:
                    entry_widget._dark_guard_job = None

            _tick(retries)

        def force_dark_colors(event=None):
            _apply_dark_colors()
            # 在焦点/输入等关键阶段做短时守护，避免长期循环
            _schedule_guard(retries=10)

        # 绑定多个事件，确保颜色在关键交互时恢复
        entry_widget.bind("<FocusIn>", force_dark_colors, add="+")
        entry_widget.bind("<FocusOut>", force_dark_colors, add="+")
        entry_widget.bind("<Button-1>", force_dark_colors, add="+")
        entry_widget.bind("<KeyPress>", force_dark_colors, add="+")
        entry_widget.bind("<KeyRelease>", force_dark_colors, add="+")
        entry_widget.bind("<ButtonRelease-1>", force_dark_colors, add="+")
        entry_widget.bind("<Map>", force_dark_colors, add="+")
        entry_widget.bind("<Destroy>", _cancel_guard, add="+")

        # 初始设置
        force_dark_colors()

    def _make_scroll_tab(self, settings_notebook: ttk.Notebook, title: str):
        """创建带滚动容器的设置页子页，返回内部可放控件的 frame。"""
        tab = tk.Frame(settings_notebook, bg=Theme.BG_SECONDARY)
        settings_notebook.add(tab, text=title)

        canvas = tk.Canvas(tab, bg=Theme.BG_SECONDARY, highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=Theme.BG_SECONDARY)

        inner.bind(
            "<Configure>",
            lambda _e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            if event.delta:
                canvas.yview_scroll(int(-1 * event.delta), "units")
            elif event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

        def _bind_mousewheel_recursive(widget):
            widget.bind("<MouseWheel>", _on_mousewheel)
            widget.bind("<Button-4>", _on_mousewheel)
            widget.bind("<Button-5>", _on_mousewheel)
            for child in widget.winfo_children():
                _bind_mousewheel_recursive(child)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 仅在当前设置页面容器内绑定滚轮，避免污染全局事件绑定。
        _bind_mousewheel_recursive(tab)

        return inner

    # -- settings page container (was SettingsPageLayoutSettingsPageMixin) --

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

    # -- advanced tab (was SettingsPageLayoutAdvancedMixin) --

    def _build_advanced_settings_tab(self, scrollable_frame: tk.Frame) -> None:
        """构建"高级"标签页内容。"""
        # ========== 7. 高级选项 ==========
        grp_advanced = ttk.LabelFrame(scrollable_frame, text="🔧 高级选项", padding=(15, 10))
        grp_advanced.pack(fill="x", padx=15, pady=(10, 10))
        
        advanced_options_frame = tk.Frame(grp_advanced, bg=Theme.BG_SECONDARY)
        advanced_options_frame.pack(fill="x", padx=8, pady=8)
        
        # 主题切换
        theme_frame = tk.Frame(advanced_options_frame, bg=Theme.BG_SECONDARY)
        theme_frame.pack(fill="x", pady=5)
        tk.Label(theme_frame, text="界面主题:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).pack(side="left")
        tk.Button(theme_frame, text="🌙 深色主题", command=self._set_dark_theme, bg="#374151", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=(10, 5))
        tk.Button(theme_frame, text="☀️ 浅色主题", command=self._set_light_theme, bg="#F1F5F9", fg="#1E293B",
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=5)
        
        # 配置导入导出
        config_frame = tk.Frame(advanced_options_frame, bg=Theme.BG_SECONDARY)
        config_frame.pack(fill="x", pady=5)
        tk.Label(config_frame, text="配置管理:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).pack(side="left")
        tk.Button(config_frame, text="📥 导入配置", command=self._import_config_ui, bg="#3B82F6", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=(10, 5))
        tk.Button(config_frame, text="📤 导出配置", command=self._export_config_ui, bg="#10B981", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=5)
        tk.Button(config_frame, text="📤 导出(含密钥)", command=self._export_config_with_keys, bg="#F59E0B", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=5)
        
        # 缓存管理
        cache_frame = tk.Frame(advanced_options_frame, bg=Theme.BG_SECONDARY)
        cache_frame.pack(fill="x", pady=5)
        tk.Label(cache_frame, text="缓存管理:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).pack(side="left")
        tk.Button(cache_frame, text="🗑️ 清除缓存", command=self._clear_cache_ui, bg="#EF4444", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=(10, 5))
        self.cache_size_label = tk.Label(cache_frame, text="缓存大小: 计算中...", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY)
        self.cache_size_label.pack(side="left", padx=10)
        self.after(500, self._update_cache_size)
        
        # 快捷键提示
        shortcut_frame = tk.Frame(advanced_options_frame, bg=Theme.BG_SECONDARY)
        shortcut_frame.pack(fill="x", pady=5)
        tk.Label(shortcut_frame, text="快捷键:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).pack(side="left")
        tk.Button(shortcut_frame, text="⌨️ 查看快捷键", command=self._show_shortcuts_ui, bg="#6366F1", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=(10, 5))
        tk.Label(shortcut_frame, text="提示: Ctrl+T切换主题, Ctrl+S保存, F1帮助", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY,
                 font=("", 9)).pack(side="left", padx=10)
        
        # ========== 7. 关于 ==========
        grp_about = ttk.LabelFrame(scrollable_frame, text="ℹ️ 关于", padding=(15, 10))
        grp_about.pack(fill="x", padx=15, pady=(10, 20))
        
        about_frame = tk.Frame(grp_about, bg=Theme.BG_SECONDARY)
        about_frame.pack(fill="x", padx=8, pady=8)
        
        tk.Label(about_frame, text="ScriptWeaver v2.0", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY,
                 font=("", 14, "bold")).pack(anchor="w")
        tk.Label(about_frame, text="智能故事创作平台 - 支持多种AI提供商", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY).pack(anchor="w", pady=2)
        tk.Label(about_frame, text="支持的AI: OpenAI, Gemini, Claude, DeepSeek, 通义, 文心, 智谱等", 
                 bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY, font=("", 10)).pack(anchor="w", pady=2)
