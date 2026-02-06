"""Story功能模块"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, messagebox, filedialog, scrolledtext
import tkinter as tk
from tkinter import ttk
import threading
import re
from pathlib import Path
from dotenv import load_dotenv

from src.clients.deepseek_client import DeepSeekClient
from src.kb.ingest import KnowledgeBaseIngestor, IngestConfig
from src.kb.search import KnowledgeBaseSearcher, SearchConfig
from src.utils.text import sanitize as _sanitize
from ...theme import Theme


class StoryUIBuilderMixin:
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

		# 第一行：种类 + 风格 + 按钮
		row1_frame = tk.Frame(self.story_tab_create, bg="#2b2b2b")
		row1_frame.grid(row=0, column=0, columnspan=2, sticky="we", padx=15, pady=(15, 12))
		
		# 左侧：种类
		tk.Label(row1_frame, text="📚 种类:", font=("", 12, "bold"), bg="#2b2b2b", fg="#ffffff").pack(side=LEFT, padx=(0, 8))
		self.combo_category = ttk.Combobox(row1_frame, textvariable=self.category, width=12, 
										   values=("爱情", "悬疑", "职场", "科幻", "成长", "亲情", "社会观察", "校园", "历史", "奇幻"),
										   font=("", 12))
		self.combo_category.pack(side=LEFT, padx=(0, 20))
		
		# 模型选择
		tk.Label(row1_frame, text="🤖 模型:", font=("", 12, "bold"), bg="#2b2b2b", fg=Theme.TEXT_PRIMARY).pack(side=LEFT, padx=(0, 8))
		self.story_model_var = tk.StringVar(value="claude-sonnet-4-5")
		self.combo_story_model = ttk.Combobox(row1_frame, textvariable=self.story_model_var, width=25,
											  values=["正在加载..."],
											  state="normal", font=("", 11))
		self.combo_story_model.pack(side=LEFT, padx=(0, 20))
		
		# 异步加载模型列表
		self.after(500, self._load_available_models)
		
		# 中间：风格
		tk.Label(row1_frame, text="🎨 风格:", font=("", 12, "bold"), bg="#2b2b2b", fg="#ffffff").pack(side=LEFT, padx=(0, 8))
		self.entry_style = tk.Entry(row1_frame, textvariable=self.style, width=45, font=("", 12),
									 relief=tk.FLAT, borderwidth=0, bg="#1e1e1e", fg="#ffffff",
									 insertbackground="white", selectbackground="#ffffff", selectforeground="#000000",
									 highlightthickness=0)
		self.entry_style.pack(side=LEFT, padx=(0, 6))
		# 修复Entry颜色问题
		if hasattr(self, '_fix_entry_colors'):
			self._fix_entry_colors(self.entry_style)
		self.btn_add_style = tk.Button(row1_frame, text="➕", command=self._show_style_menu,
									   font=("", 11, "bold"), bg="#000000", fg="#ffffff", relief=tk.FLAT,
									   padx=10, pady=4, cursor="hand2", activebackground="#000000", activeforeground="#ffffff")
		self.btn_add_style.pack(side=LEFT, padx=(0, 20))
		
		# 右侧：快捷按钮组
		btn_frame = tk.Frame(row1_frame, bg="#1e1e1e")
		btn_frame.pack(side=RIGHT)
		self.btn_outline = tk.Button(btn_frame, text="📋 生成目录", command=self.on_generate_outline, 
									  font=("", 13, "bold"), bg="#000000", fg="#ffffff", relief=tk.FLAT, 
									  padx=18, pady=10, cursor="hand2", activebackground="#000000", activeforeground="#ffffff")
		self.btn_outline.pack(side=LEFT, padx=4)
		self.btn_generate = tk.Button(btn_frame, text="🚀 生成故事", command=self.on_generate, 
									   font=("", 13, "bold"), bg="#000000", fg="#ffffff", relief=tk.FLAT, 
									   padx=18, pady=10, cursor="hand2", activebackground="#000000", activeforeground="#ffffff")
		self.btn_generate.pack(side=LEFT, padx=4)
		tk.Button(btn_frame, text="💾 保存为...", command=self.on_save_as, font=("", 13, "bold"), 
				  bg="#000000", fg="#ffffff", relief=tk.FLAT, padx=18, pady=10, cursor="hand2", 
				  activebackground="#000000", activeforeground="#ffffff").pack(side=LEFT, padx=4)

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
		self.prompt_text.pack(fill="both", expand=True)
		
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
		
		self.status = tk.StringVar(value="就绪")
		status_bar = ttk.Label(self.story_tab_create, textvariable=self.status, anchor="w")
		status_bar.grid(row=4, column=0, columnspan=2, sticky="we", padx=10, pady=(0, 8))
		
		# 配置行列权重，让output区域可以扩展
		self.story_tab_create.rowconfigure(3, weight=1)

	
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
			f"【创作信息】\n"
			f"- 主题/需求：{requirement}\n"
			f"- 种类：{category}\n"
			f"- 目标字数：{target_chars}字\n\n"
			f"【参考资料】\n{ctx if ctx else '无特定资料'}\n\n"
			"请直接输出章节列表，格式如下：\n"
			"1. 平静的开端\n"
			"2. 意外降临\n"
			"3. 危机爆发\n"
			"4. 绝地反击\n"
			"5. 尘埃落定"
		)

	
	def _build_prompt(self, requirement, contexts, category, outline=""):
		ctx = "\n\n".join(f"【资料{i+1}】\n{c}" for i, c in enumerate(contexts))
		outline_part = ("\n\n请严格参照下述目录完成写作：\n" + outline.strip()) if outline else ""
		style_part = self.style.get().strip()
		target = self.target_chars.get()
		# 计算字数范围
		min_chars = int(target * 0.9)
		max_chars = int(target * 1.1)
		return (
			"请基于以下资料，创作一篇知乎风格的长篇故事/回答。\n\n"
			"【核心要求】\n"
			f"1. **字数要求（强制）**：必须写足 {min_chars}-{max_chars} 字之间，目标 {target} 字。请务必写够长度，不要过早结束。\n"
			f"2. **种类**：{category}\n"
			f"3. **风格倾向**：{style_part}\n"
			f"4. **创作主题/需求**：{requirement}\n\n"
			"【写作规范】\n"
			"- 语言自然口语化，逻辑清晰，富有生活气息；\n"
			"- 不要写标题，直接进入正文；段落衔接自然，避免列表化与生硬小标题；\n"
			"- 开头要抓人，中段有冲突与反转，结尾有观点或反思；\n"
			"- 输出为纯文本，不使用任何 Markdown 标记（不要 #、*、-、**、``` 等）；\n"
			"- 即使参考目录，也不要显式输出分节标题；将要点融合到连续正文中；\n"
			"- 可以适当分段，但段落之间要自然过渡。\n\n"
			"【特别提醒】\n"
			f"请一定要写到至少 {min_chars} 字，不要因为觉得写完了就停止。如果还没达到字数，请继续展开细节、增加情节、深化描写。\n"
			f"{outline_part}\n\n"
			f"【参考资料】\n{ctx if ctx else '无特定资料，请根据主题自由创作。'}"
		)

	
	def _build_section_prompt(self, section, section_index, total_sections, previous_content, requirement, contexts, category, style_part, target_chars_per_section):
		"""构建单个章节的生成提示词"""
		ctx = "\n\n".join(f"【资料{i+1}】\n{c}" for i, c in enumerate(contexts)) if contexts else ""
		
		# 计算本节字数范围
		min_chars = int(target_chars_per_section * 0.85)
		max_chars = int(target_chars_per_section * 1.15)
		
		# 构建章节要点
		section_title = section["title"]
		section_items = "\n".join(f"  - {item}" for item in section["items"]) if section["items"] else ""
		
		# 上下文提示
		context_hint = ""
		if section_index == 0:
			context_hint = "这是故事的开篇部分，需要引人入胜，设置场景和主要人物。"
		elif section_index == total_sections - 1:
			context_hint = f"这是故事的最后部分，需要收尾总结，呼应前文。\n\n前文概要：\n{previous_content[-500:] if previous_content else '无'}"
		else:
			context_hint = f"这是故事的第 {section_index + 1} 部分，需要承上启下，保持情节连贯。\n\n前文最后部分：\n{previous_content[-500:] if previous_content else '无'}"
		
		return (
			f"请继续创作知乎风格故事的第 {section_index + 1}/{total_sections} 部分。\n\n"
			f"【本节要求】\n"
			f"1. **字数**：必须写足 {min_chars}-{max_chars} 字，目标 {target_chars_per_section} 字\n"
			f"2. **章节主题**：{section_title}\n"
			f"3. **要点**：\n{section_items if section_items else '  根据标题自由发挥'}\n"
			f"4. **种类**：{category}\n"
			f"5. **风格**：{style_part}\n\n"
			f"【上下文】\n{context_hint}\n\n"
			f"【写作规范】\n"
			f"- 语言自然口语化，逻辑清晰，富有生活气息\n"
			f"- **不要写章节标题**，直接进入正文内容\n"
			f"- 与前文保持人物、情节、语气的连贯性\n"
			f"- 段落衔接自然，避免列表化\n"
			f"- 输出为纯文本，不使用任何 Markdown 标记\n"
			f"- 如果前文已有内容，本节要自然承接，不要重复前文情节\n\n"
			f"【特别提醒】\n"
			f"请写够 {min_chars} 字以上，展开细节描写和情节发展。\n"
			f"主题/需求：{requirement}\n\n"
			+ (f"【参考资料】\n{ctx}\n" if ctx else "")
			+ "请直接开始写正文，不要任何前缀或标题："
		)


	

	
	def _load_available_models(self):
		"""异步加载可用的模型列表"""
		def task():
			try:
				import requests
				
				# 从配置中获取 API 信息
				if hasattr(self, 'api_presets') and "自定义" in self.api_presets:
					api_config = self.api_presets["自定义"]
					api_key = api_config.get("key", "")
					base_url = api_config.get("base_url", "")
					
					if not api_key or not base_url:
						print("[WARN] API 配置不完整，使用默认模型列表")
						self._set_default_models()
						return
					
					base_url = base_url.rstrip("/")
					candidates = []
					if base_url.endswith("/v1"):
						candidates.append(f"{base_url}/models")
					else:
						candidates.append(f"{base_url}/v1/models")
						candidates.append(f"{base_url}/models")
					
					# 调用 API 获取模型列表
					headers = {
						"Authorization": f"Bearer {api_key}",
						"User-Agent": "Mozilla/5.0"
					}
					last_status = None
					result = None
					for url in candidates:
						try:
							response = requests.get(url, headers=headers, timeout=10)
							last_status = response.status_code
							if response.status_code == 200:
								result = response.json()
								break
						except Exception:
							continue
					
					if result is not None:
						models = []
						if isinstance(result, dict):
							if isinstance(result.get("data"), list):
								models = [m.get("id") or m.get("name") for m in result["data"] if isinstance(m, dict)]
							elif isinstance(result.get("models"), list):
								models = [m.get("id") or m.get("name") for m in result["models"] if isinstance(m, dict)]
						elif isinstance(result, list):
							models = [m.get("id") or m.get("name") for m in result if isinstance(m, dict)]
						
						models = [m for m in models if m]
						if models:
							# 更新故事生成页面的下拉框
							if hasattr(self, 'combo_story_model'):
								self._ui(self.combo_story_model.__setitem__, 'values', models)
								current = self._ui_get(self.story_model_var.get) if hasattr(self, '_ui_get') else self.story_model_var.get()
								if current not in models:
									self._ui(self.story_model_var.set, models[0])
							
							# 更新人物生成页面的下拉框
							if hasattr(self, 'combo_char_model'):
								self._ui(self.combo_char_model.__setitem__, 'values', models)
								current = self._ui_get(self.char_model_var.get) if hasattr(self, '_ui_get') else self.char_model_var.get()
								if current not in models:
									self._ui(self.char_model_var.set, models[0])
							
							print(f"[OK] 已加载 {len(models)} 个可用模型（故事生成 + 人物生成）")
						else:
							print("[WARN] API 响应未包含模型列表，使用默认模型列表")
							self._set_default_models()
					else:
						print(f"[WARN] 获取模型列表失败 ({last_status})，使用默认模型列表")
						self._set_default_models()
				else:
					print("[WARN] 未找到自定义 API 配置，使用默认模型列表")
					self._set_default_models()
					
			except Exception as e:
				print(f"[WARN] 加载模型列表出错: {e}")
				self._set_default_models()
		
		# 在后台线程中执行
		threading.Thread(target=task, daemon=True).start()
	
	
	def _set_default_models(self):
		"""设置默认模型列表（当无法从 API 获取时）"""
		def _ui_call(func, *args):
			if hasattr(self, '_ui'):
				return self._ui(func, *args)
			return func(*args)

		default_models = [
			"claude-sonnet-4-5",
			"claude-sonnet-4-5-20250929",
			"claude-sonnet-4",
			"gemini-3-pro-preview",
			"gemini-3-flash-preview",
			"gemini-2.5-pro",
			"gemini-2.5-flash",
			"gpt-4o",
			"gpt-4o-mini",
		]
		
		# 更新故事生成页面
		if hasattr(self, 'combo_story_model'):
			_ui_call(self.combo_story_model.__setitem__, 'values', default_models)
			
			# 如果当前值不在列表中，设置为第一个
			current = self._ui_get(self.story_model_var.get) if hasattr(self, '_ui_get') else self.story_model_var.get()
			if current not in default_models:
				_ui_call(self.story_model_var.set, default_models[0])
		
		# 更新人物生成页面
		if hasattr(self, 'combo_char_model'):
			_ui_call(self.combo_char_model.__setitem__, 'values', default_models)
			
			# 如果当前值不在列表中，设置为第一个
			current = self._ui_get(self.char_model_var.get) if hasattr(self, '_ui_get') else self.char_model_var.get()
			if current not in default_models:
				_ui_call(self.char_model_var.set, default_models[0])
			
		print(f"[INFO] 使用默认模型列表 ({len(default_models)} 个)")

