"""
统一设置页面模块
将所有配置集中到一个页面
"""

from __future__ import annotations

import os
import re
import threading
import tkinter as tk
from tkinter import ttk, END, messagebox
from pathlib import Path
from dotenv import load_dotenv

from ..theme import Theme
from .config_modules.model_routing import MODEL_ROUTING_TASKS
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


class SettingsMixin:
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
    
    def _build_settings_page(self) -> None:
        """构建统一设置页面"""
        # 使用分区标签页，让设置结构更清晰
        container = tk.Frame(self.page_settings, bg=Theme.BG_SECONDARY)
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        settings_notebook = ttk.Notebook(container)
        settings_notebook.pack(fill="both", expand=True)
        
        def _make_scroll_tab(title: str):
            tab = tk.Frame(settings_notebook, bg=Theme.BG_SECONDARY)
            settings_notebook.add(tab, text=title)
            
            canvas = tk.Canvas(tab, bg=Theme.BG_SECONDARY, highlightthickness=0)
            scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
            inner = tk.Frame(canvas, bg=Theme.BG_SECONDARY)
            
            inner.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
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
        
        api_frame = _make_scroll_tab("API 配置")
        routing_frame = _make_scroll_tab("模型路由")
        data_frame = _make_scroll_tab("知识库 & 参数")
        advanced_frame = _make_scroll_tab("高级")
        
        scrollable_frame = data_frame
        # 页面说明
        data_tip = ttk.LabelFrame(scrollable_frame, text="🧭 使用说明", padding=(12, 8))
        data_tip.pack(fill="x", padx=15, pady=(10, 6))
        tk.Label(data_tip, text="1. 先设置知识库数据目录与索引目录", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY).pack(anchor="w")
        tk.Label(data_tip, text="2. 点击“构建索引”后即可使用检索增强", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY).pack(anchor="w")
        tk.Label(data_tip, text="3. 生成参数会影响默认创作长度与随机性", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY).pack(anchor="w")
        # ========== 1. 知识库配置 ==========
        grp_kb = ttk.LabelFrame(scrollable_frame, text="📚 知识库配置", padding=(15, 10))
        grp_kb.pack(fill="x", padx=15, pady=(15, 10))
        grp_kb.columnconfigure(1, weight=1)
        
        # 数据目录
        tk.Label(grp_kb, text="数据目录:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.entry_data = tk.Entry(grp_kb, textvariable=self.data_dir, bg=Theme.SURFACE, fg=Theme.TEXT_PRIMARY, 
                                   insertbackground=Theme.TEXT_PRIMARY, relief=tk.FLAT)
        self.entry_data.grid(row=0, column=1, sticky="we", padx=8)
        self._fix_entry_colors(self.entry_data)
        tk.Button(grp_kb, text="选择...", command=self.choose_data, bg="#374151", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2").grid(row=0, column=2, padx=(4, 8), pady=6)
        tk.Button(grp_kb, text="一键选择库", command=self.choose_library_quick, bg="#6366F1", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2").grid(row=0, column=3, padx=(0, 8), pady=6)
        
        # 索引目录
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
        
        # ========== 2. 生成参数 ==========
        grp_params = ttk.LabelFrame(scrollable_frame, text="⚙️ 生成参数", padding=(15, 10))
        grp_params.pack(fill="x", padx=15, pady=10)
        
        params_frame = tk.Frame(grp_params, bg=Theme.BG_SECONDARY)
        params_frame.pack(fill="x", padx=8, pady=8)
        
        # TopK
        tk.Label(params_frame, text="TopK:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).pack(side="left", padx=(0, 5))
        self.spin_topk = tk.Spinbox(params_frame, from_=1, to=20, textvariable=self.top_k, width=6,
                                    bg=Theme.SURFACE, fg=Theme.TEXT_PRIMARY, relief=tk.FLAT)
        self.spin_topk.pack(side="left", padx=(0, 20))
        
        # 温度
        tk.Label(params_frame, text="温度:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).pack(side="left", padx=(0, 5))
        self.spin_temp = tk.Spinbox(params_frame, from_=0.0, to=1.5, increment=0.1, textvariable=self.temperature, 
                                    width=6, bg=Theme.SURFACE, fg=Theme.TEXT_PRIMARY, relief=tk.FLAT)
        self.spin_temp.pack(side="left", padx=(0, 20))
        
        # 目标字数
        tk.Label(params_frame, text="目标字数:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).pack(side="left", padx=(0, 5))
        self.spin_len = tk.Spinbox(params_frame, from_=500, to=30000, increment=500, textvariable=self.target_chars,
                                   width=8, bg=Theme.SURFACE, fg=Theme.TEXT_PRIMARY, relief=tk.FLAT)
        self.spin_len.pack(side="left")

        if not hasattr(self, "rag_min_score"):
            self.rag_min_score = tk.DoubleVar(value=0.12)
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

        if not hasattr(self, "story_template_key"):
            self.story_template_key = tk.StringVar(value=DEFAULT_STORY_TEMPLATE_KEY)

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

        if not hasattr(self, "story_template_strategy"):
            self.story_template_strategy = tk.StringVar(value=DEFAULT_STORY_TEMPLATE_STRATEGY)

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

        if not hasattr(self, "story_creativity_mode"):
            self.story_creativity_mode = tk.StringVar(value="stable")

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

        if not hasattr(self, "story_quality_review_enabled"):
            self.story_quality_review_enabled = tk.BooleanVar(value=True)
        if not hasattr(self, "story_quality_min_avg"):
            self.story_quality_min_avg = tk.DoubleVar(value=7.4)
        if not hasattr(self, "story_quality_min_dim"):
            self.story_quality_min_dim = tk.DoubleVar(value=6.8)

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

        tk.Label(
            grp_params,
            text="💡 低于阈值会自动触发章节精修；想更自然细腻可适当提高阈值。",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_SECONDARY,
            font=("", 9),
        ).pack(anchor="w", padx=12, pady=(0, 6))
        
        scrollable_frame = api_frame
        # 页面说明
        api_tip = ttk.LabelFrame(scrollable_frame, text="✅ 快速配置", padding=(12, 8))
        api_tip.pack(fill="x", padx=15, pady=(10, 6))
        tk.Label(api_tip, text="1. 选择提供商 → 填写 Key/Base URL → 选择模型", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY).pack(anchor="w")
        tk.Label(api_tip, text="2. 点击“测试连接”验证可用性", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY).pack(anchor="w")
        tk.Label(api_tip, text="3. 点击“保存配置”，后续生成将直接使用该配置", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY).pack(anchor="w")
        # ========== 3. 故事API配置 ==========
        grp_story_api = ttk.LabelFrame(scrollable_frame, text="📝 故事生成 API", padding=(15, 10))
        grp_story_api.pack(fill="x", padx=15, pady=10)
        grp_story_api.columnconfigure(1, weight=1)
        
        # 提供商选择
        tk.Label(grp_story_api, text="API提供商:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).grid(row=0, column=0, sticky="e", padx=(8, 4), pady=8)
        self.settings_api_provider = tk.StringVar(value="DeepSeek")
        
        provider_names = list(self.api_providers.keys()) if hasattr(self, 'api_providers') else ["DeepSeek"]
        if hasattr(self, 'api_presets'):
            for name in self.api_presets.keys():
                if name not in provider_names:
                    provider_names.append(name)
        self.settings_combo_provider = ttk.Combobox(grp_story_api, textvariable=self.settings_api_provider,
                                                     values=provider_names, state="readonly", width=25)
        self.settings_combo_provider.grid(row=0, column=1, sticky="w", padx=(0, 8), pady=8)
        self.settings_combo_provider.bind("<<ComboboxSelected>>", self._on_settings_provider_change)
        
        # 模型选择
        tk.Label(grp_story_api, text="模型:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).grid(row=1, column=0, sticky="e", padx=(8, 4), pady=4)
        self.settings_model_var = tk.StringVar(value="deepseek-chat")
        self.settings_combo_model = ttk.Combobox(grp_story_api, textvariable=self.settings_model_var,
                                                  values=["deepseek-chat"], state="normal", width=35)
        self.settings_combo_model.grid(row=1, column=1, sticky="w", padx=(0, 8), pady=4)
        tk.Label(grp_story_api, text="(可手动输入)", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY, font=("", 9)).grid(row=1, column=2, sticky="w")
        
        # API Key
        tk.Label(grp_story_api, text="API Key:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).grid(row=2, column=0, sticky="e", padx=(8, 4), pady=4)
        self.settings_api_key = tk.Entry(grp_story_api, show="•", width=50, bg=Theme.SURFACE, fg=Theme.TEXT_PRIMARY,
                                         insertbackground=Theme.TEXT_PRIMARY, relief=tk.FLAT, highlightthickness=1,
                                         highlightbackground=Theme.BORDER, highlightcolor=Theme.BORDER_FOCUS,
                                         disabledbackground=Theme.SURFACE, disabledforeground=Theme.TEXT_SECONDARY,
                                         readonlybackground=Theme.SURFACE)
        self.settings_api_key.grid(row=2, column=1, sticky="w", padx=(0, 8), pady=4)
        # 强制保持深色主题，防止焦点时变白
        self._fix_entry_colors(self.settings_api_key)
        
        # 显示/隐藏密钥按钮
        self.show_key_var = tk.BooleanVar(value=False)
        tk.Checkbutton(grp_story_api, text="显示", variable=self.show_key_var, 
                       command=self._toggle_key_visibility, bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY,
                       selectcolor=Theme.BG_SECONDARY, activebackground=Theme.BG_SECONDARY).grid(row=2, column=2, padx=4)
        
        # Base URL（可编辑，用于自定义）
        tk.Label(grp_story_api, text="Base URL:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).grid(row=3, column=0, sticky="e", padx=(8, 4), pady=4)
        self.settings_base_url = tk.Entry(grp_story_api, width=50, bg=Theme.SURFACE, fg=Theme.TEXT_PRIMARY,
                                          insertbackground=Theme.TEXT_PRIMARY, relief=tk.FLAT, highlightthickness=1,
                                          highlightbackground=Theme.BORDER, highlightcolor=Theme.BORDER_FOCUS,
                                          disabledbackground=Theme.SURFACE, disabledforeground=Theme.TEXT_SECONDARY,
                                          readonlybackground=Theme.SURFACE)
        self.settings_base_url.grid(row=3, column=1, sticky="w", padx=(0, 8), pady=4)
        self._fix_entry_colors(self.settings_base_url)
        
        # 自定义模型输入（仅当选择自定义时显示）
        tk.Label(grp_story_api, text="自定义模型:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY).grid(row=4, column=0, sticky="e", padx=(8, 4), pady=4)
        self.settings_custom_model = tk.Entry(grp_story_api, width=50, bg=Theme.SURFACE, fg=Theme.TEXT_PRIMARY,
                                               insertbackground=Theme.TEXT_PRIMARY, relief=tk.FLAT, highlightthickness=1,
                                               highlightbackground=Theme.BORDER, highlightcolor=Theme.BORDER_FOCUS,
                                               disabledbackground=Theme.SURFACE, disabledforeground=Theme.TEXT_SECONDARY,
                                               readonlybackground=Theme.SURFACE)
        self.settings_custom_model.grid(row=4, column=1, sticky="w", padx=(0, 8), pady=4)
        self._fix_entry_colors(self.settings_custom_model)
        tk.Label(grp_story_api, text="(仅自定义时使用)", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY, font=("", 9)).grid(row=4, column=2, sticky="w")
        
        # 按钮
        btn_frame = tk.Frame(grp_story_api, bg=Theme.BG_SECONDARY)
        btn_frame.grid(row=5, column=0, columnspan=3, pady=(10, 5))
        
        tk.Button(btn_frame, text="🔍 测试连接", command=self._test_story_api, bg="#3B82F6", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, padx=15, pady=6, cursor="hand2").pack(side="left", padx=5)
        tk.Button(btn_frame, text="💾 保存配置", command=self._save_story_api_settings, bg="#10B981", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, padx=15, pady=6, cursor="hand2").pack(side="left", padx=5)
        
        # ========== 4. 图片API配置 ==========
        grp_img_api = ttk.LabelFrame(scrollable_frame, text="🎨 图片生成 API", padding=(15, 10))
        grp_img_api.pack(fill="x", padx=15, pady=10)
        grp_img_api.columnconfigure(1, weight=1)
        
        # 图片API提供商
        tk.Label(grp_img_api, text="API提供商:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).grid(row=0, column=0, sticky="e", padx=(8, 4), pady=8)
        self.settings_img_provider = tk.StringVar(value="OpenAI (DALL-E)")
        
        img_provider_names = list(self.img_api_providers.keys()) if hasattr(self, 'img_api_providers') else ["OpenAI (DALL-E)"]
        self.settings_combo_img_provider = ttk.Combobox(grp_img_api, textvariable=self.settings_img_provider,
                                                         values=img_provider_names, state="readonly", width=25)
        self.settings_combo_img_provider.grid(row=0, column=1, sticky="w", padx=(0, 8), pady=8)
        self.settings_combo_img_provider.bind("<<ComboboxSelected>>", self._on_settings_img_provider_change)
        
        # 图片模型选择
        tk.Label(grp_img_api, text="模型:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).grid(row=1, column=0, sticky="e", padx=(8, 4), pady=4)
        self.settings_img_model_var = tk.StringVar(value="dall-e-3")
        self.settings_combo_img_model = ttk.Combobox(grp_img_api, textvariable=self.settings_img_model_var,
                                                      values=["dall-e-3"], state="normal", width=35)
        self.settings_combo_img_model.grid(row=1, column=1, sticky="w", padx=(0, 8), pady=4)
        tk.Label(grp_img_api, text="(可手动输入)", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY, font=("", 9)).grid(row=1, column=2, sticky="w")
        
        # 图片API Key
        tk.Label(grp_img_api, text="API Key:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).grid(row=2, column=0, sticky="e", padx=(8, 4), pady=4)
        self.settings_img_api_key = tk.Entry(grp_img_api, show="•", width=50, bg=Theme.SURFACE, fg=Theme.TEXT_PRIMARY,
                                              insertbackground=Theme.TEXT_PRIMARY, relief=tk.FLAT, highlightthickness=1,
                                              highlightbackground=Theme.BORDER, highlightcolor=Theme.BORDER_FOCUS,
                                              disabledbackground=Theme.SURFACE, disabledforeground=Theme.TEXT_SECONDARY,
                                              readonlybackground=Theme.SURFACE)
        self.settings_img_api_key.grid(row=2, column=1, sticky="w", padx=(0, 8), pady=4)
        self._fix_entry_colors(self.settings_img_api_key)
        
        # 显示/隐藏密钥
        self.show_img_key_var = tk.BooleanVar(value=False)
        tk.Checkbutton(grp_img_api, text="显示", variable=self.show_img_key_var,
                       command=self._toggle_img_key_visibility, bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY,
                       selectcolor=Theme.BG_SECONDARY, activebackground=Theme.BG_SECONDARY).grid(row=2, column=2, padx=4)
        
        # 图片Base URL
        tk.Label(grp_img_api, text="Base URL:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).grid(row=3, column=0, sticky="e", padx=(8, 4), pady=4)
        self.settings_img_base_url = tk.Entry(grp_img_api, width=50, bg=Theme.SURFACE, fg=Theme.TEXT_PRIMARY,
                                               insertbackground=Theme.TEXT_PRIMARY, relief=tk.FLAT, highlightthickness=1,
                                               highlightbackground=Theme.BORDER, highlightcolor=Theme.BORDER_FOCUS,
                                               disabledbackground=Theme.SURFACE, disabledforeground=Theme.TEXT_SECONDARY,
                                               readonlybackground=Theme.SURFACE)
        self.settings_img_base_url.grid(row=3, column=1, sticky="w", padx=(0, 8), pady=4)
        self._fix_entry_colors(self.settings_img_base_url)
        
        # 自定义模型
        tk.Label(grp_img_api, text="自定义模型:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY).grid(row=4, column=0, sticky="e", padx=(8, 4), pady=4)
        self.settings_img_custom_model = tk.Entry(grp_img_api, width=50, bg=Theme.SURFACE, fg=Theme.TEXT_PRIMARY,
                                                   insertbackground=Theme.TEXT_PRIMARY, relief=tk.FLAT, highlightthickness=1,
                                                   highlightbackground=Theme.BORDER, highlightcolor=Theme.BORDER_FOCUS,
                                                   disabledbackground=Theme.SURFACE, disabledforeground=Theme.TEXT_SECONDARY,
                                                   readonlybackground=Theme.SURFACE)
        self.settings_img_custom_model.grid(row=4, column=1, sticky="w", padx=(0, 8), pady=4)
        self._fix_entry_colors(self.settings_img_custom_model)
        tk.Label(grp_img_api, text="(仅自定义时使用)", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY, font=("", 9)).grid(row=4, column=2, sticky="w")
        
        # 按钮
        img_btn_frame = tk.Frame(grp_img_api, bg=Theme.BG_SECONDARY)
        img_btn_frame.grid(row=5, column=0, columnspan=3, pady=(10, 5))
        
        tk.Button(img_btn_frame, text="🔍 测试连接", command=self._test_img_api, bg="#3B82F6", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, padx=15, pady=6, cursor="hand2").pack(side="left", padx=5)
        tk.Button(img_btn_frame, text="💾 保存配置", command=self._save_img_api_settings, bg="#10B981", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, padx=15, pady=6, cursor="hand2").pack(side="left", padx=5)
        
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

        scrollable_frame = routing_frame
        # ========== 6. 模型路由 ==========
        grp_routing = ttk.LabelFrame(scrollable_frame, text="🧭 模型路由", padding=(15, 10))
        grp_routing.pack(fill="x", padx=15, pady=(10, 10))
        grp_routing.columnconfigure(0, weight=1)

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

        self.model_routing_advanced_frame = tk.Frame(grp_routing, bg=Theme.BG_SECONDARY)
        self.model_routing_advanced_frame.grid(row=4, column=0, sticky="we")
        self.model_routing_advanced_frame.columnconfigure(2, weight=1)

        # 记录路由变量与控件
        self.model_route_vars = {}
        provider_names = list(self.api_providers.keys()) if hasattr(self, 'api_providers') else ["DeepSeek"]

        for idx, (task_key, task_label) in enumerate(MODEL_ROUTING_TASKS):
            row = idx
            tk.Label(self.model_routing_advanced_frame, text=task_label, bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY,
                     font=("", 10, "bold")).grid(row=row, column=0, sticky="e", padx=(8, 6), pady=4)

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

            tk.Label(self.model_routing_advanced_frame, text="(可手动输入)", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY,
                     font=("", 9)).grid(row=row, column=3, sticky="w")

            combo_provider.bind("<<ComboboxSelected>>", lambda e, k=task_key: self._on_route_provider_change(k))

            self.model_route_vars[task_key] = {
                "provider_var": provider_var,
                "model_var": model_var,
                "combo_model": combo_model,
                "task_key": task_key,
            }

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
        self._toggle_model_routing_advanced_ui(False)

        scrollable_frame = api_frame
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
        
        scrollable_frame = advanced_frame
        # ========== 7. 高级选项 ==========
        grp_advanced = ttk.LabelFrame(scrollable_frame, text="🔧 高级选项", padding=(15, 10))
        grp_advanced.pack(fill="x", padx=15, pady=(10, 10))
        
        advanced_frame = tk.Frame(grp_advanced, bg=Theme.BG_SECONDARY)
        advanced_frame.pack(fill="x", padx=8, pady=8)
        
        # 主题切换
        theme_frame = tk.Frame(advanced_frame, bg=Theme.BG_SECONDARY)
        theme_frame.pack(fill="x", pady=5)
        tk.Label(theme_frame, text="界面主题:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).pack(side="left")
        tk.Button(theme_frame, text="🌙 深色主题", command=self._set_dark_theme, bg="#374151", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=(10, 5))
        tk.Button(theme_frame, text="☀️ 浅色主题", command=self._set_light_theme, bg="#F1F5F9", fg="#1E293B",
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=5)
        
        # 配置导入导出
        config_frame = tk.Frame(advanced_frame, bg=Theme.BG_SECONDARY)
        config_frame.pack(fill="x", pady=5)
        tk.Label(config_frame, text="配置管理:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).pack(side="left")
        tk.Button(config_frame, text="📥 导入配置", command=self._import_config_ui, bg="#3B82F6", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=(10, 5))
        tk.Button(config_frame, text="📤 导出配置", command=self._export_config_ui, bg="#10B981", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=5)
        tk.Button(config_frame, text="📤 导出(含密钥)", command=self._export_config_with_keys, bg="#F59E0B", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=5)
        
        # 缓存管理
        cache_frame = tk.Frame(advanced_frame, bg=Theme.BG_SECONDARY)
        cache_frame.pack(fill="x", pady=5)
        tk.Label(cache_frame, text="缓存管理:", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).pack(side="left")
        tk.Button(cache_frame, text="🗑️ 清除缓存", command=self._clear_cache_ui, bg="#EF4444", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=(10, 5))
        self.cache_size_label = tk.Label(cache_frame, text="缓存大小: 计算中...", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY)
        self.cache_size_label.pack(side="left", padx=10)
        self.after(500, self._update_cache_size)
        
        # 快捷键提示
        shortcut_frame = tk.Frame(advanced_frame, bg=Theme.BG_SECONDARY)
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
        
        # 加载当前配置
        self._load_settings_values()
    
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

    def _on_story_template_changed(self, _event=None):
        label = self.story_template_select_var.get().strip() if hasattr(self, "story_template_select_var") else ""
        key = ""
        if hasattr(self, "story_template_label_to_key"):
            key = self.story_template_label_to_key.get(label, "")
        if not key:
            key = DEFAULT_STORY_TEMPLATE_KEY
        if hasattr(self, "story_template_key"):
            self.story_template_key.set(key)
        self._update_story_template_desc()
        self._persist_story_template_selection()

    def _update_story_template_desc(self):
        if not hasattr(self, "story_template_desc_label"):
            return
        key = self.story_template_key.get().strip() if hasattr(self, "story_template_key") else DEFAULT_STORY_TEMPLATE_KEY
        template = get_story_template(key)
        label = template.get("label", key)
        desc = template.get("description", "")
        self.story_template_desc_label.config(text=f"{label}: {desc}")

    def _persist_story_template_selection(self):
        try:
            from pathlib import Path
            from dotenv import find_dotenv, set_key

            key = self.story_template_key.get().strip() if hasattr(self, "story_template_key") else DEFAULT_STORY_TEMPLATE_KEY
            if not key:
                key = DEFAULT_STORY_TEMPLATE_KEY
            env_path_str = find_dotenv(usecwd=True)
            env_path = Path(env_path_str) if env_path_str else Path.cwd() / ".env"
            env_path.touch(exist_ok=True)
            set_key(str(env_path), "STORY_TEMPLATE_KEY", key)
        except Exception as e:
            if hasattr(self, "settings_log"):
                self.settings_log.insert(END, f"⚠ 保存故事模版失败: {e}\n")

    def _on_story_template_strategy_changed(self, _event=None):
        label = (
            self.story_template_strategy_select_var.get().strip()
            if hasattr(self, "story_template_strategy_select_var")
            else ""
        )
        strategy = ""
        if hasattr(self, "story_template_strategy_label_to_key"):
            strategy = self.story_template_strategy_label_to_key.get(label, "")
        strategy = normalize_story_template_strategy(strategy or DEFAULT_STORY_TEMPLATE_STRATEGY)
        if hasattr(self, "story_template_strategy"):
            self.story_template_strategy.set(strategy)
        self._update_story_template_strategy_desc()
        self._persist_story_template_strategy()

    def _update_story_template_strategy_desc(self):
        if not hasattr(self, "story_template_strategy_desc_label"):
            return
        strategy_key = DEFAULT_STORY_TEMPLATE_STRATEGY
        if hasattr(self, "story_template_strategy"):
            strategy_key = normalize_story_template_strategy(self.story_template_strategy.get())
        for item in list_story_template_strategies():
            if item.get("key") == strategy_key:
                self.story_template_strategy_desc_label.config(
                    text=f"{item.get('label', strategy_key)}: {item.get('description', '')}"
                )
                return
        self.story_template_strategy_desc_label.config(text=strategy_key)

    def _persist_story_template_strategy(self):
        try:
            from pathlib import Path
            from dotenv import find_dotenv, set_key

            strategy = DEFAULT_STORY_TEMPLATE_STRATEGY
            if hasattr(self, "story_template_strategy"):
                strategy = normalize_story_template_strategy(self.story_template_strategy.get())
                self.story_template_strategy.set(strategy)
            env_path_str = find_dotenv(usecwd=True)
            env_path = Path(env_path_str) if env_path_str else Path.cwd() / ".env"
            env_path.touch(exist_ok=True)
            set_key(str(env_path), "STORY_TEMPLATE_STRATEGY", strategy)
        except Exception as e:
            if hasattr(self, "settings_log"):
                self.settings_log.insert(END, f"⚠ 保存模版策略失败: {e}\n")

    def _on_story_creativity_mode_changed(self, _event=None):
        label = self.story_creativity_select_var.get().strip() if hasattr(self, "story_creativity_select_var") else ""
        mode = ""
        if hasattr(self, "story_creativity_label_to_key"):
            mode = self.story_creativity_label_to_key.get(label, "")
        mode = normalize_story_creativity_mode(mode or DEFAULT_STORY_CREATIVITY_MODE)
        if hasattr(self, "story_creativity_mode"):
            self.story_creativity_mode.set(mode)
        self._update_story_creativity_mode_desc()
        self._persist_story_creativity_mode()

    def _update_story_creativity_mode_desc(self):
        if not hasattr(self, "story_creativity_desc_label"):
            return
        mode_key = DEFAULT_STORY_CREATIVITY_MODE
        if hasattr(self, "story_creativity_mode"):
            mode_key = normalize_story_creativity_mode(self.story_creativity_mode.get())
        for item in list_story_creativity_modes():
            if item.get("key") == mode_key:
                self.story_creativity_desc_label.config(
                    text=f"{item.get('label', mode_key)}: {item.get('description', '')}"
                )
                return
        self.story_creativity_desc_label.config(text=mode_key)

    def _persist_story_creativity_mode(self):
        try:
            from pathlib import Path
            from dotenv import find_dotenv, set_key

            mode = DEFAULT_STORY_CREATIVITY_MODE
            if hasattr(self, "story_creativity_mode"):
                mode = normalize_story_creativity_mode(self.story_creativity_mode.get())
                self.story_creativity_mode.set(mode)
            env_path_str = find_dotenv(usecwd=True)
            env_path = Path(env_path_str) if env_path_str else Path.cwd() / ".env"
            env_path.touch(exist_ok=True)
            set_key(str(env_path), "STORY_CREATIVITY_MODE", mode)
        except Exception as e:
            if hasattr(self, "settings_log"):
                self.settings_log.insert(END, f"⚠ 保存创新模式失败: {e}\n")

    def _load_model_routing_from_file(self) -> None:
        """从文件加载模型路由配置"""
        try:
            import json
            from pathlib import Path

            path = Path("model_routing.json")
            if not path.exists():
                self.model_routing = {}
                self.model_routing_meta = {}
                self._model_routing_loaded = True
                return

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                meta = data.get("__meta__", {})
                self.model_routing_meta = meta if isinstance(meta, dict) else {}
                self.model_routing = {
                    k: v
                    for k, v in data.items()
                    if k != "__meta__" and isinstance(v, dict)
                }
            else:
                self.model_routing = {}
                self.model_routing_meta = {}
            self._model_routing_loaded = True
        except Exception:
            self.model_routing = {}
            self.model_routing_meta = {}
            self._model_routing_loaded = True

    def _save_model_routing_to_file(self) -> None:
        """保存模型路由配置到文件"""
        try:
            import json

            routing = self.model_routing if isinstance(getattr(self, "model_routing", {}), dict) else {}
            payload = dict(routing)
            meta = self.model_routing_meta if isinstance(getattr(self, "model_routing_meta", {}), dict) else {}
            if meta:
                payload["__meta__"] = meta
            with open("model_routing.json", "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception:
            # 路由保存失败不应阻断主流程
            pass

    def _ensure_model_routing_loaded(self) -> None:
        """确保模型路由已加载并包含默认任务键"""
        if getattr(self, "_model_routing_loaded", False):
            if not isinstance(getattr(self, "model_routing", None), dict):
                self.model_routing = {}
            if not isinstance(getattr(self, "model_routing_meta", None), dict):
                self.model_routing_meta = {}
            return

        self._load_model_routing_from_file()
        if not isinstance(getattr(self, "model_routing", None), dict):
            self.model_routing = {}
        if not isinstance(getattr(self, "model_routing_meta", None), dict):
            self.model_routing_meta = {}

        for task_key, _label in MODEL_ROUTING_TASKS:
            if task_key not in self.model_routing:
                self.model_routing[task_key] = {"provider": "", "model": ""}

        self._model_routing_loaded = True

    def _get_task_route(self, task_key: str) -> dict:
        """获取任务路由配置"""
        self._ensure_model_routing_loaded()
        route = self.model_routing.get(task_key, {}) if isinstance(self.model_routing, dict) else {}
        return route if isinstance(route, dict) else {}

    def _resolve_task_api(self, task_key: str, fallback_provider: str | None = None, fallback_model: str | None = None) -> dict:
        """解析任务应使用的 API 配置（provider/key/base_url/model）"""
        self._ensure_model_routing_loaded()

        route = self._get_task_route(task_key)
        provider = (route.get("provider", "") if isinstance(route, dict) else "").strip()
        if not provider:
            provider = (fallback_provider or "").strip()
        if not provider and hasattr(self, "settings_api_provider"):
            provider = self.settings_api_provider.get().strip()
        if not provider and hasattr(self, "api_preset"):
            provider = self.api_preset.get().strip()
        if not provider:
            provider = "DeepSeek"

        provider_cfg = {}
        if hasattr(self, "api_providers") and provider in self.api_providers:
            provider_cfg = self.api_providers.get(provider, {}) or {}
        elif hasattr(self, "api_presets") and provider in self.api_presets:
            provider_cfg = self.api_presets.get(provider, {}) or {}

        key = str(provider_cfg.get("key", "") or "").strip()
        base_url = str(provider_cfg.get("base_url", "") or "").strip()

        # Backward compatibility: allow legacy DeepSeek env vars when routing key is empty.
        if provider == "DeepSeek":
            if not key:
                key = os.getenv("DEEPSEEK_API_KEY", "").strip()
            if not base_url:
                base_url = os.getenv("DEEPSEEK_BASE_URL", "").strip()

        route_model = ""
        if isinstance(route, dict):
            route_model = str(route.get("model", "") or "").strip()
        if hasattr(self, "_strip_model_label"):
            route_model = self._strip_model_label(route_model)

        model = route_model
        if not model:
            cfg_model = str(provider_cfg.get("model", "") or "").strip()
            if hasattr(self, "_strip_model_label"):
                cfg_model = self._strip_model_label(cfg_model)
            model = cfg_model
        if not model:
            models = provider_cfg.get("models", []) if isinstance(provider_cfg, dict) else []
            if isinstance(models, list) and models:
                first_model = str(models[0]).strip()
                model = self._strip_model_label(first_model) if hasattr(self, "_strip_model_label") else first_model
        if not model:
            model = self._strip_model_label((fallback_model or "").strip()) if hasattr(self, "_strip_model_label") else (fallback_model or "").strip()
        if not model and provider == "DeepSeek":
            model = os.getenv("DEEPSEEK_MODEL", "").strip()
        if not model:
            model = "deepseek-chat"

        return {
            "provider": provider,
            "key": key,
            "base_url": base_url,
            "model": model,
        }

    def _strip_model_label(self, model: str) -> str:
        """去除模型前缀标签（📝 文本 / 🖼️ 图像）"""
        if not model:
            return ""
        m = str(model).strip()
        # 去掉 emoji 与文字前缀
        m = re.sub(r'^(📝|🖼️)\s*', '', m)
        m = re.sub(r'^(文本|图像|图片)\s*', '', m)
        m = re.sub(r'^[\|\-·:：]\s*', '', m)
        return m.strip()

    def _decorate_model_value(self, model: str, kind: str) -> str:
        """为模型值添加可读前缀"""
        raw = self._strip_model_label(model)
        if not raw:
            return ""
        prefix = "🖼️ 图像" if kind == "image" else "📝 文本"
        return f"{prefix} {raw}"

    def _decorate_model_list(self, models, kind: str):
        """批量为模型列表添加前缀"""
        if not models:
            return []
        return [self._decorate_model_value(m, kind) for m in models if str(m).strip()]

    def _models_need_refresh(self, models) -> bool:
        """判断模型列表是否需要刷新"""
        if not models:
            return True
        cleaned = []
        for m in models:
            if isinstance(m, str) and m.strip():
                cleaned.append(m.strip())
        if not cleaned:
            return True
        if len(cleaned) == 1 and cleaned[0].lower() == "default":
            return True
        return False

    def _fetch_models_from_api(self, api_key: str, base_url: str):
        """从 API 获取模型列表"""
        try:
            import requests
            
            base = (base_url or "").strip().rstrip("/")
            if not base:
                return [], "Base URL 为空"
            
            candidates = []
            if base.endswith("/v1"):
                candidates.append(f"{base}/models")
            else:
                candidates.append(f"{base}/v1/models")
                candidates.append(f"{base}/models")
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "Mozilla/5.0"
            }
            
            last_error = None
            for url in candidates:
                try:
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code != 200:
                        last_error = f"{resp.status_code}"
                        continue
                    result = resp.json()
                    
                    def _extract(items):
                        out = []
                        for item in items:
                            if isinstance(item, dict):
                                mid = item.get("id") or item.get("name")
                            elif isinstance(item, str):
                                mid = item
                            else:
                                mid = None
                            if mid:
                                out.append(str(mid))
                        return out
                    
                    models = []
                    if isinstance(result, dict):
                        if isinstance(result.get("data"), list):
                            models = _extract(result.get("data", []))
                        elif isinstance(result.get("models"), list):
                            models = _extract(result.get("models", []))
                        elif isinstance(result.get("result"), list):
                            models = _extract(result.get("result", []))
                    elif isinstance(result, list):
                        models = _extract(result)
                    
                    # 去重保持顺序
                    seen = set()
                    unique = []
                    for m in models:
                        if m not in seen:
                            seen.add(m)
                            unique.append(m)
                    
                    if unique:
                        return unique, None
                    last_error = "响应未包含模型列表"
                except Exception as e:
                    last_error = str(e)
                    continue
            return [], last_error or "请求失败"
        except Exception as e:
            return [], str(e)

    def _refresh_models_for_provider(self, provider: str, api_key: str, base_url: str, log_to_settings: bool = False) -> None:
        """刷新指定提供商的模型列表，并更新界面"""
        if not provider or not api_key or not base_url:
            return
        if not hasattr(self, "_model_fetching"):
            self._model_fetching = set()
        if provider in self._model_fetching:
            return
        self._model_fetching.add(provider)
        
        def ui_call(func, *args, **kwargs):
            if hasattr(self, '_ui'):
                return self._ui(func, *args, **kwargs)
            return func(*args, **kwargs)
        
        def task():
            try:
                models, err = self._fetch_models_from_api(api_key, base_url)
                
                if models:
                    def apply_models():
                        if hasattr(self, 'api_providers') and provider in self.api_providers:
                            self.api_providers[provider]["models"] = models
                            # 同步内存中的 key/base_url，方便后续使用
                            self.api_providers[provider]["key"] = api_key
                            self.api_providers[provider]["base_url"] = base_url
                        
                        # 更新设置页的模型下拉框
                        if (
                            hasattr(self, 'settings_api_provider')
                            and self.settings_api_provider.get() == provider
                            and hasattr(self, 'settings_combo_model')
                        ):
                            display_models = self._decorate_model_list(models, "text")
                            self.settings_combo_model['values'] = display_models or [""]
                            current = self.settings_model_var.get().strip()
                            raw_current = self._strip_model_label(current)
                            if not raw_current and models:
                                if display_models:
                                    self.settings_model_var.set(display_models[0])
                            elif raw_current in models:
                                decorated = self._decorate_model_value(raw_current, "text")
                                if current != decorated:
                                    self.settings_model_var.set(decorated)
                        
                        # 更新模型路由的模型下拉框
                        if hasattr(self, 'model_route_vars'):
                            for _task_key, route_ui in self.model_route_vars.items():
                                if route_ui["provider_var"].get() == provider:
                                    task_key = route_ui.get("task_key", "")
                                    kind = "image" if str(task_key).startswith("image_") else "text"
                                    display_models = self._decorate_model_list(models, kind)
                                    route_ui["combo_model"]['values'] = display_models or [""]
                                    current = route_ui["model_var"].get().strip()
                                    raw_current = self._strip_model_label(current)
                                    if not raw_current and models:
                                        if display_models:
                                            route_ui["model_var"].set(display_models[0])
                                    elif raw_current in models:
                                        decorated = self._decorate_model_value(raw_current, kind)
                                        if current != decorated:
                                            route_ui["model_var"].set(decorated)
                        
                        if log_to_settings and hasattr(self, 'settings_log'):
                            self.settings_log.insert(END, f"✅ 已加载 {len(models)} 个模型\n")
                            self.settings_log.see(END)
                    
                    ui_call(apply_models)
                else:
                    if log_to_settings and hasattr(self, 'settings_log'):
                        ui_call(self.settings_log.insert, END, f"⚠️ 获取模型列表失败: {err or '未知错误'}\n")
                        ui_call(self.settings_log.see, END)
            finally:
                try:
                    self._model_fetching.discard(provider)
                except Exception:
                    pass
        
        threading.Thread(target=task, daemon=True).start()

    def _on_route_provider_change(self, task_key: str) -> None:
        """模型路由提供商切换"""
        if not hasattr(self, 'model_route_vars'):
            return
        route_ui = self.model_route_vars.get(task_key)
        if not route_ui:
            return
        provider = route_ui["provider_var"].get()
        models = []
        provider_cfg = None
        if hasattr(self, 'api_providers') and provider in self.api_providers:
            provider_cfg = self.api_providers[provider]
            models = provider_cfg.get("models", [])
        elif hasattr(self, 'api_presets') and provider in self.api_presets:
            saved_model = self.api_presets[provider].get("model", "")
            if saved_model:
                models = [saved_model]
        combo_model = route_ui["combo_model"]
        task_key = route_ui.get("task_key", "")
        kind = "image" if str(task_key).startswith("image_") else "text"
        display_models = self._decorate_model_list(models, kind)
        combo_model['values'] = display_models or [""]
        # 如果当前模型不在列表中，保持用户输入
        current_model = route_ui["model_var"].get().strip()
        raw_current = self._strip_model_label(current_model)
        if not raw_current and models:
            if display_models:
                route_ui["model_var"].set(display_models[0])
        elif raw_current in models:
            decorated = self._decorate_model_value(raw_current, kind)
            if current_model != decorated:
                route_ui["model_var"].set(decorated)

        # 如果模型列表为空或占位，尝试从 API 获取
        if self._models_need_refresh(models):
            key = ""
            base_url = ""
            if provider_cfg:
                key = provider_cfg.get("key", "")
                base_url = provider_cfg.get("base_url", "")
            # 如果当前设置页正好是该 provider，优先用用户输入的 key/base_url
            if hasattr(self, 'settings_api_provider') and self.settings_api_provider.get() == provider:
                key = self.settings_api_key.get().strip() or key
                base_url = self.settings_base_url.get().strip() or base_url
            if key and base_url:
                self._refresh_models_for_provider(provider, key, base_url, log_to_settings=False)

    def _load_model_routing_to_ui(self) -> None:
        """将模型路由加载到设置界面"""
        if not hasattr(self, 'model_route_vars'):
            return
        # 确保路由已加载
        if hasattr(self, '_ensure_model_routing_loaded'):
            self._ensure_model_routing_loaded()
        advanced_mode = bool(getattr(self, "model_routing_meta", {}).get("advanced_mode", False))
        self._toggle_model_routing_advanced_ui(advanced_mode)
        for task_key, _label in MODEL_ROUTING_TASKS:
            route = self._get_task_route(task_key) if hasattr(self, '_get_task_route') else {}
            route_ui = self.model_route_vars.get(task_key)
            if not route_ui:
                continue
            provider = route.get("provider", "") or (self.settings_api_provider.get() if hasattr(self, 'settings_api_provider') else "DeepSeek")
            model = route.get("model", "")
            route_ui["provider_var"].set(provider)
            # 更新模型列表
            self._on_route_provider_change(task_key)
            if model:
                kind = "image" if str(task_key).startswith("image_") else "text"
                route_ui["model_var"].set(self._decorate_model_value(model, kind))

    def _save_model_routing_settings(self) -> None:
        """保存模型路由配置"""
        if not hasattr(self, 'model_route_vars'):
            return
        if not hasattr(self, 'model_routing'):
            self.model_routing = {}
        if not hasattr(self, "model_routing_meta") or not isinstance(self.model_routing_meta, dict):
            self.model_routing_meta = {}
        self.model_routing_meta["advanced_mode"] = bool(
            self.model_route_advanced_var.get() if hasattr(self, "model_route_advanced_var") else False
        )
        for task_key, _label in MODEL_ROUTING_TASKS:
            route_ui = self.model_route_vars.get(task_key)
            if not route_ui:
                continue
            provider = route_ui["provider_var"].get().strip()
            model = self._strip_model_label(route_ui["model_var"].get().strip())
            self.model_routing[task_key] = {
                "provider": provider,
                "model": model,
            }
        self._model_routing_loaded = True
        if hasattr(self, '_save_model_routing_to_file'):
            self._save_model_routing_to_file()
        if hasattr(self, 'settings_log'):
            self.settings_log.insert(END, "✅ 模型路由配置已保存\n")
            self.settings_log.see(END)
        messagebox.showinfo("成功", "模型路由已保存")

    def _toggle_model_routing_advanced_ui(self, enabled: bool | None = None) -> None:
        """切换模型路由高级视图（默认隐藏复杂配置）"""
        if enabled is None:
            enabled = bool(self.model_route_advanced_var.get()) if hasattr(self, "model_route_advanced_var") else False
        enabled = bool(enabled)
        if hasattr(self, "model_route_advanced_var"):
            self.model_route_advanced_var.set(enabled)
        if hasattr(self, "model_routing_advanced_frame"):
            if enabled:
                self.model_routing_advanced_frame.grid()
            else:
                self.model_routing_advanced_frame.grid_remove()
        if hasattr(self, "model_route_mode_hint_label"):
            if enabled:
                self.model_route_mode_hint_label.config(
                    text="当前：高级模式（可为每个功能单独设置模型）",
                    fg="#F59E0B",
                )
            else:
                self.model_route_mode_hint_label.config(
                    text="当前：简洁模式（默认用主模型；需要时再打开高级模式）",
                    fg=Theme.TEXT_SECONDARY,
                )

    def _on_model_route_mode_toggle(self) -> None:
        """高级模式开关变更"""
        self._toggle_model_routing_advanced_ui()
        if not hasattr(self, "model_routing_meta") or not isinstance(self.model_routing_meta, dict):
            self.model_routing_meta = {}
        self.model_routing_meta["advanced_mode"] = bool(
            self.model_route_advanced_var.get() if hasattr(self, "model_route_advanced_var") else False
        )
        if hasattr(self, "_save_model_routing_to_file"):
            self._save_model_routing_to_file()

    def _apply_story_model_to_text_routes(self) -> None:
        """使用主模型快速覆盖所有文本任务路由"""
        if not hasattr(self, "model_route_vars"):
            return

        provider = ""
        if hasattr(self, "settings_api_provider"):
            provider = self.settings_api_provider.get().strip()
        if not provider and hasattr(self, "quick_story_api"):
            provider = self.quick_story_api.get().strip()
        if not provider and hasattr(self, "api_preset"):
            provider = self.api_preset.get().strip()
        if not provider and hasattr(self, "api_providers") and self.api_providers:
            provider = list(self.api_providers.keys())[0]

        model = ""
        if hasattr(self, "story_model_var"):
            model = self._strip_model_label(self.story_model_var.get().strip())
        if not model and hasattr(self, "settings_model_var"):
            model = self._strip_model_label(self.settings_model_var.get().strip())
        if not model and provider and hasattr(self, "api_providers") and provider in self.api_providers:
            model = self._strip_model_label(str(self.api_providers[provider].get("model", "") or ""))

        if not provider:
            messagebox.showwarning("提示", "未找到可用的故事提供商，请先在设置页配置故事 API")
            return
        if not model:
            messagebox.showwarning("提示", "未找到可用的主模型，请先在故事页或设置页选择模型")
            return

        updated = 0
        for task_key, _label in MODEL_ROUTING_TASKS:
            if str(task_key).startswith("image_"):
                continue
            route_ui = self.model_route_vars.get(task_key)
            if not route_ui:
                continue
            route_ui["provider_var"].set(provider)
            self._on_route_provider_change(task_key)
            route_ui["model_var"].set(self._decorate_model_value(model, "text"))
            updated += 1

        if hasattr(self, "settings_log"):
            self.settings_log.insert(
                END,
                f"✅ 已同步主模型到 {updated} 个文本任务: {provider} / {model}\n",
            )
            self.settings_log.see(END)
    
    def _on_settings_provider_change(self, event=None):
        """故事API提供商切换 - 更新模型列表"""
        provider_name = self.settings_api_provider.get()
        print(f"[INFO] 切换到提供商: {provider_name}")
        
        if hasattr(self, 'api_providers') and provider_name in self.api_providers:
            provider = self.api_providers[provider_name]
            
            # 更新模型下拉框的选项列表
            models = provider.get("models", ["default"])
            display_models = self._decorate_model_list(models, "text")
            self.settings_combo_model['values'] = display_models or [""]
            print(f"   可用模型: {models}")
            
            # 用户切换提供商时，若模型列表为空则尝试拉取
            if event is not None and self._models_need_refresh(models):
                key = provider.get("key", "")
                base_url = provider.get("base_url", "")
                if key and base_url:
                    self._refresh_models_for_provider(provider_name, key, base_url, log_to_settings=False)
            
            # 尝试从 api_presets 加载已保存的模型
            saved_model = None
            if hasattr(self, 'api_presets') and provider_name in self.api_presets:
                saved_model = self.api_presets[provider_name].get("model", "")
                print(f"   已保存的模型: {saved_model}")
            
            # 如果有保存的模型，使用保存的；否则使用列表第一个
            if saved_model:
                raw_saved = self._strip_model_label(saved_model)
                self.settings_model_var.set(self._decorate_model_value(raw_saved, "text"))
                print(f"   [OK] 设置模型为: {raw_saved}")
            else:
                default_model = models[0] if models else ""
                self.settings_model_var.set(self._decorate_model_value(default_model, "text"))
                print(f"   [WARN] 使用默认模型: {default_model}")
            
            # 自定义提供商时，优先填充自定义模型输入框
            if provider_name == "自定义" and hasattr(self, 'settings_custom_model'):
                current_custom = self.settings_custom_model.get().strip()
                if not current_custom and saved_model:
                    self.settings_custom_model.delete(0, END)
                    self.settings_custom_model.insert(0, saved_model)
            
            # 强制刷新 Combobox 显示
            if hasattr(self, 'settings_combo_model'):
                self.settings_combo_model.update()
            
            # 更新Base URL
            self.settings_base_url.delete(0, END)
            self.settings_base_url.insert(0, provider.get("base_url", ""))
            
            # 加载已保存的API Key
            self.settings_api_key.delete(0, END)
            self.settings_api_key.insert(0, provider.get("key", ""))
    
    def _on_settings_img_provider_change(self, event=None):
        """图片API提供商切换 - 更新模型列表"""
        provider_name = self.settings_img_provider.get()
        if hasattr(self, 'img_api_providers') and provider_name in self.img_api_providers:
            provider = self.img_api_providers[provider_name]
            
            # 更新模型下拉框的选项列表
            models = provider.get("models", ["default"])
            display_models = self._decorate_model_list(models, "image")
            self.settings_combo_img_model['values'] = display_models or [""]
            
            # 尝试从 img_api_presets 加载已保存的模型
            saved_model = None
            if hasattr(self, 'img_api_presets') and provider_name in self.img_api_presets:
                saved_model = self.img_api_presets[provider_name].get("model", "")
            
            # 如果有保存的模型，使用保存的；否则使用列表第一个
            if saved_model:
                raw_saved = self._strip_model_label(saved_model)
                self.settings_img_model_var.set(self._decorate_model_value(raw_saved, "image"))
            else:
                default_model = models[0] if models else ""
                self.settings_img_model_var.set(self._decorate_model_value(default_model, "image"))
            
            # 自定义提供商时，优先填充自定义模型输入框
            if provider_name == "自定义" and hasattr(self, 'settings_img_custom_model'):
                current_custom = self.settings_img_custom_model.get().strip()
                if not current_custom and saved_model:
                    self.settings_img_custom_model.delete(0, END)
                    self.settings_img_custom_model.insert(0, saved_model)
            
            # 更新Base URL
            self.settings_img_base_url.delete(0, END)
            self.settings_img_base_url.insert(0, provider.get("base_url", ""))
            
            # 加载已保存的API Key
            self.settings_img_api_key.delete(0, END)
            self.settings_img_api_key.insert(0, provider.get("key", ""))

            # 同步运行时图片API配置
            self._sync_img_runtime_from_settings(provider_name)
    
    def _toggle_key_visibility(self):
        """切换API Key显示/隐藏"""
        if self.show_key_var.get():
            self.settings_api_key.config(show="")
        else:
            self.settings_api_key.config(show="•")
    
    def _toggle_img_key_visibility(self):
        """切换图片API Key显示/隐藏"""
        if self.show_img_key_var.get():
            self.settings_img_api_key.config(show="")
        else:
            self.settings_img_api_key.config(show="•")

    def _sync_img_runtime_from_settings(self, provider_name: str | None = None) -> None:
        """将设置页图片API配置同步到运行时变量"""
        try:
            name = provider_name or (self.settings_img_provider.get().strip() if hasattr(self, 'settings_img_provider') else "")
            key = self.settings_img_api_key.get().strip() if hasattr(self, 'settings_img_api_key') else ""
            base_url = self.settings_img_base_url.get().strip() if hasattr(self, 'settings_img_base_url') else ""
            model = self._get_current_img_model() if hasattr(self, '_get_current_img_model') else ""

            if hasattr(self, 'img_api_key'):
                self.img_api_key.set(key)
            if hasattr(self, 'img_base_url'):
                self.img_base_url.set(base_url)
            if hasattr(self, 'img_model'):
                self.img_model.set(model)

            if hasattr(self, 'img_api_type'):
                api_type = None
                if hasattr(self, 'img_api_providers') and name in self.img_api_providers:
                    api_type = self.img_api_providers[name].get("provider")
                if not api_type:
                    lower = name.lower()
                    if "混元" in name or "hunyuan" in lower:
                        api_type = "hunyuan"
                    else:
                        api_type = "openai"
                self.img_api_type.set(api_type)
        except Exception:
            pass

    def _sync_img_runtime_from_config(self, provider_name: str | None = None) -> None:
        """从已加载的配置中同步图片API到运行时（无需打开设置页）"""
        try:
            import os
            name = provider_name or ""
            if not name:
                name = os.getenv("IMAGE_GEN_API", "") or os.getenv("IMG_API_PRESET", "")
            if not name and hasattr(self, 'settings_img_provider'):
                name = self.settings_img_provider.get().strip()

            config = None
            if hasattr(self, 'img_api_providers') and name in self.img_api_providers:
                config = self.img_api_providers[name]
            elif hasattr(self, 'img_api_presets') and name in self.img_api_presets:
                config = self.img_api_presets[name]
            elif hasattr(self, 'img_api_providers'):
                for _name, cfg in self.img_api_providers.items():
                    if cfg.get("key"):
                        name = _name
                        config = cfg
                        break

            if not config:
                return

            key = (config.get("key") or "").strip()
            base_url = (config.get("base_url") or "").strip()
            model = self._strip_model_label(config.get("model", "")) if hasattr(self, '_strip_model_label') else (config.get("model", "") or "")

            if hasattr(self, 'img_api_key'):
                self.img_api_key.set(key)
            if hasattr(self, 'img_base_url'):
                self.img_base_url.set(base_url)
            if hasattr(self, 'img_model'):
                self.img_model.set(model)

            if hasattr(self, 'img_api_type'):
                api_type = config.get("provider")
                if not api_type:
                    lower = name.lower()
                    if "混元" in name or "hunyuan" in lower:
                        api_type = "hunyuan"
                    else:
                        api_type = "openai"
                self.img_api_type.set(api_type)
        except Exception:
            pass
    
    def _get_current_story_model(self):
        """获取当前选择的故事模型"""
        # 直接从模型下拉框获取（现在支持手动输入）
        model = self._strip_model_label(self.settings_model_var.get().strip())
        
        custom_model = ""
        if hasattr(self, 'settings_custom_model'):
            custom_model = self._strip_model_label(self.settings_custom_model.get().strip())
        
        provider = self.settings_api_provider.get().strip() if hasattr(self, 'settings_api_provider') else ""
        if provider == "自定义":
            return custom_model or model or "gpt-3.5-turbo"
        
        return model or custom_model or "gpt-3.5-turbo"  # 默认值
    
    def _get_current_img_model(self):
        """获取当前选择的图片模型"""
        # 直接从模型下拉框获取（现在支持手动输入）
        model = self._strip_model_label(self.settings_img_model_var.get().strip())
        
        custom_model = ""
        if hasattr(self, 'settings_img_custom_model'):
            custom_model = self._strip_model_label(self.settings_img_custom_model.get().strip())
        
        provider = self.settings_img_provider.get().strip() if hasattr(self, 'settings_img_provider') else ""
        if provider == "自定义":
            return custom_model or model or "dall-e-3"
        
        return model or custom_model or "dall-e-3"  # 默认值
    
    def _test_story_api(self):
        """测试故事API连接"""
        from src.utils.text import try_chat_api
        
        key = self.settings_api_key.get().strip()
        base_url = self.settings_base_url.get().strip()
        model = self._get_current_story_model()
        provider = self.settings_api_provider.get()
        
        if not key:
            messagebox.showwarning("提示", "请先填写API Key")
            return
        
        def ui_call(func, *args, **kwargs):
            if hasattr(self, '_ui'):
                return self._ui(func, *args, **kwargs)
            return func(*args, **kwargs)
        
        def task():
            ui_call(self.settings_log.insert, END, f"\n🔍 测试 {provider} API...\n")
            ui_call(self.settings_log.insert, END, f"   模型: {model}\n")
            ui_call(self.settings_log.insert, END, f"   Base URL: {base_url}\n")
            ui_call(self.settings_log.see, END)
            
            ok, msg = try_chat_api(key, base_url, model)
            if ok:
                ui_call(self.settings_log.insert, END, "✅ 连接成功!\n")
                ui_call(self.settings_log.insert, END, "🔄 正在获取模型列表...\n")
                ui_call(self.settings_log.see, END)
                # 测试成功后刷新模型列表
                self._refresh_models_for_provider(provider, key, base_url, log_to_settings=True)
            else:
                ui_call(self.settings_log.insert, END, f"❌ 连接失败: {msg}\n")
                ui_call(self.settings_log.see, END)
        
        threading.Thread(target=task, daemon=True).start()
    
    def _test_img_api(self):
        """测试图片API连接"""
        from src.utils.text import try_image_api
        
        key = self.settings_img_api_key.get().strip()
        base_url = self.settings_img_base_url.get().strip()
        model = self._get_current_img_model()
        provider = self.settings_img_provider.get()
        
        if not key:
            messagebox.showwarning("提示", "请先填写API Key")
            return

        def ui_call(func, *args, **kwargs):
            if hasattr(self, '_ui'):
                return self._ui(func, *args, **kwargs)
            return func(*args, **kwargs)
        
        def task():
            ui_call(self.settings_log.insert, END, f"\n🔍 测试 {provider} 图片API...\n")
            ui_call(self.settings_log.insert, END, f"   模型: {model}\n")
            ui_call(self.settings_log.see, END)
            
            ok, msg = try_image_api(key, base_url, model)
            if ok:
                ui_call(self.settings_log.insert, END, f"✅ 连接成功: {msg}\n")
            else:
                ui_call(self.settings_log.insert, END, f"❌ 连接失败: {msg}\n")
            ui_call(self.settings_log.see, END)
        
        threading.Thread(target=task, daemon=True).start()

    def _save_story_quality_settings(self, env_path: Path) -> None:
        """保存故事质量控制参数到 .env。"""
        from dotenv import set_key

        if hasattr(self, "story_quality_review_enabled"):
            try:
                quality_review_enabled = bool(self.story_quality_review_enabled.get())
            except Exception:
                quality_review_enabled = True
            set_key(str(env_path), "STORY_QUALITY_REVIEW", "1" if quality_review_enabled else "0")
        if hasattr(self, "story_quality_min_avg"):
            try:
                quality_min_avg_value = float(self.story_quality_min_avg.get())
            except Exception:
                quality_min_avg_value = 7.4
            quality_min_avg_value = max(1.0, min(10.0, quality_min_avg_value))
            set_key(str(env_path), "STORY_QUALITY_MIN_AVG", f"{quality_min_avg_value:.1f}")
        if hasattr(self, "story_quality_min_dim"):
            try:
                quality_min_dim_value = float(self.story_quality_min_dim.get())
            except Exception:
                quality_min_dim_value = 6.8
            quality_min_dim_value = max(1.0, min(10.0, quality_min_dim_value))
            set_key(str(env_path), "STORY_QUALITY_MIN_DIM", f"{quality_min_dim_value:.1f}")
    
    def _save_story_api_settings(self):
        """保存故事API配置"""
        provider_name = self.settings_api_provider.get()
        model = self._get_current_story_model()
        key = self.settings_api_key.get().strip()
        base_url = self.settings_base_url.get().strip()
        
        # 更新provider配置
        if hasattr(self, 'api_providers') and provider_name in self.api_providers:
            self.api_providers[provider_name]["key"] = key
            # Always persist base_url so third-party endpoints survive restart
            self.api_providers[provider_name]["base_url"] = base_url
            if provider_name == "自定义":
                self.api_providers[provider_name]["base_url"] = base_url
        
        # 同步更新api_presets
        if hasattr(self, 'api_presets'):
            self.api_presets[provider_name] = {
                "key": key,
                "base_url": base_url,
                "model": model
            }

        # 持久化故事路由与当前提供商，确保重启后无需再次切换
        try:
            import hashlib
            from pathlib import Path
            from dotenv import find_dotenv, set_key

            env_path_str = find_dotenv(usecwd=True)
            env_path = Path(env_path_str) if env_path_str else Path.cwd() / ".env"
            env_path.touch(exist_ok=True)

            if any(ord(c) > 127 for c in provider_name):
                hash_suffix = hashlib.md5(provider_name.encode()).hexdigest()[:8]
                safe_preset_name = f"CUSTOM_{hash_suffix}"
            else:
                safe_preset_name = provider_name.replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")

            set_key(str(env_path), "API_PRESET", provider_name)
            set_key(str(env_path), "STORY_OUTLINE_GEN_API", provider_name)
            set_key(str(env_path), "STORY_STORY_GEN_API", provider_name)
            set_key(str(env_path), f"STORY_{safe_preset_name}_KEY", key)
            set_key(str(env_path), f"STORY_{safe_preset_name}_BASE_URL", base_url)
            set_key(str(env_path), f"STORY_{safe_preset_name}_MODEL", model)
            if hasattr(self, "story_template_key"):
                template_key = self.story_template_key.get().strip() or DEFAULT_STORY_TEMPLATE_KEY
                set_key(str(env_path), "STORY_TEMPLATE_KEY", template_key)
            if hasattr(self, "story_template_strategy"):
                template_strategy = normalize_story_template_strategy(self.story_template_strategy.get())
                self.story_template_strategy.set(template_strategy)
                set_key(str(env_path), "STORY_TEMPLATE_STRATEGY", template_strategy)
            if hasattr(self, "story_creativity_mode"):
                creativity_mode = normalize_story_creativity_mode(self.story_creativity_mode.get())
                self.story_creativity_mode.set(creativity_mode)
                set_key(str(env_path), "STORY_CREATIVITY_MODE", creativity_mode)
            if hasattr(self, 'target_chars'):
                try:
                    chars_value = int(self.target_chars.get())
                except Exception:
                    chars_value = 1800
                chars_value = max(500, min(30000, chars_value))
                set_key(str(env_path), "TARGET_CHARS", str(chars_value))
            if hasattr(self, 'model_only'):
                try:
                    model_only_value = bool(self.model_only.get())
                except Exception:
                    model_only_value = False
                set_key(str(env_path), "MODEL_ONLY", "1" if model_only_value else "0")
            if hasattr(self, 'rag_min_score'):
                try:
                    rag_min_score_value = float(self.rag_min_score.get())
                except Exception:
                    rag_min_score_value = 0.12
                rag_min_score_value = max(0.0, min(1.0, rag_min_score_value))
                set_key(str(env_path), "RAG_MIN_SCORE", f"{rag_min_score_value:.2f}")
            self._save_story_quality_settings(env_path)

            if hasattr(self, 'quick_story_api'):
                self.quick_story_api.set(provider_name)
            if hasattr(self, 'outline_gen_api'):
                self.outline_gen_api.set(provider_name)
            if hasattr(self, 'story_gen_api'):
                self.story_gen_api.set(provider_name)
        except Exception as e:
            self.settings_log.insert(END, f"⚠ 保存故事提供商到 .env 失败: {e}\n")
        
        # 保存到文件
        self._save_api_config_to_file()
        
        self.settings_log.insert(END, f"✅ 故事API配置已保存: {provider_name} / {model}\n")
        self.settings_log.see(END)
        messagebox.showinfo("成功", f"配置已保存\n提供商: {provider_name}\n模型: {model}")
    
    def _save_img_api_settings(self):
        """保存图片API配置"""
        provider_name = self.settings_img_provider.get()
        model = self._get_current_img_model()
        key = self.settings_img_api_key.get().strip()
        base_url = self.settings_img_base_url.get().strip()
        
        # 更新provider配置
        if hasattr(self, 'img_api_providers') and provider_name in self.img_api_providers:
            self.img_api_providers[provider_name]["key"] = key
            # Always persist base_url so third-party endpoints survive restart
            self.img_api_providers[provider_name]["base_url"] = base_url
            if provider_name == "自定义":
                self.img_api_providers[provider_name]["base_url"] = base_url
        
        # 同步更新img_api_presets
        if hasattr(self, 'img_api_presets'):
            provider_type = "openai"
            if hasattr(self, 'img_api_providers') and provider_name in self.img_api_providers:
                provider_type = self.img_api_providers[provider_name].get("provider", "openai")
            self.img_api_presets[provider_name] = {
                "key": key,
                "base_url": base_url,
                "model": model,
                "provider": provider_type
            }

        # Persist current image provider selection for next launch
        try:
            from pathlib import Path
            from dotenv import find_dotenv, set_key

            env_path_str = find_dotenv(usecwd=True)
            env_path = Path(env_path_str) if env_path_str else Path.cwd() / ".env"
            env_path.touch(exist_ok=True)
            set_key(str(env_path), "IMAGE_GEN_API", provider_name)
            set_key(str(env_path), "IMG_API_PRESET", provider_name)
            if hasattr(self, 'quick_image_api'):
                self.quick_image_api.set(provider_name)
            if hasattr(self, 'img_api_preset'):
                self.img_api_preset.set(provider_name)
        except Exception as e:
            self.settings_log.insert(END, f"⚠ 保存图片提供商到 .env 失败: {e}\n")
        
        # 保存到文件
        self._save_api_config_to_file()

        # 同步到运行时变量，确保图片生成功能可直接使用
        self._sync_img_runtime_from_settings(provider_name)
        
        self.settings_log.insert(END, f"✅ 图片API配置已保存: {provider_name} / {model}\n")
        self.settings_log.see(END)
        messagebox.showinfo("成功", f"配置已保存\n提供商: {provider_name}\n模型: {model}")
    
    def _save_api_config_to_file(self):
        """保存API配置到文件"""
        try:
            import json
            from pathlib import Path
            
            # 保存故事API配置
            story_config = {}
            if hasattr(self, 'api_providers'):
                for name, config in self.api_providers.items():
                    if config.get("key"):  # 只保存有key的配置
                        # 获取当前选中的模型（如果是当前provider）
                        current_model = None
                        if hasattr(self, 'settings_api_provider') and self.settings_api_provider.get() == name:
                            current_model = self._get_current_story_model()
                        
                        story_config[name] = {
                            "key": config["key"],
                            "base_url": config["base_url"],
                            "models": config.get("models", [])
                        }
                        
                        # 保存当前选中的模型
                        if current_model:
                            story_config[name]["model"] = current_model
            
            if story_config:
                with open("custom_api_presets.json", 'w', encoding='utf-8') as f:
                    json.dump(story_config, f, ensure_ascii=False, indent=2)
            
            # 保存图片API配置
            img_config = {}
            if hasattr(self, 'img_api_providers'):
                for name, config in self.img_api_providers.items():
                    if config.get("key"):  # 只保存有key的配置
                        # 获取当前选中的模型（如果是当前provider）
                        current_model = None
                        if hasattr(self, 'settings_img_provider') and self.settings_img_provider.get() == name:
                            current_model = self._get_current_img_model()
                        
                        img_config[name] = {
                            "key": config["key"],
                            "base_url": config["base_url"],
                            "models": config.get("models", []),
                            "provider": config.get("provider", "openai")
                        }
                        
                        # 保存当前选中的模型
                        if current_model:
                            img_config[name]["model"] = current_model
                        if config.get("secret_key"):
                            img_config[name]["secret_key"] = config.get("secret_key")
            
            if img_config:
                with open("custom_image_api_presets.json", 'w', encoding='utf-8') as f:
                    json.dump(img_config, f, ensure_ascii=False, indent=2)
            
            print("[OK] API配置已保存到文件")
        except Exception as e:
            print(f"[ERROR] 保存配置失败: {e}")
            messagebox.showerror("错误", f"保存配置失败: {str(e)}")
    
    def _load_api_config_from_file(self):
        """从文件加载API配置"""
        try:
            import json
            from pathlib import Path
            
            def _infer_img_provider(name: str) -> str:
                lower = name.lower()
                if "混元" in name or "hunyuan" in lower:
                    return "hunyuan"
                return "openai"
            
            # 加载故事API配置
            story_file = Path("custom_api_presets.json")
            if story_file.exists():
                with open(story_file, 'r', encoding='utf-8') as f:
                    story_config = json.load(f)
                    
                if hasattr(self, 'api_providers'):
                    for name, config in story_config.items():
                        if name in self.api_providers:
                            self.api_providers[name]["key"] = config.get("key", "")
                            if "base_url" in config:
                                self.api_providers[name]["base_url"] = config["base_url"]
                            # 加载保存的模型列表
                            if "models" in config:
                                self.api_providers[name]["models"] = config["models"]
                
                # 同步到 api_presets（用于加载保存的模型）
                if hasattr(self, 'api_presets'):
                    for name, config in story_config.items():
                        if name not in self.api_presets:
                            self.api_presets[name] = {}
                        self.api_presets[name]["key"] = config.get("key", "")
                        self.api_presets[name]["base_url"] = config.get("base_url", "")
                        # 保存用户选择的模型
                        if "model" in config:
                            self.api_presets[name]["model"] = config["model"]
                
                print(f"[OK] 已加载 {len(story_config)} 个故事API配置")
            
            # 加载图片API配置
            img_file = Path("custom_image_api_presets.json")
            if img_file.exists():
                with open(img_file, 'r', encoding='utf-8') as f:
                    img_config = json.load(f)
                    
                if hasattr(self, 'img_api_providers'):
                    for name, config in img_config.items():
                        if name in self.img_api_providers:
                            self.img_api_providers[name]["key"] = config.get("key", "")
                            if "base_url" in config:
                                self.img_api_providers[name]["base_url"] = config["base_url"]
                            # 加载保存的模型列表
                            if "models" in config:
                                self.img_api_providers[name]["models"] = config["models"]
                            if "provider" in config:
                                self.img_api_providers[name]["provider"] = config["provider"]
                            elif "provider" not in self.img_api_providers[name]:
                                # 补充 provider（若缺失）
                                self.img_api_providers[name]["provider"] = _infer_img_provider(name)
                            if "secret_key" in config:
                                self.img_api_providers[name]["secret_key"] = config.get("secret_key", "")
                
                # 同步到 img_api_presets（用于加载保存的模型）
                if hasattr(self, 'img_api_presets'):
                    for name, config in img_config.items():
                        if name not in self.img_api_presets:
                            self.img_api_presets[name] = {}
                        self.img_api_presets[name]["key"] = config.get("key", "")
                        self.img_api_presets[name]["base_url"] = config.get("base_url", "")
                        # 保存用户选择的模型
                        if "model" in config:
                            self.img_api_presets[name]["model"] = config["model"]
                        if "provider" in config:
                            self.img_api_presets[name]["provider"] = config["provider"]
                        elif "provider" not in self.img_api_presets[name]:
                            self.img_api_presets[name]["provider"] = _infer_img_provider(name)
                        if "secret_key" in config:
                            self.img_api_presets[name]["secret_key"] = config.get("secret_key", "")
                
                print(f"[OK] 已加载 {len(img_config)} 个图片API配置")

            # 启动时自动同步图片API到运行时（即使未打开设置页）
            if hasattr(self, '_sync_img_runtime_from_config'):
                self._sync_img_runtime_from_config()
            self._api_config_from_file_loaded = True
                
        except Exception as e:
            print(f"[WARN] 加载配置失败: {e}")

    
    def _save_quick_api_switch(self):
        """保存快速 API 切换配置"""
        try:
            import os
            from pathlib import Path
            from dotenv import set_key, find_dotenv
            
            # 查找或创建 .env 文件
            env_path_str = find_dotenv(usecwd=True)
            if not env_path_str:
                env_path = Path.cwd() / ".env"
                env_path.touch()
            else:
                env_path = Path(env_path_str)
            
            # 保存故事生成 API 选择
            story_api = self.quick_story_api.get()
            set_key(str(env_path), "STORY_OUTLINE_GEN_API", story_api)
            set_key(str(env_path), "STORY_STORY_GEN_API", story_api)
            if hasattr(self, "story_template_key"):
                template_key = self.story_template_key.get().strip() or DEFAULT_STORY_TEMPLATE_KEY
                set_key(str(env_path), "STORY_TEMPLATE_KEY", template_key)
            if hasattr(self, "story_template_strategy"):
                template_strategy = normalize_story_template_strategy(self.story_template_strategy.get())
                self.story_template_strategy.set(template_strategy)
                set_key(str(env_path), "STORY_TEMPLATE_STRATEGY", template_strategy)
            if hasattr(self, "story_creativity_mode"):
                creativity_mode = normalize_story_creativity_mode(self.story_creativity_mode.get())
                self.story_creativity_mode.set(creativity_mode)
                set_key(str(env_path), "STORY_CREATIVITY_MODE", creativity_mode)
            
            # 保存图片生成 API 选择
            image_api = self.quick_image_api.get()
            set_key(str(env_path), "IMAGE_GEN_API", image_api)
            if hasattr(self, 'target_chars'):
                try:
                    chars_value = int(self.target_chars.get())
                except Exception:
                    chars_value = 1800
                chars_value = max(500, min(30000, chars_value))
                set_key(str(env_path), "TARGET_CHARS", str(chars_value))
            if hasattr(self, 'model_only'):
                try:
                    model_only_value = bool(self.model_only.get())
                except Exception:
                    model_only_value = False
                set_key(str(env_path), "MODEL_ONLY", "1" if model_only_value else "0")
            if hasattr(self, 'rag_min_score'):
                try:
                    rag_min_score_value = float(self.rag_min_score.get())
                except Exception:
                    rag_min_score_value = 0.12
                rag_min_score_value = max(0.0, min(1.0, rag_min_score_value))
                set_key(str(env_path), "RAG_MIN_SCORE", f"{rag_min_score_value:.2f}")
            self._save_story_quality_settings(env_path)
            
            # 同步到其他页面的变量
            if hasattr(self, 'outline_gen_api'):
                self.outline_gen_api.set(story_api)
            if hasattr(self, 'story_gen_api'):
                self.story_gen_api.set(story_api)
            
            self.settings_log.insert(END, f"\n✅ API 选择已保存\n")
            self.settings_log.insert(END, f"   故事生成: {story_api}\n")
            self.settings_log.insert(END, f"   图片生成: {image_api}\n")
            self.settings_log.see(END)
            
            messagebox.showinfo("成功", f"API 选择已保存！\n\n故事生成: {story_api}\n图片生成: {image_api}\n\n重启应用后生效")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")
    
    def _load_quick_api_switch(self):
        """加载快速 API 切换配置"""
        try:
            import os
            from dotenv import load_dotenv
            
            # Keep runtime/env overrides (e.g. tests or launcher env), and use .env as fallback only.
            load_dotenv(override=False)
            
            # 加载故事生成 API
            story_api = os.getenv("STORY_OUTLINE_GEN_API", "DeepSeek")
            if hasattr(self, 'quick_story_api'):
                self.quick_story_api.set(story_api)
            if hasattr(self, 'settings_api_provider') and hasattr(self, 'api_providers'):
                if story_api in self.api_providers:
                    self.settings_api_provider.set(story_api)
            if hasattr(self, 'api_preset') and hasattr(self, 'api_presets'):
                if story_api in self.api_presets:
                    self.api_preset.set(story_api)

            template_key = (os.getenv("STORY_TEMPLATE_KEY", "") or "").strip() or DEFAULT_STORY_TEMPLATE_KEY
            if hasattr(self, "story_template_key"):
                self.story_template_key.set(template_key)
            if hasattr(self, "story_template_key_to_label") and hasattr(self, "story_template_select_var"):
                template_label = self.story_template_key_to_label.get(template_key)
                if template_label:
                    self.story_template_select_var.set(template_label)
            if hasattr(self, "_update_story_template_desc"):
                self._update_story_template_desc()

            template_strategy = normalize_story_template_strategy(
                (os.getenv("STORY_TEMPLATE_STRATEGY", "") or "").strip() or DEFAULT_STORY_TEMPLATE_STRATEGY
            )
            if hasattr(self, "story_template_strategy"):
                self.story_template_strategy.set(template_strategy)
            if hasattr(self, "story_template_strategy_key_to_label") and hasattr(
                self, "story_template_strategy_select_var"
            ):
                strategy_label = self.story_template_strategy_key_to_label.get(template_strategy)
                if strategy_label:
                    self.story_template_strategy_select_var.set(strategy_label)
            if hasattr(self, "_update_story_template_strategy_desc"):
                self._update_story_template_strategy_desc()

            creativity_fallback = "stable"
            if hasattr(self, "story_creativity_mode"):
                try:
                    creativity_fallback = self.story_creativity_mode.get()
                except Exception:
                    creativity_fallback = "stable"
            creativity_mode = normalize_story_creativity_mode(
                (os.getenv("STORY_CREATIVITY_MODE", "") or "").strip() or creativity_fallback
            )
            if hasattr(self, "story_creativity_mode"):
                self.story_creativity_mode.set(creativity_mode)
            if hasattr(self, "story_creativity_key_to_label") and hasattr(self, "story_creativity_select_var"):
                creativity_label = self.story_creativity_key_to_label.get(creativity_mode)
                if creativity_label:
                    self.story_creativity_select_var.set(creativity_label)
            if hasattr(self, "_update_story_creativity_mode_desc"):
                self._update_story_creativity_mode_desc()
            
            # 加载图片生成 API
            image_api = os.getenv("IMAGE_GEN_API", "") or os.getenv("IMG_API_PRESET", "OpenAI (DALL-E)")
            if hasattr(self, 'quick_image_api'):
                self.quick_image_api.set(image_api)
            if hasattr(self, 'target_chars'):
                chars_raw = (os.getenv("TARGET_CHARS", "") or "").strip()
                if chars_raw:
                    try:
                        chars_value = int(chars_raw)
                        chars_value = max(500, min(30000, chars_value))
                        self.target_chars.set(chars_value)
                    except Exception:
                        pass
            if hasattr(self, 'model_only'):
                model_only_raw = (os.getenv("MODEL_ONLY", "") or "").strip().lower()
                if model_only_raw:
                    self.model_only.set(model_only_raw in {"1", "true", "yes", "on"})
            if hasattr(self, 'rag_min_score'):
                rag_raw = (os.getenv("RAG_MIN_SCORE", "") or "").strip()
                if rag_raw:
                    try:
                        rag_value = float(rag_raw)
                        rag_value = max(0.0, min(1.0, rag_value))
                        self.rag_min_score.set(rag_value)
                    except Exception:
                        pass
            if hasattr(self, "story_quality_review_enabled"):
                quality_review_raw = (os.getenv("STORY_QUALITY_REVIEW", "") or "").strip().lower()
                if quality_review_raw:
                    self.story_quality_review_enabled.set(
                        quality_review_raw in {"1", "true", "yes", "on"}
                    )
            if hasattr(self, "story_quality_min_avg"):
                quality_min_avg_raw = (os.getenv("STORY_QUALITY_MIN_AVG", "") or "").strip()
                if quality_min_avg_raw:
                    try:
                        quality_min_avg_value = float(quality_min_avg_raw)
                        quality_min_avg_value = max(1.0, min(10.0, quality_min_avg_value))
                        self.story_quality_min_avg.set(quality_min_avg_value)
                    except Exception:
                        pass
            if hasattr(self, "story_quality_min_dim"):
                quality_min_dim_raw = (os.getenv("STORY_QUALITY_MIN_DIM", "") or "").strip()
                if quality_min_dim_raw:
                    try:
                        quality_min_dim_value = float(quality_min_dim_raw)
                        quality_min_dim_value = max(1.0, min(10.0, quality_min_dim_value))
                        self.story_quality_min_dim.set(quality_min_dim_value)
                    except Exception:
                        pass
            if hasattr(self, 'settings_img_provider') and hasattr(self, 'img_api_providers'):
                if image_api in self.img_api_providers:
                    self.settings_img_provider.set(image_api)
            if hasattr(self, 'img_api_preset') and hasattr(self, 'img_api_presets'):
                if image_api in self.img_api_presets:
                    self.img_api_preset.set(image_api)
            if hasattr(self, 'char_draw_api_var') and image_api:
                try:
                    self.char_draw_api_var.set(image_api)
                except Exception:
                    pass
            if hasattr(self, '_sync_img_runtime_from_config'):
                self._sync_img_runtime_from_config(image_api)
            
            # 更新下拉框选项
            if hasattr(self, 'api_providers') and hasattr(self, 'combo_quick_story_api'):
                api_list = list(self.api_providers.keys())
                self.combo_quick_story_api['values'] = api_list
            
            if hasattr(self, 'img_api_providers') and hasattr(self, 'combo_quick_image_api'):
                img_api_list = list(self.img_api_providers.keys())
                self.combo_quick_image_api['values'] = img_api_list
                if hasattr(self, 'combo_char_draw_api'):
                    self.combo_char_draw_api['values'] = img_api_list
                    if hasattr(self, 'char_draw_api_var'):
                        current_char_api = self.char_draw_api_var.get().strip()
                        if image_api in img_api_list:
                            self.char_draw_api_var.set(image_api)
                        elif img_api_list and current_char_api not in img_api_list:
                            self.char_draw_api_var.set(img_api_list[0])

            # 刷新设置页输入框显示，避免界面仍显示默认 OpenAI
            if hasattr(self, '_on_settings_provider_change'):
                self._on_settings_provider_change()
            if hasattr(self, '_on_settings_img_provider_change'):
                self._on_settings_img_provider_change()
            
            print(f"[OK] 已加载快速 API 切换: 故事={story_api}, 图片={image_api}")
        except Exception as e:
            print(f"[WARN] 加载快速 API 切换失败: {e}")
