"""Story功能模块"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, messagebox, filedialog, scrolledtext
import tkinter as tk
from tkinter import ttk
import threading
import re
from pathlib import Path
from dotenv import load_dotenv

from src.clients.deepseek_client import DeepSeekClient
# 延迟导入：只在使用时才导入，避免启动时加载 sentence_transformers (3.8秒)
# from src.kb.ingest import KnowledgeBaseIngestor, IngestConfig
# from src.kb.search import KnowledgeBaseSearcher, SearchConfig
from src.utils.text import sanitize as _sanitize
from ...theme import Theme


class StoryUIBuilderMixin:
	"""Story ui_builder 功能"""
	
	def _build_story_page(self) -> None:
		"""构建故事生成页面"""

		# 创建内部标签页
		self.story_notebook = ttk.Notebook(self.page_story)
		self.story_notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)
		
		# 创建各个子页面
		self.story_tab_create = tk.Frame(self.story_notebook, bg=Theme.BG_SECONDARY)
		self.story_tab_setup = tk.Frame(self.story_notebook, bg=Theme.BG_SECONDARY)
		
		self.story_notebook.add(self.story_tab_create, text="  ✍️ 创作  ")
		self.story_notebook.add(self.story_tab_setup, text="  ⚙️ 配置  ")
		
		# 构建各个子页面
		self._build_story_create_tab()
		self._build_story_setup_tab()
	
	
	def _build_story_setup_tab(self) -> None:
		"""构建配置标签页"""
		# 创建Canvas和滚动条来支持内容滚动
		canvas = tk.Canvas(self.story_tab_setup, bg=Theme.BG_SECONDARY, highlightthickness=0)
		scrollbar = ttk.Scrollbar(self.story_tab_setup, orient="vertical", command=canvas.yview)
		scrollable_frame = tk.Frame(canvas, bg=Theme.BG_SECONDARY)
		
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
		
		# 鼠标进入Canvas区域时绑定滚轮事件
		def _bind_mousewheel(event):
			canvas.bind_all("<MouseWheel>", _on_mousewheel)  # Windows和macOS
			canvas.bind_all("<Button-4>", _on_mousewheel)    # Linux
			canvas.bind_all("<Button-5>", _on_mousewheel)    # Linux
		
		# 鼠标离开Canvas区域时解绑滚轮事件
		def _unbind_mousewheel(event):
			canvas.unbind_all("<MouseWheel>")
			canvas.unbind_all("<Button-4>")
			canvas.unbind_all("<Button-5>")
		
		canvas.bind("<Enter>", _bind_mousewheel)
		canvas.bind("<Leave>", _unbind_mousewheel)
		
		canvas.pack(side="left", fill="both", expand=True)
		scrollbar.pack(side="right", fill="y")
		
		# 将所有组件添加到scrollable_frame而不是self.story_tab_setup
		# Group 1: 数据与索引（精简布局）
		grp_paths = ttk.LabelFrame(scrollable_frame, text="📚 资料与索引")
		grp_paths.pack(fill="x", padx=15, pady=(15, 8))
		grp_paths.columnconfigure(1, weight=1)

		# 添加说明文字
		help_label = tk.Label(
			grp_paths, 
			text="💡 提示：你可以选择包含故事txt文件的任意目录作为知识库（支持.txt/.md/.markdown文件）",
			font=("", 9),
			fg=Theme.TEXT_HINT,
			bg=Theme.BG_SECONDARY,
			wraplength=600,
			justify="left"
		)
		help_label.grid(row=0, column=0, columnspan=4, sticky="w", padx=8, pady=(6, 4))
		
		tk.Label(grp_paths, text="数据目录:").grid(row=1, column=0, sticky="w", padx=8, pady=6)
		self.entry_data = tk.Entry(grp_paths, textvariable=self.data_dir)
		self.entry_data.grid(row=1, column=1, sticky="we", padx=8)
		tk.Button(grp_paths, text="选择...", command=self.choose_data).grid(row=1, column=2, padx=(4, 8), pady=6)
		tk.Button(grp_paths, text="一键选择库", command=self.choose_library_quick).grid(row=1, column=3, padx=(0, 8), pady=6)

		tk.Label(grp_paths, text="索引目录:").grid(row=2, column=0, sticky="w", padx=8, pady=(0, 6))
		self.entry_index = tk.Entry(grp_paths, textvariable=self.index_dir)
		self.entry_index.grid(row=2, column=1, sticky="we", padx=8)
		tk.Button(grp_paths, text="选择...", command=self.choose_index).grid(row=2, column=2, padx=(4, 8), pady=(0, 6))
		self.btn_ingest = tk.Button(grp_paths, text="🔨 构建索引", command=self.on_ingest)
		self.btn_ingest.grid(row=2, column=3, padx=(0, 8), pady=(0, 6))
		
		# 添加快速操作按钮行
		quick_actions_frame = tk.Frame(grp_paths, bg=Theme.BG_SECONDARY)
		quick_actions_frame.grid(row=3, column=0, columnspan=4, sticky="we", padx=8, pady=(8, 6))
		
		# 快速添加故事文件按钮
		btn_add_stories = tk.Button(
			quick_actions_frame,
			text="📁 快速添加故事文件",
			command=self.on_quick_add_stories,
			font=("", 9),
			bg="#2196F3",
			fg="white",
			relief=tk.FLAT,
			padx=12,
			pady=5,
			cursor="hand2"
		)
		btn_add_stories.pack(side=LEFT, padx=(0, 8))
		
		# 项目故事知识库选项
		self.chk_use_project_stories = ttk.Checkbutton(
			quick_actions_frame, 
			text="📖 使用项目故事作为知识库", 
			variable=self.use_project_stories,
			command=self._on_project_stories_toggle
		)
		self.chk_use_project_stories.pack(side=LEFT, padx=(8, 4))
		
		self.btn_build_project_kb = tk.Button(
			quick_actions_frame, 
			text="🚀 构建项目故事库", 
			command=self.on_build_project_stories_kb,
			font=("", 9),
			bg="#FF9800",
			fg="white",
			relief=tk.FLAT,
			padx=12,
			pady=5,
			cursor="hand2"
		)
		self.btn_build_project_kb.pack(side=LEFT, padx=(0, 8))
		
		# 查看知识库信息按钮
		btn_view_kb_info = tk.Button(
			quick_actions_frame,
			text="ℹ️ 查看知识库信息",
			command=self.on_view_kb_info,
			font=("", 9),
			bg="#9E9E9E",
			fg="white",
			relief=tk.FLAT,
			padx=12,
			pady=5,
			cursor="hand2"
		)
		btn_view_kb_info.pack(side=LEFT)

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
		row_preset = tk.Frame(grp_api, bg=Theme.BG_CARD)
		row_preset.grid(row=0, column=0, columnspan=2, sticky="we", padx=8, pady=(8, 6))
		
		tk.Label(row_preset, text="API预设:", bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY).pack(side=LEFT, padx=(0, 8))
		
		self.api_preset = tk.StringVar(value="自定义")
		self.api_presets = {
			"DeepSeek": {
				"base_url": "https://api.deepseek.com",
				"model": "deepseek-chat",
				"key": ""
			},
			"Gemini": {
				"base_url": "",
				"model": "gemini-pro",
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
		row_model = tk.Frame(grp_api, bg=Theme.BG_CARD)
		row_model.grid(row=3, column=0, columnspan=2, sticky="we", padx=8, pady=(6, 8))
		
		tk.Label(row_model, text="Model:", bg=Theme.BG_CARD, fg=Theme.TEXT_PRIMARY).pack(side=LEFT, padx=(0, 8))
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
				 fg=Theme.INFO, font=("", 9), bg=Theme.BG_CARD).grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 10))
		
		# 目录生成API选择
		tk.Label(grp_assist_api, text="目录生成API:").grid(row=1, column=0, sticky="e", padx=(8, 4), pady=8)
		self.outline_gen_api = tk.StringVar(value="DeepSeek")
		self.combo_outline_gen_api = ttk.Combobox(grp_assist_api, textvariable=self.outline_gen_api, 
											   values=["DeepSeek"],  # 初始值，会在加载配置时更新
											   state="readonly", width=35)
		self.combo_outline_gen_api.grid(row=1, column=1, sticky="w", padx=(0, 8))
		
		# 故事生成API选择
		tk.Label(grp_assist_api, text="故事生成API:").grid(row=2, column=0, sticky="e", padx=(8, 4), pady=8)
		self.story_gen_api = tk.StringVar(value="DeepSeek")
		self.combo_story_gen_api = ttk.Combobox(grp_assist_api, textvariable=self.story_gen_api,
											   values=["DeepSeek"],  # 初始值，会在加载配置时更新
											   state="readonly", width=35)
		self.combo_story_gen_api.grid(row=2, column=1, sticky="w", padx=(0, 8))
		
		# 保存按钮（居中显示）
		btn_frame = tk.Frame(grp_assist_api, bg=Theme.BG_CARD)
		btn_frame.grid(row=3, column=0, columnspan=2, padx=8, pady=(8, 8))
		btn_save_story_assist_api = tk.Button(btn_frame, text="💾 保存故事创作API配置", command=self._save_story_assist_api_config,
									   font=("", 10, "bold"), bg="#4CAF50", fg="white", relief=tk.FLAT, 
									   padx=20, pady=8, cursor="hand2")
		btn_save_story_assist_api.pack()
		
		# 测试日志输出区域（合理高度）
		grp_log = ttk.LabelFrame(scrollable_frame, text="📋 测试日志")
		grp_log.pack(fill="x", padx=15, pady=(8, 15))
		
		# 工具栏
		toolbar = tk.Frame(grp_log, bg=Theme.BG_CARD)
		toolbar.pack(fill="x", padx=5, pady=(5, 0))
		
		tk.Label(toolbar, text="💡 提示：点击上方'API测试'按钮查看详细测试结果", 
				fg=Theme.INFO, font=("", 9), bg=Theme.BG_CARD).pack(side=LEFT, padx=5)
		
		btn_clear_log = tk.Button(toolbar, text="🗑️ 清空日志", 
								  command=lambda: self.story_test_log.delete("1.0", END),
								  font=("", 9), bg="#607D8B", fg="white", 
								  relief=tk.FLAT, padx=12, pady=4, cursor="hand2")
		btn_clear_log.pack(side=RIGHT, padx=5)
		
		# 日志文本框容器（调整为更合理的高度200px）
		log_container = tk.Frame(grp_log, bg=Theme.SURFACE_DARK, relief=tk.FLAT, bd=0, height=200)
		log_container.pack(fill="both", padx=5, pady=5)
		log_container.pack_propagate(False)  # 防止子组件改变容器大小
		
		# 添加滚动条
		scroll_y = tk.Scrollbar(log_container, orient="vertical")
		scroll_y.pack(side=RIGHT, fill="y")
		
		# 日志文本框 - 固定高度
		self.story_test_log = tk.Text(log_container, wrap="word", 
									yscrollcommand=scroll_y.set,
									bg=Theme.SURFACE_DARK, fg=Theme.TEXT_PRIMARY, 
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

		# 第一行：种类 + 风格 + 按钮
		row1_frame = tk.Frame(self.story_tab_create, bg=Theme.BG_SECONDARY)
		row1_frame.grid(row=0, column=0, columnspan=2, sticky="we", padx=15, pady=(15, 12))
		
		# 左侧：种类
		tk.Label(row1_frame, text="📚 种类:", font=("", 12, "bold"), bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY).pack(side=LEFT, padx=(0, 8))
		self.combo_category = ttk.Combobox(row1_frame, textvariable=self.category, width=12, 
										   values=("爱情", "悬疑", "职场", "科幻", "成长", "亲情", "社会观察", "校园", "历史", "奇幻"),
										   font=("", 12))
		self.combo_category.pack(side=LEFT, padx=(0, 20))
		
		# 中间：风格
		tk.Label(row1_frame, text="🎨 风格:", font=("", 12, "bold"), bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY).pack(side=LEFT, padx=(0, 8))
		self.entry_style = tk.Entry(row1_frame, textvariable=self.style, width=45, font=("", 12),
									 relief=tk.FLAT, borderwidth=1, bg=Theme.SURFACE, fg=Theme.TEXT_PRIMARY,
									 insertbackground=Theme.PRIMARY, selectbackground=Theme.PRIMARY, selectforeground=Theme.TEXT_ON_PRIMARY,
									 highlightthickness=1, highlightbackground=Theme.BORDER, highlightcolor=Theme.BORDER_FOCUS)
		self.entry_style.pack(side=LEFT, padx=(0, 6), ipady=4)
		self.btn_add_style = tk.Button(row1_frame, text="➕", command=self._show_style_menu,
									   font=("", 11, "bold"), bg=Theme.BG_HOVER, fg=Theme.TEXT_PRIMARY, relief=tk.FLAT,
									   padx=10, pady=6, cursor="hand2", activebackground=Theme.BG_SELECTED, activeforeground=Theme.TEXT_PRIMARY)
		self.btn_add_style.pack(side=LEFT, padx=(0, 20))
		
		# 右侧：快捷按钮组
		btn_frame = tk.Frame(row1_frame, bg=Theme.BG_SECONDARY)
		btn_frame.pack(side=RIGHT)
		self.btn_outline = ttk.Button(btn_frame, text="📋 生成目录", command=self.on_generate_outline, style="TButton")
		self.btn_outline.pack(side=LEFT, padx=4)
		self.btn_generate = ttk.Button(btn_frame, text="🚀 生成故事", command=self.on_generate, style="Accent.TButton")
		self.btn_generate.pack(side=LEFT, padx=4)
		ttk.Button(btn_frame, text="💾 保存为...", command=self.on_save_as, style="Ghost.TButton").pack(side=LEFT, padx=4)

		# 第二行：创作需求（改为多行文本框）
		tk.Label(self.story_tab_create, text="💡 创作需求:", font=("", 12, "bold"), bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY).grid(row=1, column=0, sticky="nw", padx=(15, 10), pady=(0, 4))
		
		# 创建文本框容器
		prompt_frame = tk.Frame(self.story_tab_create, bg=Theme.BG_SECONDARY)
		prompt_frame.grid(row=1, column=1, sticky="we", padx=(0, 15), pady=(0, 12))
		
		# ★★★ 添加展开/收起控制条 ★★★
		control_bar = tk.Frame(prompt_frame, bg=Theme.SURFACE, height=20)
		control_bar.pack(fill="x", side="top")
		
		# 展开/收起状态
		self.prompt_expanded = tk.BooleanVar(value=False)  # 默认收起（3行）
		
		# 展开/收起按钮（左上角）
		def toggle_prompt_size():
			if self.prompt_expanded.get():
				# 当前已展开，点击后收起
				self.prompt_text.config(height=3)
				toggle_btn.config(text="▼")
				self.prompt_expanded.set(False)
			else:
				# 当前收起，点击后展开
				self.prompt_text.config(height=10)
				toggle_btn.config(text="▲")
				self.prompt_expanded.set(True)
		
		toggle_btn = tk.Button(control_bar, text="▼", font=("", 10), 
							   bg=Theme.SURFACE, fg=Theme.TEXT_SECONDARY,
							   relief=tk.FLAT, cursor="hand2",
							   command=toggle_prompt_size,
							   padx=8, pady=0,
							   activebackground=Theme.BG_HOVER,
							   activeforeground=Theme.TEXT_PRIMARY)
		toggle_btn.pack(side="left", padx=2, pady=2)
		
		# 提示文字
		tk.Label(control_bar, text="点击展开/收起", font=("", 8), 
				 bg=Theme.SURFACE, fg=Theme.TEXT_HINT).pack(side="left", padx=5)
		
		# 多行文本框
		self.prompt_text = tk.Text(prompt_frame, height=3, font=("", 12), wrap=tk.WORD, 
								   relief=tk.FLAT, borderwidth=1, bg=Theme.SURFACE, fg=Theme.TEXT_PRIMARY,
								   insertbackground=Theme.PRIMARY, selectbackground=Theme.PRIMARY, selectforeground=Theme.TEXT_ON_PRIMARY,
								   padx=12, pady=10, spacing1=3, spacing3=3, highlightthickness=1, 
								   highlightbackground=Theme.BORDER, highlightcolor=Theme.BORDER_FOCUS)
		self.prompt_text.pack(fill="both", expand=True)
		
		# 提示文字（使用完整的占位符文本）
		placeholder_text = "📝 请详细描述你的故事创意...\n\n💡 提示：你可以输入：\n· 故事主题和关键情节\n· 人物设定和性格特点\n· 故事背景和时代环境\n· 特殊的叙事要求或风格\n\n✨ 越详细的描述，生成的故事越符合你的期望！"
		self.prompt_text.insert("1.0", placeholder_text)
		
		# 绑定事件：清除占位符
		self.prompt_text.bind("<FocusIn>", self._clear_prompt_placeholder)
		self.prompt_text.bind("<KeyPress>", self._on_prompt_key_press)  # 处理首次输入
		self.prompt_text.bind("<FocusOut>", self._restore_prompt_placeholder)
		
		# 配置占位符样式
		self.prompt_text.tag_configure("placeholder", foreground=Theme.TEXT_HINT)
		self.prompt_text.tag_add("placeholder", "1.0", "end")
		self.prompt_text.config(fg=Theme.TEXT_HINT)  # 设置占位符颜色（使用主题色）
		
		# 保持旧的self.prompt兼容性（用于读取）
		self.prompt = tk.Entry(self.story_tab_create)  # 隐藏但保持引用
		
		# 第三行：章节控制
		tk.Label(self.story_tab_create, text="📖 章节:", font=("", 12, "bold"), bg=Theme.BG_SECONDARY, fg=Theme.TEXT_PRIMARY).grid(row=2, column=0, sticky="nw", padx=(15, 10), pady=(0, 4))
		
		self.current_section_index = tk.IntVar(value=0)
		
		# 创建一个样式来设置Combobox的颜色
		style = ttk.Style()
		style.configure('Chapter.TCombobox', foreground=Theme.TEXT_PRIMARY, fieldbackground=Theme.SURFACE, background=Theme.SURFACE, 
						borderwidth=1, relief='flat')
		style.map('Chapter.TCombobox', 
				  fieldbackground=[('readonly', Theme.SURFACE)],
				  selectbackground=[('readonly', Theme.PRIMARY)],
				  selectforeground=[('readonly', Theme.TEXT_ON_PRIMARY)])
		
		chapter_frame = tk.Frame(self.story_tab_create, bg=Theme.BG_SECONDARY)
		chapter_frame.grid(row=2, column=1, sticky="we", padx=(0, 15), pady=(0, 15))
		
		self.section_selector = ttk.Combobox(chapter_frame, textvariable=self.current_section_index, 
											 state="readonly", font=("", 12), 
											 style='Chapter.TCombobox')
		self.section_selector.pack(side=LEFT, fill="both", expand=True, padx=(0, 10))
		self.section_selector['values'] = ["请先生成目录"]
		
		# 配置下拉列表的样式
		self.option_add('*TCombobox*Listbox.font', ('', 12))
		self.option_add('*TCombobox*Listbox.foreground', Theme.TEXT_PRIMARY)
		self.option_add('*TCombobox*Listbox.background', Theme.SURFACE)
		self.option_add('*TCombobox*Listbox.selectBackground', Theme.PRIMARY)
		self.option_add('*TCombobox*Listbox.selectForeground', Theme.TEXT_ON_PRIMARY)
		
		self.btn_generate_section = ttk.Button(chapter_frame, text="📝 生成选中章节", command=self.on_generate_section, style="Accent.TButton")
		self.btn_generate_section.state(["disabled"])  # 初始禁用
		self.btn_generate_section.pack(side=LEFT, padx=4)
		self.btn_continue_next = ttk.Button(chapter_frame, text="⏭️ 继续下一章", command=self.on_continue_next_section, style="TButton")
		self.btn_continue_next.state(["disabled"])  # 初始禁用
		self.btn_continue_next.pack(side=LEFT, padx=4)
		self.btn_auto_generate = ttk.Button(chapter_frame, text="🔄 自动连续生成", command=self.on_auto_generate_all, style="Ghost.TButton")
		self.btn_auto_generate.state(["disabled"])  # 初始禁用
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

		# Output area (故事内容输出 - 更大的显示区域)
		self.output = scrolledtext.ScrolledText(self.story_tab_create, wrap=tk.WORD,
												 font=("", 12), bg=Theme.SURFACE, fg=Theme.TEXT_PRIMARY,
												 insertbackground=Theme.PRIMARY, selectbackground=Theme.PRIMARY, selectforeground=Theme.TEXT_ON_PRIMARY,
												 relief=tk.FLAT, borderwidth=1, highlightthickness=1,
												 highlightbackground=Theme.BORDER, highlightcolor=Theme.BORDER_FOCUS,
												 padx=16, pady=16)
		self.output.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=15, pady=(0, 8))
		
		# 知乎发布区域（紧凑单行布局）
		zhihu_frame = tk.Frame(self.story_tab_create, bg=Theme.BG_SECONDARY)
		zhihu_frame.grid(row=4, column=0, columnspan=2, sticky="we", padx=10, pady=(0, 5))
		self._build_zhihu_publish_ui(zhihu_frame)
		
		# Status bar（状态栏 - 移到最底部）
		self.status = tk.StringVar(value="就绪")
		status_bar = ttk.Label(self.story_tab_create, textvariable=self.status, anchor="w")
		status_bar.grid(row=5, column=0, columnspan=2, sticky="we", padx=10, pady=(0, 8))
		
		# 配置行列权重，让output区域可以扩展（占据更多空间）
		self.story_tab_create.rowconfigure(3, weight=1)

	
	def _extract_explicit_opening(self, requirement):
		"""提取用户明确指定的开头"""
		import re
		# 匹配常见的开头指定格式
		patterns = [
			r'以[「"]([^「」""]+)[」"]为开头',
			r'以[「"]([^「」""]+)[」"]开头',
			r'开头是[「"]([^「」""]+)[」"]',
			r'开头用[「"]([^「」""]+)[」"]',
			r'开头[「"]([^「」""]+)[」"]',
			r'以([^为]+)为开头',
			r'开头是([^，。]+)',
		]
		for pattern in patterns:
			match = re.search(pattern, requirement)
			if match:
				opening = match.group(1).strip()
				# 清理可能的引号
				opening = opening.strip('"\'「」""')
				return opening
		return None
	
	def _get_category_guidance(self, category):
		"""根据故事类型生成针对性指导"""
		category_map = {
			"爱情": (
				"【💕 爱情故事特别要求】\n"
				"• 必须甜美：让人感觉特别甜蜜、温馨、心动\n"
				"• 但不无脑：要有真实的情感发展、合理的冲突、自然的转折\n"
				"• 真实细节：\"我那时候心跳特别快\"、\"我当时真的紧张，手心全是汗\"、\"我记得他笑了，特别好看\"\n"
				"• 情感真实：\"我当时真的懵了\"、\"说实话，我现在想起来还觉得甜\"、\"我当时都不知道该怎么办\"\n"
				"• 甜蜜时刻：用生活化的细节展现甜蜜（\"他给我递了杯水\"、\"我记得他那时候的表情\"）\n"
				"• 避免无脑：不要过于完美、不要过于戏剧化、要有真实的不确定性\n\n"
			),
			"悬疑": (
				"【🔍 悬疑/惊悚故事特别要求】\n"
				"• 必须惊悚：让人感觉特别害怕、紧张、恐惧\n"
				"• 真实感就是最好的恐怖：真实感会让读者更害怕，因为\"如果这是真的...\"\n"
				"• 真实细节：\"我当时真的吓到了\"、\"我那时候心跳特别快\"、\"我记得那时候特别安静，安静得有点吓人\"\n"
				"• 真实反应：\"我当时就愣住了\"、\"我当时都不知道该怎么办\"、\"说实话，我现在想起来还后怕\"\n"
				"• 循序渐进：不要一开始就太吓人，要逐步增加紧张感\n"
				"• 真实场景：用生活化的场景（\"我们宿舍楼下\"、\"那家24小时便利店\"）让恐怖更真实\n\n"
			),
			"职场": (
				"【💼 职场故事特别要求】\n"
				"• 真实职场：用真实的职场场景、真实的职场冲突、真实的职场细节\n"
				"• 真实反应：\"我当时真的懵了\"、\"我当时都不知道该怎么办\"、\"说实话，我现在想起来还觉得紧张\"\n"
				"• 真实细节：\"我记得那时候会议室特别安静\"、\"我记得他那时候的表情\"、\"我记得那时候我手心全是汗\"\n\n"
			),
			"成长": (
				"【🌱 成长故事特别要求】\n"
				"• 真实变化：展现真实的成长过程、真实的挣扎、真实的改变\n"
				"• 真实反思：\"现在想想\"、\"那时候我还...\"、\"说实话，我现在明白了\"\n"
				"• 真实细节：\"我记得那时候\"、\"我记得那天\"、\"我记得那时候的我\"\n\n"
			),
			"亲情": (
				"【❤️ 亲情故事特别要求】\n"
				"• 真实情感：用真实的情感表达、真实的细节、真实的对话\n"
				"• 真实细节：\"我记得那时候\"、\"我记得我妈那时候的表情\"、\"我记得那时候我哭了\"\n"
				"• 真实情感：\"我当时真的哭了\"、\"说实话，我现在想起来还觉得...\"、\"我当时真的感动了\"\n\n"
			),
		}
		return category_map.get(category, "")
	
	def _build_outline_prompt(self, requirement, contexts, category):
		ctx = "\n\n".join(f"【资料{i+1}】\n{c}" for i, c in enumerate(contexts))
		target_chars = self.target_chars.get()
		# 根据目标字数动态决定章节数
		if target_chars <= 3000:
			suggested_sections = "3-4"
		elif target_chars <= 8000:
			suggested_sections = "4-6"
		elif target_chars <= 15000:
			suggested_sections = "6-8"
		else:
			suggested_sections = "8-10"
		
		return (
			"基于资料，为知乎读者产出一个简洁的写作目录（仅目录，不要正文）。\n\n"
			"【核心要求】\n"
			f"- 只输出 {suggested_sections} 个主要章节标题，不要子标题、不要要点列表\n"
			"- 每个章节用数字编号（1. 2. 3. ...）\n"
			"- 章节名简短有力（5-10字），能体现故事发展\n"
			"- 结构要符合：开端 → 发展 → 高潮 → 结局\n"
			"- 不要写\"第一章\"、\"第二章\"，直接写章节内容主题\n\n"
			"【章节标题吸引力要求】\n"
			"- 每个章节标题都要有吸引力，包含冲突/悬念/情绪词\n"
			"- 避免平淡的描述性标题，要用能激起好奇心的标题\n"
			"- 示例对比：\n"
			"  ❌ 差：\"平静的开端\"、\"意外降临\"、\"危机爆发\"（太常见）\n"
			"  ✅ 好：\"平安夜初遇\"、\"疯狂追求记\"、\"浪漫告白夜\"（有画面感）\n"
			"  ✅ 好：\"凌晨两点的医院\"、\"死者的照片\"、\"消失的真相\"（有悬念）\n"
			"  ✅ 好：\"那个决定改变一切\"、\"我终于明白\"、\"最后的赌注\"（有情感）\n\n"
			f"【创作信息】\n"
			f"- 主题/需求：{requirement}\n"
			f"- 种类：{category}\n"
			f"- 目标字数：{target_chars}字\n\n"
			f"【参考资料】\n{ctx if ctx else '无特定资料'}\n\n"
			"请直接输出章节列表，格式如下：\n"
			"1. 平安夜初遇\n"
			"2. 疯狂追求记\n"
			"3. 暧昧升温时\n"
			"4. 浪漫告白夜\n"
			"5. 终成眷属日"
		)

	
	def _build_prompt(self, requirement, contexts, category, outline=""):
		ctx = "\n\n".join(f"【参考故事{i+1}】\n{c}" for i, c in enumerate(contexts))
		outline_part = ("\n\n请严格参照下述目录完成写作：\n" + outline.strip()) if outline else ""
		style_part = self.style.get().strip()
		target = self.target_chars.get()
		# 计算字数范围
		min_chars = int(target * 0.9)
		max_chars = int(target * 1.1)
		
		# 检测用户是否明确指定了开头
		explicit_opening = self._extract_explicit_opening(requirement)
		
		# 根据故事类型生成针对性要求
		category_guidance = self._get_category_guidance(category)
		
		# 判断是否使用项目故事库
		use_project_stories = self.use_project_stories.get() if hasattr(self, 'use_project_stories') else False
		rag_guidance = ""
		if contexts:
			if use_project_stories:
				rag_guidance = (
					"\n【🎯 RAG增强创作指导】\n"
					"以下是系统从你的过往优秀故事中检索到的相关片段，作为创作参考。\n\n"
					"你的任务：\n"
					"1. **深度分析参考故事**：仔细阅读这些参考故事，理解它们的：\n"
					"   • 叙事技巧和节奏把控\n"
					"   • 人物塑造和情感刻画方式\n"
					"   • 情节设计和反转手法\n"
					"   • 语言风格和细节描写方法\n"
					"   • 吸引读者的关键要素\n\n"
					"2. **创新性超越参考**：\n"
					"   • 不要直接复制或改写参考故事，而是**学习并超越**\n"
					"   • 提取参考故事中的**优秀技巧**，但创造出**全新的故事**\n"
					"   • 借鉴参考故事的**叙事节奏**，但设计**更精彩的情节**\n"
					"   • 学习参考故事的**情感刻画方式**，但描绘**更深层的情感**\n"
					"   • 参考故事的**语言风格**，但写出**更精炼有力的文字**\n\n"
					"3. **创作要求**：\n"
					"   • 你的新故事应该在**所有维度上都超越参考故事**\n"
					"   • 开篇要**更抓人**，情节要**更紧凑**，反转要**更震撼**\n"
					"   • 人物要**更立体**，情感要**更细腻**，细节要**更丰富**\n"
					"   • 语言要**更流畅**，节奏要**更完美**，结尾要**更震撼**\n"
					"   • 这是你的**代表作**，每一个字都要体现你的最高水准\n\n"
					"4. **创新原则**：\n"
					"   • 如果参考故事用了某个技巧，你可以用**更高明的技巧**\n"
					"   • 如果参考故事有某个亮点，你可以创造**更多亮点**\n"
					"   • 如果参考故事有某个不足，你要**完全避免**这个不足\n"
					"   • 目标是：读者看完你的故事后会说\"这比之前的故事更好！\"\n\n"
					"记住：参考故事是你的**老师**，但你的任务是**超越老师**！\n\n"
				)
			else:
				rag_guidance = (
					"\n【📚 参考资料使用指导】\n"
					"以下是检索到的相关资料，请作为创作参考：\n"
					"• 可以借鉴资料中的情节、人物设定、叙事技巧\n"
					"• 但不要直接复制，需要进行改写与整合\n"
					"• 结合你的创作需求，创造出全新的故事\n\n"
				)
		
		# 构建完整的prompt - 使用列表然后join
		parts = [
			"🚨🚨🚨 **强制要求：你必须像在跟最好的朋友分享你的亲身经历一样写这个故事！** 🚨🚨🚨\n\n",
		]
		
		# 如果用户明确指定了开头，优先使用用户指定的开头
		if explicit_opening:
			parts.append(
				f"🎯🎯🎯 **用户明确指定的开头（最高优先级！必须严格遵守！）** 🎯🎯🎯\n"
				f"用户明确要求：故事必须以以下内容开头：\n"
				f"【{explicit_opening}】\n\n"
				f"⚠️ 重要：\n"
				f"1. 故事的第一句话必须是：{explicit_opening}\n"
				f"2. 不能添加任何前缀，不能修改这句话\n"
				f"3. 这是用户明确要求的，优先级高于所有其他规则\n"
				f"4. 在这句话之后，再按照下面的要求继续写作\n\n"
			)
		
		parts.extend([
			"🎯 **核心目标**：像**用户亲身经历写出来的**，不是创作出来的小说。\n"
			"   • 读者要感觉：\"这是他的真实经历，不是编的\"\n"
			"   • 语言要像：真实的人在回忆和讲述自己的经历\n"
			"   • 细节要像：只有亲身经历的人才有的细节\n"
			"   • 情感要像：真实经历过的人才会有的反应\n\n",
			"⚠️⚠️⚠️ **开头的绝对要求（必须严格遵守！）** ⚠️⚠️⚠️\n",
		])
		
		# 如果用户没有明确指定开头，才应用以下规则
		if not explicit_opening:
			parts.append(
				"1. **开头必须符合故事的时代背景**：\n"
				"   ⚠️ 重要：开头必须符合故事发生的时代背景！\n"
				"   ❌ 如果故事发生在70年代、80年代等没有手机的年代，绝对不能用手机相关开头！\n"
				"   ❌ 如果故事发生在乡村、古代等场景，不能用手机相关开头！\n"
				"   ✅ 只有现代城市故事才可以用手机相关开头，且不能千篇一律！\n"
				"2. **开头必须自然、多样、独特，绝对不能千篇一律**：\n"
				"   ❌ 禁止每次都用同一个开头模式（比如每次都\"手机震动\"、每次都\"手机屏幕亮起\"、每次都\"手机响了\"等）\n"
				"   ❌ 禁止任何重复的开头模式！每次都要用完全不同的开头方式！\n"
				"   ✅ 必须在以下方式中随机选择，且每次都要不同：\n"
				"      • 直入主题：\"我推开宿舍门，看见他坐在我床上。\"、\"我妈给我打电话，说我爸不见了。\"（现代）\n"
				"      • 真实感受：\"说实话，我现在都还记得那个晚上...\"、\"那时候我还不知道，这个决定会改变我的一生。\"\n"
				"      • 突然发生：\"我在平安夜当着所有人的面...\"、\"我从来没想过，会在这个地方遇见他。\"\n"
				"      • 真实对话：\"'你爸不见了。'我妈在电话里哭着说。\"（现代）、\"'你确定要这么做？'他看着我。\"\n"
				"      • 真实场景：\"我推开宿舍门，看见他坐在我床上，手里拿着我的日记。\"、\"那天下雨，我站在车站等车。\"（现代）、\"我推开那扇木门，看见他坐在院子里。\"（乡村）、\"那是个夏天的傍晚，我坐在院子里乘凉。\"（70年代/乡村）\n"
				"      • 真实回忆：\"一支520烟，毁了我三年，也救了我一辈子。\"、\"现在想想，那是我人生中最重要的一天。\"\n"
				"      • 真实状态：\"我刚下班，累得不行，就想着赶紧回家。\"（现代）、\"我那时候还在上学，每天都很忙。\"、\"那时候我还小，每天都要下地干活。\"（70年代/乡村）\n"
				"      • 时间起点：\"三年前，我还在上大学。\"、\"那是一个普通的下午。\"、\"那是1975年的夏天。\"（70年代）\n"
				"      • 如果现代城市故事，可以用手机：\"手机响了，是我妈打来的\"、\"我收到一条短信\"（但要自然，且不能每次都一样）\n"
				"   ⚠️ 写开头前必须：\n"
				"      • 先判断故事的时代背景（70年代？现代？）\n"
				"      • 如果70年代/80年代/乡村/古代等，绝对不能用手机相关开头！\n"
				"      • 如果现代城市故事，可以用手机，但要看最近用过吗？如果用过，换一个！\n"
				"      • 如果用过其他方式，也要换一个完全不同的！\n\n"
			)
		else:
			parts.append(
				"⚠️ 注意：用户已明确指定开头，请严格按照用户指定的开头开始，然后自然过渡到后续内容。\n\n"
			)
		
		parts.extend([
			"⚠️ **核心原则（必须严格遵守）**：\n",
			"1. **这是你的亲身经历**：写的时候要问：如果这件事真的发生在我身上，我会怎么跟朋友说？\n",
			"2. **禁止比喻和文学化**：不能用\"像...一样\"、\"飘得像血\"、\"心跳漏了一拍\"等\n",
			"3. **必须像亲身经历**：记忆模糊（\"可能是我记错了\"）、真实时间感（\"那时候我记得\"）、真实情感（\"我当时真的懵了\"）、真实细节（\"我那天穿着那件黑T恤\"）\n",
			"4. **必须口语化**：多用\"说实话\"、\"真的\"、\"可能是我看错了\"（每300字至少用1次）\n",
			"5. **必须简单直接**：\"头发很长\"而不是\"长发垂到腰际\"，\"我当时真的吓到了\"而不是\"全身血液都凉了\"\n",
			"6. **对话必须短**：\"这什么情况？\"而不是\"这到底是什么情况？\"\n\n",
			"═══════════════════════════════════════\n",
			"🎯 **任务**：用第一人称分享一个真实的故事，像在跟朋友聊天\n",
			"═══════════════════════════════════════\n\n",
			"【核心要求】\n",
			f"1. **字数要求（强制）**：必须写足 {min_chars}-{max_chars} 字，目标 {target} 字。请写够长度，情节充分展开。\n",
			f"2. **种类**：{category}\n",
			f"3. **风格倾向**：{style_part}\n",
			f"4. **创作主题/需求**：{requirement}\n\n",
			"【核心写作要求】\n",
			"1. **这是你的亲身经历**（最重要！）：\n",
			"   ⚠️ 写的时候要问：如果这件事真的发生在我身上，我会怎么跟朋友说？\n",
			"   ⚠️ 必须像：真实的人在回忆和讲述自己的经历，不是创作故事\n",
			"   ⚠️ 必须有不完美：记忆模糊的地方、不确定的地方、可能记错的地方\n",
			"   ⚠️ 必须有真实细节：只有亲身经历的人才有的细节和记忆\n",
			"   ⚠️ 必须有真实情感：真实经历过的人才会有的反应和感受\n\n",
			"2. **情节结构优化（必须严格遵守）**：\n",
			"   📊 **节奏控制**：\n",
			"   • 每200-300字必须有一个小冲突/转折/新信息/悬念（\"钩子\"）\n",
			"   • 每500字必须有一个情绪起伏（紧张→舒缓→更紧张，或开心→低落→更开心）\n",
			"   • 每800字必须有一个情节推进（事情有进展，不是原地踏步）\n",
			"   • 禁止平铺直叙：不能连续500字都没有任何冲突或转折\n\n",
			"   🎢 **冲突设计**：\n",
			"   • 开篇100字内必须有第一个冲突或悬念（立即抓住读者）\n",
			"   • 每个冲突都要有铺垫：重要转折前必须有2-3个细节铺垫\n",
			"   • 冲突要有层次：小冲突→中等冲突→大冲突，逐步升级\n",
			"   • 冲突要有后果：每个冲突都要有结果，不能不了了之\n",
			"   • 冲突要真实：\"他给我打电话，但我没接\"、\"我到了才发现门锁了\"这种真实的小冲突\n\n",
			"   🔄 **反转设置**：\n",
			"   • 每个故事至少要有1-2个反转（读者意想不到的发展）\n",
			"   • 反转必须有铺垫：前面不经意提到的细节，后面成为关键\n",
			"   • 反转要合理：既要意外，又要合理（\"原来是...\"）\n",
			"   • 反转要真实：\"我以为是A，结果是B\"（真实的反转，不是戏剧化的）\n\n",
			"   📈 **情节推进**：\n",
			"   • 每段都要推进情节：不能只是描述，要有事情发生\n",
			"   • 每段都要有新信息：揭示新事实、新人物、新情况\n",
			"   • 每段都要有情感变化：人物情绪要有变化（平静→紧张→恐惧）\n",
			"   • 每段都要有行动：人物要有具体行动，不能只是思考\n\n",
			"   🎯 **悬念设置**：\n",
			"   • 开篇就要有悬念：\"我从来没想过...\"、\"直到那天我才知道...\"\n",
			"   • 每300字埋一个悬念：\"我当时还不知道...\"、\"后来我才明白...\"\n",
			"   • 悬念要逐步揭示：不要一次性全说出来，要慢慢揭示\n",
			"   • 悬念要有答案：每个悬念都要有答案，不能悬而不决\n\n",
			"3. **细节层次优化**：\n",
			"   • **环境细节**：每500字至少3个环境细节（\"那天特别冷\"、\"房间里特别安静\"、\"灯光特别暗\"）\n",
			"   • **动作细节**：每300字至少2个动作细节（\"我推开门\"、\"他抬头看我\"、\"我拿出手机\"）\n",
			"   • **情感细节**：每400字至少1个情感细节（\"我当时真的懵了\"、\"我那时候心跳特别快\"）\n",
			"   • **对话细节**：每500字至少1段对话（推动情节，不是废话）\n",
			"   • 细节要真实：\"我记得那时候特别安静\"、\"我记得他那时候的表情\"\n\n",
			"4. **对话优化**：\n",
			"   • 对话要短：每句话不超过15字（\"你确定？\"、\"我也不知道\"）\n",
			"   • 对话要有信息量：每句话都要推进情节或揭示人物\n",
			"   • 对话要有潜台词：\"你觉得呢？\"（暗示不确定）、\"好吧\"（暗示妥协）\n",
			"   • 对话要有冲突：\"不行\"、\"为什么？\"、\"因为...\"\n",
			"   • 对话要真实：\"我当时真的不知道该怎么办\"、\"说实话，我也没想好\"\n\n",
			"5. **情感递进**：\n",
			"   • 情感要有变化：不能一直保持同一情绪（平静→紧张→恐惧→震惊）\n",
			"   • 情感要有层次：\"我当时有点紧张\"→\"我那时候心跳特别快\"→\"我当时真的吓到了\"\n",
			"   • 情感要真实：\"我当时真的懵了\"、\"说实话，我现在想起来还后怕\"\n",
			"   • 情感要有原因：每个情感变化都要有明确的原因\n\n",
			"6. **每300字一个钩子**：冲突/反转/新信息/悬念，让读者停不下来\n",
			"7. **震撼力来自真实**：真实感让读者更投入，恐怖故事更吓人\n\n",
			f"{category_guidance}\n",
			f"{outline_part}\n\n",
			f"{rag_guidance if contexts else ''}",
			f"{'【参考故事】' if contexts else '【参考资料】'}\n{ctx if ctx else '无特定资料，请根据主题自由创作。'}\n\n",
			"═══════════════════════════════════════\n",
			"🚀 **现在开始创作！拿出你最好的状态！**\n",
			"═══════════════════════════════════════\n\n",
			"🚨 **最后提醒（必须严格遵守！）**：\n",
		])
		
		# 根据是否有明确开头，添加不同的提醒
		if explicit_opening:
			parts.append(
				f"1. **最高优先级：故事的第一句话必须是：{explicit_opening}（用户明确要求，必须严格遵守！）**\n"
				"2. 这是你的亲身经历！写的时候要问：如果这件事真的发生在我身上，我会怎么跟朋友说？\n"
				"3. 写每一句话前都要问：这句话我会说给朋友听吗？如果不会，改！\n"
				"4. 写完后检查：是否像真实的人在回忆和讲述自己的经历，而不是在创作故事？"
			)
		else:
			parts.append(
				"1. **开头必须符合故事的时代背景！**如果故事发生在70年代/80年代/乡村/古代等，绝对不能用手机相关开头！\n"
				"2. **开头绝对不能千篇一律！**每次都要用不同的开头方式，让每个故事的开头都独特自然！\n"
				"3. 如果现代城市故事，可以用手机开头，但要看最近用过吗？如果用过，换一个！\n"
				"4. 这是你的亲身经历！写的时候要问：如果这件事真的发生在我身上，我会怎么跟朋友说？\n"
				"5. 写每一句话前都要问：这句话我会说给朋友听吗？如果不会，改！\n"
				"6. 写完后检查：是否像真实的人在回忆和讲述自己的经历，而不是在创作故事？"
			)
		
		# 组合完整的prompt
		return "".join(parts)


	
