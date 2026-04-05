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
        self.btn_ingest = tk.Button(grp_kb, text="🔨 构建索引", command=self.on_ingest, bg="#10B981", fg=Theme.TEXT_PRIMARY,
                                    relief=tk.FLAT, cursor="hand2", font=("", 11, "bold"))
        self.btn_ingest.grid(row=1, column=3, padx=(0, 8), pady=(0, 6))
        
        # 知识库选项
        kb_options = tk.Frame(grp_kb, bg=Theme.BG_SECONDARY)
        kb_options.grid(row=2, column=0, columnspan=4, sticky="w", padx=8, pady=(0, 8))
        self.chk_model_only = ttk.Checkbutton(kb_options, text="⚡ 仅用模型（不检索知识库）", variable=self.model_only)
        self.chk_model_only.pack(side="left")
        
        # 知识库管理按钮
        tk.Button(kb_options, text="👁️ 预览内容", command=self._open_kb_preview, bg="#3B82F6", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=(20, 5))
        tk.Button(kb_options, text="📚 管理知识库", command=self._open_kb_manager, bg="#6366F1", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=5)

    def _build_generation_params_section(self, scrollable_frame: tk.Frame) -> None:
        """构建生成参数区块。"""
        grp_params = ttk.LabelFrame(scrollable_frame, text="⚙️ 生成参数", padding=(15, 10))
        grp_params.pack(fill="x", padx=15, pady=10)

        self._ensure_story_generation_param_vars()
        self._build_basic_generation_params_row(grp_params)
        self._build_story_template_controls(grp_params)
        self._build_story_quality_controls(grp_params)

    def _ensure_story_generation_param_vars(self) -> None:
        """确保生成参数相关变量已初始化。"""
        if not hasattr(self, "rag_min_score"):
            self.rag_min_score = tk.DoubleVar(value=0.12)
        if not hasattr(self, "story_template_key"):
            self.story_template_key = tk.StringVar(value=DEFAULT_STORY_TEMPLATE_KEY)
        if not hasattr(self, "story_template_strategy"):
            self.story_template_strategy = tk.StringVar(value=DEFAULT_STORY_TEMPLATE_STRATEGY)
        if not hasattr(self, "story_creativity_mode"):
            self.story_creativity_mode = tk.StringVar(value=DEFAULT_STORY_CREATIVITY_MODE)
        if not hasattr(self, "story_quality_review_enabled"):
            self.story_quality_review_enabled = tk.BooleanVar(value=True)
        if not hasattr(self, "story_quality_min_avg"):
            self.story_quality_min_avg = tk.DoubleVar(value=7.4)
        if not hasattr(self, "story_quality_min_dim"):
            self.story_quality_min_dim = tk.DoubleVar(value=6.8)
        if not hasattr(self, "story_outline_alignment_strict"):
            self.story_outline_alignment_strict = tk.BooleanVar(value=True)
        if not hasattr(self, "story_outline_alignment_max_attempts"):
            self.story_outline_alignment_max_attempts = tk.IntVar(value=2)

    def _build_basic_generation_params_row(self, grp_params: ttk.LabelFrame) -> None:
        """构建基础生成参数行。"""
        params_frame = tk.Frame(grp_params, bg=Theme.BG_SECONDARY)
        params_frame.pack(fill="x", padx=8, pady=8)

        tk.Label(params_frame, text="TopK:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).pack(side="left", padx=(0, 5))
        self.spin_topk = tk.Spinbox(params_frame, from_=1, to=20, textvariable=self.top_k, width=6,
                                    bg=Theme.SURFACE, fg=Theme.TEXT_PRIMARY, relief=tk.FLAT)
        self.spin_topk.pack(side="left", padx=(0, 20))

        tk.Label(params_frame, text="温度:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).pack(side="left", padx=(0, 5))
        self.spin_temp = tk.Spinbox(params_frame, from_=0.0, to=1.5, increment=0.1, textvariable=self.temperature,
                                    width=6, bg=Theme.SURFACE, fg=Theme.TEXT_PRIMARY, relief=tk.FLAT)
        self.spin_temp.pack(side="left", padx=(0, 20))

        tk.Label(params_frame, text="目标字数:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).pack(side="left", padx=(0, 5))
        self.spin_len = tk.Spinbox(params_frame, from_=500, to=30000, increment=500, textvariable=self.target_chars,
                                   width=8, bg=Theme.SURFACE, fg=Theme.TEXT_PRIMARY, relief=tk.FLAT)
        self.spin_len.pack(side="left")

        tk.Label(params_frame, text="RAG阈值:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).pack(side="left", padx=(20, 5))
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
        self.spin_rag_min_score.pack(side="left")

    def _build_story_template_controls(self, grp_params: ttk.LabelFrame) -> None:
        """构建故事模版、策略与创新模式控件。"""
        self._build_story_template_selector(grp_params)
        self._build_story_template_strategy_selector(grp_params)
        self._build_story_creativity_selector(grp_params)

    def _build_story_template_selector(self, grp_params: ttk.LabelFrame) -> None:
        """构建故事模版选择控件。"""
        template_frame = tk.Frame(grp_params, bg=Theme.BG_SECONDARY)
        template_frame.pack(fill="x", padx=8, pady=(0, 8))
        tk.Label(
            template_frame,
            text="故事模版:",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_PRIMARY,
            font=("", 11, "bold"),
        ).pack(side="left", padx=(0, 5))

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
        self.combo_story_template = ttk.Combobox(
            template_frame,
            textvariable=self.story_template_select_var,
            values=list(self.story_template_label_to_key.keys()),
            state="readonly",
            width=22,
        )
        self.combo_story_template.pack(side="left", padx=(0, 10))
        self.combo_story_template.bind("<<ComboboxSelected>>", self._on_story_template_changed)

        self.story_template_desc_label = tk.Label(
            template_frame,
            text="",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_SECONDARY,
            justify="left",
            anchor="w",
        )
        self.story_template_desc_label.pack(side="left", fill="x", expand=True)
        self._update_story_template_desc()

    def _build_story_template_strategy_selector(self, grp_params: ttk.LabelFrame) -> None:
        """构建模版策略选择控件。"""
        strategy_items = list_story_template_strategies()
        self.story_template_strategy_key_to_label = {
            item["key"]: item["label"] for item in strategy_items
        }
        self.story_template_strategy_label_to_key = {
            item["label"]: item["key"] for item in strategy_items
        }
        current_strategy_key = normalize_story_template_strategy(self.story_template_strategy.get())
        self.story_template_strategy.set(current_strategy_key)

        strategy_frame = tk.Frame(grp_params, bg=Theme.BG_SECONDARY)
        strategy_frame.pack(fill="x", padx=8, pady=(0, 8))
        tk.Label(
            strategy_frame,
            text="模版策略:",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_PRIMARY,
            font=("", 11, "bold"),
        ).pack(side="left", padx=(0, 5))

        strategy_default_label = self.story_template_strategy_key_to_label.get(
            current_strategy_key, strategy_items[0]["label"]
        )
        self.story_template_strategy_select_var = tk.StringVar(value=strategy_default_label)
        self.combo_story_template_strategy = ttk.Combobox(
            strategy_frame,
            textvariable=self.story_template_strategy_select_var,
            values=list(self.story_template_strategy_label_to_key.keys()),
            state="readonly",
            width=22,
        )
        self.combo_story_template_strategy.pack(side="left", padx=(0, 10))
        self.combo_story_template_strategy.bind(
            "<<ComboboxSelected>>", self._on_story_template_strategy_changed
        )

        self.story_template_strategy_desc_label = tk.Label(
            strategy_frame,
            text="",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_SECONDARY,
            justify="left",
            anchor="w",
        )
        self.story_template_strategy_desc_label.pack(side="left", fill="x", expand=True)
        self._update_story_template_strategy_desc()

    def _build_story_creativity_selector(self, grp_params: ttk.LabelFrame) -> None:
        """构建创新模式选择控件。"""
        creativity_items = list_story_creativity_modes()
        self.story_creativity_key_to_label = {
            item["key"]: item["label"] for item in creativity_items
        }
        self.story_creativity_label_to_key = {
            item["label"]: item["key"] for item in creativity_items
        }
        current_creativity_key = normalize_story_creativity_mode(self.story_creativity_mode.get())
        self.story_creativity_mode.set(current_creativity_key)

        creativity_frame = tk.Frame(grp_params, bg=Theme.BG_SECONDARY)
        creativity_frame.pack(fill="x", padx=8, pady=(0, 8))
        tk.Label(
            creativity_frame,
            text="创新模式:",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_PRIMARY,
            font=("", 11, "bold"),
        ).pack(side="left", padx=(0, 5))

        creativity_default_label = self.story_creativity_key_to_label.get(
            current_creativity_key, creativity_items[0]["label"]
        )
        self.story_creativity_select_var = tk.StringVar(value=creativity_default_label)
        self.combo_story_creativity = ttk.Combobox(
            creativity_frame,
            textvariable=self.story_creativity_select_var,
            values=list(self.story_creativity_label_to_key.keys()),
            state="readonly",
            width=22,
        )
        self.combo_story_creativity.pack(side="left", padx=(0, 10))
        self.combo_story_creativity.bind("<<ComboboxSelected>>", self._on_story_creativity_mode_changed)

        self.story_creativity_desc_label = tk.Label(
            creativity_frame,
            text="",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_SECONDARY,
            justify="left",
            anchor="w",
        )
        self.story_creativity_desc_label.pack(side="left", fill="x", expand=True)
        self._update_story_creativity_mode_desc()

    def _build_story_quality_controls(self, grp_params: ttk.LabelFrame) -> None:
        """构建质量评审与目录强约束控件。"""
        quality_frame = tk.Frame(grp_params, bg=Theme.BG_SECONDARY)
        quality_frame.pack(fill="x", padx=8, pady=(0, 8))

        self.chk_story_quality_review = ttk.Checkbutton(
            quality_frame,
            text="开启章节质量评审与自动精修",
            variable=self.story_quality_review_enabled,
        )
        self.chk_story_quality_review.pack(side="left", padx=(0, 16))

        tk.Label(
            quality_frame,
            text="平均分阈值:",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_PRIMARY,
            font=("", 10, "bold"),
        ).pack(side="left", padx=(0, 4))
        self.spin_story_quality_min_avg = tk.Spinbox(
            quality_frame,
            from_=1.0,
            to=10.0,
            increment=0.1,
            textvariable=self.story_quality_min_avg,
            width=5,
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
        )
        self.spin_story_quality_min_avg.pack(side="left", padx=(0, 12))

        tk.Label(
            quality_frame,
            text="单项阈值:",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_PRIMARY,
            font=("", 10, "bold"),
        ).pack(side="left", padx=(0, 4))
        self.spin_story_quality_min_dim = tk.Spinbox(
            quality_frame,
            from_=1.0,
            to=10.0,
            increment=0.1,
            textvariable=self.story_quality_min_dim,
            width=5,
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY,
            relief=tk.FLAT,
        )
        self.spin_story_quality_min_dim.pack(side="left", padx=(0, 8))

        align_frame = tk.Frame(grp_params, bg=Theme.BG_SECONDARY)
        align_frame.pack(fill="x", padx=8, pady=(0, 8))
        self.chk_story_outline_alignment_strict = ttk.Checkbutton(
            align_frame,
            text="目录强约束对齐（未命中题材/锚点时自动重试）",
            variable=self.story_outline_alignment_strict,
        )
        self.chk_story_outline_alignment_strict.pack(side="left", padx=(0, 16))
        tk.Label(
            align_frame,
            text="最大重试:",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_PRIMARY,
            font=("", 10, "bold"),
        ).pack(side="left", padx=(0, 4))
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
        self.spin_story_outline_alignment_max_attempts.pack(side="left", padx=(0, 8))

        tk.Label(
            grp_params,
            text="💡 低于阈值会自动触发章节精修；目录强约束会提升贴题度，但会增加一次到数次重试耗时。",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_SECONDARY,
            font=("", 9),
        ).pack(anchor="w", padx=12, pady=(0, 6))
    
