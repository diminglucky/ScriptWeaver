"""Modern app UI/theming helpers extracted from ModernApp."""

from __future__ import annotations

from datetime import datetime
import logging
import tkinter as tk
from tkinter import ttk

from .theme import Theme, theme_manager

logger = logging.getLogger(__name__)


class ModernUiMixin:
    """Build and update modern header/status/theme UI."""

    def _setup_modern_styles(self):
        """设置现代化ttk组件样式"""
        self.ttk_style = ttk.Style()
        self.ttk_style.theme_use('clam')

        self._configure_notebook_styles()
        self._configure_frame_styles()
        self._configure_labelframe_styles()
        self._configure_button_styles()
        self._configure_entry_styles()
        self._configure_combobox_styles()
        self._configure_spinbox_styles()
        self._configure_combobox_listbox_colors()

    def _configure_notebook_styles(self) -> None:
        """配置 Notebook 样式。"""
        self.ttk_style.configure(
            "TNotebook",
            background=Theme.BG_PRIMARY,
            borderwidth=0,
            relief="flat",
            tabmargins=[0, 0, 0, 0]
        )
        self.ttk_style.configure(
            "TNotebook.Tab",
            background=Theme.BG_SECONDARY,
            foreground=Theme.TEXT_SECONDARY,
            padding=[32, 16],
            borderwidth=0,
            focuscolor="none",
            lightcolor=Theme.BG_SECONDARY,
            darkcolor=Theme.BG_SECONDARY,
            bordercolor=Theme.BG_SECONDARY,
            font=(Theme.FONT_FAMILY, 13, "normal")
        )
        self.ttk_style.map(
            "TNotebook.Tab",
            background=[
                ("selected", Theme.SURFACE),
                ("active", Theme.BG_HOVER),
                ("!active", Theme.BG_SECONDARY)
            ],
            foreground=[
                ("selected", Theme.TEXT_PRIMARY),
                ("active", Theme.TEXT_PRIMARY),
                ("!active", Theme.TEXT_SECONDARY)
            ],
            padding=[
                ("selected", [32, 16]),
                ("active", [32, 16]),
                ("!active", [32, 16])
            ]
        )

    def _configure_frame_styles(self) -> None:
        """配置 Frame 样式。"""
        self.ttk_style.configure(
            "TFrame",
            background=Theme.BG_SECONDARY,
            borderwidth=0
        )

    def _configure_labelframe_styles(self) -> None:
        """配置 LabelFrame 样式。"""
        self.ttk_style.configure(
            "TLabelframe",
            background=Theme.SURFACE,
            foreground=Theme.TEXT_PRIMARY,
            borderwidth=1,
            bordercolor=Theme.BORDER,
            relief="flat"
        )
        self.ttk_style.configure(
            "TLabelframe.Label",
            background=Theme.SURFACE,
            foreground=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_MEDIUM, "bold"),
            padding=[8, 4]
        )

    def _configure_button_styles(self) -> None:
        """配置 Button 样式。"""
        self.ttk_style.configure(
            "TButton",
            background=Theme.PRIMARY,
            foreground=Theme.TEXT_PRIMARY,
            borderwidth=0,
            relief="flat",
            padding=[28, 14],
            font=(Theme.FONT_FAMILY, 12, "normal")
        )
        self.ttk_style.map(
            "TButton",
            background=[
                ("active", Theme.PRIMARY_LIGHT),
                ("pressed", Theme.PRIMARY_DARK),
                ("disabled", Theme.BG_TERTIARY)
            ],
            foreground=[
                ("pressed", Theme.TEXT_PRIMARY),
                ("active", Theme.TEXT_PRIMARY),
                ("disabled", Theme.TEXT_DISABLED)
            ]
        )

    def _configure_entry_styles(self) -> None:
        """配置 Entry 样式。"""
        self.ttk_style.configure(
            "TEntry",
            fieldbackground=Theme.BG_TERTIARY,
            foreground=Theme.TEXT_PRIMARY,
            borderwidth=1,
            insertcolor=Theme.TEXT_PRIMARY
        )
        self.ttk_style.map(
            "TEntry",
            fieldbackground=[("disabled", Theme.BG_SECONDARY), ("!disabled", Theme.BG_TERTIARY)],
            foreground=[("disabled", Theme.TEXT_DISABLED), ("!disabled", Theme.TEXT_PRIMARY)],
        )

    def _configure_combobox_styles(self) -> None:
        """配置 Combobox 样式。"""
        self.ttk_style.configure(
            "TCombobox",
            fieldbackground=Theme.BG_TERTIARY,
            background=Theme.BG_TERTIARY,
            foreground=Theme.TEXT_PRIMARY,
            borderwidth=1,
            arrowcolor=Theme.TEXT_SECONDARY
        )
        self.ttk_style.map(
            "TCombobox",
            fieldbackground=[
                ("readonly", Theme.BG_TERTIARY),
                ("disabled", Theme.BG_SECONDARY),
                ("!disabled", Theme.BG_TERTIARY),
            ],
            background=[
                ("readonly", Theme.BG_TERTIARY),
                ("disabled", Theme.BG_SECONDARY),
                ("!disabled", Theme.BG_TERTIARY),
            ],
            foreground=[
                ("readonly", Theme.TEXT_PRIMARY),
                ("disabled", Theme.TEXT_DISABLED),
                ("!disabled", Theme.TEXT_PRIMARY),
            ],
            selectbackground=[("readonly", Theme.PRIMARY), ("!readonly", Theme.PRIMARY)],
            selectforeground=[("readonly", Theme.TEXT_PRIMARY), ("!readonly", Theme.TEXT_PRIMARY)],
            arrowcolor=[("disabled", Theme.TEXT_DISABLED), ("!disabled", Theme.TEXT_SECONDARY)],
        )

    def _configure_spinbox_styles(self) -> None:
        """配置 Spinbox 样式。"""
        self.ttk_style.configure(
            "TSpinbox",
            fieldbackground=Theme.BG_TERTIARY,
            background=Theme.BG_TERTIARY,
            foreground=Theme.TEXT_PRIMARY,
            borderwidth=1,
            arrowcolor=Theme.TEXT_SECONDARY,
        )
        self.ttk_style.map(
            "TSpinbox",
            fieldbackground=[("disabled", Theme.BG_SECONDARY), ("!disabled", Theme.BG_TERTIARY)],
            foreground=[("disabled", Theme.TEXT_DISABLED), ("!disabled", Theme.TEXT_PRIMARY)],
            arrowcolor=[("disabled", Theme.TEXT_DISABLED), ("!disabled", Theme.TEXT_SECONDARY)],
        )

    def _configure_combobox_listbox_colors(self) -> None:
        """配置 Combobox 下拉列表颜色。"""
        self.option_add("*TCombobox*Listbox*Background", Theme.BG_TERTIARY)
        self.option_add("*TCombobox*Listbox*Foreground", Theme.TEXT_PRIMARY)
        self.option_add("*TCombobox*Listbox*selectBackground", Theme.PRIMARY)
        self.option_add("*TCombobox*Listbox*selectForeground", Theme.TEXT_PRIMARY)
    
    def _create_modern_header(self):
        """创建现代化顶部标题栏 - 专业设计"""
        header = tk.Frame(self, bg=Theme.BG_PRIMARY, height=64)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        self._build_header_brand_area(header)

        right_frame = tk.Frame(header, bg=Theme.BG_PRIMARY)
        right_frame.pack(side="right", padx=24, pady=12)

        right_container = tk.Frame(right_frame, bg=Theme.BG_PRIMARY)
        right_container.pack(side="left")

        self._build_header_tools(right_container)
        self._build_header_status_card(right_container)
        self._build_header_user_card(right_container)
        self._build_header_separator()

    def _build_header_brand_area(self, header: tk.Frame) -> None:
        """构建顶部栏左侧品牌区。"""
        left_frame = tk.Frame(header, bg=Theme.BG_PRIMARY)
        left_frame.pack(side="left", padx=24, pady=12)

        icon_canvas = tk.Canvas(
            left_frame,
            width=40,
            height=40,
            bg=Theme.BG_PRIMARY,
            highlightthickness=0
        )
        icon_canvas.pack(side="left", padx=(0, 16))
        icon_canvas.create_oval(
            0, 0, 40, 40,
            fill=Theme.PRIMARY,
            outline="",
            width=0
        )
        icon_canvas.create_oval(
            4, 4, 36, 36,
            fill="",
            outline=Theme.ACCENT,
            width=2
        )
        icon_canvas.create_text(
            20, 20,
            text="AS",
            font=(Theme.FONT_FAMILY, 14, "bold"),
            fill=Theme.TEXT_PRIMARY
        )

        title_frame = tk.Frame(left_frame, bg=Theme.BG_PRIMARY)
        title_frame.pack(side="left")

        tk.Label(
            title_frame,
            text="ScriptWeaver",
            font=(Theme.FONT_FAMILY, 18, "bold"),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_PRIMARY
        ).pack(anchor="w")

        tk.Label(
            title_frame,
            text="智能创作平台",
            font=(Theme.FONT_FAMILY, 11),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_HINT
        ).pack(anchor="w")

    def _build_header_tools(self, right_container: tk.Frame) -> None:
        """构建顶部栏右侧工具按钮区。"""
        tools_frame = tk.Frame(right_container, bg=Theme.BG_PRIMARY)
        tools_frame.pack(side="left", padx=(0, 16))

        self.theme_btn = tk.Button(
            tools_frame,
            text="🌙" if theme_manager.is_dark else "☀️",
            font=(Theme.FONT_FAMILY, 14),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            command=self._toggle_theme_ui
        )
        self.theme_btn.pack(side="left", padx=4)

        tk.Button(
            tools_frame,
            text="📥",
            font=(Theme.FONT_FAMILY, 14),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            command=lambda: self.import_config() if hasattr(self, 'import_config') else None
        ).pack(side="left", padx=4)

        tk.Button(
            tools_frame,
            text="📤",
            font=(Theme.FONT_FAMILY, 14),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            command=lambda: self.export_config() if hasattr(self, 'export_config') else None
        ).pack(side="left", padx=4)

        tk.Button(
            tools_frame,
            text="⌨️",
            font=(Theme.FONT_FAMILY, 14),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
            relief="flat",
            cursor="hand2",
            command=lambda: self._show_shortcuts_help() if hasattr(self, '_show_shortcuts_help') else None
        ).pack(side="left", padx=4)

    def _build_header_status_card(self, right_container: tk.Frame) -> None:
        """构建顶部栏状态卡片。"""
        status_card = tk.Frame(
            right_container,
            bg=Theme.SURFACE,
            relief="flat"
        )
        status_card.pack(side="left", padx=(0, 12))

        status_inner = tk.Frame(status_card, bg=Theme.SURFACE)
        status_inner.pack(padx=16, pady=8)

        self.header_status_icon = tk.Label(
            status_inner,
            text="✅",
            font=(Theme.FONT_FAMILY, 14),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_SECONDARY
        )
        self.header_status_icon.pack(side="left", padx=(0, 8))

        self.header_status_text = tk.Label(
            status_inner,
            text="就绪",
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY
        )
        self.header_status_text.pack(side="left")

    def _build_header_user_card(self, right_container: tk.Frame) -> None:
        """构建顶部栏用户卡片。"""
        user_card = tk.Frame(
            right_container,
            bg=Theme.SURFACE,
            relief="flat"
        )
        user_card.pack(side="left")

        user_inner = tk.Frame(user_card, bg=Theme.SURFACE)
        user_inner.pack(padx=16, pady=8)

        tk.Label(
            user_inner,
            text="👤",
            font=(Theme.FONT_FAMILY, 16),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_SECONDARY
        ).pack(side="left", padx=(0, 10))
        
        tk.Label(
            user_inner,
            text="diming",
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY
        ).pack(side="left")

    def _build_header_separator(self) -> None:
        """构建顶部栏底部分隔线。"""
        separator = tk.Frame(self, bg=Theme.DIVIDER, height=1)
        separator.pack(fill="x")
    
    def _apply_modern_theme(self):
        """将现代化主题应用到已创建的组件"""
        # 应用到主notebook
        if hasattr(self, 'notebook'):
            self.notebook.configure(style="TNotebook")
            # 添加边距，让选项卡更有呼吸感
            self.notebook.pack_configure(padx=0, pady=0)
            
            # 更新页面背景 - 使用更深的背景色
            for page in [self.page_project, self.page_story, self.page_image, self.page_director, self.page_settings]:
                page.configure(bg=Theme.BG_CARD)
                self._apply_theme_to_children(page)
        
        # 优化内部notebook（story_notebook等）
        if hasattr(self, 'story_notebook'):
            self.story_notebook.configure(style="TNotebook")
    
    def _apply_theme_to_children(self, widget):
        """递归应用主题到所有子组件"""
        try:
            widget_class = widget.winfo_class()
            if self._should_skip_theme_widget_class(widget_class):
                self._apply_theme_to_child_widgets(widget)
                return
            self._apply_theme_to_single_widget(widget, widget_class)
            self._apply_theme_to_child_widgets(widget)
        except Exception as e:
            # 忽略无法配置的组件，避免崩溃
            logger.debug("apply theme to children failed: %s", e)

    @staticmethod
    def _should_skip_theme_widget_class(widget_class: str) -> bool:
        return widget_class in [
            "TCombobox",
            "TSpinbox",
            "TNotebook",
            "TButton",
            "TEntry",
            "TFrame",
            "TLabelframe",
        ]

    def _apply_theme_to_child_widgets(self, widget) -> None:
        for child in widget.winfo_children():
            self._apply_theme_to_children(child)

    def _apply_theme_to_single_widget(self, widget, widget_class: str) -> None:
        if widget_class == "Frame":
            widget.configure(bg=Theme.BG_SECONDARY)
            return
        if widget_class == "Label":
            self._apply_theme_to_label(widget)
            return
        if widget_class == "Text":
            self._apply_theme_to_text(widget)
            return
        if widget_class == "Entry":
            self._apply_theme_to_entry(widget)
            return
        if widget_class == "Canvas":
            self._apply_theme_to_canvas(widget)
            return
        if widget_class == "Listbox":
            self._apply_theme_to_listbox(widget)
            return
        if widget_class == "Button":
            self._apply_theme_to_button(widget)

    def _apply_theme_to_label(self, widget) -> None:
        current_bg = widget.cget("bg")
        if current_bg in ["#2b2b2b", "#1e1e1e", "SystemButtonFace", ""]:
            widget.configure(bg=Theme.BG_SECONDARY)
        try:
            current_fg = widget.cget("fg")
            if current_fg in ["#ffffff", "#FFFFFF", "#d4d4d4", "#D4D4D4", "black", "white", ""]:
                widget.configure(fg=Theme.TEXT_PRIMARY)
        except Exception as e:
            logger.debug("label fg sync skipped: %s", e)

    def _apply_theme_to_text(self, widget) -> None:
        current_bg = widget.cget("bg")
        if current_bg in ["#000000", "#1e1e1e", "#2b2b2b"]:
            text_bg = Theme.SURFACE_DARK if theme_manager.is_dark else Theme.SURFACE
            widget.configure(
                bg=text_bg,
                fg=Theme.TEXT_PRIMARY,
                insertbackground=Theme.TEXT_PRIMARY,
                selectbackground=Theme.PRIMARY,
                selectforeground=Theme.TEXT_PRIMARY,
            )

    def _apply_theme_to_entry(self, widget) -> None:
        current_bg = widget.cget("bg")
        if current_bg in ["#000000", "#1e1e1e", "#2b2b2b"]:
            entry_bg = Theme.BG_TERTIARY if theme_manager.is_dark else Theme.SURFACE_LIGHT
            widget.configure(
                bg=entry_bg,
                fg=Theme.TEXT_PRIMARY,
                insertbackground=Theme.TEXT_PRIMARY,
                selectbackground=Theme.PRIMARY,
                selectforeground=Theme.TEXT_PRIMARY,
            )

    def _apply_theme_to_canvas(self, widget) -> None:
        current_bg = widget.cget("bg")
        if current_bg in ["#000000", "#1e1e1e", "#2b2b2b"]:
            widget.configure(bg=Theme.BG_SECONDARY)

    def _apply_theme_to_listbox(self, widget) -> None:
        current_bg = widget.cget("bg")
        if current_bg in ["#000000", "#1e1e1e", "#2b2b2b"]:
            widget.configure(
                bg=Theme.SURFACE if not theme_manager.is_dark else Theme.BG_TERTIARY,
                fg=Theme.TEXT_PRIMARY,
                selectbackground=Theme.PRIMARY,
                selectforeground=Theme.TEXT_PRIMARY,
            )

    def _apply_theme_to_button(self, widget) -> None:
        current_bg = widget.cget("bg")
        current_fg = widget.cget("fg")
        active_bg = widget.cget("activebackground")
        active_fg = widget.cget("activeforeground")
        if current_bg in ["#000000", "#1e1e1e", "#2b2b2b", "SystemButtonFace", ""]:
            widget.configure(
                bg=Theme.PRIMARY_DARK,
                fg=Theme.TEXT_PRIMARY,
                activebackground=Theme.PRIMARY,
                activeforeground=Theme.TEXT_PRIMARY,
                relief="flat",
                bd=0,
            )
            return
        if active_bg in ["SystemButtonFace", "", None, "#ffffff", "#FFFFFF", "white"]:
            widget.configure(activebackground=current_bg)
        if active_fg in ["SystemButtonText", "", None] or (
            active_bg in ["#ffffff", "#FFFFFF", "white"]
            and active_fg in ["white", "#ffffff", "#FFFFFF"]
        ):
            widget.configure(activeforeground=current_fg or Theme.TEXT_PRIMARY)
    
    def _create_modern_status_bar(self):
        """创建现代化底部状态栏 - 专业设计"""
        # 微妙的分隔线
        tk.Frame(self, bg=Theme.DIVIDER, height=1).pack(fill="x", side="bottom")
        
        # 状态栏容器
        status_bar = tk.Frame(self, bg=Theme.BG_PRIMARY, height=32)
        status_bar.pack(fill="x", side="bottom")
        status_bar.pack_propagate(False)
        
        # 左侧：状态区域（带背景卡片）
        left_frame = tk.Frame(status_bar, bg=Theme.BG_PRIMARY)
        left_frame.pack(side="left", fill="y", padx=20, pady=6)
        
        # 状态指示器 - 更精致
        self.status_indicator = tk.Canvas(
            left_frame,
            width=8,
            height=8,
            bg=Theme.BG_PRIMARY,
            highlightthickness=0
        )
        self.status_indicator.pack(side="left", padx=(0, 12))
        self.status_indicator.create_oval(0, 0, 8, 8, fill=Theme.SUCCESS, outline="")
        
        # 状态文本
        if not hasattr(self, 'status'):
            self.status = tk.StringVar(value="系统就绪")
        
        self.status_label = tk.Label(
            left_frame,
            textvariable=self.status,
            font=(Theme.FONT_FAMILY, 11),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_SECONDARY
        )
        self.status_label.pack(side="left")
        
        # 右侧：信息区域
        right_frame = tk.Frame(status_bar, bg=Theme.BG_PRIMARY)
        right_frame.pack(side="right", fill="y", padx=20, pady=6)
        
        # 版本标签 - 带图标
        version_container = tk.Frame(right_frame, bg=Theme.BG_PRIMARY)
        version_container.pack(side="right")
        
        tk.Label(
            version_container,
            text="🎯",
            font=(Theme.FONT_FAMILY, 10),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_DISABLED
        ).pack(side="left", padx=(10, 4))
        
        tk.Label(
            version_container,
            text="v2.0.0",
            font=(Theme.FONT_FAMILY, 10),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_DISABLED
        ).pack(side="left")
        
        # 微妙的分隔符
        tk.Label(
            right_frame,
            text="•",
            font=(Theme.FONT_FAMILY, 10),
            bg=Theme.BG_PRIMARY,
            fg=Theme.BORDER
        ).pack(side="right", padx=8)
        
        # 时间显示 - 带图标
        time_container = tk.Frame(right_frame, bg=Theme.BG_PRIMARY)
        time_container.pack(side="right")
        
        tk.Label(
            time_container,
            text="🕐",
            font=(Theme.FONT_FAMILY, 10),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_DISABLED
        ).pack(side="left", padx=(0, 6))
        
        self.time_label = tk.Label(
            time_container,
            text="",
            font=(Theme.FONT_FAMILY, 11),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_SECONDARY
        )
        self.time_label.pack(side="left")
    
    def _update_time(self):
        """更新时间显示"""
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if hasattr(self, 'time_label'):
                self.time_label.config(text=now)
            self.after(1000, self._update_time)
        except Exception as e:
            logger.debug("update_time failed: %s", e)
    
    def _toggle_theme_ui(self):
        """切换主题（带UI更新）"""
        theme_manager.toggle()
        # 更新按钮图标
        if hasattr(self, 'theme_btn'):
            self.theme_btn.config(text="🌙" if theme_manager.is_dark else "☀️")
    
    def update_header_status(self, text: str, icon: str = "🔄", color: str = None):
        """
        更新顶部状态栏的显示
        
        参数:
            text: 要显示的状态文本
            icon: 状态图标，默认为🔄（处理中）
            color: 文本颜色（可选），如果不指定则使用默认颜色
        
        常用图标:
            🔄 - 处理中
            ✅ - 完成/就绪
            ⏳ - 等待中
            📝 - 生成中
            🎨 - 图片生成中
            ❌ - 错误
            ⚠️ - 警告
        """
        def apply():
            try:
                if hasattr(self, 'header_status_icon') and hasattr(self, 'header_status_text'):
                    self.header_status_icon.config(text=icon)
                    self.header_status_text.config(text=text)
                    if color:
                        self.header_status_text.config(fg=color)
                    else:
                        # 根据图标自动选择颜色
                        if icon == "✅":
                            self.header_status_text.config(fg=Theme.TEXT_PRIMARY)
                        elif icon == "❌":
                            self.header_status_text.config(fg="#ef5350")  # 红色
                        elif icon == "⚠️":
                            self.header_status_text.config(fg="#ffa726")  # 橙色
                        elif icon in ["🔄", "📝", "🎨", "⏳"]:
                            self.header_status_text.config(fg="#42a5f5")  # 蓝色（进行中）
                        else:
                            self.header_status_text.config(fg=Theme.TEXT_PRIMARY)
                    # 强制刷新UI
                    self.update_idletasks()
            except Exception as e:
                logger.debug("update header status failed: %s", e)
        if hasattr(self, "_ui"):
            self._ui(apply)
        else:
            apply()

    
