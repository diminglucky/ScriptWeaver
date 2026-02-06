"""
统一设置页面模块
将所有配置集中到一个页面
"""

import os
import re
import threading
import tkinter as tk
from tkinter import ttk, END, messagebox
from pathlib import Path
from dotenv import load_dotenv

from ..theme import Theme
from .config_modules.model_routing import MODEL_ROUTING_TASKS


class SettingsMixin:
    """统一设置页面功能"""
    
    def _fix_entry_colors(self, entry_widget):
        """
        修复Entry组件的颜色问题，防止焦点时变成白底白字
        使用更强制的方法来保持深色主题
        """
        def force_dark_colors(event=None):
            """强制设置深色主题颜色"""
            try:
                # 强制设置颜色
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
                # 使用after确保颜色设置生效
                entry_widget.after(1, lambda: entry_widget.config(
                    bg=Theme.BG_TERTIARY, 
                    fg=Theme.TEXT_PRIMARY,
                    insertbackground=Theme.TEXT_PRIMARY
                ))
                # 再次延迟确保
                entry_widget.after(10, lambda: entry_widget.config(
                    bg=Theme.BG_TERTIARY, 
                    fg=Theme.TEXT_PRIMARY,
                    insertbackground=Theme.TEXT_PRIMARY
                ))
            except:
                pass
        
        # 绑定多个事件，确保颜色始终正确
        entry_widget.bind("<FocusIn>", force_dark_colors)
        entry_widget.bind("<FocusOut>", force_dark_colors)
        entry_widget.bind("<Button-1>", force_dark_colors)
        entry_widget.bind("<KeyPress>", force_dark_colors)
        entry_widget.bind("<KeyRelease>", force_dark_colors)
        entry_widget.bind("<ButtonRelease-1>", force_dark_colors)
        
        # 初始设置
        force_dark_colors()
        
        # 持续监控（每100ms检查一次）
        def keep_dark():
            try:
                current_bg = entry_widget.cget("bg")
                if current_bg != Theme.BG_TERTIARY:
                    force_dark_colors()
                entry_widget.after(100, keep_dark)
            except:
                pass
        keep_dark()
    
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
            
            def _bind_mousewheel(event):
                canvas.bind_all("<MouseWheel>", _on_mousewheel)
                canvas.bind_all("<Button-4>", _on_mousewheel)
                canvas.bind_all("<Button-5>", _on_mousewheel)
            
            def _unbind_mousewheel(event):
                canvas.unbind_all("<MouseWheel>")
                canvas.unbind_all("<Button-4>")
                canvas.unbind_all("<Button-5>")
            
            canvas.bind("<Enter>", _bind_mousewheel)
            canvas.bind("<Leave>", _unbind_mousewheel)
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
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
        tk.Label(grp_kb, text="数据目录:", bg=Theme.BG_SECONDARY, fg="#FCD34D", font=("", 11, "bold")).grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.entry_data = tk.Entry(grp_kb, textvariable=self.data_dir, bg=Theme.SURFACE, fg=Theme.TEXT_PRIMARY, 
                                   insertbackground=Theme.TEXT_PRIMARY, relief=tk.FLAT)
        self.entry_data.grid(row=0, column=1, sticky="we", padx=8)
        self._fix_entry_colors(self.entry_data)
        tk.Button(grp_kb, text="选择...", command=self.choose_data, bg="#374151", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2").grid(row=0, column=2, padx=(4, 8), pady=6)
        tk.Button(grp_kb, text="一键选择库", command=self.choose_library_quick, bg="#6366F1", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2").grid(row=0, column=3, padx=(0, 8), pady=6)
        
        # 索引目录
        tk.Label(grp_kb, text="索引目录:", bg=Theme.BG_SECONDARY, fg="#FCD34D", font=("", 11, "bold")).grid(row=1, column=0, sticky="w", padx=8, pady=(0, 6))
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
        tk.Label(params_frame, text="TopK:", bg=Theme.BG_SECONDARY, fg="#FCD34D", font=("", 11, "bold")).pack(side="left", padx=(0, 5))
        self.spin_topk = tk.Spinbox(params_frame, from_=1, to=20, textvariable=self.top_k, width=6,
                                    bg=Theme.SURFACE, fg=Theme.TEXT_PRIMARY, relief=tk.FLAT)
        self.spin_topk.pack(side="left", padx=(0, 20))
        
        # 温度
        tk.Label(params_frame, text="温度:", bg=Theme.BG_SECONDARY, fg="#FCD34D", font=("", 11, "bold")).pack(side="left", padx=(0, 5))
        self.spin_temp = tk.Spinbox(params_frame, from_=0.0, to=1.5, increment=0.1, textvariable=self.temperature, 
                                    width=6, bg=Theme.SURFACE, fg=Theme.TEXT_PRIMARY, relief=tk.FLAT)
        self.spin_temp.pack(side="left", padx=(0, 20))
        
        # 目标字数
        tk.Label(params_frame, text="目标字数:", bg=Theme.BG_SECONDARY, fg="#FCD34D", font=("", 11, "bold")).pack(side="left", padx=(0, 5))
        self.spin_len = tk.Spinbox(params_frame, from_=500, to=30000, increment=500, textvariable=self.target_chars,
                                   width=8, bg=Theme.SURFACE, fg=Theme.TEXT_PRIMARY, relief=tk.FLAT)
        self.spin_len.pack(side="left")
        
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
        tk.Label(grp_story_api, text="API提供商:", bg=Theme.BG_SECONDARY, fg="#FCD34D", font=("", 11, "bold")).grid(row=0, column=0, sticky="e", padx=(8, 4), pady=8)
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
        tk.Label(grp_story_api, text="模型:", bg=Theme.BG_SECONDARY, fg="#FCD34D", font=("", 11, "bold")).grid(row=1, column=0, sticky="e", padx=(8, 4), pady=4)
        self.settings_model_var = tk.StringVar(value="deepseek-chat")
        self.settings_combo_model = ttk.Combobox(grp_story_api, textvariable=self.settings_model_var,
                                                  values=["deepseek-chat"], state="normal", width=35)
        self.settings_combo_model.grid(row=1, column=1, sticky="w", padx=(0, 8), pady=4)
        tk.Label(grp_story_api, text="(可手动输入)", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY, font=("", 9)).grid(row=1, column=2, sticky="w")
        
        # API Key
        tk.Label(grp_story_api, text="API Key:", bg=Theme.BG_SECONDARY, fg="#FCD34D", font=("", 11, "bold")).grid(row=2, column=0, sticky="e", padx=(8, 4), pady=4)
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
        tk.Label(grp_story_api, text="Base URL:", bg=Theme.BG_SECONDARY, fg="#FCD34D", font=("", 11, "bold")).grid(row=3, column=0, sticky="e", padx=(8, 4), pady=4)
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
        tk.Label(grp_img_api, text="API提供商:", bg=Theme.BG_SECONDARY, fg="#FCD34D", font=("", 11, "bold")).grid(row=0, column=0, sticky="e", padx=(8, 4), pady=8)
        self.settings_img_provider = tk.StringVar(value="OpenAI (DALL-E)")
        
        img_provider_names = list(self.img_api_providers.keys()) if hasattr(self, 'img_api_providers') else ["OpenAI (DALL-E)"]
        self.settings_combo_img_provider = ttk.Combobox(grp_img_api, textvariable=self.settings_img_provider,
                                                         values=img_provider_names, state="readonly", width=25)
        self.settings_combo_img_provider.grid(row=0, column=1, sticky="w", padx=(0, 8), pady=8)
        self.settings_combo_img_provider.bind("<<ComboboxSelected>>", self._on_settings_img_provider_change)
        
        # 图片模型选择
        tk.Label(grp_img_api, text="模型:", bg=Theme.BG_SECONDARY, fg="#FCD34D", font=("", 11, "bold")).grid(row=1, column=0, sticky="e", padx=(8, 4), pady=4)
        self.settings_img_model_var = tk.StringVar(value="dall-e-3")
        self.settings_combo_img_model = ttk.Combobox(grp_img_api, textvariable=self.settings_img_model_var,
                                                      values=["dall-e-3"], state="normal", width=35)
        self.settings_combo_img_model.grid(row=1, column=1, sticky="w", padx=(0, 8), pady=4)
        tk.Label(grp_img_api, text="(可手动输入)", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY, font=("", 9)).grid(row=1, column=2, sticky="w")
        
        # 图片API Key
        tk.Label(grp_img_api, text="API Key:", bg=Theme.BG_SECONDARY, fg="#FCD34D", font=("", 11, "bold")).grid(row=2, column=0, sticky="e", padx=(8, 4), pady=4)
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
        tk.Label(grp_img_api, text="Base URL:", bg=Theme.BG_SECONDARY, fg="#FCD34D", font=("", 11, "bold")).grid(row=3, column=0, sticky="e", padx=(8, 4), pady=4)
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
        tk.Label(grp_quick_switch, text="📝 故事生成:", bg=Theme.BG_SECONDARY, fg="#FCD34D", font=("", 11, "bold")).grid(row=1, column=0, sticky="e", padx=(8, 4), pady=8)
        self.quick_story_api = tk.StringVar(value="DeepSeek")
        self.combo_quick_story_api = ttk.Combobox(grp_quick_switch, textvariable=self.quick_story_api,
                                                   values=["DeepSeek"], state="readonly", width=30)
        self.combo_quick_story_api.grid(row=1, column=1, sticky="w", padx=(0, 8), pady=8)
        tk.Label(grp_quick_switch, text="← 用于生成目录和故事", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY, font=("", 9)).grid(row=1, column=2, sticky="w")
        
        # 图片生成 API 选择
        tk.Label(grp_quick_switch, text="🎨 图片生成:", bg=Theme.BG_SECONDARY, fg="#FCD34D", font=("", 11, "bold")).grid(row=2, column=0, sticky="e", padx=(8, 4), pady=8)
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
        grp_routing.columnconfigure(2, weight=1)

        tk.Label(
            grp_routing,
            text="💡 为每个功能单独选择模型与提供商（未设置时使用默认/快速配置）",
            bg=Theme.BG_SECONDARY,
            fg="#90CAF9",
            font=("", 10),
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=8, pady=(0, 10))

        # 记录路由变量与控件
        self.model_route_vars = {}
        provider_names = list(self.api_providers.keys()) if hasattr(self, 'api_providers') else ["DeepSeek"]

        for idx, (task_key, task_label) in enumerate(MODEL_ROUTING_TASKS, start=1):
            row = idx
            tk.Label(grp_routing, text=task_label, bg=Theme.BG_SECONDARY, fg="#FCD34D",
                     font=("", 10, "bold")).grid(row=row, column=0, sticky="e", padx=(8, 6), pady=4)

            provider_var = tk.StringVar(value=provider_names[0] if provider_names else "DeepSeek")
            model_var = tk.StringVar(value="")

            combo_provider = ttk.Combobox(
                grp_routing,
                textvariable=provider_var,
                values=provider_names,
                state="readonly",
                width=18,
            )
            combo_provider.grid(row=row, column=1, sticky="w", padx=(0, 8), pady=4)

            combo_model = ttk.Combobox(
                grp_routing,
                textvariable=model_var,
                values=[""],
                state="normal",
                width=35,
            )
            combo_model.grid(row=row, column=2, sticky="w", padx=(0, 8), pady=4)

            tk.Label(grp_routing, text="(可手动输入)", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY,
                     font=("", 9)).grid(row=row, column=3, sticky="w")

            combo_provider.bind("<<ComboboxSelected>>", lambda e, k=task_key: self._on_route_provider_change(k))

            self.model_route_vars[task_key] = {
                "provider_var": provider_var,
                "model_var": model_var,
                "combo_model": combo_model,
                "task_key": task_key,
            }

        route_btn_frame = tk.Frame(grp_routing, bg=Theme.BG_SECONDARY)
        route_btn_frame.grid(row=len(MODEL_ROUTING_TASKS) + 1, column=0, columnspan=4, pady=(10, 5))
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
        tk.Label(theme_frame, text="界面主题:", bg=Theme.BG_SECONDARY, fg="#FCD34D", font=("", 11, "bold")).pack(side="left")
        tk.Button(theme_frame, text="🌙 深色主题", command=self._set_dark_theme, bg="#374151", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=(10, 5))
        tk.Button(theme_frame, text="☀️ 浅色主题", command=self._set_light_theme, bg="#F1F5F9", fg="#1E293B",
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=5)
        
        # 配置导入导出
        config_frame = tk.Frame(advanced_frame, bg=Theme.BG_SECONDARY)
        config_frame.pack(fill="x", pady=5)
        tk.Label(config_frame, text="配置管理:", bg=Theme.BG_SECONDARY, fg="#FCD34D", font=("", 11, "bold")).pack(side="left")
        tk.Button(config_frame, text="📥 导入配置", command=self._import_config_ui, bg="#3B82F6", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=(10, 5))
        tk.Button(config_frame, text="📤 导出配置", command=self._export_config_ui, bg="#10B981", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=5)
        tk.Button(config_frame, text="📤 导出(含密钥)", command=self._export_config_with_keys, bg="#F59E0B", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=5)
        
        # 缓存管理
        cache_frame = tk.Frame(advanced_frame, bg=Theme.BG_SECONDARY)
        cache_frame.pack(fill="x", pady=5)
        tk.Label(cache_frame, text="缓存管理:", bg=Theme.BG_SECONDARY, fg="#FCD34D", font=("", 11, "bold")).pack(side="left")
        tk.Button(cache_frame, text="🗑️ 清除缓存", command=self._clear_cache_ui, bg="#EF4444", fg=Theme.TEXT_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=(10, 5))
        self.cache_size_label = tk.Label(cache_frame, text="缓存大小: 计算中...", bg=Theme.BG_SECONDARY, fg=Theme.TEXT_SECONDARY)
        self.cache_size_label.pack(side="left", padx=10)
        self.after(500, self._update_cache_size)
        
        # 快捷键提示
        shortcut_frame = tk.Frame(advanced_frame, bg=Theme.BG_SECONDARY)
        shortcut_frame.pack(fill="x", pady=5)
        tk.Label(shortcut_frame, text="快捷键:", bg=Theme.BG_SECONDARY, fg="#FCD34D", font=("", 11, "bold")).pack(side="left")
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
    
    def _on_settings_provider_change(self, event=None):
        """故事API提供商切换 - 更新模型列表"""
        provider_name = self.settings_api_provider.get()
        print(f"🔍 切换到提供商: {provider_name}")
        
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
                print(f"   ✅ 设置模型为: {raw_saved}")
            else:
                default_model = models[0] if models else ""
                self.settings_model_var.set(self._decorate_model_value(default_model, "text"))
                print(f"   ⚠️ 使用默认模型: {default_model}")
            
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
    
    def _save_story_api_settings(self):
        """保存故事API配置"""
        provider_name = self.settings_api_provider.get()
        model = self._get_current_story_model()
        key = self.settings_api_key.get().strip()
        base_url = self.settings_base_url.get().strip()
        
        # 更新provider配置
        if hasattr(self, 'api_providers') and provider_name in self.api_providers:
            self.api_providers[provider_name]["key"] = key
            if provider_name == "自定义":
                self.api_providers[provider_name]["base_url"] = base_url
        
        # 同步更新api_presets
        if hasattr(self, 'api_presets'):
            self.api_presets[provider_name] = {
                "key": key,
                "base_url": base_url,
                "model": model
            }
        
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
            if provider_name == "自定义":
                self.img_api_providers[provider_name]["base_url"] = base_url
        
        # 同步更新img_api_presets
        if hasattr(self, 'img_api_presets'):
            self.img_api_presets[provider_name] = {
                "key": key,
                "base_url": base_url,
                "model": model
            }
        
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
                            "models": config.get("models", [])
                        }
                        
                        # 保存当前选中的模型
                        if current_model:
                            img_config[name]["model"] = current_model
            
            if img_config:
                with open("custom_image_api_presets.json", 'w', encoding='utf-8') as f:
                    json.dump(img_config, f, ensure_ascii=False, indent=2)
            
            print("✅ API配置已保存到文件")
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
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
                
                print(f"✅ 已加载 {len(story_config)} 个故事API配置")
            
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
                            # 补充 provider（若缺失）
                            if "provider" not in self.img_api_providers[name]:
                                self.img_api_providers[name]["provider"] = _infer_img_provider(name)
                
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
                        if "provider" not in self.img_api_presets[name]:
                            self.img_api_presets[name]["provider"] = _infer_img_provider(name)
                
                print(f"✅ 已加载 {len(img_config)} 个图片API配置")

            # 启动时自动同步图片API到运行时（即使未打开设置页）
            if hasattr(self, '_sync_img_runtime_from_config'):
                self._sync_img_runtime_from_config()
                
        except Exception as e:
            print(f"⚠️ 加载配置失败: {e}")

    
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
            
            # 保存图片生成 API 选择
            image_api = self.quick_image_api.get()
            set_key(str(env_path), "IMAGE_GEN_API", image_api)
            
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
            
            load_dotenv(override=True)
            
            # 加载故事生成 API
            story_api = os.getenv("STORY_OUTLINE_GEN_API", "DeepSeek")
            if hasattr(self, 'quick_story_api'):
                self.quick_story_api.set(story_api)
            
            # 加载图片生成 API
            image_api = os.getenv("IMAGE_GEN_API", "OpenAI (DALL-E)")
            if hasattr(self, 'quick_image_api'):
                self.quick_image_api.set(image_api)
            if hasattr(self, '_sync_img_runtime_from_config'):
                self._sync_img_runtime_from_config(image_api)
            
            # 更新下拉框选项
            if hasattr(self, 'api_providers') and hasattr(self, 'combo_quick_story_api'):
                api_list = list(self.api_providers.keys())
                self.combo_quick_story_api['values'] = api_list
            
            if hasattr(self, 'img_api_providers') and hasattr(self, 'combo_quick_image_api'):
                img_api_list = list(self.img_api_providers.keys())
                self.combo_quick_image_api['values'] = img_api_list
            
            print(f"✅ 已加载快速 API 切换: 故事={story_api}, 图片={image_api}")
        except Exception as e:
            print(f"⚠️ 加载快速 API 切换失败: {e}")
