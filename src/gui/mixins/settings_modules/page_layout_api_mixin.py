"""API settings tab layout builders."""

from __future__ import annotations

import tkinter as tk
from tkinter import END, ttk
from typing import Optional

from ...theme import Theme


class SettingsPageLayoutApiMixin:
    """Build API configuration controls."""
    def _build_api_settings_tab(self, scrollable_frame: tk.Frame) -> None:
        """构建“API 配置”标签页内容。"""
        # 页面说明
        api_tip = ttk.LabelFrame(scrollable_frame, text="✅ 快速配置", padding=(12, 8))
        api_tip.pack(fill="x", padx=15, pady=(10, 6))
        tk.Label(api_tip, text="1. 选择提供商 → 填写 Key/Base URL → 选择模型", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY).pack(anchor="w")
        tk.Label(api_tip, text="2. 点击“测试连接”验证可用性", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY).pack(anchor="w")
        tk.Label(api_tip, text="3. 点击“保存配置”，后续生成将直接使用该配置", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY).pack(anchor="w")
        self._build_story_api_section(scrollable_frame)
        self._build_image_api_section(scrollable_frame)
        
        # ========== 5. 快速 API 切换 ==========
        grp_quick_switch = ttk.LabelFrame(scrollable_frame, text="⚡ 快速 API 切换", padding=(15, 10))
        grp_quick_switch.pack(fill="x", padx=15, pady=(10, 10))
        grp_quick_switch.columnconfigure(1, weight=1)
        
        # 说明文字
        tk.Label(grp_quick_switch, text="💡 在这里快速选择生成时使用的 API（无需切换页面）", 
                 bg=Theme.BG_SECONDARY, fg="#90CAF9", font=("", 10)).grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 10))
        
        # 故事生成 API 选择
        tk.Label(grp_quick_switch, text="📝 故事生成:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).grid(row=1, column=0, sticky="e", padx=(8, 4), pady=8)
        self.quick_story_api = tk.StringVar(value="DeepSeek")
        self.combo_quick_story_api = ttk.Combobox(grp_quick_switch, textvariable=self.quick_story_api,
                                                   values=["DeepSeek"], state="readonly", width=30)
        self.combo_quick_story_api.grid(row=1, column=1, sticky="w", padx=(0, 8), pady=8)
        tk.Label(grp_quick_switch, text="← 用于生成目录和故事", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY, font=("", 9)).grid(row=1, column=2, sticky="w")
        
        # 图片生成 API 选择
        tk.Label(grp_quick_switch, text="🎨 图片生成:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).grid(row=2, column=0, sticky="e", padx=(8, 4), pady=8)
        self.quick_image_api = tk.StringVar(value="OpenAI (DALL-E)")
        self.combo_quick_image_api = ttk.Combobox(grp_quick_switch, textvariable=self.quick_image_api,
                                                   values=["OpenAI (DALL-E)"], state="readonly", width=30)
        self.combo_quick_image_api.grid(row=2, column=1, sticky="w", padx=(0, 8), pady=8)
        tk.Label(grp_quick_switch, text="← 用于生成图片", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY, font=("", 9)).grid(row=2, column=2, sticky="w")
        
        # 保存按钮
        quick_btn_frame = tk.Frame(grp_quick_switch, bg=Theme.BG_SECONDARY)
        quick_btn_frame.grid(row=3, column=0, columnspan=3, pady=(10, 5))
        tk.Button(quick_btn_frame, text="💾 保存 API 选择", command=self._save_quick_api_switch, 
                  bg="#10B981", fg=Theme.TEXT_PRIMARY, relief=tk.FLAT, padx=20, pady=8, cursor="hand2",
                  font=("", 11, "bold")).pack()

        # ========== 7. 测试日志 ==========
        grp_log = ttk.LabelFrame(scrollable_frame, text="📋 测试日志", padding=(15, 10))
        grp_log.pack(fill="x", padx=15, pady=(10, 20))
        
        # 日志工具栏
        log_toolbar = tk.Frame(grp_log, bg=Theme.BG_SECONDARY)
        log_toolbar.pack(fill="x", pady=(0, 5))
        tk.Label(log_toolbar, text="💡 API测试结果将显示在这里", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY).pack(side="left")
        tk.Button(log_toolbar, text="🗑️ 清空", command=lambda: self.settings_log.delete("1.0", END),
                  bg="#4B5563", fg=Theme.TEXT_PRIMARY, relief=tk.FLAT, padx=10, cursor="hand2").pack(side="right")
        
        # 日志文本框
        log_container = tk.Frame(grp_log, bg=Theme.SURFACE, height=150)
        log_container.pack(fill="x")
        log_container.pack_propagate(False)
        
        scroll_y = tk.Scrollbar(log_container, orient="vertical")
        scroll_y.pack(side="right", fill="y")
        
        self.settings_log = tk.Text(log_container, wrap="word", yscrollcommand=scroll_y.set,
                                     bg=Theme.SURFACE, fg=Theme.TEXT_PRIMARY, font=("Consolas", 10),
                                     relief=tk.FLAT, padx=10, pady=10)
        self.settings_log.pack(fill="both", expand=True)
        scroll_y.config(command=self.settings_log.yview)
        
        self.settings_log.insert("1.0", "设置页面已加载。\n配置好API后点击'测试连接'验证。\n")

    def _create_settings_entry(
        self,
        parent: tk.Misc,
        width: int = 50,
        show: Optional[str] = None,
    ) -> tk.Entry:
        """创建统一风格的设置页 Entry。"""
        kwargs = {
            "width": width,
            "bg": Theme.SURFACE,
            "fg": Theme.TEXT_PRIMARY,
            "insertbackground": Theme.TEXT_PRIMARY,
            "relief": tk.FLAT,
            "highlightthickness": 1,
            "highlightbackground": Theme.BORDER,
            "highlightcolor": Theme.BORDER_FOCUS,
            "disabledbackground": Theme.SURFACE,
            "disabledforeground": Theme.TEXT_SECONDARY,
            "readonlybackground": Theme.SURFACE,
        }
        if show:
            kwargs["show"] = show
        entry = tk.Entry(parent, **kwargs)
        self._fix_entry_colors(entry)
        return entry

    def _build_story_api_section(self, scrollable_frame: tk.Frame) -> None:
        """构建故事 API 配置区块。"""
        grp_story_api = self._create_api_group_frame(scrollable_frame, "📝 故事生成 API")
        self._build_story_api_provider_row(grp_story_api)
        self._build_story_api_model_row(grp_story_api)
        self._build_story_api_credentials_rows(grp_story_api)
        self._build_story_api_buttons(grp_story_api)

    def _build_image_api_section(self, scrollable_frame: tk.Frame) -> None:
        """构建图片 API 配置区块。"""
        grp_img_api = self._create_api_group_frame(scrollable_frame, "🎨 图片生成 API")
        self._build_image_api_provider_row(grp_img_api)
        self._build_image_api_model_row(grp_img_api)
        self._build_image_api_credentials_rows(grp_img_api)
        self._build_image_api_buttons(grp_img_api)

    def _create_api_group_frame(self, scrollable_frame: tk.Frame, title: str) -> ttk.LabelFrame:
        """创建 API 设置分组容器。"""
        group = ttk.LabelFrame(scrollable_frame, text=title, padding=(15, 10))
        group.pack(fill="x", padx=15, pady=10)
        group.columnconfigure(1, weight=1)
        return group

    def _get_story_provider_names(self) -> list[str]:
        provider_names = list(self.api_providers.keys()) if hasattr(self, "api_providers") else ["DeepSeek"]
        if hasattr(self, "api_presets"):
            for name in self.api_presets.keys():
                if name not in provider_names:
                    provider_names.append(name)
        return provider_names

    def _get_image_provider_names(self) -> list[str]:
        if hasattr(self, "img_api_providers"):
            return list(self.img_api_providers.keys())
        return ["OpenAI (DALL-E)"]

    def _build_story_api_provider_row(self, group: ttk.LabelFrame) -> None:
        tk.Label(group, text="API提供商:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).grid(
            row=0, column=0, sticky="e", padx=(8, 4), pady=8
        )
        self.settings_api_provider = tk.StringVar(value="DeepSeek")
        self.settings_combo_provider = ttk.Combobox(
            group,
            textvariable=self.settings_api_provider,
            values=self._get_story_provider_names(),
            state="readonly",
            width=25,
        )
        self.settings_combo_provider.grid(row=0, column=1, sticky="w", padx=(0, 8), pady=8)
        self.settings_combo_provider.bind("<<ComboboxSelected>>", self._on_settings_provider_change)

    def _build_story_api_model_row(self, group: ttk.LabelFrame) -> None:
        tk.Label(group, text="模型:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).grid(
            row=1, column=0, sticky="e", padx=(8, 4), pady=4
        )
        self.settings_model_var = tk.StringVar(value="deepseek-chat")
        self.settings_combo_model = ttk.Combobox(
            group,
            textvariable=self.settings_model_var,
            values=["deepseek-chat"],
            state="normal",
            width=35,
        )
        self.settings_combo_model.grid(row=1, column=1, sticky="w", padx=(0, 8), pady=4)
        tk.Label(group, text="(可手动输入)", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY, font=("", 9)).grid(
            row=1, column=2, sticky="w"
        )

    def _build_story_api_credentials_rows(self, group: ttk.LabelFrame) -> None:
        tk.Label(group, text="API Key:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).grid(
            row=2, column=0, sticky="e", padx=(8, 4), pady=4
        )
        self.settings_api_key = self._create_settings_entry(group, width=50, show="•")
        self.settings_api_key.grid(row=2, column=1, sticky="w", padx=(0, 8), pady=4)

        self.show_key_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            group,
            text="显示",
            variable=self.show_key_var,
            command=self._toggle_key_visibility,
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_SECONDARY,
            selectcolor=Theme.BG_SECONDARY,
            activebackground=Theme.BG_SECONDARY,
        ).grid(row=2, column=2, padx=4)

        tk.Label(group, text="Base URL:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).grid(
            row=3, column=0, sticky="e", padx=(8, 4), pady=4
        )
        self.settings_base_url = self._create_settings_entry(group, width=50)
        self.settings_base_url.grid(row=3, column=1, sticky="w", padx=(0, 8), pady=4)

        tk.Label(group, text="自定义模型:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY).grid(
            row=4, column=0, sticky="e", padx=(8, 4), pady=4
        )
        self.settings_custom_model = self._create_settings_entry(group, width=50)
        self.settings_custom_model.grid(row=4, column=1, sticky="w", padx=(0, 8), pady=4)
        tk.Label(group, text="(仅自定义时使用)", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY, font=("", 9)).grid(
            row=4, column=2, sticky="w"
        )

    def _build_story_api_buttons(self, group: ttk.LabelFrame) -> None:
        btn_frame = tk.Frame(group, bg=Theme.BG_SECONDARY)
        btn_frame.grid(row=5, column=0, columnspan=3, pady=(10, 5))
        tk.Button(
            btn_frame,
            text="🔍 测试连接",
            command=self._test_story_api,
            bg="#3B82F6",
            fg=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
            padx=15,
            pady=6,
            cursor="hand2",
        ).pack(side="left", padx=5)
        tk.Button(
            btn_frame,
            text="💾 保存配置",
            command=self._save_story_api_settings,
            bg="#10B981",
            fg=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
            padx=15,
            pady=6,
            cursor="hand2",
        ).pack(side="left", padx=5)

    def _build_image_api_provider_row(self, group: ttk.LabelFrame) -> None:
        tk.Label(group, text="API提供商:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).grid(
            row=0, column=0, sticky="e", padx=(8, 4), pady=8
        )
        self.settings_img_provider = tk.StringVar(value="OpenAI (DALL-E)")
        self.settings_combo_img_provider = ttk.Combobox(
            group,
            textvariable=self.settings_img_provider,
            values=self._get_image_provider_names(),
            state="readonly",
            width=25,
        )
        self.settings_combo_img_provider.grid(row=0, column=1, sticky="w", padx=(0, 8), pady=8)
        self.settings_combo_img_provider.bind("<<ComboboxSelected>>", self._on_settings_img_provider_change)

    def _build_image_api_model_row(self, group: ttk.LabelFrame) -> None:
        tk.Label(group, text="模型:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).grid(
            row=1, column=0, sticky="e", padx=(8, 4), pady=4
        )
        self.settings_img_model_var = tk.StringVar(value="dall-e-3")
        self.settings_combo_img_model = ttk.Combobox(
            group,
            textvariable=self.settings_img_model_var,
            values=["dall-e-3"],
            state="normal",
            width=35,
        )
        self.settings_combo_img_model.grid(row=1, column=1, sticky="w", padx=(0, 8), pady=4)
        tk.Label(group, text="(可手动输入)", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY, font=("", 9)).grid(
            row=1, column=2, sticky="w"
        )

    def _build_image_api_credentials_rows(self, group: ttk.LabelFrame) -> None:
        tk.Label(group, text="API Key:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).grid(
            row=2, column=0, sticky="e", padx=(8, 4), pady=4
        )
        self.settings_img_api_key = self._create_settings_entry(group, width=50, show="•")
        self.settings_img_api_key.grid(row=2, column=1, sticky="w", padx=(0, 8), pady=4)

        self.show_img_key_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            group,
            text="显示",
            variable=self.show_img_key_var,
            command=self._toggle_img_key_visibility,
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_SECONDARY,
            selectcolor=Theme.BG_SECONDARY,
            activebackground=Theme.BG_SECONDARY,
        ).grid(row=2, column=2, padx=4)

        tk.Label(group, text="Base URL:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).grid(
            row=3, column=0, sticky="e", padx=(8, 4), pady=4
        )
        self.settings_img_base_url = self._create_settings_entry(group, width=50)
        self.settings_img_base_url.grid(row=3, column=1, sticky="w", padx=(0, 8), pady=4)

        tk.Label(group, text="自定义模型:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY).grid(
            row=4, column=0, sticky="e", padx=(8, 4), pady=4
        )
        self.settings_img_custom_model = self._create_settings_entry(group, width=50)
        self.settings_img_custom_model.grid(row=4, column=1, sticky="w", padx=(0, 8), pady=4)
        tk.Label(group, text="(仅自定义时使用)", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY, font=("", 9)).grid(
            row=4, column=2, sticky="w"
        )

    def _build_image_api_buttons(self, group: ttk.LabelFrame) -> None:
        img_btn_frame = tk.Frame(group, bg=Theme.BG_SECONDARY)
        img_btn_frame.grid(row=5, column=0, columnspan=3, pady=(10, 5))
        tk.Button(
            img_btn_frame,
            text="🔍 测试连接",
            command=self._test_img_api,
            bg="#3B82F6",
            fg=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
            padx=15,
            pady=6,
            cursor="hand2",
        ).pack(side="left", padx=5)
        tk.Button(
            img_btn_frame,
            text="💾 保存配置",
            command=self._save_img_api_settings,
            bg="#10B981",
            fg=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
            padx=15,
            pady=6,
            cursor="hand2",
        ).pack(side="left", padx=5)

