"""
统一设置页面模块
将所有配置集中到一个页面
"""

import os
import tkinter as tk
from tkinter import ttk, END, messagebox
from pathlib import Path
from dotenv import load_dotenv


class SettingsMixin:
    """统一设置页面功能"""
    
    def _build_settings_page(self) -> None:
        """构建统一设置页面"""
        # 创建Canvas和滚动条支持内容滚动
        canvas = tk.Canvas(self.page_settings, bg="#2b2b2b", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.page_settings, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#2b2b2b")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 绑定Canvas大小变化
        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)
        
        # 鼠标滚轮支持
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
        
        # ========== 1. 知识库配置 ==========
        grp_kb = ttk.LabelFrame(scrollable_frame, text="📚 知识库配置", padding=(15, 10))
        grp_kb.pack(fill="x", padx=15, pady=(15, 10))
        grp_kb.columnconfigure(1, weight=1)
        
        # 数据目录
        tk.Label(grp_kb, text="数据目录:", bg="#2b2b2b", fg="#ffffff").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.entry_data = tk.Entry(grp_kb, textvariable=self.data_dir, bg="#1e1e1e", fg="#ffffff", 
                                   insertbackground="white", relief=tk.FLAT)
        self.entry_data.grid(row=0, column=1, sticky="we", padx=8)
        tk.Button(grp_kb, text="选择...", command=self.choose_data, bg="#374151", fg="#ffffff",
                  relief=tk.FLAT, cursor="hand2").grid(row=0, column=2, padx=(4, 8), pady=6)
        tk.Button(grp_kb, text="一键选择库", command=self.choose_library_quick, bg="#6366F1", fg="#ffffff",
                  relief=tk.FLAT, cursor="hand2").grid(row=0, column=3, padx=(0, 8), pady=6)
        
        # 索引目录
        tk.Label(grp_kb, text="索引目录:", bg="#2b2b2b", fg="#ffffff").grid(row=1, column=0, sticky="w", padx=8, pady=(0, 6))
        self.entry_index = tk.Entry(grp_kb, textvariable=self.index_dir, bg="#1e1e1e", fg="#ffffff",
                                    insertbackground="white", relief=tk.FLAT)
        self.entry_index.grid(row=1, column=1, sticky="we", padx=8)
        tk.Button(grp_kb, text="选择...", command=self.choose_index, bg="#374151", fg="#ffffff",
                  relief=tk.FLAT, cursor="hand2").grid(row=1, column=2, padx=(4, 8), pady=(0, 6))
        self.btn_ingest = tk.Button(grp_kb, text="🔨 构建索引", command=self.on_ingest, bg="#10B981", fg="#ffffff",
                                    relief=tk.FLAT, cursor="hand2", font=("", 11, "bold"))
        self.btn_ingest.grid(row=1, column=3, padx=(0, 8), pady=(0, 6))
        
        # 知识库选项
        kb_options = tk.Frame(grp_kb, bg="#2b2b2b")
        kb_options.grid(row=2, column=0, columnspan=4, sticky="w", padx=8, pady=(0, 8))
        self.chk_model_only = ttk.Checkbutton(kb_options, text="⚡ 仅用模型（不检索知识库）", variable=self.model_only)
        self.chk_model_only.pack(side="left")
        
        # 知识库管理按钮
        tk.Button(kb_options, text="👁️ 预览内容", command=self._open_kb_preview, bg="#3B82F6", fg="#ffffff",
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=(20, 5))
        tk.Button(kb_options, text="📚 管理知识库", command=self._open_kb_manager, bg="#6366F1", fg="#ffffff",
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=5)
        
        # ========== 2. 生成参数 ==========
        grp_params = ttk.LabelFrame(scrollable_frame, text="⚙️ 生成参数", padding=(15, 10))
        grp_params.pack(fill="x", padx=15, pady=10)
        
        params_frame = tk.Frame(grp_params, bg="#2b2b2b")
        params_frame.pack(fill="x", padx=8, pady=8)
        
        # TopK
        tk.Label(params_frame, text="TopK:", bg="#2b2b2b", fg="#ffffff").pack(side="left", padx=(0, 5))
        self.spin_topk = tk.Spinbox(params_frame, from_=1, to=20, textvariable=self.top_k, width=6,
                                    bg="#1e1e1e", fg="#ffffff", relief=tk.FLAT)
        self.spin_topk.pack(side="left", padx=(0, 20))
        
        # 温度
        tk.Label(params_frame, text="温度:", bg="#2b2b2b", fg="#ffffff").pack(side="left", padx=(0, 5))
        self.spin_temp = tk.Spinbox(params_frame, from_=0.0, to=1.5, increment=0.1, textvariable=self.temperature, 
                                    width=6, bg="#1e1e1e", fg="#ffffff", relief=tk.FLAT)
        self.spin_temp.pack(side="left", padx=(0, 20))
        
        # 目标字数
        tk.Label(params_frame, text="目标字数:", bg="#2b2b2b", fg="#ffffff").pack(side="left", padx=(0, 5))
        self.spin_len = tk.Spinbox(params_frame, from_=500, to=30000, increment=500, textvariable=self.target_chars,
                                   width=8, bg="#1e1e1e", fg="#ffffff", relief=tk.FLAT)
        self.spin_len.pack(side="left")
        
        # ========== 3. 故事API配置 ==========
        grp_story_api = ttk.LabelFrame(scrollable_frame, text="📝 故事生成 API", padding=(15, 10))
        grp_story_api.pack(fill="x", padx=15, pady=10)
        grp_story_api.columnconfigure(1, weight=1)
        
        # 提供商选择
        tk.Label(grp_story_api, text="API提供商:", bg="#2b2b2b", fg="#ffffff").grid(row=0, column=0, sticky="e", padx=(8, 4), pady=8)
        self.settings_api_provider = tk.StringVar(value="DeepSeek")
        
        provider_names = list(self.api_providers.keys()) if hasattr(self, 'api_providers') else ["DeepSeek"]
        self.settings_combo_provider = ttk.Combobox(grp_story_api, textvariable=self.settings_api_provider,
                                                     values=provider_names, state="readonly", width=25)
        self.settings_combo_provider.grid(row=0, column=1, sticky="w", padx=(0, 8), pady=8)
        self.settings_combo_provider.bind("<<ComboboxSelected>>", self._on_settings_provider_change)
        
        # 模型选择
        tk.Label(grp_story_api, text="模型:", bg="#2b2b2b", fg="#ffffff").grid(row=1, column=0, sticky="e", padx=(8, 4), pady=4)
        self.settings_model_var = tk.StringVar(value="deepseek-chat")
        self.settings_combo_model = ttk.Combobox(grp_story_api, textvariable=self.settings_model_var,
                                                  values=["deepseek-chat"], state="readonly", width=35)
        self.settings_combo_model.grid(row=1, column=1, sticky="w", padx=(0, 8), pady=4)
        
        # API Key
        tk.Label(grp_story_api, text="API Key:", bg="#2b2b2b", fg="#ffffff").grid(row=2, column=0, sticky="e", padx=(8, 4), pady=4)
        self.settings_api_key = tk.Entry(grp_story_api, show="•", width=50, bg="#1e1e1e", fg="#ffffff",
                                         insertbackground="white", relief=tk.FLAT)
        self.settings_api_key.grid(row=2, column=1, sticky="w", padx=(0, 8), pady=4)
        
        # 显示/隐藏密钥按钮
        self.show_key_var = tk.BooleanVar(value=False)
        tk.Checkbutton(grp_story_api, text="显示", variable=self.show_key_var, 
                       command=self._toggle_key_visibility, bg="#2b2b2b", fg="#9CA3AF",
                       selectcolor="#2b2b2b", activebackground="#2b2b2b").grid(row=2, column=2, padx=4)
        
        # Base URL（可编辑，用于自定义）
        tk.Label(grp_story_api, text="Base URL:", bg="#2b2b2b", fg="#ffffff").grid(row=3, column=0, sticky="e", padx=(8, 4), pady=4)
        self.settings_base_url = tk.Entry(grp_story_api, width=50, bg="#1e1e1e", fg="#ffffff",
                                          insertbackground="white", relief=tk.FLAT)
        self.settings_base_url.grid(row=3, column=1, sticky="w", padx=(0, 8), pady=4)
        
        # 自定义模型输入（仅当选择自定义时显示）
        tk.Label(grp_story_api, text="自定义模型:", bg="#2b2b2b", fg="#6B7280").grid(row=4, column=0, sticky="e", padx=(8, 4), pady=4)
        self.settings_custom_model = tk.Entry(grp_story_api, width=50, bg="#1e1e1e", fg="#ffffff",
                                               insertbackground="white", relief=tk.FLAT)
        self.settings_custom_model.grid(row=4, column=1, sticky="w", padx=(0, 8), pady=4)
        tk.Label(grp_story_api, text="(仅自定义时使用)", bg="#2b2b2b", fg="#6B7280", font=("", 9)).grid(row=4, column=2, sticky="w")
        
        # 按钮
        btn_frame = tk.Frame(grp_story_api, bg="#2b2b2b")
        btn_frame.grid(row=5, column=0, columnspan=3, pady=(10, 5))
        
        tk.Button(btn_frame, text="🔍 测试连接", command=self._test_story_api, bg="#3B82F6", fg="#ffffff",
                  relief=tk.FLAT, padx=15, pady=6, cursor="hand2").pack(side="left", padx=5)
        tk.Button(btn_frame, text="💾 保存配置", command=self._save_story_api_settings, bg="#10B981", fg="#ffffff",
                  relief=tk.FLAT, padx=15, pady=6, cursor="hand2").pack(side="left", padx=5)
        
        # ========== 4. 图片API配置 ==========
        grp_img_api = ttk.LabelFrame(scrollable_frame, text="🎨 图片生成 API", padding=(15, 10))
        grp_img_api.pack(fill="x", padx=15, pady=10)
        grp_img_api.columnconfigure(1, weight=1)
        
        # 图片API提供商
        tk.Label(grp_img_api, text="API提供商:", bg="#2b2b2b", fg="#ffffff").grid(row=0, column=0, sticky="e", padx=(8, 4), pady=8)
        self.settings_img_provider = tk.StringVar(value="OpenAI (DALL-E)")
        
        img_provider_names = list(self.img_api_providers.keys()) if hasattr(self, 'img_api_providers') else ["OpenAI (DALL-E)"]
        self.settings_combo_img_provider = ttk.Combobox(grp_img_api, textvariable=self.settings_img_provider,
                                                         values=img_provider_names, state="readonly", width=25)
        self.settings_combo_img_provider.grid(row=0, column=1, sticky="w", padx=(0, 8), pady=8)
        self.settings_combo_img_provider.bind("<<ComboboxSelected>>", self._on_settings_img_provider_change)
        
        # 图片模型选择
        tk.Label(grp_img_api, text="模型:", bg="#2b2b2b", fg="#ffffff").grid(row=1, column=0, sticky="e", padx=(8, 4), pady=4)
        self.settings_img_model_var = tk.StringVar(value="dall-e-3")
        self.settings_combo_img_model = ttk.Combobox(grp_img_api, textvariable=self.settings_img_model_var,
                                                      values=["dall-e-3"], state="readonly", width=35)
        self.settings_combo_img_model.grid(row=1, column=1, sticky="w", padx=(0, 8), pady=4)
        
        # 图片API Key
        tk.Label(grp_img_api, text="API Key:", bg="#2b2b2b", fg="#ffffff").grid(row=2, column=0, sticky="e", padx=(8, 4), pady=4)
        self.settings_img_api_key = tk.Entry(grp_img_api, show="•", width=50, bg="#1e1e1e", fg="#ffffff",
                                              insertbackground="white", relief=tk.FLAT)
        self.settings_img_api_key.grid(row=2, column=1, sticky="w", padx=(0, 8), pady=4)
        
        # 显示/隐藏密钥
        self.show_img_key_var = tk.BooleanVar(value=False)
        tk.Checkbutton(grp_img_api, text="显示", variable=self.show_img_key_var,
                       command=self._toggle_img_key_visibility, bg="#2b2b2b", fg="#9CA3AF",
                       selectcolor="#2b2b2b", activebackground="#2b2b2b").grid(row=2, column=2, padx=4)
        
        # 图片Base URL
        tk.Label(grp_img_api, text="Base URL:", bg="#2b2b2b", fg="#ffffff").grid(row=3, column=0, sticky="e", padx=(8, 4), pady=4)
        self.settings_img_base_url = tk.Entry(grp_img_api, width=50, bg="#1e1e1e", fg="#ffffff",
                                               insertbackground="white", relief=tk.FLAT)
        self.settings_img_base_url.grid(row=3, column=1, sticky="w", padx=(0, 8), pady=4)
        
        # 自定义模型
        tk.Label(grp_img_api, text="自定义模型:", bg="#2b2b2b", fg="#6B7280").grid(row=4, column=0, sticky="e", padx=(8, 4), pady=4)
        self.settings_img_custom_model = tk.Entry(grp_img_api, width=50, bg="#1e1e1e", fg="#ffffff",
                                                   insertbackground="white", relief=tk.FLAT)
        self.settings_img_custom_model.grid(row=4, column=1, sticky="w", padx=(0, 8), pady=4)
        tk.Label(grp_img_api, text="(仅自定义时使用)", bg="#2b2b2b", fg="#6B7280", font=("", 9)).grid(row=4, column=2, sticky="w")
        
        # 按钮
        img_btn_frame = tk.Frame(grp_img_api, bg="#2b2b2b")
        img_btn_frame.grid(row=5, column=0, columnspan=3, pady=(10, 5))
        
        tk.Button(img_btn_frame, text="🔍 测试连接", command=self._test_img_api, bg="#3B82F6", fg="#ffffff",
                  relief=tk.FLAT, padx=15, pady=6, cursor="hand2").pack(side="left", padx=5)
        tk.Button(img_btn_frame, text="💾 保存配置", command=self._save_img_api_settings, bg="#10B981", fg="#ffffff",
                  relief=tk.FLAT, padx=15, pady=6, cursor="hand2").pack(side="left", padx=5)
        
        # ========== 5. 测试日志 ==========
        grp_log = ttk.LabelFrame(scrollable_frame, text="📋 测试日志", padding=(15, 10))
        grp_log.pack(fill="x", padx=15, pady=(10, 20))
        
        # 日志工具栏
        log_toolbar = tk.Frame(grp_log, bg="#2b2b2b")
        log_toolbar.pack(fill="x", pady=(0, 5))
        tk.Label(log_toolbar, text="💡 API测试结果将显示在这里", bg="#2b2b2b", fg="#6B7280").pack(side="left")
        tk.Button(log_toolbar, text="🗑️ 清空", command=lambda: self.settings_log.delete("1.0", END),
                  bg="#4B5563", fg="#ffffff", relief=tk.FLAT, padx=10, cursor="hand2").pack(side="right")
        
        # 日志文本框
        log_container = tk.Frame(grp_log, bg="#1e1e1e", height=150)
        log_container.pack(fill="x")
        log_container.pack_propagate(False)
        
        scroll_y = tk.Scrollbar(log_container, orient="vertical")
        scroll_y.pack(side="right", fill="y")
        
        self.settings_log = tk.Text(log_container, wrap="word", yscrollcommand=scroll_y.set,
                                     bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 10),
                                     relief=tk.FLAT, padx=10, pady=10)
        self.settings_log.pack(fill="both", expand=True)
        scroll_y.config(command=self.settings_log.yview)
        
        self.settings_log.insert("1.0", "设置页面已加载。\n配置好API后点击'测试连接'验证。\n")
        
        # ========== 6. 高级选项 ==========
        grp_advanced = ttk.LabelFrame(scrollable_frame, text="🔧 高级选项", padding=(15, 10))
        grp_advanced.pack(fill="x", padx=15, pady=(10, 10))
        
        advanced_frame = tk.Frame(grp_advanced, bg="#2b2b2b")
        advanced_frame.pack(fill="x", padx=8, pady=8)
        
        # 主题切换
        theme_frame = tk.Frame(advanced_frame, bg="#2b2b2b")
        theme_frame.pack(fill="x", pady=5)
        tk.Label(theme_frame, text="界面主题:", bg="#2b2b2b", fg="#ffffff").pack(side="left")
        tk.Button(theme_frame, text="🌙 深色主题", command=self._set_dark_theme, bg="#374151", fg="#ffffff",
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=(10, 5))
        tk.Button(theme_frame, text="☀️ 浅色主题", command=self._set_light_theme, bg="#F1F5F9", fg="#1E293B",
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=5)
        
        # 配置导入导出
        config_frame = tk.Frame(advanced_frame, bg="#2b2b2b")
        config_frame.pack(fill="x", pady=5)
        tk.Label(config_frame, text="配置管理:", bg="#2b2b2b", fg="#ffffff").pack(side="left")
        tk.Button(config_frame, text="📥 导入配置", command=self._import_config_ui, bg="#3B82F6", fg="#ffffff",
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=(10, 5))
        tk.Button(config_frame, text="📤 导出配置", command=self._export_config_ui, bg="#10B981", fg="#ffffff",
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=5)
        tk.Button(config_frame, text="📤 导出(含密钥)", command=self._export_config_with_keys, bg="#F59E0B", fg="#ffffff",
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=5)
        
        # 缓存管理
        cache_frame = tk.Frame(advanced_frame, bg="#2b2b2b")
        cache_frame.pack(fill="x", pady=5)
        tk.Label(cache_frame, text="缓存管理:", bg="#2b2b2b", fg="#ffffff").pack(side="left")
        tk.Button(cache_frame, text="🗑️ 清除缓存", command=self._clear_cache_ui, bg="#EF4444", fg="#ffffff",
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=(10, 5))
        self.cache_size_label = tk.Label(cache_frame, text="缓存大小: 计算中...", bg="#2b2b2b", fg="#6B7280")
        self.cache_size_label.pack(side="left", padx=10)
        self.after(500, self._update_cache_size)
        
        # 快捷键提示
        shortcut_frame = tk.Frame(advanced_frame, bg="#2b2b2b")
        shortcut_frame.pack(fill="x", pady=5)
        tk.Label(shortcut_frame, text="快捷键:", bg="#2b2b2b", fg="#ffffff").pack(side="left")
        tk.Button(shortcut_frame, text="⌨️ 查看快捷键", command=self._show_shortcuts_ui, bg="#6366F1", fg="#ffffff",
                  relief=tk.FLAT, cursor="hand2", padx=10).pack(side="left", padx=(10, 5))
        tk.Label(shortcut_frame, text="提示: Ctrl+T切换主题, Ctrl+S保存, F1帮助", bg="#2b2b2b", fg="#6B7280",
                 font=("", 9)).pack(side="left", padx=10)
        
        # ========== 7. 关于 ==========
        grp_about = ttk.LabelFrame(scrollable_frame, text="ℹ️ 关于", padding=(15, 10))
        grp_about.pack(fill="x", padx=15, pady=(10, 20))
        
        about_frame = tk.Frame(grp_about, bg="#2b2b2b")
        about_frame.pack(fill="x", padx=8, pady=8)
        
        tk.Label(about_frame, text="AI Story Creator Pro v2.0", bg="#2b2b2b", fg="#ffffff",
                 font=("", 14, "bold")).pack(anchor="w")
        tk.Label(about_frame, text="智能故事创作平台 - 支持多种AI提供商", bg="#2b2b2b", fg="#9CA3AF").pack(anchor="w", pady=2)
        tk.Label(about_frame, text="支持的AI: OpenAI, Gemini, Claude, DeepSeek, 通义, 文心, 智谱等", 
                 bg="#2b2b2b", fg="#6B7280", font=("", 10)).pack(anchor="w", pady=2)
        
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
        # 加载故事API配置
        self._on_settings_provider_change()
        
        # 加载图片API配置
        self._on_settings_img_provider_change()
    
    def _on_settings_provider_change(self, event=None):
        """故事API提供商切换 - 更新模型列表"""
        provider_name = self.settings_api_provider.get()
        if hasattr(self, 'api_providers') and provider_name in self.api_providers:
            provider = self.api_providers[provider_name]
            
            # 更新模型下拉框
            models = provider.get("models", ["default"])
            self.settings_combo_model['values'] = models
            self.settings_model_var.set(models[0])
            
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
            
            # 更新模型下拉框
            models = provider.get("models", ["default"])
            self.settings_combo_img_model['values'] = models
            self.settings_img_model_var.set(models[0])
            
            # 更新Base URL
            self.settings_img_base_url.delete(0, END)
            self.settings_img_base_url.insert(0, provider.get("base_url", ""))
            
            # 加载已保存的API Key
            self.settings_img_api_key.delete(0, END)
            self.settings_img_api_key.insert(0, provider.get("key", ""))
    
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
    
    def _get_current_story_model(self):
        """获取当前选择的故事模型"""
        provider = self.settings_api_provider.get()
        if provider == "自定义":
            return self.settings_custom_model.get().strip() or self.settings_model_var.get()
        return self.settings_model_var.get()
    
    def _get_current_img_model(self):
        """获取当前选择的图片模型"""
        provider = self.settings_img_provider.get()
        if provider == "自定义":
            return self.settings_img_custom_model.get().strip() or self.settings_img_model_var.get()
        return self.settings_img_model_var.get()
    
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
        
        self.settings_log.insert(END, f"\n🔍 测试 {provider} API...\n")
        self.settings_log.insert(END, f"   模型: {model}\n")
        self.settings_log.insert(END, f"   Base URL: {base_url}\n")
        self.settings_log.see(END)
        self.update()
        
        ok, msg = try_chat_api(key, base_url, model)
        if ok:
            self.settings_log.insert(END, f"✅ 连接成功!\n")
        else:
            self.settings_log.insert(END, f"❌ 连接失败: {msg}\n")
        self.settings_log.see(END)
    
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
        
        self.settings_log.insert(END, f"\n🔍 测试 {provider} 图片API...\n")
        self.settings_log.insert(END, f"   模型: {model}\n")
        self.settings_log.see(END)
        self.update()
        
        ok, msg = try_image_api(key, base_url, model)
        if ok:
            self.settings_log.insert(END, f"✅ 连接成功: {msg}\n")
        else:
            self.settings_log.insert(END, f"❌ 连接失败: {msg}\n")
        self.settings_log.see(END)
    
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
        if hasattr(self, '_save_custom_presets'):
            self._save_custom_presets()
        
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
        if hasattr(self, '_save_custom_image_presets'):
            self._save_custom_image_presets()
        
        self.settings_log.insert(END, f"✅ 图片API配置已保存: {provider_name} / {model}\n")
        self.settings_log.see(END)
        messagebox.showinfo("成功", f"配置已保存\n提供商: {provider_name}\n模型: {model}")
