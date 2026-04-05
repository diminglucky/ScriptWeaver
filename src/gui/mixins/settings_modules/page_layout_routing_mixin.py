"""Model routing tab layout builders."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ...theme import Theme
from ..config_modules.model_routing import MODEL_ROUTING_TASKS


class SettingsPageLayoutRoutingMixin:
    """Build model routing controls."""
    def _build_model_routing_tab(self, scrollable_frame: tk.Frame) -> None:
        """构建“模型路由”标签页内容。"""
        grp_routing = ttk.LabelFrame(scrollable_frame, text="🧭 模型路由", padding=(15, 10))
        grp_routing.pack(fill="x", padx=15, pady=(10, 10))
        grp_routing.columnconfigure(0, weight=1)
        self._build_model_routing_intro(grp_routing)
        self._build_model_routing_mode_controls(grp_routing)
        self._build_model_routing_advanced_form(grp_routing)
        self._toggle_model_routing_advanced_ui(False)

    def _build_model_routing_intro(self, grp_routing: ttk.LabelFrame) -> None:
        """构建模型路由说明区。"""
        tk.Label(
            grp_routing,
            text="💡 默认只用主模型；仅在需要时才开启按功能单独路由",
            bg=Theme.BG_SECONDARY,
            fg="#90CAF9",
            font=("", 10),
        ).grid(row=0, column=0, sticky="w", padx=8, pady=(0, 4))

        tk.Label(
            grp_routing,
            text="🎨 最终出图模型请到：设置 -> 图片生成 API -> 模型（并保存配置）",
            bg=Theme.BG_SECONDARY,
            fg="#F59E0B",
            font=("", 10, "bold"),
        ).grid(row=1, column=0, sticky="w", padx=8, pady=(0, 8))

    def _build_model_routing_mode_controls(self, grp_routing: ttk.LabelFrame) -> None:
        """构建模型路由模式切换区。"""
        self.model_route_advanced_var = tk.BooleanVar(value=False)
        mode_frame = tk.Frame(grp_routing, bg=Theme.BG_SECONDARY)
        mode_frame.grid(row=2, column=0, sticky="we", padx=8, pady=(0, 6))
        mode_frame.columnconfigure(0, weight=1)

        self.chk_model_route_advanced = ttk.Checkbutton(
            mode_frame,
            text="高级模式：按功能单独设置模型路由",
            variable=self.model_route_advanced_var,
            command=self._on_model_route_mode_toggle,
        )
        self.chk_model_route_advanced.grid(row=0, column=0, sticky="w")

        tk.Button(
            mode_frame,
            text="🔁 用当前主模型覆盖文本任务",
            command=self._apply_story_model_to_text_routes,
            bg="#2563EB",
            fg=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
            font=("", 10, "bold"),
        ).grid(row=0, column=1, sticky="e", padx=(10, 0))

        self.model_route_mode_hint_label = tk.Label(
            grp_routing,
            text="",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_SECONDARY,
            font=("", 9),
        )
        self.model_route_mode_hint_label.grid(row=3, column=0, sticky="w", padx=8, pady=(0, 8))

    def _build_model_routing_advanced_form(self, grp_routing: ttk.LabelFrame) -> None:
        """构建高级模型路由配置表格。"""
        self.model_routing_advanced_frame = tk.Frame(grp_routing, bg=Theme.BG_SECONDARY)
        self.model_routing_advanced_frame.grid(row=4, column=0, sticky="we")
        self.model_routing_advanced_frame.columnconfigure(2, weight=1)
        self.model_route_vars = {}
        self._populate_model_routing_rows()

        route_btn_frame = tk.Frame(self.model_routing_advanced_frame, bg=Theme.BG_SECONDARY)
        route_btn_frame.grid(row=len(MODEL_ROUTING_TASKS), column=0, columnspan=4, pady=(10, 5))
        tk.Button(
            route_btn_frame,
            text="💾 保存模型路由",
            command=self._save_model_routing_settings,
            bg="#10B981",
            fg=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
            padx=20,
            pady=8,
            cursor="hand2",
            font=("", 11, "bold"),
        ).pack()

    def _populate_model_routing_rows(self) -> None:
        """填充模型路由任务行。"""
        provider_names = list(self.api_providers.keys()) if hasattr(self, "api_providers") else ["DeepSeek"]
        for idx, (task_key, task_label) in enumerate(MODEL_ROUTING_TASKS):
            row = idx
            tk.Label(
                self.model_routing_advanced_frame,
                text=task_label,
                bg=Theme.BG_SECONDARY,
                fg=Theme.TEXT_PRIMARY,
                font=("", 10, "bold"),
            ).grid(row=row, column=0, sticky="e", padx=(8, 6), pady=4)

            provider_var = tk.StringVar(value=provider_names[0] if provider_names else "DeepSeek")
            model_var = tk.StringVar(value="")
            combo_provider = ttk.Combobox(
                self.model_routing_advanced_frame,
                textvariable=provider_var,
                values=provider_names,
                state="readonly",
                width=18,
            )
            combo_provider.grid(row=row, column=1, sticky="w", padx=(0, 8), pady=4)

            combo_model = ttk.Combobox(
                self.model_routing_advanced_frame,
                textvariable=model_var,
                values=[""],
                state="normal",
                width=35,
            )
            combo_model.grid(row=row, column=2, sticky="w", padx=(0, 8), pady=4)
            tk.Label(
                self.model_routing_advanced_frame,
                text="(可手动输入)",
                bg=Theme.BG_SECONDARY,
                fg=Theme.TEXT_SECONDARY,
                font=("", 9),
            ).grid(row=row, column=3, sticky="w")

            combo_provider.bind("<<ComboboxSelected>>", lambda e, k=task_key: self._on_route_provider_change(k))
            self.model_route_vars[task_key] = {
                "provider_var": provider_var,
                "model_var": model_var,
                "combo_model": combo_model,
                "task_key": task_key,
            }

