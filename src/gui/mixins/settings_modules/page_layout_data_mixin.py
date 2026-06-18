"""Knowledge-base and generation-parameter layout builders."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ...theme import Theme
from ...helpers.story_creativity import (
    DEFAULT_STORY_CREATIVITY_MODE,
    list_story_creativity_modes,
    normalize_story_creativity_mode,
)
from ...helpers.story_generation_modes import (
    DEFAULT_STORY_GENERATION_MODE,
    list_story_generation_modes,
    normalize_story_generation_mode,
)
from ...helpers.story_templates import (
    DEFAULT_STORY_TEMPLATE_KEY,
    DEFAULT_STORY_TEMPLATE_STRATEGY,
    list_story_template_strategies,
    list_story_templates,
    normalize_story_template_strategy,
)


class SettingsPageLayoutDataMixin:
    """Build data/KB and story generation parameter controls."""
    def _build_data_kb_and_params_tab(self, scrollable_frame: tk.Frame) -> None:
        """构建“知识库 & 参数”标签页内容。"""
        self._build_data_tab_tip(scrollable_frame)
        self._build_kb_config_section(scrollable_frame)
        self._build_generation_params_section(scrollable_frame)

    def _build_data_tab_tip(self, scrollable_frame: tk.Frame) -> None:
        """构建知识库与参数页顶部说明。"""
        data_tip = ttk.LabelFrame(scrollable_frame, text="🧭 使用说明", padding=(12, 8))
        data_tip.pack(fill="x", padx=15, pady=(10, 6))
        tk.Label(data_tip, text="1. 先设置知识库数据目录与索引目录", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY).pack(anchor="w")
        tk.Label(data_tip, text="2. 点击“构建索引”后即可使用检索增强", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY).pack(anchor="w")
        tk.Label(data_tip, text="3. 生成参数会影响默认创作长度与随机性", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY).pack(anchor="w")

    def _build_kb_config_section(self, scrollable_frame: tk.Frame) -> None:
        """构建知识库配置区块。"""
        grp_kb = ttk.LabelFrame(scrollable_frame, text="📚 知识库配置", padding=(15, 10))
        grp_kb.pack(fill="x", padx=15, pady=(15, 10))
        grp_kb.columnconfigure(1, weight=1)

        tk.Label(grp_kb, text="数据目录:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.entry_data = tk.Entry(grp_kb, textvariable=self.data_dir, bg=Theme.SURFACE, fg=Theme.TEXT_PRIMARY,
                                   insertbackground=Theme.TEXT_PRIMARY, relief=tk.FLAT)
        self.entry_data.grid(row=0, column=1, sticky="we", padx=8)
        self._fix_entry_colors(self.entry_data)
        tk.Button(grp_kb, text="选择...", command=self.choose_data, bg="#374151", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2").grid(row=0, column=2, padx=(4, 8), pady=6)
        tk.Button(grp_kb, text="一键选择库", command=self.choose_library_quick, bg="#6366F1", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2").grid(row=0, column=3, padx=(0, 8), pady=6)

        tk.Label(grp_kb, text="索引目录:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).grid(row=1, column=0, sticky="w", padx=8, pady=(0, 6))
        self.entry_index = tk.Entry(grp_kb, textvariable=self.index_dir, bg=Theme.SURFACE, fg=Theme.TEXT_PRIMARY,
                                    insertbackground=Theme.TEXT_PRIMARY, relief=tk.FLAT)
        self.entry_index.grid(row=1, column=1, sticky="we", padx=8)
        self._fix_entry_colors(self.entry_index)
        tk.Button(grp_kb, text="选择...", command=self.choose_index, bg="#374151", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2").grid(row=1, column=2, padx=(4, 8), pady=(0, 6))
        self.btn_ingest = tk.Button(grp_kb, text="🔄 增量更新", command=self.on_ingest_incremental, bg="#2563EB", fg=Theme.TEXT_PRIMARY,
                                    relief=tk.FLAT, cursor="hand2", font=("", 11, "bold"))
        self.btn_ingest.grid(row=1, column=3, padx=(0, 8), pady=(0, 6))

        chunk_options = tk.Frame(grp_kb, bg=Theme.BG_SECONDARY)
        chunk_options.grid(row=2, column=0, columnspan=4, sticky="we", padx=8, pady=(2, 8))
        for col in (1, 3):
            chunk_options.columnconfigure(col, weight=1)

        def add_chunk_param(row: int, col: int, text: str, widget: tk.Widget) -> None:
            tk.Label(
                chunk_options,
                text=text,
                bg=Theme.BG_SECONDARY,
                fg=Theme.TEXT_PRIMARY,
                font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL, "bold"),
            ).grid(row=row, column=col, sticky="e", padx=(0, 5), pady=4)
            widget.grid(row=row, column=col + 1, sticky="w", padx=(0, 14), pady=4)

        self.spin_rag_paragraphs_per_chunk = tk.Spinbox(
            chunk_options,
            from_=1,
            to=12,
            increment=1,
            textvariable=self.rag_paragraphs_per_chunk,
            width=5,
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
        )
        add_chunk_param(0, 0, "\u6bcf\u5757\u6bb5\u843d:", self.spin_rag_paragraphs_per_chunk)

        self.spin_rag_overlap_paragraphs = tk.Spinbox(
            chunk_options,
            from_=0,
            to=11,
            increment=1,
            textvariable=self.rag_overlap_paragraphs,
            width=5,
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
        )
        add_chunk_param(0, 2, "\u91cd\u53e0\u6bb5\u843d:", self.spin_rag_overlap_paragraphs)

        self.spin_rag_long_paragraph_chars = tk.Spinbox(
            chunk_options,
            from_=200,
            to=4000,
            increment=100,
            textvariable=self.rag_long_paragraph_chars,
            width=6,
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
        )
        add_chunk_param(1, 0, "\u8d85\u957f\u5355\u6bb5:", self.spin_rag_long_paragraph_chars)

        kb_options = tk.Frame(grp_kb, bg=Theme.BG_SECONDARY)
        kb_options.grid(row=3, column=0, columnspan=4, sticky="we", padx=8, pady=(0, 8))
        kb_options.columnconfigure(0, weight=1)
        kb_options.columnconfigure(1, weight=1)
        kb_options.columnconfigure(2, weight=1)

        self.chk_model_only = ttk.Checkbutton(
            kb_options,
            text="\u26a1 \u4ec5\u7528\u6a21\u578b\uff08\u4e0d\u68c0\u7d22\u77e5\u8bc6\u5e93\uff09",
            variable=self.model_only,
        )
        self.chk_model_only.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))

        tk.Button(
            kb_options,
            text="\U0001f441\ufe0f \u9884\u89c8\u5185\u5bb9",
            command=self._open_kb_preview,
            bg="#3B82F6",
            fg=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
            cursor="hand2",
            padx=10,
        ).grid(row=1, column=0, sticky="we", padx=(0, 5))
        tk.Button(
            kb_options,
            text="\U0001f4da \u7ba1\u7406\u77e5\u8bc6\u5e93",
            command=self._open_kb_manager,
            bg="#6366F1",
            fg=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
            cursor="hand2",
            padx=10,
        ).grid(row=1, column=1, sticky="we", padx=5)
        self.btn_rebuild_index = tk.Button(
            kb_options,
            text="\U0001f528 \u5b8c\u5168\u91cd\u5efa",
            command=self.on_ingest_rebuild,
            bg="#10B981",
            fg=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
            cursor="hand2",
            padx=10,
        )
        self.btn_rebuild_index.grid(row=1, column=2, sticky="we", padx=(5, 0))

    def _build_generation_params_section(self, scrollable_frame: tk.Frame) -> None:
        """构建生成参数区块。"""
        grp_params = ttk.LabelFrame(scrollable_frame, text="⚙️ 生成参数", padding=(15, 10))
        grp_params.pack(fill="x", padx=15, pady=10)

        self._ensure_story_generation_param_vars()
        self._build_basic_generation_params_row(grp_params)
        self._build_story_generation_mode_selector(grp_params)
        self._build_story_template_controls(grp_params)
        self._build_story_quality_controls(grp_params)

    def _ensure_story_generation_param_vars(self) -> None:
        """确保生成参数相关变量已初始化。"""
        if not hasattr(self, "rag_min_score"):
            self.rag_min_score = tk.DoubleVar(value=0.12)
        if not hasattr(self, "rag_paragraphs_per_chunk"):
            self.rag_paragraphs_per_chunk = tk.IntVar(value=4)
        if not hasattr(self, "rag_overlap_paragraphs"):
            self.rag_overlap_paragraphs = tk.IntVar(value=1)
        if not hasattr(self, "rag_long_paragraph_chars"):
            self.rag_long_paragraph_chars = tk.IntVar(value=800)
        if not hasattr(self, "story_template_key"):
            self.story_template_key = tk.StringVar(value=DEFAULT_STORY_TEMPLATE_KEY)
        if not hasattr(self, "story_template_strategy"):
            self.story_template_strategy = tk.StringVar(value=DEFAULT_STORY_TEMPLATE_STRATEGY)
        if not hasattr(self, "story_creativity_mode"):
            self.story_creativity_mode = tk.StringVar(value=DEFAULT_STORY_CREATIVITY_MODE)
        if not hasattr(self, "story_quality_review_enabled"):
            self.story_quality_review_enabled = tk.BooleanVar(value=True)
        if not hasattr(self, "story_auto_polish_enabled"):
            self.story_auto_polish_enabled = tk.BooleanVar(value=True)
        if not hasattr(self, "story_quality_min_avg"):
            self.story_quality_min_avg = tk.DoubleVar(value=7.4)
        if not hasattr(self, "story_quality_min_dim"):
            self.story_quality_min_dim = tk.DoubleVar(value=6.8)
        if not hasattr(self, "story_outline_alignment_strict"):
            self.story_outline_alignment_strict = tk.BooleanVar(value=True)
        if not hasattr(self, "story_outline_alignment_max_attempts"):
            self.story_outline_alignment_max_attempts = tk.IntVar(value=2)
        if not hasattr(self, "story_global_overview_enabled"):
            self.story_global_overview_enabled = tk.BooleanVar(value=True)
        if not hasattr(self, "story_overview_before_generate"):
            self.story_overview_before_generate = tk.BooleanVar(value=True)
        if not hasattr(self, "story_preview_before_apply"):
            self.story_preview_before_apply = tk.BooleanVar(value=True)
        if not hasattr(self, "story_generation_mode"):
            self.story_generation_mode = tk.StringVar(value=DEFAULT_STORY_GENERATION_MODE)

    def _build_basic_generation_params_row(self, grp_params: ttk.LabelFrame) -> None:
        """Build basic generation parameter controls."""
        params_frame = tk.Frame(grp_params, bg=Theme.BG_SECONDARY)
        params_frame.pack(fill="x", padx=8, pady=8)
        for col in (1, 3):
            params_frame.columnconfigure(col, weight=1)

        def add_param(row: int, col: int, label: str, widget: tk.Widget) -> None:
            tk.Label(
                params_frame,
                text=label,
                bg=Theme.BG_SECONDARY,
                fg=Theme.TEXT_PRIMARY,
                font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL, "bold"),
            ).grid(row=row, column=col, sticky="e", padx=(0, 6), pady=5)
            widget.grid(row=row, column=col + 1, sticky="w", padx=(0, 18), pady=5)

        self.spin_topk = tk.Spinbox(
            params_frame,
            from_=1,
            to=20,
            textvariable=self.top_k,
            width=6,
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
        )
        add_param(0, 0, "TopK:", self.spin_topk)

        self.spin_temp = tk.Spinbox(
            params_frame,
            from_=0.0,
            to=1.5,
            increment=0.1,
            textvariable=self.temperature,
            width=6,
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
        )
        add_param(0, 2, "\u6e29\u5ea6:", self.spin_temp)

        self.spin_len = tk.Spinbox(
            params_frame,
            from_=500,
            to=30000,
            increment=500,
            textvariable=self.target_chars,
            width=8,
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
        )
        add_param(1, 0, "\u76ee\u6807\u5b57\u6570:", self.spin_len)

        self.spin_rag_min_score = tk.Spinbox(
            params_frame,
            from_=0.0,
            to=1.0,
            increment=0.05,
            textvariable=self.rag_min_score,
            width=6,
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
        )
        add_param(1, 2, "RAG\u9608\u503c:", self.spin_rag_min_score)

    def _bind_responsive_wrap(self, label: tk.Label, min_width: int = 240) -> None:
        """Keep long helper text readable when the settings panel is resized."""
        def _update_wrap(event: tk.Event) -> None:
            label.configure(wraplength=max(min_width, event.width - 12))

        label.bind("<Configure>", _update_wrap)

    def _build_select_with_desc_row(
        self,
        grp_params: ttk.LabelFrame,
        label_text: str,
        variable: tk.StringVar,
        values: list[str],
        on_change,
    ) -> tuple[ttk.Combobox, tk.Label]:
        row_frame = tk.Frame(grp_params, bg=Theme.BG_SECONDARY)
        row_frame.pack(fill="x", padx=8, pady=(0, 8))
        row_frame.columnconfigure(1, weight=1)

        tk.Label(
            row_frame,
            text=label_text,
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 4))

        combo = ttk.Combobox(
            row_frame,
            textvariable=variable,
            values=values,
            state="readonly",
            width=22,
        )
        combo.grid(row=0, column=1, sticky="w", pady=(0, 4))
        combo.bind("<<ComboboxSelected>>", on_change)

        desc_label = tk.Label(
            row_frame,
            text="",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_SECONDARY,
            justify="left",
            anchor="w",
        )
        desc_label.grid(row=1, column=0, columnspan=2, sticky="we", pady=(0, 2))
        self._bind_responsive_wrap(desc_label)
        return combo, desc_label

    def _build_story_template_controls(self, grp_params: ttk.LabelFrame) -> None:
        """Build story template, strategy, and creativity controls."""
        self._build_story_template_selector(grp_params)
        self._build_story_template_strategy_selector(grp_params)
        self._build_story_creativity_selector(grp_params)

    def _build_story_generation_mode_selector(self, grp_params: ttk.LabelFrame) -> None:
        """Build the one-click generation mode selector."""
        mode_items = list_story_generation_modes()
        self.story_generation_mode_key_to_label = {
            item["key"]: item["label"] for item in mode_items
        }
        self.story_generation_mode_label_to_key = {
            item["label"]: item["key"] for item in mode_items
        }
        current_mode_key = normalize_story_generation_mode(self.story_generation_mode.get())
        self.story_generation_mode.set(current_mode_key)

        default_label = self.story_generation_mode_key_to_label.get(
            current_mode_key, mode_items[0]["label"]
        )
        self.story_generation_mode_select_var = tk.StringVar(value=default_label)
        self.combo_story_generation_mode, self.story_generation_mode_desc_label = self._build_select_with_desc_row(
            grp_params,
            "\u751f\u6210\u6a21\u5f0f:",
            self.story_generation_mode_select_var,
            list(self.story_generation_mode_label_to_key.keys()),
            self._on_story_generation_mode_changed,
        )
        if hasattr(self, "_update_story_generation_mode_desc"):
            self._update_story_generation_mode_desc()

    def _build_story_template_selector(self, grp_params: ttk.LabelFrame) -> None:
        """Build the story template selector."""
        template_items = list_story_templates()
        self.story_template_key_to_label = {
            item["key"]: item["label"] for item in template_items
        }
        self.story_template_label_to_key = {
            item["label"]: item["key"] for item in template_items
        }
        if self.story_template_key.get() not in self.story_template_key_to_label:
            self.story_template_key.set(DEFAULT_STORY_TEMPLATE_KEY)

        default_label = self.story_template_key_to_label.get(
            self.story_template_key.get(), template_items[0]["label"]
        )
        self.story_template_select_var = tk.StringVar(value=default_label)
        self.combo_story_template, self.story_template_desc_label = self._build_select_with_desc_row(
            grp_params,
            "\u6545\u4e8b\u6a21\u677f:",
            self.story_template_select_var,
            list(self.story_template_label_to_key.keys()),
            self._on_story_template_changed,
        )
        self._update_story_template_desc()

    def _build_story_template_strategy_selector(self, grp_params: ttk.LabelFrame) -> None:
        """Build the template strategy selector."""
        strategy_items = list_story_template_strategies()
        self.story_template_strategy_key_to_label = {
            item["key"]: item["label"] for item in strategy_items
        }
        self.story_template_strategy_label_to_key = {
            item["label"]: item["key"] for item in strategy_items
        }
        current_strategy_key = normalize_story_template_strategy(self.story_template_strategy.get())
        self.story_template_strategy.set(current_strategy_key)

        strategy_default_label = self.story_template_strategy_key_to_label.get(
            current_strategy_key, strategy_items[0]["label"]
        )
        self.story_template_strategy_select_var = tk.StringVar(value=strategy_default_label)
        self.combo_story_template_strategy, self.story_template_strategy_desc_label = self._build_select_with_desc_row(
            grp_params,
            "\u6a21\u677f\u7b56\u7565:",
            self.story_template_strategy_select_var,
            list(self.story_template_strategy_label_to_key.keys()),
            self._on_story_template_strategy_changed,
        )
        self._update_story_template_strategy_desc()

    def _build_story_creativity_selector(self, grp_params: ttk.LabelFrame) -> None:
        """Build the creativity mode selector."""
        creativity_items = list_story_creativity_modes()
        self.story_creativity_key_to_label = {
            item["key"]: item["label"] for item in creativity_items
        }
        self.story_creativity_label_to_key = {
            item["label"]: item["key"] for item in creativity_items
        }
        current_creativity_key = normalize_story_creativity_mode(self.story_creativity_mode.get())
        self.story_creativity_mode.set(current_creativity_key)

        creativity_default_label = self.story_creativity_key_to_label.get(
            current_creativity_key, creativity_items[0]["label"]
        )
        self.story_creativity_select_var = tk.StringVar(value=creativity_default_label)
        self.combo_story_creativity, self.story_creativity_desc_label = self._build_select_with_desc_row(
            grp_params,
            "\u521b\u65b0\u6a21\u5f0f:",
            self.story_creativity_select_var,
            list(self.story_creativity_label_to_key.keys()),
            self._on_story_creativity_mode_changed,
        )
        self._update_story_creativity_mode_desc()

    def _build_story_quality_controls(self, grp_params: ttk.LabelFrame) -> None:
        """Build quality review and outline alignment controls."""
        quality_frame = tk.Frame(grp_params, bg=Theme.BG_SECONDARY)
        quality_frame.pack(fill="x", padx=8, pady=(0, 8))
        quality_frame.columnconfigure(0, weight=1)
        quality_frame.columnconfigure(1, weight=1)

        check_options = [
            ("\u5f00\u542f\u7ae0\u8282\u8d28\u91cf\u8bc4\u5ba1\u4e0e\u81ea\u52a8\u7cbe\u4fee", self.story_quality_review_enabled),
            ("\u5199\u4f5c\u524d\u5148\u786e\u8ba4\u5168\u4e66\u603b\u89c8", self.story_global_overview_enabled),
            ("\u7ae0\u8282\u751f\u6210\u524d\u5148\u51fa\u603b\u89c8\u5e76\u53ef\u6539\u5199", self.story_overview_before_generate),
            ("\u7ae0\u8282\u751f\u6210\u540e\u5148\u9884\u89c8\u518d\u5165\u7a3f", self.story_preview_before_apply),
        ]
        for index, (text, variable) in enumerate(check_options):
            chk = ttk.Checkbutton(quality_frame, text=text, variable=variable)
            chk.grid(row=index // 2, column=index % 2, sticky="w", padx=(0, 18), pady=3)

        threshold_frame = tk.Frame(grp_params, bg=Theme.BG_SECONDARY)
        threshold_frame.pack(fill="x", padx=8, pady=(0, 8))
        for col in (1, 3):
            threshold_frame.columnconfigure(col, weight=1)

        tk.Label(
            threshold_frame,
            text="\u5e73\u5747\u5206\u9608\u503c:",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL, "bold"),
        ).grid(row=0, column=0, sticky="e", padx=(0, 4), pady=4)
        self.spin_story_quality_min_avg = tk.Spinbox(
            threshold_frame,
            from_=1.0,
            to=10.0,
            increment=0.1,
            textvariable=self.story_quality_min_avg,
            width=5,
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
        )
        self.spin_story_quality_min_avg.grid(row=0, column=1, sticky="w", padx=(0, 18), pady=4)

        tk.Label(
            threshold_frame,
            text="\u5355\u9879\u9608\u503c:",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL, "bold"),
        ).grid(row=0, column=2, sticky="e", padx=(0, 4), pady=4)
        self.spin_story_quality_min_dim = tk.Spinbox(
            threshold_frame,
            from_=1.0,
            to=10.0,
            increment=0.1,
            textvariable=self.story_quality_min_dim,
            width=5,
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
        )
        self.spin_story_quality_min_dim.grid(row=0, column=3, sticky="w", padx=(0, 8), pady=4)

        align_frame = tk.Frame(grp_params, bg=Theme.BG_SECONDARY)
        align_frame.pack(fill="x", padx=8, pady=(0, 8))
        align_frame.columnconfigure(0, weight=1)
        self.chk_story_outline_alignment_strict = ttk.Checkbutton(
            align_frame,
            text="\u76ee\u5f55\u5f3a\u7ea6\u675f\u5bf9\u9f50\uff08\u672a\u547d\u4e2d\u9898\u6750/\u951a\u70b9\u65f6\u81ea\u52a8\u91cd\u8bd5\uff09",
            variable=self.story_outline_alignment_strict,
        )
        self.chk_story_outline_alignment_strict.grid(row=0, column=0, sticky="w", padx=(0, 16), pady=(0, 4))
        tk.Label(
            align_frame,
            text="\u6700\u5927\u91cd\u8bd5:",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL, "bold"),
        ).grid(row=1, column=0, sticky="w", pady=(2, 4))
        self.spin_story_outline_alignment_max_attempts = tk.Spinbox(
            align_frame,
            from_=1,
            to=4,
            increment=1,
            textvariable=self.story_outline_alignment_max_attempts,
            width=4,
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
        )
        self.spin_story_outline_alignment_max_attempts.grid(row=1, column=1, sticky="w", padx=(6, 0), pady=(2, 4))

        hint_label = tk.Label(
            grp_params,
            text="\U0001f4a1 \u4f4e\u4e8e\u9608\u503c\u4f1a\u81ea\u52a8\u89e6\u53d1\u7ae0\u8282\u7cbe\u4fee\uff1b\u76ee\u5f55\u5f3a\u7ea6\u675f\u4f1a\u63d0\u5347\u8d34\u9898\u5ea6\uff0c\u4f46\u4f1a\u589e\u52a0\u4e00\u6b21\u5230\u6570\u6b21\u91cd\u8bd5\u8017\u65f6\u3002",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_SECONDARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL),
            justify="left",
            anchor="w",
        )
        hint_label.pack(fill="x", padx=12, pady=(0, 6))
        self._bind_responsive_wrap(hint_label)

