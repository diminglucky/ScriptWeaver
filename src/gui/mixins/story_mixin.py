"""
Story相关功能模块
"""

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
from ..utils import sanitize as _sanitize


class StoryMixin:
	"""Story管理功能"""
	
	def _build_story_page(self) -> None:
		"""构建故事生成页面"""

		# 创建内部标签页
		self.story_notebook = ttk.Notebook(self.page_story)
		self.story_notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)
		
		# 创建各个子页面
		self.story_tab_create = tk.Frame(self.story_notebook, bg="#2b2b2b")
		self.story_tab_setup = tk.Frame(self.story_notebook, bg="#2b2b2b")
		
		self.story_notebook.add(self.story_tab_create, text="  ✍️ 创作  ")
		self.story_notebook.add(self.story_tab_setup, text="  ⚙️ 配置  ")
		
		# 构建各个子页面
		self._build_story_create_tab()
		self._build_story_setup_tab()
	
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
		
		# 中间：风格
		tk.Label(row1_frame, text="🎨 风格:", font=("", 12, "bold"), bg="#2b2b2b", fg="#ffffff").pack(side=LEFT, padx=(0, 8))
		self.entry_style = tk.Entry(row1_frame, textvariable=self.style, width=20, font=("", 12),
									 relief=tk.FLAT, borderwidth=0, bg="#1e1e1e", fg="#ffffff",
									 insertbackground="white", selectbackground="#ffffff", selectforeground="#000000",
									 highlightthickness=0)
		self.entry_style.pack(side=LEFT, padx=(0, 6))
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
		style.configure('Chapter.TCombobox', foreground='#ffffff', fieldbackground='#000000', background='#000000', 
						borderwidth=0, relief='flat')
		style.map('Chapter.TCombobox', 
				  fieldbackground=[('readonly', '#000000')],
				  selectbackground=[('readonly', '#000000')],
				  selectforeground=[('readonly', '#ffffff')])
		
		chapter_frame = tk.Frame(self.story_tab_create, bg="#2b2b2b")
		chapter_frame.grid(row=2, column=1, sticky="we", padx=(0, 15), pady=(0, 15))
		
		self.section_selector = ttk.Combobox(chapter_frame, textvariable=self.current_section_index, 
											 state="readonly", font=("", 14), 
											 style='Chapter.TCombobox')
		self.section_selector.pack(side=LEFT, fill="both", expand=True, padx=(0, 10))
		self.section_selector['values'] = ["请先生成目录"]
		
		# 配置下拉列表的样式
		self.option_add('*TCombobox*Listbox.font', ('', 14))
		self.option_add('*TCombobox*Listbox.foreground', '#ffffff')
		self.option_add('*TCombobox*Listbox.background', '#000000')
		self.option_add('*TCombobox*Listbox.selectBackground', '#ffffff')
		self.option_add('*TCombobox*Listbox.selectForeground', '#000000')
		
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

	def on_generate_outline(self) -> None:
		requirement = self._get_prompt_content()
		if not requirement:
			messagebox.showwarning("提示", "请先输入创作需求/主题")
			return
		
		# 获取选中的目录生成API配置
		selected_api = self.outline_gen_api.get() if hasattr(self, 'outline_gen_api') else "DeepSeek"
		if selected_api not in self.api_presets:
			messagebox.showerror("错误", f"未找到API预设: {selected_api}")
			return
		
		api_config = self.api_presets[selected_api]
		api_key = _sanitize(api_config.get("key", ""))
		if not api_key:
			messagebox.showwarning("提示", f"API Key 为空，请在'基础 API 配置'中为 {selected_api} 填写后保存")
			return
		
		if self.model_only.get():
			self._generate_outline_model_only(requirement)
			return
		need_build = False
		index_path = Path(self.index_dir.get()) / "kb.index"
		if not index_path.exists():
			if messagebox.askyesno("提示", "未找到索引，是否现在根据当前数据目录自动构建？"):
				need_build = True
			else:
				return
		def task():
			try:
				self.set_busy(True)
				self.status.set(f"使用 {selected_api} 检索素材并生成目录中...")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("正在生成目录...", "📝")
				
				load_dotenv()
				if need_build:
					if hasattr(self, 'update_header_status'):
						self.update_header_status("正在构建索引...", "⏳")
					cfg = IngestConfig(data_root=Path(self.data_dir.get()), index_dir=Path(self.index_dir.get()))
					KnowledgeBaseIngestor(cfg).build()
				
				if hasattr(self, 'update_header_status'):
					self.update_header_status("检索资料中...", "🔍")
				searcher = KnowledgeBaseSearcher(SearchConfig(index_dir=Path(self.index_dir.get()), top_k=self.top_k.get()))
				results = searcher.search(requirement, self.top_k.get())
				contexts = [c for c, _s, _m in results]
				
				# 使用选中的API配置
				if hasattr(self, 'update_header_status'):
					self.update_header_status("AI生成目录中...", "📝")
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				outline_prompt = self._build_outline_prompt(requirement, contexts, self.category.get())
				self.output.delete("1.0", END)
				self.output.insert(END, "生成目录中...\n\n")
				outline_text = client.chat([
					{"role": "system", "content": "你是资深知乎创作者与编辑。请先产出结构化目录，不要写正文。"},
					{"role": "user", "content": outline_prompt},
				], temperature=max(0.4, self.temperature.get() - 0.2))
				self.current_outline = outline_text.strip()
				estimate = self._estimate_chars(self.current_outline)
				
				# 解析章节并更新选择器
				self.parsed_sections = self._parse_outline_sections(self.current_outline)
				self._update_section_selector()
				
				self.output.insert(END, f"目录（共{len(self.parsed_sections)}章，预估字数≈{estimate}字）\n\n{self.current_outline}\n\n")
				self.status.set("目录已生成")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("目录生成完成", "✅")
			except Exception as e:
				import traceback
				self.output.insert(END, "生成目录出错:\n" + traceback.format_exc() + "\n")
				messagebox.showerror("错误", str(e))
				self.status.set("生成目录失败")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("生成目录失败", "❌")
			finally:
				self.set_busy(False)
		threading.Thread(target=task, daemon=True).start()

	def on_generate(self) -> None:
		query = self._get_prompt_content()
		if not query:
			messagebox.showwarning("提示", "请先输入创作需求/主题")
			return
		
		# 获取选中的故事生成API配置
		selected_api = self.story_gen_api.get() if hasattr(self, 'story_gen_api') else "DeepSeek"
		if selected_api not in self.api_presets:
			messagebox.showerror("错误", f"未找到API预设: {selected_api}")
			return
		
		api_config = self.api_presets[selected_api]
		api_key = _sanitize(api_config.get("key", ""))
		if not api_key:
			messagebox.showwarning("提示", f"API Key 为空，请在'基础 API 配置'中为 {selected_api} 填写后保存")
			return
		
		if self.model_only.get():
			self._generate_model_only(query)
			return
		need_build = False
		index_path = Path(self.index_dir.get()) / "kb.index"
		if not index_path.exists():
			if messagebox.askyesno("提示", "未找到索引，是否现在根据当前数据目录自动构建？"):
				need_build = True
			else:
				return
		def task():
			try:
				self.set_busy(True)
				self.status.set(f"使用 {selected_api} 检索素材并生成正文中...")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("准备生成故事...", "📝")
				
				load_dotenv()
				if need_build:
					if hasattr(self, 'update_header_status'):
						self.update_header_status("正在构建索引...", "⏳")
					cfg = IngestConfig(data_root=Path(self.data_dir.get()), index_dir=Path(self.index_dir.get()))
					KnowledgeBaseIngestor(cfg).build()
				
				if hasattr(self, 'update_header_status'):
					self.update_header_status("检索资料中...", "🔍")
				searcher = KnowledgeBaseSearcher(SearchConfig(index_dir=Path(self.index_dir.get()), top_k=self.top_k.get()))
				results = searcher.search(query, self.top_k.get())
				contexts = [c for c, _s, _m in results]
				
				# 使用选中的API配置
				if hasattr(self, 'update_header_status'):
					self.update_header_status("AI创作故事中...", "📝")
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				self.output.delete("1.0", END)
				
				# 检查是否需要分段生成
				target_chars = self.target_chars.get()
				sections = self._parse_outline_sections(self.current_outline) if self.current_outline else []
				
				# 如果字数 > 8000 且有目录，则分段生成
				if target_chars > 8000 and sections:
					self._generate_in_sections(client, query, contexts, sections, target_chars)
				else:
					# 一次性生成（原逻辑）
					self.output.insert(END, "生成中...\n\n")
					prompt = self._build_prompt(query, contexts, self.category.get(), self.current_outline)
					for delta in client.stream([
						{"role": "system", "content": "你是资深知乎创作者，擅长结合资料写出有观点、有结构的中文故事。"},
						{"role": "user", "content": prompt},
					], temperature=self.temperature.get(), max_tokens=int(target_chars*2.5)):
						self.output.insert(END, delta)
						self.output.see(END)
				
				self.status.set("生成完成")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("故事生成完成", "✅")
				# 自动保存到当前项目
				self._auto_save_to_project()
			except Exception as e:
				import traceback
				self.output.insert(END, "生成出错:\n" + traceback.format_exc() + "\n")
				messagebox.showerror("错误", str(e))
				self.status.set("生成失败")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("生成故事失败", "❌")
			finally:
				self.set_busy(False)
		threading.Thread(target=task, daemon=True).start()

	def on_generate_section(self) -> None:
		"""生成选中的章节"""
		if not self.parsed_sections:
			messagebox.showwarning("提示", "请先生成目录")
			return
		
		query = self._get_prompt_content()
		if not query:
			messagebox.showwarning("提示", "请先输入创作需求/主题")
			return
		
		if not (_sanitize(self.api_key.get())):
			messagebox.showwarning("提示", "API Key 为空")
			return
		
		# 获取选中的章节索引
		selected_index = self.section_selector.current()
		if selected_index < 0:
			messagebox.showwarning("提示", "请选择要生成的章节")
			return
		
		# 启动生成
		if self.model_only.get():
			self._generate_single_section(query, [], selected_index)
		else:
			# 带知识库检索
			need_build = False
			index_path = Path(self.index_dir.get()) / "kb.index"
			if not index_path.exists():
				if messagebox.askyesno("提示", "未找到索引，是否现在构建？"):
					need_build = True
				else:
					return
			
			def task():
				try:
					self.set_busy(True)
					load_dotenv()
					if need_build:
						cfg = IngestConfig(data_root=Path(self.data_dir.get()), index_dir=Path(self.index_dir.get()))
						KnowledgeBaseIngestor(cfg).build()
					searcher = KnowledgeBaseSearcher(SearchConfig(index_dir=Path(self.index_dir.get()), top_k=self.top_k.get()))
					results = searcher.search(query, self.top_k.get())
					contexts = [c for c, _s, _m in results]
					self._generate_single_section_with_contexts(query, contexts, selected_index)
				except Exception as e:
					import traceback
					self.output.insert(END, "\n生成出错:\n" + traceback.format_exc() + "\n")
					messagebox.showerror("错误", str(e))
				finally:
					self.set_busy(False)
			threading.Thread(target=task, daemon=True).start()
	
	def on_continue_next_section(self) -> None:
		"""继续生成下一章"""
		current_index = self.section_selector.current()
		if current_index < 0:
			messagebox.showwarning("提示", "请先选择当前章节")
			return
		
		next_index = current_index + 1
		if next_index >= len(self.parsed_sections):
			messagebox.showinfo("提示", "已经是最后一章了！")
			return
		
		# 自动选中下一章
		self.section_selector.current(next_index)
		
		# 直接生成
		self.on_generate_section()
	
	def on_auto_generate_all(self) -> None:
		"""自动连续生成所有章节"""
		if not self.parsed_sections:
			messagebox.showwarning("提示", "请先生成目录")
			return
		
		query = self._get_prompt_content()
		if not query:
			messagebox.showwarning("提示", "请先输入创作需求/主题")
			return
		
		if not (_sanitize(self.api_key.get())):
			messagebox.showwarning("提示", "API Key 为空")
			return
		
		# 确认开始
		total_chapters = len(self.parsed_sections)
		current_index = self.section_selector.current()
		start_index = max(0, current_index)
		
		confirm = messagebox.askyesno(
			"确认自动生成",
			f"将从第 {start_index + 1} 章开始，自动连续生成到第 {total_chapters} 章。\n\n"
			f"共需生成 {total_chapters - start_index} 章，可能需要较长时间。\n\n"
			f"期间请勿关闭窗口，是否继续？"
		)
		
		if not confirm:
			return
		
		# 启动自动生成
		if self.model_only.get():
			self._auto_generate_all_sections(query, [], start_index)
		else:
			# 带知识库检索
			need_build = False
			index_path = Path(self.index_dir.get()) / "kb.index"
			if not index_path.exists():
				if messagebox.askyesno("提示", "未找到索引，是否现在构建？"):
					need_build = True
				else:
					return
			
			def task():
				try:
					self.set_busy(True)
					load_dotenv()
					if need_build:
						cfg = IngestConfig(data_root=Path(self.data_dir.get()), index_dir=Path(self.index_dir.get()))
						KnowledgeBaseIngestor(cfg).build()
					searcher = KnowledgeBaseSearcher(SearchConfig(index_dir=Path(self.index_dir.get()), top_k=self.top_k.get()))
					results = searcher.search(query, self.top_k.get())
					contexts = [c for c, _s, _m in results]
					self._auto_generate_all_sections_with_contexts(query, contexts, start_index)
				except Exception as e:
					import traceback
					self.output.insert(END, "\n自动生成出错:\n" + traceback.format_exc() + "\n")
					messagebox.showerror("错误", str(e))
				finally:
					self.set_busy(False)
			threading.Thread(target=task, daemon=True).start()
	
	def _generate_outline_model_only(self, requirement) -> None:
		def task():
			try:
				self.set_busy(True)
				
				# 获取选中的目录生成API配置
				selected_api = self.outline_gen_api.get() if hasattr(self, 'outline_gen_api') else "DeepSeek"
				if selected_api not in self.api_presets:
					messagebox.showerror("错误", f"未找到API预设: {selected_api}")
					return
				
				api_config = self.api_presets[selected_api]
				api_key = _sanitize(api_config.get("key", ""))
				
				self.status.set(f"使用 {selected_api} 生成目录中...")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("AI生成目录中...", "📝")
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
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
				
				prompt = (
					"请产出一个简洁的写作目录（仅目录，不要正文）。\n\n"
					"【核心要求】\n"
					f"- 只输出 {suggested_sections} 个主要章节标题，不要子标题、不要要点列表\n"
					"- 每个章节用数字编号（1. 2. 3. ...）\n"
					"- 章节名简短有力（5-10字），能体现故事发展\n"
					"- 结构要符合：开端 → 发展 → 高潮 → 结局\n"
					"- 不要写\"第一章\"、\"第二章\"，直接写章节内容主题\n\n"
					f"【创作信息】\n"
					f"- 主题/需求：{requirement}\n"
					f"- 种类：{self.category.get()}\n"
					f"- 目标字数：{target_chars}字\n\n"
					"请直接输出章节列表，格式如下：\n"
					"1. 平静的开端\n"
					"2. 意外降临\n"
					"3. 危机爆发\n"
					"4. 绝地反击\n"
					"5. 尘埃落定"
				)
				self.output.delete("1.0", END)
				self.output.insert(END, "生成目录中...\n\n")
				outline_text = client.chat([
					{"role": "system", "content": "你是资深知乎创作者与编辑。请先产出结构化目录，不要写正文。"},
					{"role": "user", "content": prompt},
				], temperature=max(0.4, self.temperature.get() - 0.2))
				self.current_outline = outline_text.strip()
				estimate = self._estimate_chars(self.current_outline)
				
				# 解析章节并更新选择器
				self.parsed_sections = self._parse_outline_sections(self.current_outline)
				self._update_section_selector()
				
				self.output.insert(END, f"目录（共{len(self.parsed_sections)}章，预估字数≈{estimate}字）\n\n{self.current_outline}\n\n")
				self.status.set("目录已生成")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("目录生成完成", "✅")
			except Exception as e:
				messagebox.showerror("错误", str(e))
				self.status.set("生成目录失败")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("生成目录失败", "❌")
			finally:
				self.set_busy(False)
		threading.Thread(target=task, daemon=True).start()

	def _generate_model_only(self, query) -> None:
		def task():
			try:
				self.set_busy(True)
				
				# 获取选中的故事生成API配置
				selected_api = self.story_gen_api.get() if hasattr(self, 'story_gen_api') else "DeepSeek"
				if selected_api not in self.api_presets:
					messagebox.showerror("错误", f"未找到API预设: {selected_api}")
					return
				
				api_config = self.api_presets[selected_api]
				api_key = _sanitize(api_config.get("key", ""))
				
				self.status.set(f"使用 {selected_api} 准备生成...")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("AI创作故事中...", "📝")
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				self.output.delete("1.0", END)
				
				# 检查是否需要分段生成
				target_chars = self.target_chars.get()
				sections = self._parse_outline_sections(self.current_outline) if self.current_outline else []
				
				# 如果字数 > 8000 且有目录，则分段生成
				if target_chars > 8000 and sections:
					self._generate_in_sections(client, query, [], sections, target_chars)
				else:
					# 一次性生成（原逻辑）
					self.output.insert(END, "生成中...\n\n")
					prompt = self._build_prompt(query, [], self.category.get(), self.current_outline)
					for delta in client.stream([
						{"role": "system", "content": "你是资深知乎创作者，擅长结合资料写出有观点、有结构的中文故事。"},
						{"role": "user", "content": prompt},
					], temperature=self.temperature.get(), max_tokens=int(target_chars*2.5)):
						self.output.insert(END, delta)
						self.output.see(END)
				
				self.status.set("生成完成")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("故事生成完成", "✅")
				# 自动保存到当前项目
				self._auto_save_to_project()
			except Exception as e:
				import traceback
				self.output.insert(END, "\n\n生成出错:\n" + traceback.format_exc() + "\n")
				messagebox.showerror("错误", str(e))
				self.status.set("生成失败")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("生成故事失败", "❌")
			finally:
				self.set_busy(False)
		threading.Thread(target=task, daemon=True).start()
	
	def _generate_in_sections(self, client, requirement, contexts, sections, target_chars) -> None:
		"""分段生成长文本"""
		total_sections = len(sections)
		target_per_section = int(target_chars / total_sections)
		
		self.output.insert(END, f"📖 开始分段生成（共{total_sections}段，目标总字数{target_chars}字）\n\n")
		self.output.insert(END, "=" * 50 + "\n\n")
		
		accumulated_content = ""
		style_part = self.style.get().strip()
		category = self.category.get()
		
		for idx, section in enumerate(sections):
			# 更新状态
			self.status.set(f"生成第 {idx+1}/{total_sections} 段: {section['title']}")
			self.output.insert(END, f"【正在生成第 {idx+1}/{total_sections} 段】\n\n")
			self.output.see(END)
			# 更新顶部状态栏
			if hasattr(self, 'update_header_status'):
				self.update_header_status(f"生成中 ({idx+1}/{total_sections})", "📝")
			
			# 构建本段提示词
			section_prompt = self._build_section_prompt(
				section=section,
				section_index=idx,
				total_sections=total_sections,
				previous_content=accumulated_content,
				requirement=requirement,
				contexts=contexts,
				category=category,
				style_part=style_part,
				target_chars_per_section=target_per_section
			)
			
			# 流式生成本段
			section_content = ""
			for delta in client.stream([
				{"role": "system", "content": "你是资深知乎创作者，擅长结合资料写出有观点、有结构的中文故事。"},
				{"role": "user", "content": section_prompt},
			], temperature=self.temperature.get(), max_tokens=int(target_per_section*2.5)):
				self.output.insert(END, delta)
				self.output.see(END)
				section_content += delta
			
			# 累积内容（用于下一段的上下文）
			accumulated_content += section_content
			
			# 段落分隔
			if idx < total_sections - 1:
				self.output.insert(END, "\n\n")
				self.output.see(END)
		
		# 完成提示
		final_length = len(accumulated_content)
		self.output.insert(END, f"\n\n" + "=" * 50 + "\n")
		self.output.insert(END, f"✅ 生成完成！总字数：{final_length} 字\n")
		self.status.set(f"生成完成（{final_length} 字）")

	def _generate_single_section(self, query: str, contexts: list[str], section_index: int) -> None:
		"""生成单个章节（无知识库）"""
		def task():
			try:
				self.set_busy(True)
				
				# 获取选中的故事生成API配置
				selected_api = self.story_gen_api.get() if hasattr(self, 'story_gen_api') else "DeepSeek"
				if selected_api not in self.api_presets:
					messagebox.showerror("错误", f"未找到API预设: {selected_api}")
					return
				
				api_config = self.api_presets[selected_api]
				api_key = _sanitize(api_config.get("key", ""))
				
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				self._do_generate_section(client, query, contexts, section_index)
			except Exception as e:
				import traceback
				self.output.insert(END, "\n生成出错:\n" + traceback.format_exc() + "\n")
				messagebox.showerror("错误", str(e))
			finally:
				self.set_busy(False)
		threading.Thread(target=task, daemon=True).start()
	
	def _generate_single_section_with_contexts(self, query: str, contexts: list[str], section_index: int) -> None:
		"""生成单个章节（带知识库）"""
		# 获取选中的故事生成API配置
		selected_api = self.story_gen_api.get() if hasattr(self, 'story_gen_api') else "DeepSeek"
		if selected_api not in self.api_presets:
			messagebox.showerror("错误", f"未找到API预设: {selected_api}")
			return
		
		api_config = self.api_presets[selected_api]
		api_key = _sanitize(api_config.get("key", ""))
		
		client = DeepSeekClient(
			api_key=api_key,
			base_url=_sanitize(api_config.get("base_url", "")),
			model=_sanitize(api_config.get("model", "")),
		)
		self._do_generate_section(client, query, contexts, section_index)
	
	def _do_generate_section(self, client, query, contexts, section_index):
		"""实际执行章节生成的核心逻辑"""
		section = self.parsed_sections[section_index]
		total_sections = len(self.parsed_sections)
		
		# 计算本章字数
		target_chars = self.target_chars.get()
		target_per_section = int(target_chars / total_sections)
		
		# 读取当前已有内容作为上下文
		current_output = self.output.get("1.0", END).strip()
		# 提取已生成的故事内容（排除目录部分）
		if "目录" in current_output and "\n\n" in current_output:
			parts = current_output.split("\n\n", 2)
			if len(parts) >= 3:
				self.generated_content = parts[2]  # 跳过"生成目录中..."和目录本身
			elif len(parts) == 2:
				self.generated_content = current_output.split(self.current_outline)[-1].strip()
		
		# 更新状态
		self.status.set(f"生成第 {section_index+1}/{total_sections} 章: {section['title']}")
		# 更新顶部状态栏
		if hasattr(self, 'update_header_status'):
			self.update_header_status(f"生成章节 ({section_index+1}/{total_sections})", "📝")
		self.output.insert(END, f"\n{'='*50}\n")
		self.output.insert(END, f"【第 {section_index+1}/{total_sections} 章：{section['title']}】\n\n")
		self.output.see(END)
		
		# 构建提示词
		section_prompt = self._build_section_prompt(
			section=section,
			section_index=section_index,
			total_sections=total_sections,
			previous_content=self.generated_content,
			requirement=query,
			contexts=contexts,
			category=self.category.get(),
			style_part=self.style.get().strip(),
			target_chars_per_section=target_per_section
		)
		
		# 流式生成
		section_content = ""
		for delta in client.stream([
			{"role": "system", "content": "你是资深知乎创作者，擅长结合资料写出有观点、有结构的中文故事。"},
			{"role": "user", "content": section_prompt},
		], temperature=self.temperature.get(), max_tokens=int(target_per_section*2.5)):
			self.output.insert(END, delta)
			self.output.see(END)
			section_content += delta
		
		# 累积内容
		self.generated_content += "\n\n" + section_content
		
		# 完成提示
		self.output.insert(END, f"\n\n{'='*50}\n")
		self.output.insert(END, f"✅ 第 {section_index+1} 章完成！本章字数：{len(section_content)} 字\n")
		self.status.set(f"第 {section_index+1} 章完成（{len(section_content)} 字）")
		# 更新顶部状态栏
		if hasattr(self, 'update_header_status'):
			self.update_header_status(f"第 {section_index+1} 章完成", "✅")
		
		# 自动保存
		self._auto_save_to_project()
	
	def _auto_generate_all_sections(self, query, contexts, start_index=0):
		"""自动生成所有章节（无知识库）"""
		def task():
			try:
				self.set_busy(True)
				
				# 获取选中的故事生成API配置
				selected_api = self.story_gen_api.get() if hasattr(self, 'story_gen_api') else "DeepSeek"
				if selected_api not in self.api_presets:
					messagebox.showerror("错误", f"未找到API预设: {selected_api}")
					return
				
				api_config = self.api_presets[selected_api]
				api_key = _sanitize(api_config.get("key", ""))
				
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				
				total_sections = len(self.parsed_sections)
				for idx in range(start_index, total_sections):
					# 更新选择器
					self.section_selector.current(idx)
					
					# 生成当前章节
					self._do_generate_section(client, query, contexts, idx)
					
					# 如果不是最后一章，添加提示
					if idx < total_sections - 1:
						self.output.insert(END, f"\n\n⏳ 准备生成下一章...\n\n")
						self.output.see(END)
				
				# 全部完成
				self.output.insert(END, f"\n\n{'='*50}\n")
				self.output.insert(END, f"🎉 全部章节生成完成！共 {total_sections} 章，总字数：{len(self.generated_content)} 字\n")
				self.status.set(f"全部完成（{len(self.generated_content)} 字）")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("全部章节完成", "✅")
				messagebox.showinfo("完成", f"所有章节已生成完成！\n\n共 {total_sections} 章，总字数：{len(self.generated_content)} 字")
			except Exception as e:
				import traceback
				self.output.insert(END, "\n自动生成出错:\n" + traceback.format_exc() + "\n")
				messagebox.showerror("错误", str(e))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("自动生成失败", "❌")
			finally:
				self.set_busy(False)
		threading.Thread(target=task, daemon=True).start()
	
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
			f"{f'【参考资料】\n{ctx}\n' if ctx else ''}"
			f"请直接开始写正文，不要任何前缀或标题："
		)


	def _update_section_selector(self) -> None:
		"""更新章节选择器"""
		if not self.parsed_sections:
			self.section_selector['values'] = ["请先生成目录"]
			self.btn_generate_section.config(state=DISABLED)
			self.btn_continue_next.config(state=DISABLED)
			return
		
		# 构建章节选项列表
		section_options = []
		for idx, section in enumerate(self.parsed_sections):
			title = section['title']
			section_options.append(f"{idx+1}. {title}")
		
		self.section_selector['values'] = section_options
		self.section_selector.current(0)  # 默认选中第一章
		self.btn_generate_section.config(state=NORMAL)
		self.btn_continue_next.config(state=NORMAL)
		
		# 重置生成内容
		self.generated_content = ""
		
		self.status.set(f"已解析 {len(self.parsed_sections)} 个章节，可开始逐章生成")
	
	def on_save_as(self) -> None:
		content = self.output.get("1.0", END).strip()
		if not content:
			messagebox.showwarning("提示", "当前没有可保存的内容")
			return
		path = filedialog.asksaveasfilename(defaultextension=".md", filetypes=[
			("Markdown", "*.md"),
			("Text", "*.txt"),
			("All Files", "*.*"),
		])
		if not path:
			return
		try:
			with open(path, "w", encoding="utf-8") as f:
				f.write(content)
			messagebox.showinfo("成功", f"已保存到: {path}")
		except Exception as e:
			messagebox.showerror("错误", str(e))

	def on_clear_output(self) -> None:
		self.output.delete("1.0", END)
		self.status.set("输出已清空")

	def on_copy_output(self) -> None:
		text = self.output.get("1.0", END)
		self.clipboard_clear()
		self.clipboard_append(text)
		self.status.set("内容已复制到剪贴板")
	
	def _save_story_assist_api_config(self) -> None:
		"""保存故事创作功能API配置（目录生成和故事生成）"""
		try:
			from pathlib import Path
			from dotenv import find_dotenv, set_key
			from dotenv import load_dotenv
			
			env_path_str = find_dotenv(usecwd=True)
			if not env_path_str:
				env_path = Path.cwd() / ".env"
			else:
				env_path = Path(env_path_str)
			env_path.touch(exist_ok=True)
			
			# 保存目录生成API
			if hasattr(self, 'outline_gen_api'):
				set_key(str(env_path), "STORY_OUTLINE_GEN_API", self.outline_gen_api.get())
			
			# 保存故事生成API
			if hasattr(self, 'story_gen_api'):
				set_key(str(env_path), "STORY_STORY_GEN_API", self.story_gen_api.get())
			
			load_dotenv(override=True)
			messagebox.showinfo("成功", f"已保存故事创作功能API配置\n\n目录生成: {self.outline_gen_api.get()}\n故事生成: {self.story_gen_api.get()}")
		except Exception as e:
			messagebox.showerror("错误", f"保存配置失败: {str(e)}")
	
	def on_test_story_api(self) -> None:
		"""测试故事生成API（输出到配置页面的测试日志）"""
		try:
			self.set_busy(True)
			self.status.set("测试故事生成 API 中...")
			
			# 确保使用故事配置页面的日志框
			if not hasattr(self, 'story_test_log'):
				messagebox.showwarning(
					"提示", 
					"请先切换到【故事生成 → 配置】标签页，\n"
					"以便在该页面查看详细的测试日志。"
				)
				return
			
			log_widget = self.story_test_log
			# 清空之前的日志
			log_widget.delete("1.0", END)
			import datetime
			timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			log_widget.insert(END, f"[{timestamp}] 开始测试故事生成API...\n")
			
			from ..utils import sanitize as _sanitize, try_chat_api as _try_chat
			
			key = _sanitize(self.api_key.get())
			base = _sanitize(self.base_url.get())
			model = _sanitize(self.model.get()) or "deepseek-chat"
			
			if not key:
				messagebox.showwarning("警告", "请先填写API Key")
				self.status.set("测试失败：缺少API Key")
				log_widget.insert(END, "❌ 错误: 缺少API Key\n")
				return
			
			if not base:
				messagebox.showwarning("警告", "请先填写Base URL")
				self.status.set("测试失败：缺少Base URL")
				log_widget.insert(END, "❌ 错误: 缺少Base URL\n")
				return
			
			# 记录测试参数
			log_widget.insert(END, f"\n📋 测试参数:\n")
			log_widget.insert(END, f"  • Model: {model}\n")
			log_widget.insert(END, f"  • API Key: {'*' * (len(key)-8) + key[-8:] if len(key) > 8 else '***'}\n")
			
			candidates = []
			# try user-provided
			candidates.append(base.rstrip("/"))
			# also try toggling /v1 suffix
			if base.rstrip("/").endswith("/v1"):
				candidates.append(base.rstrip("/")[:-3])
			else:
				candidates.append(base.rstrip("/") + "/v1")
			
			log_widget.insert(END, f"\n🔍 尝试的Base URL:\n")
			
			tried_msgs: list[str] = []
			for i, b in enumerate(candidates, 1):
				log_widget.insert(END, f"\n[{i}/{len(candidates)}] 测试: {b}\n")
				log_widget.update()
				
				ok, msg = _try_chat(key, b, model)
				tried_msgs.append(f"base_url={b} -> {'SUCCESS' if ok else 'FAIL'}: {msg}")
				
				if ok:
					log_widget.insert(END, f"✅ 成功: {msg}\n")
				else:
					log_widget.insert(END, f"❌ 失败: {msg}\n")
				
				if ok:
					self.base_url.set(b)
					log_widget.insert(END, f"\n🎉 测试成功！已自动更新Base URL为: {b}\n")
					messagebox.showinfo("测试成功", f"故事生成 API 可用\n{b}")
					self.status.set("故事API可用")
					return
			
			# all failed
			full_msg = "\n".join(tried_msgs)
			log_widget.insert(END, "\n" + "="*60 + "\n")
			log_widget.insert(END, "❌ 故事API测试失败（已尝试所有可能的base_url）\n")
			log_widget.insert(END, "="*60 + "\n")
			log_widget.insert(END, full_msg + "\n")
			log_widget.insert(END, "\n💡 可能的原因:\n")
			log_widget.insert(END, "  1. API密钥错误或已过期\n")
			log_widget.insert(END, "  2. 账户余额不足\n")
			log_widget.insert(END, "  3. Base URL不正确\n")
			log_widget.insert(END, "  4. 网络连接问题\n")
			log_widget.insert(END, "  5. 模型名称不支持\n")
			log_widget.insert(END, "\n建议操作:\n")
			log_widget.insert(END, "  • 检查API密钥是否正确\n")
			log_widget.insert(END, "  • 登录服务商网站查看账户余额\n")
			log_widget.insert(END, "  • 确认Base URL格式正确\n")
			messagebox.showerror("API 错误", "故事API鉴权失败，请检查密钥/额度/网络/模型。\n详情见配置页面的测试日志。")
			self.status.set("故事API测试失败")
		except Exception as e:
			import traceback
			if 'log_widget' not in locals():
				log_widget = getattr(self, 'story_test_log', None)
			if log_widget:
				error_trace = traceback.format_exc()
				log_widget.insert(END, "\n" + "="*60 + "\n")
				log_widget.insert(END, "💥 故事API测试异常\n")
				log_widget.insert(END, "="*60 + "\n")
				log_widget.insert(END, error_trace + "\n")
			
			messagebox.showerror("API 错误", f"测试时发生异常:\n{str(e)}\n\n详情见配置页面的测试日志。")
			self.status.set("故事API测试失败")
		finally:
			self.set_busy(False)
	
	def _estimate_chars(self, outline: str) -> int:
		"""根据目录估算字数"""
		lines = [l.strip() for l in outline.splitlines() if l.strip()]
		# Count section-like lines
		count = 0
		for l in lines:
			if l[:2].isdigit() or l[:1] in {"-", "•", "*"} or l.startswith(("一、", "二、", "三、", "四、", "五、")):
				count += 1
		if count <= 0:
			count = max(3, min(8, len(lines)//2 or 4))
		# Rough estimate: ~350 chars per section
		return int(count * 350)
	
	def _parse_outline_sections(self, outline: str) -> list[dict[str, str]]:
		"""解析目录，提取章节信息"""
		if not outline:
			return []
		
		sections = []
		lines = outline.strip().splitlines()
		current_section = None
		current_items = []
		
		for line in lines:
			stripped = line.strip()
			if not stripped:
				continue
			
			# 检测是否为章节标题（数字编号、中文编号、或 -, *, •）
			is_main_section = False
			if re.match(r'^\d+[.、]', stripped) or re.match(r'^[一二三四五六七八九十]+[.、]', stripped):
				is_main_section = True
			elif stripped[:1] in ("-", "•", "*") and not stripped[1:2].isdigit():
				# 一级标题
				is_main_section = True
			
			if is_main_section:
				# 保存上一个章节
				if current_section:
					sections.append({
						"title": current_section,
						"items": current_items.copy()
					})
				current_section = stripped
				current_items = []
			else:
				# 子项
				if current_section:
					current_items.append(stripped)
		
		# 添加最后一个章节
		if current_section:
			sections.append({
				"title": current_section,
				"items": current_items
			})
		
		return sections


