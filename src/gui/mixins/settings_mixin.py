"""
统一设置页面模块
将所有配置集中到一个页面
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, END, messagebox

from ..theme import Theme
from .config_modules.model_routing import MODEL_ROUTING_TASKS
from .settings_modules.api_config_persistence_mixin import SettingsApiConfigPersistenceMixin
from .settings_modules.api_test_mixin import SettingsApiTestMixin
from .settings_modules.quick_switch_mixin import SettingsQuickSwitchMixin
from .settings_modules.routing_provider_mixin import SettingsRoutingProviderMixin
from .settings_modules.story_env_mixin import SettingsStoryEnvMixin
from .settings_modules.story_template_mixin import SettingsStoryTemplateMixin
from ..helpers.story_templates import (
    DEFAULT_STORY_TEMPLATE_KEY,
    DEFAULT_STORY_TEMPLATE_STRATEGY,
    get_story_template,
    list_story_template_strategies,
    list_story_templates,
    normalize_story_template_strategy,
)
from ..helpers.story_creativity import (
    DEFAULT_STORY_CREATIVITY_MODE,
    list_story_creativity_modes,
    normalize_story_creativity_mode,
)


class SettingsMixin(
    SettingsStoryTemplateMixin,
    SettingsQuickSwitchMixin,
    SettingsStoryEnvMixin,
    SettingsApiTestMixin,
    SettingsApiConfigPersistenceMixin,
    SettingsRoutingProviderMixin,
):
    """统一设置页面功能"""
    
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
            except:
                pass

        def _cancel_guard(_event=None):
            job = getattr(entry_widget, "_dark_guard_job", None)
            try:
                if job:
                    entry_widget.after_cancel(job)
            except:
                pass
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
                except:
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
        show: str | None = None,
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

    def _build_advanced_settings_tab(self, scrollable_frame: tk.Frame) -> None:
        """构建“高级”标签页内容。"""
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
        
        tk.Label(about_frame, text="AI Story Creator Pro v2.0", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY,
                 font=("", 14, "bold")).pack(anchor="w")
        tk.Label(about_frame, text="智能故事创作平台 - 支持多种AI提供商", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY).pack(anchor="w", pady=2)
        tk.Label(about_frame, text="支持的AI: OpenAI, Gemini, Claude, DeepSeek, 通义, 文心, 智谱等", 
                 bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY, font=("", 10)).pack(anchor="w", pady=2)
    
    def _set_dark_theme(self):
        """设置深色主题"""
        from ..theme import theme_manager
        theme_manager.set_dark()
        messagebox.showinfo("提示", "已切换到深色主题")
    
    def _set_light_theme(self):
        """设置浅色主题"""
        from ..theme import theme_manager
        theme_manager.set_light()
        messagebox.showinfo("提示", "已切换到浅色主题")
    
    def _import_config_ui(self):
        """导入配置UI"""
        if hasattr(self, 'import_config'):
            self.import_config()
    
    def _export_config_ui(self):
        """导出配置UI（不含密钥）"""
        if hasattr(self, 'export_config'):
            self.export_config(include_keys=False)
    
    def _export_config_with_keys(self):
        """导出配置（含密钥）"""
        if messagebox.askyesno("确认", "导出文件将包含API密钥，请注意保管！\n确定继续吗？"):
            if hasattr(self, 'export_config'):
                self.export_config(include_keys=True)
    
    def _clear_cache_ui(self):
        """清除缓存UI"""
        if messagebox.askyesno("确认", "确定要清除所有缓存吗？"):
            if hasattr(self, 'clear_cache'):
                self.clear_cache()
            self._update_cache_size()
    
    def _update_cache_size(self):
        """更新缓存大小显示"""
        try:
            from pathlib import Path
            cache_dir = Path("cache")
            if cache_dir.exists():
                total_size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file())
                if total_size < 1024:
                    size_str = f"{total_size} B"
                elif total_size < 1024 * 1024:
                    size_str = f"{total_size / 1024:.1f} KB"
                else:
                    size_str = f"{total_size / (1024*1024):.1f} MB"
            else:
                size_str = "0 B"
            
            if hasattr(self, 'cache_size_label'):
                self.cache_size_label.config(text=f"缓存大小: {size_str}")
        except Exception:
            pass
    
    def _show_shortcuts_ui(self):
        """显示快捷键帮助"""
        if hasattr(self, '_show_shortcuts_help'):
            self._show_shortcuts_help()
        else:
            shortcuts_text = """快捷键列表:

文件操作:
  Ctrl+N: 新建项目
  Ctrl+O: 打开项目
  Ctrl+S: 保存项目
  Ctrl+E: 导出项目
  Ctrl+I: 导入项目

生成操作:
  Ctrl+G: 生成大纲
  Ctrl+Shift+G: 生成故事
  F5: 生成选中章节

视图切换:
  Ctrl+1: 项目页
  Ctrl+2: 故事页
  Ctrl+3: 图片页
  Ctrl+4: 设置页
  Ctrl+T: 切换主题

其他:
  F1: 显示帮助
  Ctrl+Z: 撤销
  Ctrl+Y: 重做"""
            messagebox.showinfo("快捷键帮助", shortcuts_text)
    
    def _open_kb_preview(self):
        """打开知识库预览"""
        if hasattr(self, 'open_kb_preview'):
            self.open_kb_preview()
    
    def _open_kb_manager(self):
        """打开知识库管理"""
        if hasattr(self, 'open_kb_manager'):
            self.open_kb_manager()
    
    def _load_settings_values(self):
        """加载当前配置值到设置页面"""
        # 从文件加载保存的配置
        if hasattr(self, '_load_api_config_from_file'):
            self._load_api_config_from_file()

        # 加载模型路由
        if hasattr(self, '_ensure_model_routing_loaded'):
            self._ensure_model_routing_loaded()
        
        # 加载故事API配置
        self._on_settings_provider_change()
        
        # 加载图片API配置
        self._on_settings_img_provider_change()

        # 加载模型路由到UI
        if hasattr(self, '_load_model_routing_to_ui'):
            self._load_model_routing_to_ui()

        # 加载快速 API 切换配置
        if hasattr(self, '_load_quick_api_switch'):
            self._load_quick_api_switch()

        if hasattr(self, "_update_story_template_desc"):
            self._update_story_template_desc()
        if hasattr(self, "_update_story_template_strategy_desc"):
            self._update_story_template_strategy_desc()
        if hasattr(self, "_update_story_creativity_mode_desc"):
            self._update_story_creativity_mode_desc()
