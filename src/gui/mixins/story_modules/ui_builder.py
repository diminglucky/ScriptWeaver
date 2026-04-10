"""Story功能模块"""

from tkinter import LEFT, RIGHT, DISABLED, END, scrolledtext, messagebox
import logging
import threading
import tkinter as tk
from tkinter import ttk
from ...theme import Theme
from .prompt_builder_mixin import StoryPromptBuilderMixin

logger = logging.getLogger(__name__)


class StoryUIBuilderMixin(StoryPromptBuilderMixin):
	"""Story ui_builder 功能"""
	
	def _build_story_page(self) -> None:
		"""构建故事生成页面 - 简化版，配置已移至设置页面"""
		
		# 直接在页面上构建创作界面，不再使用子标签页
		self.story_tab_create = self.page_story  # 兼容旧代码引用
		
		# 构建创作界面
		self._build_story_create_tab()
	
	
	def _build_story_setup_tab(self) -> None:
		"""构建配置标签页"""
		# 创建Canvas和滚动条来支持内容滚动
		canvas = tk.Canvas(self.story_tab_setup, bg="#2b2b2b", highlightthickness=0)
		scrollbar = ttk.Scrollbar(self.story_tab_setup, orient="vertical", command=canvas.yview)
		scrollable_frame = tk.Frame(canvas, bg="#2b2b2b")
		
		scrollable_frame.bind(
			"<Configure>",
			lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
		)
		
		# 创建窗口并保存ID
		canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
		canvas.configure(yscrollcommand=scrollbar.set)
		
		# 绑定Canvas大小变化事件，使scrollable_frame填充整个宽度
		def _on_canvas_configure(event):
			canvas.itemconfig(canvas_window, width=event.width)
		canvas.bind("<Configure>", _on_canvas_configure)
		
		# 绑定鼠标滚轮事件（支持macOS和Windows）
		def _on_mousewheel(event):
			# macOS使用event.delta，Windows使用event.delta/120
			if event.delta:
				canvas.yview_scroll(int(-1 * event.delta), "units")
			elif event.num == 4:  # Linux向上滚动
				canvas.yview_scroll(-1, "units")
			elif event.num == 5:  # Linux向下滚动
				canvas.yview_scroll(1, "units")
		
		# Use local bindings to avoid cross-tab/global wheel conflicts.
		canvas.bind("<MouseWheel>", _on_mousewheel)
		canvas.bind("<Button-4>", _on_mousewheel)
		canvas.bind("<Button-5>", _on_mousewheel)
		scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
		scrollable_frame.bind("<Button-4>", _on_mousewheel)
		scrollable_frame.bind("<Button-5>", _on_mousewheel)
		
		canvas.pack(side="left", fill="both", expand=True)
		scrollbar.pack(side="right", fill="y")
		
		# 将所有组件添加到scrollable_frame而不是self.story_tab_setup
		# Group 1: 数据与索引（精简布局）
		grp_paths = ttk.LabelFrame(scrollable_frame, text="📚 资料与索引")
		grp_paths.pack(fill="x", padx=15, pady=(15, 8))
		grp_paths.columnconfigure(1, weight=1)

		tk.Label(grp_paths, text="数据目录:").grid(row=0, column=0, sticky="w", padx=8, pady=6)
		self.entry_data = tk.Entry(grp_paths, textvariable=self.data_dir)
		self.entry_data.grid(row=0, column=1, sticky="we", padx=8)
		tk.Button(grp_paths, text="选择...", command=self.choose_data).grid(row=0, column=2, padx=(4, 8), pady=6)
		tk.Button(grp_paths, text="一键选择库", command=self.choose_library_quick).grid(row=0, column=3, padx=(0, 8), pady=6)

		tk.Label(grp_paths, text="索引目录:").grid(row=1, column=0, sticky="w", padx=8, pady=(0, 6))
		self.entry_index = tk.Entry(grp_paths, textvariable=self.index_dir)
		self.entry_index.grid(row=1, column=1, sticky="we", padx=8)
		tk.Button(grp_paths, text="选择...", command=self.choose_index).grid(row=1, column=2, padx=(4, 8), pady=(0, 6))
		self.btn_ingest = tk.Button(grp_paths, text="构建索引", command=self.on_ingest)
		self.btn_ingest.grid(row=1, column=3, padx=(0, 8), pady=(0, 6))

		# Group 2: 参数（简化布局）
		grp_params = ttk.LabelFrame(scrollable_frame, text="⚙️ 生成参数")
		grp_params.pack(fill="x", padx=15, pady=8)
		grp_params.columnconfigure(1, weight=1)
		grp_params.columnconfigure(3, weight=1)
		grp_params.columnconfigure(5, weight=1)
		
		# 模型参数
		tk.Label(grp_params, text="TopK:").grid(row=0, column=0, sticky="e", padx=(8, 4), pady=8)
		self.spin_topk = tk.Spinbox(grp_params, from_=1, to=20, textvariable=self.top_k, width=6)
		self.spin_topk.grid(row=0, column=1, sticky="w", padx=(0, 15))
		
		tk.Label(grp_params, text="温度:").grid(row=0, column=2, sticky="e", padx=(0, 4))
		self.spin_temp = tk.Spinbox(grp_params, from_=0.0, to=1.5, increment=0.1, textvariable=self.temperature, width=6)
		self.spin_temp.grid(row=0, column=3, sticky="w", padx=(0, 15))
		
		tk.Label(grp_params, text="目标字数:").grid(row=0, column=4, sticky="e", padx=(0, 4))
		self.spin_len = tk.Spinbox(grp_params, from_=500, to=30000, increment=500, textvariable=self.target_chars, width=8)
		self.spin_len.grid(row=0, column=5, sticky="w", padx=(0, 8))
		
		self.chk_model_only = ttk.Checkbutton(grp_params, text="⚡ 仅用模型（不检索知识库）", variable=self.model_only)
		self.chk_model_only.grid(row=1, column=0, columnspan=6, sticky="w", padx=8, pady=(0, 8))

		# Group 3: API 配置（优化布局）
		grp_api = ttk.LabelFrame(scrollable_frame, text="🔌 基础 API 配置")
		grp_api.pack(fill="x", padx=15, pady=8)
		grp_api.columnconfigure(1, weight=1)
		
		# API预设下拉框（第一行）
		row_preset = tk.Frame(grp_api, bg="#2b2b2b")
		row_preset.grid(row=0, column=0, columnspan=2, sticky="we", padx=8, pady=(8, 6))
		
		tk.Label(row_preset, text="API预设:", bg="#2b2b2b").pack(side=LEFT, padx=(0, 8))
		
		self.api_preset = tk.StringVar(value="自定义")
		self.api_presets = {
			"DeepSeek": {
				"base_url": "https://api.deepseek.com",
				"model": "deepseek-chat",
				"key": ""
			},
			"OpenAI": {
				"base_url": "https://api.openai.com/v1",
				"model": "gpt-4",
				"key": ""
			},
			"Azure OpenAI": {
				"base_url": "https://YOUR_RESOURCE.openai.azure.com",
				"model": "gpt-4",
				"key": ""
			},
			"Moonshot (月之暗面)": {
				"base_url": "https://api.moonshot.cn/v1",
				"model": "moonshot-v1-8k",
				"key": ""
			},
			"智谱AI (GLM)": {
				"base_url": "https://open.bigmodel.cn/api/paas/v4",
				"model": "glm-4",
				"key": ""
			},
			"百度文心": {
				"base_url": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop",
				"model": "ernie-4.0",
				"key": ""
			},
			"阿里通义": {
				"base_url": "https://dashscope.aliyuncs.com/api/v1",
				"model": "qwen-max",
				"key": ""
			},
			"自定义": {
				"base_url": "",
				"model": "",
				"key": ""
			}
		}
		
		# 加载自定义配置
		self._load_custom_presets()
		self._normalize_story_preset_names()
		if hasattr(self, "api_preset"):
			current = (self.api_preset.get() or "").strip()
			if current not in self.api_presets:
				self.api_preset.set("Custom" if "Custom" in self.api_presets else next(iter(self.api_presets), ""))
		
		self.combo_api_preset = ttk.Combobox(row_preset, textvariable=self.api_preset, 
											  values=list(self.api_presets.keys()),
											  state="readonly", width=22)
		self.combo_api_preset.pack(side=LEFT, padx=(0, 10))
		self.combo_api_preset.bind("<<ComboboxSelected>>", self._on_api_preset_selected)
		
		# 自定义预设按钮
		btn_save_preset = tk.Button(row_preset, text="💾 保存预设", command=self._save_custom_preset, 
				  font=("", 9), bg="#607D8B", fg="white", relief=tk.FLAT, padx=10, pady=4, cursor="hand2")
		btn_save_preset.pack(side=LEFT, padx=2)
		
		btn_delete_preset = tk.Button(row_preset, text="🗑️ 删除", command=self._delete_custom_preset, 
				  font=("", 9), bg="#d32f2f", fg="white", relief=tk.FLAT, padx=10, pady=4, cursor="hand2")
		btn_delete_preset.pack(side=LEFT, padx=2)

		# API Key（第二行）
		tk.Label(grp_api, text="API Key:").grid(row=1, column=0, sticky="e", padx=(8, 4), pady=6)
		self.entry_api = tk.Entry(grp_api, textvariable=self.api_key, show="*")
		self.entry_api.grid(row=1, column=1, sticky="we", padx=(0, 8))
		
		# Base URL（第三行）
		tk.Label(grp_api, text="Base URL:").grid(row=2, column=0, sticky="e", padx=(8, 4), pady=6)
		self.entry_base = tk.Entry(grp_api, textvariable=self.base_url)
		self.entry_base.grid(row=2, column=1, sticky="we", padx=(0, 8))
		
		# Model + 操作按钮（第四行）
		row_model = tk.Frame(grp_api, bg="#2b2b2b")
		row_model.grid(row=3, column=0, columnspan=2, sticky="we", padx=8, pady=(6, 8))
		
		tk.Label(row_model, text="Model:", bg="#2b2b2b").pack(side=LEFT, padx=(0, 8))
		self.entry_model = tk.Entry(row_model, textvariable=self.model, width=25)
		self.entry_model.pack(side=LEFT, padx=(0, 15))
		
		tk.Button(row_model, text="💾 保存配置", command=self.save_api_config, 
				 bg="#4CAF50", fg="white", relief=tk.FLAT, padx=12, pady=5, cursor="hand2").pack(side=LEFT, padx=2)
		tk.Button(row_model, text="📥 加载配置", command=self.load_api_config,
				 bg="#2196F3", fg="white", relief=tk.FLAT, padx=12, pady=5, cursor="hand2").pack(side=LEFT, padx=2)
		tk.Button(row_model, text="🔌 API测试", command=self.on_test_story_api,
				 bg="#FF9800", fg="white", relief=tk.FLAT, padx=12, pady=5, cursor="hand2").pack(side=LEFT, padx=2)
		
		# Group 4: 故事创作功能API配置（优化布局）
		grp_assist_api = ttk.LabelFrame(scrollable_frame, text="🤖 故事创作功能 API 配置")
		grp_assist_api.pack(fill="x", padx=15, pady=8)
		grp_assist_api.columnconfigure(1, weight=1)
		
		# 说明文字
		tk.Label(grp_assist_api, text="💡 提示：选择用于生成目录和故事的API（使用上方配置的API Key）", 
				 fg="#90CAF9", font=("", 9), bg="#2b2b2b").grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 10))
		
		# 目录生成API选择
		tk.Label(grp_assist_api, text="目录生成API:", bg="#2b2b2b", fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).grid(row=1, column=0, sticky="e", padx=(8, 4), pady=8)
		self.outline_gen_api = tk.StringVar(value="DeepSeek")
		self.combo_outline_gen_api = ttk.Combobox(grp_assist_api, textvariable=self.outline_gen_api, 
											   values=["DeepSeek"],  # 初始值，会在加载配置时更新
											   state="readonly", width=35)
		self.combo_outline_gen_api.grid(row=1, column=1, sticky="w", padx=(0, 8))
		
		# 故事生成API选择
		tk.Label(grp_assist_api, text="故事生成API:", bg="#2b2b2b", fg=Theme.TEXT_PRIMARY, font=("", 11, "bold")).grid(row=2, column=0, sticky="e", padx=(8, 4), pady=8)
		self.story_gen_api = tk.StringVar(value="DeepSeek")
		self.combo_story_gen_api = ttk.Combobox(grp_assist_api, textvariable=self.story_gen_api,
											   values=["DeepSeek"],  # 初始值，会在加载配置时更新
											   state="readonly", width=35)
		self.combo_story_gen_api.grid(row=2, column=1, sticky="w", padx=(0, 8))
		
		# 保存按钮（居中显示）
		btn_frame = tk.Frame(grp_assist_api, bg="#2b2b2b")
		btn_frame.grid(row=3, column=0, columnspan=2, padx=8, pady=(8, 8))
		btn_save_story_assist_api = tk.Button(btn_frame, text="💾 保存故事创作API配置", command=self._save_story_assist_api_config,
									   font=("", 10, "bold"), bg="#4CAF50", fg="white", relief=tk.FLAT, 
									   padx=20, pady=8, cursor="hand2")
		btn_save_story_assist_api.pack()
		
		# 测试日志输出区域（合理高度）
		grp_log = ttk.LabelFrame(scrollable_frame, text="📋 测试日志")
		grp_log.pack(fill="x", padx=15, pady=(8, 15))
		
		# 工具栏
		toolbar = tk.Frame(grp_log, bg="#2b2b2b")
		toolbar.pack(fill="x", padx=5, pady=(5, 0))
		
		tk.Label(toolbar, text="💡 提示：点击上方'API测试'按钮查看详细测试结果", 
				fg="#90CAF9", font=("", 9), bg="#2b2b2b").pack(side=LEFT, padx=5)
		
		btn_clear_log = tk.Button(toolbar, text="🗑️ 清空日志", 
								  command=lambda: self.story_test_log.delete("1.0", END),
								  font=("", 9), bg="#607D8B", fg="white", 
								  relief=tk.FLAT, padx=12, pady=4, cursor="hand2")
		btn_clear_log.pack(side=RIGHT, padx=5)
		
		# 日志文本框容器（调整为更合理的高度200px）
		log_container = tk.Frame(grp_log, bg="#1e1e1e", relief=tk.SUNKEN, bd=1, height=200)
		log_container.pack(fill="both", padx=5, pady=5)
		log_container.pack_propagate(False)  # 防止子组件改变容器大小
		
		# 添加滚动条
		scroll_y = tk.Scrollbar(log_container, orient="vertical")
		scroll_y.pack(side=RIGHT, fill="y")
		
		# 日志文本框 - 固定高度
		self.story_test_log = tk.Text(log_container, wrap="word", 
									yscrollcommand=scroll_y.set,
									bg="#1e1e1e", fg="#d4d4d4", 
									font=("Consolas", 10), relief=tk.FLAT,
									padx=10, pady=10)
		self.story_test_log.pack(fill="both", expand=True)
		scroll_y.config(command=self.story_test_log.yview)
		
		# 初始提示信息
		self.story_test_log.insert("1.0", "欢迎使用AI故事创作平台！\n\n")
		self.story_test_log.insert(END, "📝 使用说明：\n")
		self.story_test_log.insert(END, "1. 配置好上方的API信息\n")
		self.story_test_log.insert(END, "2. 点击'API测试'按钮测试连接\n")
		self.story_test_log.insert(END, "3. 测试结果会显示在此区域\n\n")
		self.story_test_log.insert(END, "准备就绪，可以开始测试了... ✨\n")
	
	
	def _build_story_create_tab(self) -> None:
		"""构建创作标签页"""
		# 直接使用tab背景，不添加额外容器
		self.story_tab_create.columnconfigure(1, weight=1)

		# 第一行：种类 + 风格 + 按钮（单行）
		row1_frame = tk.Frame(self.story_tab_create, bg="#2b2b2b")
		row1_frame.grid(row=0, column=0, columnspan=2, sticky="we", padx=15, pady=(15, 12))

		# 右侧：快捷按钮组（固定单行显示）
		btn_frame = tk.Frame(row1_frame, bg="#1e1e1e")
		btn_frame.pack(side=RIGHT)

		# 左侧：题材与风格
		row1_left = tk.Frame(row1_frame, bg="#2b2b2b")
		row1_left.pack(side=LEFT, fill="x", expand=True, padx=(0, 10))

		tk.Label(row1_left, text="📚 种类:", font=("", 12, "bold"), bg="#2b2b2b", fg="#ffffff").pack(side=LEFT, padx=(0, 8))
		self.combo_category = ttk.Combobox(
			row1_left,
			textvariable=self.category,
			width=12,
			values=("爱情", "悬疑", "职场", "科幻", "成长", "亲情", "社会观察", "校园", "历史", "奇幻"),
			font=("", 12),
		)
		self.combo_category.pack(side=LEFT, padx=(0, 20))

		# 主模型选择已迁移到“设置”页，这里仅保留运行时变量兼容旧逻辑
		if not hasattr(self, "story_model_var"):
			initial_story_model = ""
			if hasattr(self, "model"):
				try:
					initial_story_model = str(self.model.get() or "").strip()
				except Exception:
					initial_story_model = ""
			self.story_model_var = tk.StringVar(value=initial_story_model or "claude-sonnet-4-5")

		# 异步加载模型列表（仍用于其它页模型下拉）
		self.after(500, self._load_available_models)

		tk.Label(row1_left, text="🎨 风格:", font=("", 12, "bold"), bg="#2b2b2b", fg="#ffffff").pack(side=LEFT, padx=(0, 8))
		self.entry_style = tk.Entry(
			row1_left,
			textvariable=self.style,
			width=42,
			font=("", 12),
			relief=tk.FLAT,
			borderwidth=0,
			bg="#1e1e1e",
			fg="#ffffff",
			insertbackground="white",
			selectbackground="#ffffff",
			selectforeground="#000000",
			highlightthickness=0,
		)
		self.entry_style.pack(side=LEFT, fill="x", expand=True, padx=(0, 6))
		# 修复Entry颜色问题
		if hasattr(self, '_fix_entry_colors'):
			self._fix_entry_colors(self.entry_style)
			self.btn_add_style = tk.Button(
				row1_left,
				text="➕",
				command=self._show_style_menu,
				font=("", 11, "bold"),
				bg="#000000",
				fg="#ffffff",
				relief=tk.FLAT,
				padx=10,
				pady=4,
				cursor="hand2",
				activebackground="#000000",
				activeforeground="#ffffff",
			)
			self.btn_add_style.pack(side=LEFT, padx=(0, 8))
			self.chk_story_global_overview_quick = tk.Checkbutton(
				btn_frame,
				text="先全书总览",
				variable=self.story_global_overview_enabled,
				font=("", 10, "bold"),
				bg="#1e1e1e",
				fg="#93c5fd",
				selectcolor="#111827",
				activebackground="#1e1e1e",
				activeforeground="#93c5fd",
				relief=tk.FLAT,
				borderwidth=0,
				padx=6,
				pady=2,
				cursor="hand2",
			)
			self.chk_story_global_overview_quick.pack(side=LEFT, padx=(0, 6))
			self.chk_story_overview_quick = tk.Checkbutton(
				btn_frame,
				text="先章节总览",
				variable=self.story_overview_before_generate,
				font=("", 10, "bold"),
				bg="#1e1e1e",
				fg="#93c5fd",
				selectcolor="#111827",
				activebackground="#1e1e1e",
				activeforeground="#93c5fd",
				relief=tk.FLAT,
				borderwidth=0,
				padx=6,
				pady=2,
				cursor="hand2",
			)
			self.chk_story_overview_quick.pack(side=LEFT, padx=(0, 8))
			self.btn_story_overview = tk.Button(
				btn_frame,
				text="🧭 总览预览",
				command=self.on_generate_story_overview,
				font=("", 11, "bold"),
				bg="#000000",
				fg="#ffffff",
				relief=tk.FLAT,
				padx=10,
				pady=8,
				cursor="hand2",
				activebackground="#000000",
				activeforeground="#ffffff",
			)
			self.btn_story_overview.pack(side=LEFT, padx=(0, 8))

		self.btn_outline = tk.Button(btn_frame, text="📋 生成目录", command=self.on_generate_outline, 
									  font=("", 13, "bold"), bg="#000000", fg="#ffffff", relief=tk.FLAT, 
									  padx=12, pady=10, cursor="hand2",
									  activebackground="#000000", activeforeground="#ffffff")
		self.btn_outline.pack(side=LEFT, padx=4)
		self.btn_blueprint = tk.Button(
			btn_frame, text="🗺️ 生成蓝图",
			command=self.generate_chapter_blueprints_async,
			font=("", 13, "bold"), bg="#000000", fg="#ffffff",
			relief=tk.FLAT, padx=12, pady=10, cursor="hand2",
			activebackground="#000000", activeforeground="#ffffff",
		)
		self.btn_blueprint.pack(side=LEFT, padx=4)
		self.btn_generate = tk.Button(btn_frame, text="🚀 生成故事", command=self.on_generate, 
									   font=("", 13, "bold"), bg="#000000", fg="#ffffff", relief=tk.FLAT, 
									   padx=12, pady=10, cursor="hand2",
									   activebackground="#000000", activeforeground="#ffffff")
		self.btn_generate.pack(side=LEFT, padx=4)
		self.btn_save_as = tk.Button(
			btn_frame,
			text="💾 保存为…",
			command=self.on_save_as,
			font=("", 13, "bold"),
			bg="#000000",
			fg="#ffffff",
			relief=tk.FLAT,
			padx=12,
			pady=10,
			cursor="hand2",
			activebackground="#000000",
			activeforeground="#ffffff",
		)
		self.btn_save_as.pack(side=LEFT, padx=4)

		# 第二行：创作需求（改为多行文本框）
		tk.Label(self.story_tab_create, text="💡 创作需求:", font=("", 12, "bold"), bg="#2b2b2b", fg="#ffffff").grid(row=1, column=0, sticky="nw", padx=(15, 10), pady=(0, 4))
		
		# 创建文本框容器
		prompt_frame = tk.Frame(self.story_tab_create, bg="#2b2b2b")
		prompt_frame.grid(row=1, column=1, sticky="we", padx=(0, 15), pady=(0, 12))
		
		# 多行文本框
		self.prompt_text = tk.Text(prompt_frame, height=3, font=("", 14), wrap=tk.WORD, 
								   relief=tk.FLAT, borderwidth=0, bg="#000000", fg="#ffffff",
								   insertbackground="white", selectbackground="#ffffff", selectforeground="#000000",
								   padx=10, pady=8, spacing1=3, spacing3=3, highlightthickness=0)
		self.prompt_text.pack(side="left", fill="both", expand=True)

		self.btn_ai_expand = tk.Button(
			prompt_frame, text="✨ AI补充", command=self._on_ai_expand_prompt,
			font=("", 11, "bold"), bg="#2563eb", fg="#ffffff", relief=tk.FLAT,
			padx=10, pady=6, cursor="hand2",
			activebackground="#1d4ed8", activeforeground="#ffffff",
		)
		self.btn_ai_expand.pack(side="right", padx=(6, 0), pady=4)
		
		# 提示文字
		self.prompt_text.insert("1.0", "例如：写一个惊悚短篇，要求特别惊奇感人，跌宕起伏...")
		self.prompt_text.bind("<FocusIn>", self._clear_prompt_placeholder)
		self.prompt_text.bind("<FocusOut>", self._restore_prompt_placeholder)
		self.prompt_text.tag_configure("placeholder", foreground="#666666")
		self.prompt_text.tag_add("placeholder", "1.0", "end")
		
		# 保持旧的self.prompt兼容性（用于读取）
		self.prompt = tk.Entry(self.story_tab_create)  # 隐藏但保持引用
		
		# 第三行：章节控制
		tk.Label(self.story_tab_create, text="📖 章节:", font=("", 12, "bold"), bg="#2b2b2b", fg="#ffffff").grid(row=2, column=0, sticky="nw", padx=(15, 10), pady=(0, 4))
		
		self.current_section_index = tk.IntVar(value=0)
		
		# 创建一个样式来设置Combobox的颜色
		style = ttk.Style()
		style.configure(
			'Chapter.TCombobox',
			foreground=Theme.TEXT_PRIMARY,
			fieldbackground=Theme.SURFACE,
			background=Theme.SURFACE,
			borderwidth=0,
			relief='flat'
		)
		style.map(
			'Chapter.TCombobox',
			fieldbackground=[('readonly', Theme.SURFACE)],
			selectbackground=[('readonly', Theme.SURFACE)],
			selectforeground=[('readonly', Theme.TEXT_PRIMARY)]
		)
		
		chapter_frame = tk.Frame(self.story_tab_create, bg="#2b2b2b")
		chapter_frame.grid(row=2, column=1, sticky="we", padx=(0, 15), pady=(0, 15))
		
		self.section_selector = ttk.Combobox(chapter_frame, textvariable=self.current_section_index, 
											 state="readonly", font=("", 14), 
											 style='Chapter.TCombobox')
		self.section_selector.pack(side=LEFT, fill="both", expand=True, padx=(0, 10))
		self.section_selector['values'] = ["请先生成目录"]
		
		# 配置下拉列表的样式
		self.option_add('*TCombobox*Listbox.font', ('', 14))
		self.option_add('*TCombobox*Listbox.foreground', Theme.TEXT_PRIMARY)
		self.option_add('*TCombobox*Listbox.background', Theme.SURFACE)
		self.option_add('*TCombobox*Listbox.selectBackground', Theme.PRIMARY)
		self.option_add('*TCombobox*Listbox.selectForeground', Theme.TEXT_PRIMARY)
		
		self.btn_generate_section = tk.Button(chapter_frame, text="📝 生成选中章节", command=self.on_generate_section, 
											   state=DISABLED, font=("", 12, "bold"), bg="#000000", fg="#ffffff",
											   relief=tk.FLAT, padx=15, pady=8, cursor="hand2",
											   activebackground="#000000", activeforeground="#ffffff",
											   disabledforeground="#666666")
		self.btn_generate_section.pack(side=LEFT, padx=4)
		self.btn_continue_next = tk.Button(chapter_frame, text="⏭️ 继续下一章", command=self.on_continue_next_section, 
										   state=DISABLED, font=("", 12, "bold"), bg="#000000", fg="#ffffff",
										   relief=tk.FLAT, padx=15, pady=8, cursor="hand2",
										   activebackground="#000000", activeforeground="#ffffff",
										   disabledforeground="#666666")
		self.btn_continue_next.pack(side=LEFT, padx=4)
		self.btn_auto_generate = tk.Button(chapter_frame, text="🔄 自动连续生成", command=self.on_auto_generate_all, 
											state=DISABLED, font=("", 12, "bold"), bg="#000000", fg="#ffffff",
											relief=tk.FLAT, padx=15, pady=8, cursor="hand2",
											activebackground="#000000", activeforeground="#ffffff",
											disabledforeground="#666666")
		self.btn_auto_generate.pack(side=LEFT, padx=4)
		
		# 预设风格标签（用于快速选择）
		self.preset_styles = [
			"情感起伏",
			"反转/悬念",
			"细节描写",
			"有画面感",
			"口语化/接地气",
			"幽默搞笑",
			"温馨感人",
			"紧张刺激",
			"励志正能量",
			"讽刺批判",
			"第一人称视角",
			"第三人称全知",
			"对话丰富",
			"心理描写",
			"环境渲染",
			"快节奏",
			"慢节奏/细腻",
			"爽文风格",
			"现实主义",
			"浪漫主义",
		]

		# Output area + status bar (使用grid布局保持一致)
		self.output = scrolledtext.ScrolledText(self.story_tab_create, wrap=tk.WORD,
												 font=("", 13), bg="#000000", fg="#ffffff",
												 insertbackground="white", selectbackground="#ffffff", selectforeground="#000000",
												 relief=tk.FLAT, borderwidth=0, highlightthickness=0,
												 padx=15, pady=15)
		self.output.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=0, pady=0)

		# 章节质量/记忆面板
		diag_frame = tk.Frame(self.story_tab_create, bg="#2b2b2b")
		diag_frame.grid(row=4, column=0, columnspan=2, sticky="we", padx=12, pady=(4, 4))
		diag_frame.columnconfigure(0, weight=1)
		diag_frame.columnconfigure(1, weight=1)

		self.story_quality_summary_var = tk.StringVar(value="质量评审：未开始")
		self.story_memory_summary_var = tk.StringVar(value="记忆账本：暂无章节记忆")

		self.lbl_story_quality_summary = tk.Label(
			diag_frame,
			textvariable=self.story_quality_summary_var,
			bg="#1f2937",
			fg="#93c5fd",
			anchor="w",
			justify="left",
			font=("", 10, "bold"),
			padx=10,
			pady=6,
		)
		self.lbl_story_quality_summary.grid(row=0, column=0, sticky="we", padx=(0, 6))

		self.lbl_story_memory_summary = tk.Label(
			diag_frame,
			textvariable=self.story_memory_summary_var,
			bg="#111827",
			fg="#a7f3d0",
			anchor="w",
			justify="left",
			font=("", 10),
			padx=10,
			pady=6,
		)
		self.lbl_story_memory_summary.grid(row=0, column=1, sticky="we", padx=(6, 0))
		self._update_story_diagnostics_panel()

		# 知乎发布区域
		zhihu_frame = tk.Frame(self.story_tab_create, bg="#2b2b2b")
		zhihu_frame.grid(row=5, column=0, columnspan=2, sticky="we", padx=10, pady=(0, 4))
		if hasattr(self, "_build_zhihu_publish_ui"):
			self._build_zhihu_publish_ui(zhihu_frame)
		
		self.status = tk.StringVar(value="就绪")
		status_bar = ttk.Label(self.story_tab_create, textvariable=self.status, anchor="w")
		status_bar.grid(row=6, column=0, columnspan=2, sticky="we", padx=10, pady=(0, 8))
		
		# 配置行列权重，让output区域可以扩展
		self.story_tab_create.rowconfigure(3, weight=1)

	# ------------------------------------------------------------------
	# AI 补充创作需求
	# ------------------------------------------------------------------

	def _on_ai_expand_prompt(self) -> None:
		"""根据用户输入的简短需求，用 AI 补充完善为更具体的创作需求。"""
		raw = self._get_prompt_content() if hasattr(self, "_get_prompt_content") else ""
		if not raw:
			messagebox.showwarning("提示", "请先输入一句简短的创作需求，AI 才能帮你补充。")
			return

		try:
			api_config = self._resolve_generation_api_config("story_generate")
		except Exception:
			messagebox.showwarning("提示", "无法获取 API 配置，请检查设置。")
			return
		from src.utils.text import sanitize as _sanitize
		api_key = _sanitize(api_config.get("key", ""))
		if not api_key:
			messagebox.showwarning("提示", "API Key 为空，请先在设置中配置。")
			return

		category = self.category.get() if hasattr(self, "category") else ""
		self.btn_ai_expand.configure(state="disabled", text="⏳ 补充中...")
		self.status.set("AI 正在补充创作需求...")

		def _task():
			try:
				from .story_infra import resolve_deepseek_client_cls as _resolve_cls
				client = _resolve_cls()(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=api_config.get("model", ""),
				)
				prompt = (
					"你是中文小说策划。用户给出了一句简短的创作需求，请帮他补充完善为一段更具体、"
					"更有画面感的创作需求说明（100~200字）。\n"
					"要求：\n"
					"1) 保留用户原意，不要偏离主题；\n"
					"2) 补充故事氛围、主角特征、核心冲突、情感基调等；\n"
					"3) 仅输出补充后的完整创作需求，不要解释你在做什么。\n\n"
					f"题材：{category or '自动'}\n"
					f"用户原始需求：{raw}\n"
				)
				result = client.chat(
					[{"role": "user", "content": prompt}],
					temperature=0.75,
					max_tokens=600,
				).strip()
				if result:
					def _apply():
						self.prompt_text.delete("1.0", "end")
						self.prompt_text.insert("1.0", result)
						self.prompt_text.tag_remove("placeholder", "1.0", "end")
						self.status.set("AI 补充完成，可继续编辑。")
					self.after(0, _apply)
				else:
					self.after(0, lambda: self.status.set("AI 返回为空，请重试。"))
			except Exception as exc:
				logger.debug("ai expand prompt failed: %s", exc)
				brief = str(exc)[:120]
				self.after(0, lambda: self.status.set(f"AI 补充失败：{brief}"))
			finally:
				def _restore_btn():
					self.btn_ai_expand.configure(state="normal", text="✨ AI补充")
				self.after(0, _restore_btn)

		threading.Thread(target=_task, daemon=True).start()
