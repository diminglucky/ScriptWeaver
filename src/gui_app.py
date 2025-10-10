from __future__ import annotations

import threading
from pathlib import Path
from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

import os
import re
from dotenv import load_dotenv, find_dotenv, set_key
from openai import OpenAI
from PIL import Image, ImageTk

from src.kb.ingest import IngestConfig, KnowledgeBaseIngestor
from src.kb.search import KnowledgeBaseSearcher, SearchConfig
from src.clients.deepseek_client import DeepSeekClient
from src.clients.image_client import OpenAIImageClient
from src.project_manager import ProjectManager, Project


def _sanitize(s: str) -> str:
	# Remove quotes, bearer prefix, and exotic spaces
	val = (s or "")
	val = val.replace("\u200b", "").replace("\u2003", " ").replace("\u00A0", " ")
	val = val.strip().strip('"').strip("'")
	if val.lower().startswith("bearer "):
		val = val[7:].strip()
	return val


def _try_chat(key: str, base_url: str, model: str) -> tuple[bool, str]:
	try:
		client = OpenAI(api_key=key, base_url=base_url, timeout=20)
		resp = client.chat.completions.create(model=model, messages=[{"role": "user", "content": "ping"}], max_tokens=5)
		_ok = bool(resp.choices and resp.choices[0].message)
		return True, "ok"
	except Exception as e:
		return False, str(e)


class App(tk.Tk):
	def __init__(self) -> None:
		super().__init__()
		self.title("创作知乎故事 · 知识库 + DeepSeek")
		self.geometry("1200x900")
		self.minsize(1100, 800)  # 设置最小窗口尺寸，防止缩小后遮挡

		# Load env to prefill API config
		load_dotenv()

		self.data_dir = tk.StringVar(value=str(Path("data/raw").resolve()))
		self.index_dir = tk.StringVar(value=str(Path("index").resolve()))
		self.top_k = tk.IntVar(value=6)
		self.temperature = tk.DoubleVar(value=0.7)
		self.api_key = tk.StringVar(value=os.getenv("DEEPSEEK_API_KEY", ""))
		self.base_url = tk.StringVar(value=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"))
		self.model = tk.StringVar(value=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
		self.category = tk.StringVar(value="职场")
		self.model_only = tk.BooleanVar(value=True)
		self.current_outline: str | None = None
		self.target_chars = tk.IntVar(value=1800)
		self.style = tk.StringVar(value="情感起伏/反转/细节描写/有画面感/口语化")
		
		# 项目管理
		self.project_manager = ProjectManager()
		self.current_project: Project | None = None
		
		# 章节管理
		self.parsed_sections: list[dict] = []  # 解析后的章节列表
		self.generated_content: str = ""  # 已生成的累积内容

		self._build_ui()
		
		# 启动后自动加载上次使用的API配置
		self.after(100, self._auto_load_api_config)

	def _build_ui(self) -> None:
		# Pages container with styled notebook
		self.notebook = ttk.Notebook(self)
		self.notebook.pack(fill=BOTH, expand=True, padx=10, pady=(10, 8))
		
		self.page_project = tk.Frame(self.notebook, bg="#2b2b2b")
		self.page_story = tk.Frame(self.notebook, bg="#2b2b2b")
		self.page_image = tk.Frame(self.notebook, bg="#2b2b2b")
		self.notebook.add(self.page_project, text="  📁 项目管理  ")
		self.notebook.add(self.page_story, text="  📝 故事生成  ")
		self.notebook.add(self.page_image, text="  🎨 图片生成  ")
		
		# Build pages
		self._build_project_page()
		self._build_story_page()
		self._build_image_page()
	
	def _build_project_page(self) -> None:
		"""构建项目管理页面"""
		# 顶部：当前项目信息
		top_frame = ttk.LabelFrame(self.page_project, text="📂 当前项目", padding=(10, 8))
		top_frame.pack(fill="x", padx=10, pady=(10, 8))
		
		self.lbl_current_project = tk.Label(top_frame, text="未选择项目", font=("", 12, "bold"), fg="#888888", anchor="w")
		self.lbl_current_project.pack(fill="x", pady=(0, 4))
		
		btn_row = ttk.Frame(top_frame)
		btn_row.pack(fill="x")
		self.btn_new_project = ttk.Button(btn_row, text="➕ 新建项目", command=self._on_new_project)
		self.btn_new_project.pack(side=LEFT, padx=(0, 6))
		self.btn_save_story = ttk.Button(btn_row, text="💾 保存当前故事", command=self._on_save_story, state=DISABLED)
		self.btn_save_story.pack(side=LEFT, padx=6)
		
		# 中间：项目列表
		mid_frame = ttk.LabelFrame(self.page_project, text="📚 我的项目", padding=(10, 8))
		mid_frame.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))
		
		# 创建表格
		columns = ("name", "category", "story_len", "images", "updated")
		self.project_tree = ttk.Treeview(mid_frame, columns=columns, show="headings", height=15)
		self.project_tree.heading("name", text="项目名称")
		self.project_tree.heading("category", text="类别")
		self.project_tree.heading("story_len", text="故事字数")
		self.project_tree.heading("images", text="图片数")
		self.project_tree.heading("updated", text="更新时间")
		
		self.project_tree.column("name", width=250)
		self.project_tree.column("category", width=100)
		self.project_tree.column("story_len", width=100)
		self.project_tree.column("images", width=80)
		self.project_tree.column("updated", width=180)
		
		scrollbar = ttk.Scrollbar(mid_frame, orient="vertical", command=self.project_tree.yview)
		self.project_tree.configure(yscrollcommand=scrollbar.set)
		
		self.project_tree.pack(side=LEFT, fill=BOTH, expand=True)
		scrollbar.pack(side=RIGHT, fill="y")
		
		# 底部：操作按钮
		btn_frame = ttk.Frame(mid_frame)
		btn_frame.pack(fill="x", pady=(8, 0))
		
		self.btn_load_project = ttk.Button(btn_frame, text="📖 加载选中项目", command=self._on_load_project)
		self.btn_load_project.pack(side=LEFT, padx=(0, 6))
		self.btn_refresh_list = ttk.Button(btn_frame, text="🔄 刷新列表", command=self._refresh_project_list)
		self.btn_refresh_list.pack(side=LEFT, padx=6)
		self.btn_delete_project = ttk.Button(btn_frame, text="🗑️ 删除选中项目", command=self._on_delete_project)
		self.btn_delete_project.pack(side=LEFT, padx=6)
		
		# 初始加载项目列表
		self._refresh_project_list()
	
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
		# Group 1: 数据与索引
		grp_paths = ttk.LabelFrame(self.story_tab_setup, text="资料与索引")
		grp_paths.pack(fill="x", padx=10, pady=(10, 5))
		grp_paths.columnconfigure(1, weight=1)

		tk.Label(grp_paths, text="数据目录:").grid(row=0, column=0, sticky="w", padx=6, pady=4)
		self.entry_data = tk.Entry(grp_paths, textvariable=self.data_dir)
		self.entry_data.grid(row=0, column=1, sticky="we", padx=6)
		tk.Button(grp_paths, text="选择...", command=self.choose_data).grid(row=0, column=2, padx=4)
		tk.Button(grp_paths, text="一键选择库", command=self.choose_library_quick).grid(row=0, column=3, padx=4)

		tk.Label(grp_paths, text="索引目录:").grid(row=1, column=0, sticky="w", padx=6, pady=4)
		self.entry_index = tk.Entry(grp_paths, textvariable=self.index_dir)
		self.entry_index.grid(row=1, column=1, sticky="we", padx=6)
		tk.Button(grp_paths, text="选择...", command=self.choose_index).grid(row=1, column=2, padx=4)
		self.btn_ingest = tk.Button(grp_paths, text="构建索引", command=self.on_ingest)
		self.btn_ingest.grid(row=1, column=3, padx=4)

		# Group 2: 参数
		grp_params = ttk.LabelFrame(self.story_tab_setup, text="参数")
		grp_params.pack(fill="x", padx=10, pady=5)
		for i in range(8):
			grp_params.columnconfigure(i, weight=1)
		
		# 第一行：模型参数
		tk.Label(grp_params, text="TopK:").grid(row=0, column=0, sticky="e", padx=6, pady=4)
		self.spin_topk = tk.Spinbox(grp_params, from_=1, to=20, textvariable=self.top_k, width=6)
		self.spin_topk.grid(row=0, column=1, sticky="w")
		tk.Label(grp_params, text="温度:").grid(row=0, column=2, sticky="e", padx=6)
		self.spin_temp = tk.Spinbox(grp_params, from_=0.0, to=1.5, increment=0.1, textvariable=self.temperature, width=6)
		self.spin_temp.grid(row=0, column=3, sticky="w")
		tk.Label(grp_params, text="目标字数:").grid(row=0, column=4, sticky="e", padx=6)
		self.spin_len = tk.Spinbox(grp_params, from_=500, to=30000, increment=500, textvariable=self.target_chars, width=8)
		self.spin_len.grid(row=0, column=5, sticky="w")
		self.chk_model_only = ttk.Checkbutton(grp_params, text="⚡ 仅用模型（不检索知识库）", variable=self.model_only)
		self.chk_model_only.grid(row=0, column=6, columnspan=2, sticky="w", padx=(12, 6))
		
		# 第二行：操作按钮
		self.btn_locate_index = ttk.Button(grp_params, text="📂 定位索引", command=self.locate_existing_index)
		self.btn_locate_index.grid(row=1, column=0, columnspan=2, padx=6, pady=(0, 4), sticky="we")
		self.btn_test_api = ttk.Button(grp_params, text="🔌 测试API", command=self.on_test_api)
		self.btn_test_api.grid(row=1, column=2, columnspan=2, padx=6, pady=(0, 4), sticky="we")
		self.btn_clear = ttk.Button(grp_params, text="🗑️ 清空输出", command=self.on_clear_output)
		self.btn_clear.grid(row=1, column=4, columnspan=2, padx=6, pady=(0, 4), sticky="we")
		self.btn_copy = ttk.Button(grp_params, text="📋 复制内容", command=self.on_copy_output)
		self.btn_copy.grid(row=1, column=6, columnspan=2, padx=6, pady=(0, 4), sticky="we")

		# Group 3: API 配置
		grp_api = ttk.LabelFrame(self.story_tab_setup, text="API 配置")
		grp_api.pack(fill="x", padx=10, pady=5)
		grp_api.columnconfigure(1, weight=1)
		grp_api.columnconfigure(3, weight=1)
		
		# API预设下拉框
		tk.Label(grp_api, text="API预设:").grid(row=0, column=0, sticky="e", padx=6, pady=4)
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
		
		self.combo_api_preset = ttk.Combobox(grp_api, textvariable=self.api_preset, 
											  values=list(self.api_presets.keys()),
											  state="readonly", width=20)
		self.combo_api_preset.grid(row=0, column=1, sticky="w", padx=6)
		self.combo_api_preset.bind("<<ComboboxSelected>>", self._on_api_preset_selected)
		
		# 添加保存自定义API按钮
		tk.Button(grp_api, text="💾 保存为自定义预设", command=self._save_custom_preset, 
				  font=("", 9), bg="#607D8B", fg="white", relief=tk.FLAT, padx=8, pady=3, cursor="hand2").grid(row=0, column=2, padx=6)
		
		tk.Label(grp_api, text="提示: 可保存当前配置为自定义预设", fg="gray", font=("", 9)).grid(row=0, column=3, sticky="w", padx=6)

		tk.Label(grp_api, text="API Key:").grid(row=1, column=0, sticky="e", padx=6, pady=4)
		self.entry_api = tk.Entry(grp_api, textvariable=self.api_key, show="*")
		self.entry_api.grid(row=1, column=1, sticky="we", padx=6)
		tk.Label(grp_api, text="Base URL:").grid(row=1, column=2, sticky="e", padx=6)
		self.entry_base = tk.Entry(grp_api, textvariable=self.base_url)
		self.entry_base.grid(row=1, column=3, sticky="we", padx=6)
		
		tk.Label(grp_api, text="Model:").grid(row=2, column=0, sticky="e", padx=6, pady=4)
		self.entry_model = tk.Entry(grp_api, textvariable=self.model)
		self.entry_model.grid(row=2, column=1, sticky="we", padx=6)
		tk.Button(grp_api, text="保存配置", command=self.save_api_config).grid(row=2, column=2, padx=6)
		tk.Button(grp_api, text="加载配置", command=self.load_api_config).grid(row=2, column=3, padx=6, sticky="w")
	
	def _build_story_create_tab(self) -> None:
		"""构建创作标签页"""
		# 去掉LabelFrame的边框，直接使用Frame
		grp_create = tk.Frame(self.story_tab_create, bg="#1e1e1e", relief=tk.FLAT)
		grp_create.pack(fill="x", padx=0, pady=0)
		grp_create.columnconfigure(1, weight=1)

		# 第一行：种类 + 风格 + 按钮
		row1_frame = tk.Frame(grp_create, bg="#1e1e1e")
		row1_frame.grid(row=0, column=0, columnspan=2, sticky="we", padx=15, pady=(15, 12))
		
		# 左侧：种类
		tk.Label(row1_frame, text="📚 种类:", font=("", 12, "bold"), bg="#1e1e1e", fg="#ffffff").pack(side=LEFT, padx=(0, 8))
		self.combo_category = ttk.Combobox(row1_frame, textvariable=self.category, width=12, 
										   values=("爱情", "悬疑", "职场", "科幻", "成长", "亲情", "社会观察", "校园", "历史", "奇幻"),
										   font=("", 12))
		self.combo_category.pack(side=LEFT, padx=(0, 20))
		
		# 中间：风格
		tk.Label(row1_frame, text="🎨 风格:", font=("", 12, "bold"), bg="#1e1e1e", fg="#ffffff").pack(side=LEFT, padx=(0, 8))
		self.entry_style = tk.Entry(row1_frame, textvariable=self.style, width=20, font=("", 12),
									 relief=tk.FLAT, borderwidth=0, bg="#000000", fg="#ffffff",
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
		tk.Label(grp_create, text="💡 创作需求:", font=("", 12, "bold"), bg="#1e1e1e", fg="#ffffff").grid(row=1, column=0, sticky="nw", padx=(15, 10), pady=(0, 4))
		
		# 创建文本框容器
		prompt_frame = tk.Frame(grp_create, bg="#1e1e1e")
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
		self.prompt = tk.Entry(grp_create)  # 隐藏但保持引用
		
		# 第三行：章节控制
		tk.Label(grp_create, text="📖 章节:", font=("", 12, "bold"), bg="#1e1e1e", fg="#ffffff").grid(row=2, column=0, sticky="nw", padx=(15, 10), pady=(0, 4))
		
		self.current_section_index = tk.IntVar(value=0)
		
		# 创建一个样式来设置Combobox的颜色
		style = ttk.Style()
		style.configure('Chapter.TCombobox', foreground='#ffffff', fieldbackground='#000000', background='#000000', 
						borderwidth=0, relief='flat')
		style.map('Chapter.TCombobox', 
				  fieldbackground=[('readonly', '#000000')],
				  selectbackground=[('readonly', '#000000')],
				  selectforeground=[('readonly', '#ffffff')])
		
		chapter_frame = tk.Frame(grp_create, bg="#1e1e1e")
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

		# Output area + status bar
		self.output = scrolledtext.ScrolledText(self.story_tab_create, wrap=tk.WORD,
												 font=("", 13), bg="#000000", fg="#ffffff",
												 insertbackground="white", selectbackground="#ffffff", selectforeground="#000000",
												 relief=tk.FLAT, borderwidth=0, highlightthickness=0,
												 padx=15, pady=15)
		self.output.pack(fill=BOTH, expand=True, padx=0, pady=0)
		self.status = tk.StringVar(value="就绪")
		status_bar = ttk.Label(self.story_tab_create, textvariable=self.status, anchor="w")
		status_bar.pack(fill="x", padx=10, pady=(0, 8))

	def _clear_prompt_placeholder(self, event=None) -> None:
		"""清除占位符"""
		content = self.prompt_text.get("1.0", "end-1c")
		if "例如：" in content:
			self.prompt_text.delete("1.0", END)
			self.prompt_text.tag_remove("placeholder", "1.0", "end")
	
	def _restore_prompt_placeholder(self, event=None) -> None:
		"""恢复占位符"""
		content = self.prompt_text.get("1.0", "end-1c").strip()
		if not content:
			self.prompt_text.insert("1.0", "例如：写一个惊悚短篇，要求特别惊奇感人，跌宕起伏...")
			self.prompt_text.tag_add("placeholder", "1.0", "end")
	
	def _get_prompt_content(self) -> str:
		"""获取创作需求内容（过滤占位符）"""
		content = self.prompt_text.get("1.0", "end-1c").strip()
		if "例如：" in content and "placeholder" in str(self.prompt_text.tag_names("1.0")):
			return ""
		return content

	def on_clear_output(self) -> None:
		self.output.delete("1.0", END)
		self.status.set("输出已清空")

	def on_copy_output(self) -> None:
		text = self.output.get("1.0", END)
		self.clipboard_clear()
		self.clipboard_append(text)
		self.status.set("内容已复制到剪贴板")

	def _load_custom_presets(self) -> None:
		"""加载用户自定义的API预设"""
		custom_presets_file = Path("custom_api_presets.json")
		if custom_presets_file.exists():
			try:
				import json
				with open(custom_presets_file, 'r', encoding='utf-8') as f:
					custom_presets = json.load(f)
					self.api_presets.update(custom_presets)
			except Exception:
				pass  # 加载失败则跳过
	
	def _save_custom_preset(self) -> None:
		"""保存当前配置为自定义预设"""
		from tkinter import simpledialog
		preset_name = simpledialog.askstring(
			"保存自定义预设",
			"请输入预设名称（例如：我的DeepSeek、公司API等）：",
			parent=self
		)
		
		if not preset_name:
			return
		
		# 检查是否覆盖内置预设
		built_in_presets = ["DeepSeek", "OpenAI", "Azure OpenAI", "Moonshot (月之暗面)", 
							"智谱AI (GLM)", "百度文心", "阿里通义", "自定义"]
		if preset_name in built_in_presets:
			messagebox.showwarning("警告", "不能覆盖内置预设，请使用其他名称")
			return
		
		# 保存当前配置
		self.api_presets[preset_name] = {
			"base_url": self.base_url.get(),
			"model": self.model.get(),
			"key": self.api_key.get()
		}
		
		# 保存到文件
		try:
			import json
			custom_presets_file = Path("custom_api_presets.json")
			# 只保存自定义预设，不保存内置的
			custom_presets = {k: v for k, v in self.api_presets.items() if k not in built_in_presets}
			with open(custom_presets_file, 'w', encoding='utf-8') as f:
				json.dump(custom_presets, f, ensure_ascii=False, indent=2)
			
			# 更新下拉框
			self.combo_api_preset['values'] = list(self.api_presets.keys())
			self.api_preset.set(preset_name)
			
			messagebox.showinfo("成功", f"已保存自定义预设: {preset_name}")
			if hasattr(self, 'status'):
				self.status.set(f"已保存自定义预设: {preset_name}")
		except Exception as e:
			messagebox.showerror("错误", f"保存失败: {str(e)}")
	
	def _load_custom_image_presets(self) -> None:
		"""加载用户自定义的图片API预设"""
		custom_presets_file = Path("custom_image_api_presets.json")
		if custom_presets_file.exists():
			try:
				import json
				with open(custom_presets_file, 'r', encoding='utf-8') as f:
					custom_presets = json.load(f)
					self.img_api_presets.update(custom_presets)
			except Exception:
				pass  # 加载失败则跳过
	
	def _save_custom_image_preset(self) -> None:
		"""保存当前图片API配置为自定义预设"""
		from tkinter import simpledialog
		preset_name = simpledialog.askstring(
			"保存自定义图片API预设",
			"请输入预设名称（例如：我的DALL-E、公司图片API等）：",
			parent=self
		)
		
		if not preset_name:
			return
		
		# 检查是否覆盖内置预设
		built_in_presets = ["OpenAI (DALL-E)", "Azure OpenAI", "Stability AI", "Midjourney API", "自定义"]
		if preset_name in built_in_presets:
			messagebox.showwarning("警告", "不能覆盖内置预设，请使用其他名称")
			return
		
		# 保存当前配置
		self.img_api_presets[preset_name] = {
			"base_url": self.img_base_url.get(),
			"model": self.img_model.get(),
			"key": self.img_api_key.get()
		}
		
		# 保存到文件
		try:
			import json
			custom_presets_file = Path("custom_image_api_presets.json")
			# 只保存自定义预设，不保存内置的
			custom_presets = {k: v for k, v in self.img_api_presets.items() if k not in built_in_presets}
			with open(custom_presets_file, 'w', encoding='utf-8') as f:
				json.dump(custom_presets, f, ensure_ascii=False, indent=2)
			
			# 更新下拉框
			self.combo_img_api_preset['values'] = list(self.img_api_presets.keys())
			self.img_api_preset.set(preset_name)
			
			messagebox.showinfo("成功", f"已保存自定义图片API预设: {preset_name}")
		except Exception as e:
			messagebox.showerror("错误", f"保存失败: {str(e)}")
	
	def _on_img_api_preset_selected(self, event=None) -> None:
		"""当选择图片API预设时，自动填充配置"""
		preset_name = self.img_api_preset.get()
		if preset_name in self.img_api_presets:
			preset = self.img_api_presets[preset_name]
			self.img_base_url.set(preset["base_url"])
			self.img_model.set(preset["model"])
			# 不覆盖已有的API Key，只在为空时填充
			if not self.img_api_key.get() and preset["key"]:
				self.img_api_key.set(preset["key"])
	
	def _save_image_api_config(self) -> None:
		"""保存图片API配置到.env文件"""
		try:
			load_dotenv()
			env_path = Path(".env")
			
			# 读取现有配置
			if env_path.exists():
				with open(env_path, 'r', encoding='utf-8') as f:
					lines = f.readlines()
			else:
				lines = []
			
			# 更新或添加图片API配置
			config_keys = {
				'IMG_API_PRESET': self.img_api_preset.get(),
				'IMG_API_KEY': self.img_api_key.get(),
				'IMG_BASE_URL': self.img_base_url.get(),
				'IMG_MODEL': self.img_model.get(),
				'IMG_SIZE': self.img_size.get()
			}
			
			# 更新配置
			new_lines = []
			keys_found = set()
			
			for line in lines:
				key = line.split('=')[0].strip()
				if key in config_keys:
					new_lines.append(f"{key}={config_keys[key]}\n")
					keys_found.add(key)
				else:
					new_lines.append(line)
			
			# 添加未找到的配置
			for key, value in config_keys.items():
				if key not in keys_found:
					new_lines.append(f"{key}={value}\n")
			
			# 写入文件
			with open(env_path, 'w', encoding='utf-8') as f:
				f.writelines(new_lines)
			
			messagebox.showinfo("成功", "图片API配置已保存")
			self.status.set("图片API配置已保存")
		except Exception as e:
			messagebox.showerror("错误", f"保存失败: {str(e)}")
	
	def _auto_load_image_api_config(self) -> None:
		"""自动加载图片API配置"""
		try:
			load_dotenv()
			
			# 加载预设
			preset = os.getenv("IMG_API_PRESET")
			if preset and preset in self.img_api_presets:
				self.img_api_preset.set(preset)
			
			# 加载API Key
			api_key = os.getenv("IMG_API_KEY")
			if api_key:
				self.img_api_key.set(api_key)
			
			# 加载Base URL
			base_url = os.getenv("IMG_BASE_URL")
			if base_url:
				self.img_base_url.set(base_url)
			
			# 加载模型
			model = os.getenv("IMG_MODEL")
			if model:
				self.img_model.set(model)
			
			# 加载尺寸
			size = os.getenv("IMG_SIZE")
			if size:
				self.img_size.set(size)
			
			print(f"已自动加载图片API配置: {preset or 'OpenAI (DALL-E)'}")
		except Exception as e:
			print(f"加载图片API配置失败: {e}")
	
	def _on_api_preset_selected(self, event=None) -> None:
		"""当选择API预设时，自动填充配置"""
		preset_name = self.api_preset.get()
		if preset_name in self.api_presets:
			preset = self.api_presets[preset_name]
			self.base_url.set(preset["base_url"])
			self.model.set(preset["model"])
			# 不覆盖已有的API Key，只在为空时填充
			if not self.api_key.get() and preset["key"]:
				self.api_key.set(preset["key"])
			if hasattr(self, 'status'):
				self.status.set(f"已选择 {preset_name} API预设")
	
	def open_image_window(self) -> None:
		# switch to image page instead of popup
		if hasattr(self, 'notebook') and hasattr(self, 'page_image'):
			self.notebook.select(self.page_image)

	def on_test_api(self) -> None:
		try:
			self.set_busy(True)
			self.status.set("测试 API 中...")
			key = _sanitize(self.api_key.get())
			base = _sanitize(self.base_url.get())
			model = _sanitize(self.model.get()) or "deepseek-chat"
			candidates = []
			# try user-provided
			candidates.append(base.rstrip("/"))
			# also try toggling /v1 suffix
			if base.rstrip("/").endswith("/v1"):
				candidates.append(base.rstrip("/")[:-3])
			else:
				candidates.append(base.rstrip("/") + "/v1")
			tried_msgs: list[str] = []
			for b in candidates:
				ok, msg = _try_chat(key, b, model)
				tried_msgs.append(f"base_url={b} -> {'SUCCESS' if ok else 'FAIL'}: {msg}")
				if ok:
					self.base_url.set(b)
					messagebox.showinfo("测试成功", f"API 可用\n{b}")
					self.status.set("API 可用")
					return
			# all failed
			full_msg = "\n".join(tried_msgs)
			self.output.insert(END, "API 测试失败（已尝试多种 base_url）:\n" + full_msg + "\n")
			messagebox.showerror("API 错误", "鉴权失败，请检查密钥/额度/网络/模型。详情见下方输出日志。")
			self.status.set("API 测试失败")
		except Exception as e:
			import traceback
			self.output.insert(END, "API 测试异常:\n" + traceback.format_exc() + "\n")
			messagebox.showerror("API 错误", str(e))
			self.status.set("API 测试失败")
		finally:
			self.set_busy(False)

	def locate_existing_index(self) -> None:
		"""If current index_dir is a parent, find first child that contains kb.index and switch to it."""
		base = Path(self.index_dir.get())
		if base.is_file():
			base = base.parent
		candidates = list(base.rglob("kb.index"))
		if not candidates:
			messagebox.showinfo("提示", "未在当前索引目录下找到任何 kb.index")
			return
		chosen = candidates[0].parent
		self.index_dir.set(str(chosen))
		self.output.insert(END, f"已定位到索引目录: {chosen}\n")
		self.status.set("已定位到现有索引")

	def choose_data(self) -> None:
		path = filedialog.askdirectory(initialdir=self.data_dir.get())
		if path:
			self.data_dir.set(path)
			self.status.set("已选择数据目录")

	def choose_library_quick(self) -> None:
		path = filedialog.askdirectory(initialdir=self.data_dir.get())
		if not path:
			return
		self.data_dir.set(path)
		base = Path(path).name
		auto_index = Path.cwd() / "index" / base
		auto_index.mkdir(parents=True, exist_ok=True)
		self.index_dir.set(str(auto_index))
		self.output.insert(END, f"已选择资料库: {path}\n已自动设置索引目录: {auto_index}\n")
		self.status.set("已选择资料库并设置索引目录")

	def choose_index(self) -> None:
		path = filedialog.askdirectory(initialdir=self.index_dir.get())
		if path:
			self.index_dir.set(path)
			self.status.set("已选择索引目录")

	def set_busy(self, busy: bool) -> None:
		state = DISABLED if busy else NORMAL
		self.btn_ingest.configure(state=state)
		self.btn_generate.configure(state=state)
		self.btn_outline.configure(state=state)
		if hasattr(self, 'btn_test_api'):
			self.btn_test_api.configure(state=state)
		if hasattr(self, 'btn_clear'):
			self.btn_clear.configure(state=state)
		if hasattr(self, 'btn_copy'):
			self.btn_copy.configure(state=state)
		# 章节生成按钮
		if hasattr(self, 'btn_generate_section'):
			# 只在有章节数据时才启用
			if busy or not self.parsed_sections:
				self.btn_generate_section.configure(state=DISABLED)
				self.btn_continue_next.configure(state=DISABLED)
				if hasattr(self, 'btn_auto_generate'):
					self.btn_auto_generate.configure(state=DISABLED)
			else:
				self.btn_generate_section.configure(state=NORMAL)
				self.btn_continue_next.configure(state=NORMAL)
				if hasattr(self, 'btn_auto_generate'):
					self.btn_auto_generate.configure(state=NORMAL)
		# Image page controls
		for name in (
			'img_btn_build', 'img_btn_gen', 'img_btn_save', 'img_btn_browse',
			'img_btn_extract', 'img_btn_build_from_shots', 'img_btn_copy', 'img_btn_clear',
			'img_btn_copy_shots', 'img_btn_clear_shots'
		):
			if hasattr(self, name):
				getattr(self, name).configure(state=state)

	def on_ingest(self) -> None:
		# Preflight
		if not Path(self.data_dir.get()).exists():
			messagebox.showwarning("提示", "数据目录不存在，请先选择有效的数据目录")
			return
		if not any(Path(self.data_dir.get()).rglob("*.txt")) and not any(Path(self.data_dir.get()).rglob("*.md")) and not any(Path(self.data_dir.get()).rglob("*.markdown")):
			messagebox.showwarning("提示", "数据目录下未发现 .txt/.md/.markdown 文件")
			return
		def task():
			try:
				self.set_busy(True)
				self.status.set("构建索引中...")
				cfg = IngestConfig(data_root=Path(self.data_dir.get()), index_dir=Path(self.index_dir.get()))
				KnowledgeBaseIngestor(cfg).build()
				self.output.insert(END, f"索引已生成: {self.index_dir.get()}\n")
				self.status.set("索引已生成")
			except Exception as e:
				import traceback
				self.output.insert(END, "构建索引出错:\n" + traceback.format_exc() + "\n")
				messagebox.showerror("错误", str(e))
				self.status.set("构建索引失败")
			finally:
				self.set_busy(False)
		threading.Thread(target=task, daemon=True).start()

	def on_generate_outline(self) -> None:
		requirement = self._get_prompt_content()
		if not requirement:
			messagebox.showwarning("提示", "请先输入创作需求/主题")
			return
		if not (_sanitize(self.api_key.get())):
			messagebox.showwarning("提示", "API Key 为空，请在‘API 配置’中填写后保存")
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
				self.status.set("检索素材并生成目录中...")
				load_dotenv()
				if need_build:
					cfg = IngestConfig(data_root=Path(self.data_dir.get()), index_dir=Path(self.index_dir.get()))
					KnowledgeBaseIngestor(cfg).build()
				searcher = KnowledgeBaseSearcher(SearchConfig(index_dir=Path(self.index_dir.get()), top_k=self.top_k.get()))
				results = searcher.search(requirement, self.top_k.get())
				contexts = [c for c, _s, _m in results]
				client = DeepSeekClient(
					api_key=_sanitize(self.api_key.get()),
					base_url=_sanitize(self.base_url.get()),
					model=_sanitize(self.model.get()),
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
			except Exception as e:
				import traceback
				self.output.insert(END, "生成目录出错:\n" + traceback.format_exc() + "\n")
				messagebox.showerror("错误", str(e))
				self.status.set("生成目录失败")
			finally:
				self.set_busy(False)
		threading.Thread(target=task, daemon=True).start()

	def on_generate(self) -> None:
		query = self._get_prompt_content()
		if not query:
			messagebox.showwarning("提示", "请先输入创作需求/主题")
			return
		if not (_sanitize(self.api_key.get())):
			messagebox.showwarning("提示", "API Key 为空，请在‘API 配置’中填写后保存")
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
				self.status.set("检索素材并生成正文中...")
				load_dotenv()
				if need_build:
					cfg = IngestConfig(data_root=Path(self.data_dir.get()), index_dir=Path(self.index_dir.get()))
					KnowledgeBaseIngestor(cfg).build()
				searcher = KnowledgeBaseSearcher(SearchConfig(index_dir=Path(self.index_dir.get()), top_k=self.top_k.get()))
				results = searcher.search(query, self.top_k.get())
				contexts = [c for c, _s, _m in results]
				client = DeepSeekClient(
					api_key=_sanitize(self.api_key.get()),
					base_url=_sanitize(self.base_url.get()),
					model=_sanitize(self.model.get()),
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
				# 自动保存到当前项目
				self._auto_save_to_project()
			except Exception as e:
				import traceback
				self.output.insert(END, "生成出错:\n" + traceback.format_exc() + "\n")
				messagebox.showerror("错误", str(e))
				self.status.set("生成失败")
			finally:
				self.set_busy(False)
		threading.Thread(target=task, daemon=True).start()

	def _generate_outline_model_only(self, requirement: str) -> None:
		def task():
			try:
				self.set_busy(True)
				self.status.set("生成目录中...")
				client = DeepSeekClient(
					api_key=_sanitize(self.api_key.get()),
					base_url=_sanitize(self.base_url.get()),
					model=_sanitize(self.model.get()),
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
			except Exception as e:
				messagebox.showerror("错误", str(e))
				self.status.set("生成目录失败")
			finally:
				self.set_busy(False)
		threading.Thread(target=task, daemon=True).start()

	def _generate_model_only(self, query: str) -> None:
		def task():
			try:
				self.set_busy(True)
				self.status.set("准备生成...")
				client = DeepSeekClient(
					api_key=_sanitize(self.api_key.get()),
					base_url=_sanitize(self.base_url.get()),
					model=_sanitize(self.model.get()),
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
				# 自动保存到当前项目
				self._auto_save_to_project()
			except Exception as e:
				import traceback
				self.output.insert(END, "\n\n生成出错:\n" + traceback.format_exc() + "\n")
				messagebox.showerror("错误", str(e))
				self.status.set("生成失败")
			finally:
				self.set_busy(False)
		threading.Thread(target=task, daemon=True).start()
	
	def _generate_in_sections(self, client: DeepSeekClient, requirement: str, contexts: list[str], sections: list[dict], target_chars: int) -> None:
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

	def save_api_config(self) -> None:
		try:
			# Determine .env path
			env_path_str = find_dotenv(usecwd=True)
			if not env_path_str:
				env_path = Path.cwd() / ".env"
			else:
				env_path = Path(env_path_str)
			env_path.touch(exist_ok=True)
			set_key(str(env_path), "DEEPSEEK_API_KEY", self.api_key.get().strip())
			set_key(str(env_path), "DEEPSEEK_BASE_URL", self.base_url.get().strip())
			set_key(str(env_path), "DEEPSEEK_MODEL", self.model.get().strip())
			set_key(str(env_path), "API_PRESET", self.api_preset.get().strip())
			load_dotenv(override=True)
			messagebox.showinfo("成功", f"配置已保存到: {env_path}")
		except Exception as e:
			messagebox.showerror("错误", str(e))

	def load_api_config(self) -> None:
		try:
			load_dotenv(override=True)
			self.api_key.set(os.getenv("DEEPSEEK_API_KEY", ""))
			self.base_url.set(os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"))
			self.model.set(os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
			preset = os.getenv("API_PRESET", "DeepSeek")
			if preset in self.api_presets:
				self.api_preset.set(preset)
			messagebox.showinfo("成功", "已从 .env 加载配置")
		except Exception as e:
			messagebox.showerror("错误", str(e))
	
	def _auto_load_api_config(self) -> None:
		"""启动时自动加载上次使用的API配置"""
		try:
			load_dotenv(override=True)
			self.api_key.set(os.getenv("DEEPSEEK_API_KEY", ""))
			self.base_url.set(os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"))
			self.model.set(os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
			preset = os.getenv("API_PRESET", "DeepSeek")
			if preset in self.api_presets:
				self.api_preset.set(preset)
			if hasattr(self, 'status'):
				self.status.set(f"已自动加载配置: {preset}")
		except Exception:
			pass  # 静默失败，使用默认值

	def _build_outline_prompt(self, requirement: str, contexts: list[str], category: str) -> str:
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

	def _build_prompt(self, requirement: str, contexts: list[str], category: str, outline: str | None) -> str:
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

	def _estimate_chars(self, outline: str) -> int:
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
	
	def _build_section_prompt(self, section: dict, section_index: int, total_sections: int, 
							   previous_content: str, requirement: str, contexts: list[str], 
							   category: str, style_part: str, target_chars_per_section: int) -> str:
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


	def _build_image_page(self) -> None:
		"""构建图片生成页面，分为"创作"和"配置"两个子标签页"""
		# Vars for image page
		self.img_prompt = tk.StringVar()
		self.img_size = tk.StringVar(value="1024x1024")
		self.img_seed = tk.StringVar(value="")
		self.img_ref_path = tk.StringVar(value="")
		self.img_api_key = tk.StringVar(value=os.getenv("OPENAI_API_KEY", ""))
		self.img_model = tk.StringVar(value=os.getenv("OPENAI_IMAGE_MODEL", "dall-e-3"))
		self.img_last_image: Image.Image | None = None
		self.img_preview_photo: ImageTk.PhotoImage | None = None
		self.parsed_shots: list[str] = []  # 存储解析后的分镜列表
		
		# 创建图片页面的内部Notebook
		self.image_notebook = ttk.Notebook(self.page_image)
		self.image_notebook.pack(fill=BOTH, expand=True, padx=0, pady=0)
		
		# 创建两个子标签页
		self.image_tab_create = ttk.Frame(self.image_notebook)
		self.image_tab_setup = ttk.Frame(self.image_notebook)
		
		self.image_notebook.add(self.image_tab_create, text="  创作  ")
		self.image_notebook.add(self.image_tab_setup, text="  配置  ")
		
		# 构建各个标签页
		self._build_image_create_tab()
		self._build_image_setup_tab()
	
	def _build_image_create_tab(self) -> None:
		"""构建图片创作页面"""
		# Body two-column layout with better padding
		body = ttk.Frame(self.image_tab_create)
		body.pack(fill=BOTH, expand=True, padx=10, pady=10)
		left = ttk.Frame(body)
		left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
		right = ttk.Frame(body)
		right.grid(row=0, column=1, sticky="nsew")
		body.columnconfigure(0, weight=3)
		body.columnconfigure(1, weight=2)
		body.rowconfigure(0, weight=1)

		# Left: 分镜头列表
		grp_shots = ttk.LabelFrame(left, text="📋 所有分镜头", padding=(8, 5))
		grp_shots.pack(fill="both", expand=True, padx=0, pady=(0, 8))
		
		# 显示所有分镜头的文本框
		self.img_txt_all_shots = tk.Text(grp_shots, height=8, font=("", 10), wrap=tk.WORD, relief=tk.SOLID, borderwidth=1)
		self.img_txt_all_shots.pack(fill="both", expand=True, padx=6, pady=(6, 8))
		self.img_txt_all_shots.insert("1.0", "点击下方按钮从故事生成分镜头列表...")
		self.img_txt_all_shots.config(state=DISABLED)
		
		rowf = ttk.Frame(grp_shots)
		rowf.pack(fill="x", padx=6, pady=(0, 6))
		self.img_btn_extract = ttk.Button(rowf, text="📝 从故事生成分镜", command=self._on_img_extract_shots)
		self.img_btn_extract.pack(side=LEFT, padx=(0, 4))
		self.img_btn_copy_shots = ttk.Button(rowf, text="📋 复制所有", command=self._on_copy_shots)
		self.img_btn_copy_shots.pack(side=LEFT, padx=4)
		self.img_btn_clear_shots = ttk.Button(rowf, text="🗑️ 清空", command=self._on_clear_shots)
		self.img_btn_clear_shots.pack(side=LEFT, padx=4)
		
		# 选择单个分镜
		grp_shot_select = ttk.LabelFrame(left, text="🎯 选择要生成的分镜", padding=(8, 5))
		grp_shot_select.pack(fill="x", padx=0, pady=(0, 8))
		
		shot_select_frame = ttk.Frame(grp_shot_select)
		shot_select_frame.pack(fill="x", padx=6, pady=6)
		tk.Label(shot_select_frame, text="分镜:", font=("", 10)).pack(side=LEFT, padx=(0, 6))
		self.shot_selector = ttk.Combobox(shot_select_frame, state="disabled", width=50, font=("", 10))
		self.shot_selector.pack(side=LEFT, fill="x", expand=True)
		self.shot_selector.bind("<<ComboboxSelected>>", self._on_shot_selected)

		# Left: 场景/角色补充
		grp_ctx_add = ttk.LabelFrame(left, text="✨ 场景与角色补充（可选）", padding=(8, 5))
		grp_ctx_add.pack(fill="x", padx=0, pady=(0, 8))
		grp_ctx_add.columnconfigure(1, weight=1)
		tk.Label(grp_ctx_add, text="场景描述:", font=("", 10)).grid(row=0, column=0, sticky="e", padx=(0, 8), pady=6)
		self.img_entry_scene = ttk.Entry(grp_ctx_add, font=("", 10))
		self.img_entry_scene.grid(row=0, column=1, sticky="we", padx=(0, 6), pady=6)
		tk.Label(grp_ctx_add, text="角色特征:", font=("", 10)).grid(row=1, column=0, sticky="ne", padx=(0, 8), pady=(0, 6))
		self.img_txt_roles = tk.Text(grp_ctx_add, height=3, font=("", 10), wrap=tk.WORD, relief=tk.SOLID, borderwidth=1)
		self.img_txt_roles.grid(row=1, column=1, sticky="we", padx=(0, 6), pady=(0, 6))

		# Left: 提示词（中文）
		grp_prompt = ttk.LabelFrame(left, text="💬 图片描述（中文，可编辑）", padding=(8, 5))
		grp_prompt.pack(fill="both", expand=True, padx=0, pady=0)
		self.img_txt_prompt_cn = tk.Text(grp_prompt, height=5, font=("", 10), wrap=tk.WORD, relief=tk.SOLID, borderwidth=1)
		self.img_txt_prompt_cn.pack(fill="both", expand=True, padx=6, pady=(6, 8))
		rowp = ttk.Frame(grp_prompt)
		rowp.pack(fill="x", padx=6, pady=(0, 6))
		self.img_btn_build_from_shot = ttk.Button(rowp, text="✨ 从当前分镜生成", command=self._on_img_prompt_from_current_shot)
		self.img_btn_build_from_shot.pack(side=LEFT, padx=(0, 4))
		self.img_btn_copy = ttk.Button(rowp, text="📋 复制", command=self._on_copy_img_prompt)
		self.img_btn_copy.pack(side=LEFT, padx=4)
		self.img_btn_clear = ttk.Button(rowp, text="🗑️ 清空", command=self._on_clear_img_prompt)
		self.img_btn_clear.pack(side=LEFT, padx=4)

		# Right: 参考与生成
		grp_ctx = ttk.LabelFrame(right, text="🎯 参考与参数", padding=(8, 5))
		grp_ctx.pack(fill="x", padx=0, pady=(0, 8))
		grp_ctx.columnconfigure(1, weight=1)
		tk.Label(grp_ctx, text="参考图:", font=("", 10)).grid(row=0, column=0, sticky="e", padx=(0, 8), pady=6)
		self.img_entry_ref = ttk.Entry(grp_ctx, textvariable=self.img_ref_path, font=("", 9))
		self.img_entry_ref.grid(row=0, column=1, sticky="we", padx=(0, 6), pady=6)
		self.img_btn_browse = ttk.Button(grp_ctx, text="📁 选择", command=self._img_choose_ref)
		self.img_btn_browse.grid(row=0, column=2, padx=(0, 6), pady=6)
		tk.Label(grp_ctx, text="随机种子:", font=("", 10)).grid(row=1, column=0, sticky="e", padx=(0, 8), pady=(0, 6))
		self.img_entry_seed = ttk.Entry(grp_ctx, textvariable=self.img_seed, width=20, font=("", 10))
		self.img_entry_seed.grid(row=1, column=1, columnspan=2, sticky="w", padx=(0, 6), pady=(0, 6))

		grp_actions = ttk.LabelFrame(right, text="🚀 操作", padding=(8, 5))
		grp_actions.pack(fill="x", padx=0, pady=(0, 8))
		action_row = ttk.Frame(grp_actions)
		action_row.pack(fill="x", padx=6, pady=6)
		self.img_btn_gen = ttk.Button(action_row, text="🎨 生成图片", command=self._on_img_generate)
		self.img_btn_gen.pack(side=LEFT, padx=(0, 6), fill="x", expand=True)
		self.img_btn_save = ttk.Button(action_row, text="💾 保存", command=self._on_img_save, state=DISABLED)
		self.img_btn_save.pack(side=LEFT, fill="x", expand=True)

		grp_preview = ttk.LabelFrame(right, text="🖼️ 预览", padding=(8, 5))
		grp_preview.pack(fill=BOTH, expand=True, padx=0, pady=0)
		self.img_preview = ttk.Label(grp_preview, text="图片预览区\n\n点击\"生成图片\"后\n图片将显示在这里", 
									  font=("", 10), foreground="#888888", anchor="center")
		self.img_preview.pack(fill=BOTH, expand=True, padx=10, pady=10)
	
	def _build_image_setup_tab(self) -> None:
		"""构建图片API配置页面"""
		# API 配置组
		grp_api = ttk.LabelFrame(self.image_tab_setup, text="🔑 图片生成 API 配置", padding=(10, 10))
		grp_api.pack(fill="x", padx=10, pady=10)
		grp_api.columnconfigure(1, weight=1)
		
		# API预设下拉框
		tk.Label(grp_api, text="API预设:", font=("", 10)).grid(row=0, column=0, sticky="e", padx=6, pady=4)
		self.img_api_preset = tk.StringVar(value="OpenAI (DALL-E)")
		self.img_api_presets = {
			"OpenAI (DALL-E)": {
				"base_url": "https://api.openai.com/v1",
				"model": "dall-e-3",
				"key": ""
			},
			"Azure OpenAI": {
				"base_url": "https://YOUR_RESOURCE.openai.azure.com",
				"model": "dall-e-3",
				"key": ""
			},
			"Stability AI": {
				"base_url": "https://api.stability.ai/v1",
				"model": "stable-diffusion-xl-1024-v1-0",
				"key": ""
			},
			"Midjourney API": {
				"base_url": "https://api.midjourneyapi.io/v1",
				"model": "midjourney",
				"key": ""
			},
			"自定义": {
				"base_url": "",
				"model": "",
				"key": ""
			}
		}
		
		# 加载自定义图片API预设
		self._load_custom_image_presets()
		
		self.combo_img_api_preset = ttk.Combobox(grp_api, textvariable=self.img_api_preset, 
												  values=list(self.img_api_presets.keys()),
												  state="readonly", width=30, font=("", 11))
		self.combo_img_api_preset.grid(row=0, column=1, sticky="w", padx=6, pady=4)
		self.combo_img_api_preset.bind("<<ComboboxSelected>>", self._on_img_api_preset_selected)
		
		# 添加保存自定义API按钮
		tk.Button(grp_api, text="💾 保存为自定义预设", command=self._save_custom_image_preset, 
				  font=("", 10), bg="#000000", fg="#ffffff", relief=tk.FLAT, padx=10, pady=5, 
				  cursor="hand2", activebackground="#000000", activeforeground="#ffffff").grid(row=0, column=2, padx=(10, 0), pady=4)
		
		tk.Label(grp_api, text="API Key:", font=("", 11)).grid(row=1, column=0, sticky="e", padx=6, pady=(10, 6))
		self.img_entry_key = ttk.Entry(grp_api, textvariable=self.img_api_key, show="*", font=("", 11))
		self.img_entry_key.grid(row=1, column=1, columnspan=2, sticky="we", padx=6, pady=(10, 6))
		
		tk.Label(grp_api, text="Base URL:", font=("", 11)).grid(row=2, column=0, sticky="e", padx=6, pady=6)
		self.img_base_url = tk.StringVar(value="https://api.openai.com/v1")
		self.img_entry_base_url = ttk.Entry(grp_api, textvariable=self.img_base_url, font=("", 11))
		self.img_entry_base_url.grid(row=2, column=1, columnspan=2, sticky="we", padx=6, pady=6)
		
		tk.Label(grp_api, text="模型:", font=("", 11)).grid(row=3, column=0, sticky="e", padx=6, pady=6)
		self.img_entry_model = ttk.Entry(grp_api, textvariable=self.img_model, width=30, font=("", 11))
		self.img_entry_model.grid(row=3, column=1, sticky="w", padx=6, pady=6)
		
		# 图片参数组
		grp_params = ttk.LabelFrame(self.image_tab_setup, text="🎨 图片参数", padding=(10, 10))
		grp_params.pack(fill="x", padx=10, pady=(0, 10))
		grp_params.columnconfigure(1, weight=1)
		
		tk.Label(grp_params, text="尺寸:", font=("", 11)).grid(row=0, column=0, sticky="e", padx=6, pady=6)
		self.img_combo_size = ttk.Combobox(grp_params, textvariable=self.img_size, 
										   values=("512x512","768x768","1024x1024","1024x1792","1792x1024"), 
										   width=20, font=("", 11), state="readonly")
		self.img_combo_size.grid(row=0, column=1, sticky="w", padx=6, pady=6)
		
		tk.Label(grp_params, text="提示：", fg="gray", font=("", 10)).grid(row=1, column=0, columnspan=2, sticky="w", padx=6, pady=(10, 0))
		tk.Label(grp_params, text="• 1024x1024 适合方形图片\n• 1024x1792 适合竖版海报\n• 1792x1024 适合横版封面", 
				 fg="gray", font=("", 9), justify=LEFT).grid(row=2, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 6))
		
		# 保存按钮
		btn_frame = ttk.Frame(self.image_tab_setup)
		btn_frame.pack(fill="x", padx=10, pady=(10, 10))
		tk.Button(btn_frame, text="💾 保存图片API配置", command=self._save_image_api_config, 
				  font=("", 11, "bold"), bg="#000000", fg="#ffffff", relief=tk.FLAT, padx=20, pady=8, 
				  cursor="hand2", activebackground="#000000", activeforeground="#ffffff").pack(pady=10)
		
		# 启动后自动加载配置
		self.after(100, self._auto_load_image_api_config)

	def _img_choose_ref(self) -> None:
		path = filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg;*.webp;*.bmp"),("All","*.*")])
		if path:
			self.img_ref_path.set(path)

	def _on_img_generate(self) -> None:
		"""生成图片（自动将中文翻译为英文）"""
		prompt_cn = self.img_txt_prompt_cn.get("1.0", END).strip()
		if not prompt_cn:
			messagebox.showwarning("提示", "请先生成或填写图片描述")
			return
		
		def task():
			try:
				self.img_btn_gen.configure(state=DISABLED)
				self.status.set("正在翻译图片描述为英文...")
				
				# 1. 先将中文翻译为英文提示词
				client = DeepSeekClient(
					api_key=_sanitize(self.api_key.get()),
					base_url=_sanitize(self.base_url.get()),
					model=_sanitize(self.model.get()),
				)
				inst = (
					"你是专业的图片提示词翻译专家。请将中文图片描述翻译为适合DALL-E、Stable Diffusion等AI绘图工具的英文提示词。\n"
					"要求：\n"
					"1. 保留所有细节（场景、人物、动作、光线、镜头、风格等）\n"
					"2. 使用专业的图像生成术语（如 cinematic lighting, wide shot, close-up, 4K, detailed等）\n"
					"3. 输出纯英文，不要任何中文或其他语言\n"
					"4. 不要输出任何解释，只输出最终的英文提示词"
				)
				prompt_en = client.chat([
					{"role": "system", "content": inst},
					{"role": "user", "content": f"请翻译以下中文图片描述为英文提示词：\n\n{prompt_cn}"},
				], temperature=0.3)
				
				self.status.set("正在生成图片...")
				
				# 2. 使用英文提示词生成图片
				img_client = OpenAIImageClient(
					api_key=self.img_api_key.get().strip(), 
					model=self.img_model.get().strip() or "dall-e-3",
					base_url=self.img_base_url.get().strip() if hasattr(self, 'img_base_url') else None
				)
				
				if self.img_ref_path.get().strip():
					results = img_client.generate_with_reference(
						prompt=prompt_en, 
						reference_image_path=self.img_ref_path.get().strip(), 
						size=self.img_size.get()
					)
				else:
					results = img_client.generate(prompt=prompt_en, size=self.img_size.get(), n=1)
				
				if not results:
					messagebox.showerror("错误", "生成失败")
					return
				
				self.img_last_image = results[0].image
				self._update_img_preview()
				self.img_btn_save.configure(state=NORMAL)
				self.status.set(f"图片生成成功！使用的英文提示词：{prompt_en[:50]}...")
			except Exception as e:
				messagebox.showerror("错误", str(e))
				self.status.set("生成失败")
			finally:
				self.img_btn_gen.configure(state=NORMAL)
		
		import threading
		threading.Thread(target=task, daemon=True).start()

	def _on_copy_img_prompt(self) -> None:
		text = self.img_txt_prompt_cn.get("1.0", END)
		self.clipboard_clear()
		self.clipboard_append(text)
		self.status.set("图片描述已复制")

	def _on_clear_img_prompt(self) -> None:
		self.img_txt_prompt_cn.delete("1.0", END)
		self.status.set("图片描述已清空")

	def _on_copy_shots(self) -> None:
		"""复制所有分镜"""
		all_shots = self.img_txt_all_shots.get("1.0", END)
		self.clipboard_clear()
		self.clipboard_append(all_shots)
		self.status.set("所有分镜已复制")

	def _on_clear_shots(self) -> None:
		"""清空所有分镜"""
		if hasattr(self, 'parsed_shots'):
			self.parsed_shots = []
		
		# 清空所有分镜显示框
		self.img_txt_all_shots.config(state=NORMAL)
		self.img_txt_all_shots.delete("1.0", END)
		self.img_txt_all_shots.insert("1.0", "点击下方按钮从故事生成分镜头列表...")
		self.img_txt_all_shots.config(state=DISABLED)
		
		# 清空选择器
		self.shot_selector['values'] = []
		self.shot_selector['state'] = 'disabled'
		
		self.status.set("分镜已清空")

	def _on_img_build_prompt(self) -> None:
		story_text = self.output.get("1.0", END).strip()
		if not story_text:
			messagebox.showwarning("提示", "请先在‘故事’页生成或粘贴正文内容，然后再提炼提示词")
			return
		try:
			self.set_busy(True)
			self.status.set("根据故事提炼图片提示词中...")
			scene = self.img_entry_scene.get().strip() if hasattr(self, 'img_entry_scene') else ""
			roles = self.img_txt_roles.get("1.0", END).strip() if hasattr(self, 'img_txt_roles') else ""
			client = DeepSeekClient(
				api_key=_sanitize(self.api_key.get()),
				base_url=_sanitize(self.base_url.get()),
				model=_sanitize(self.model.get()),
			)
			prompt_instruct = (
				"你是资深视觉提示词工程师。请基于提供的故事正文，生成一段用于文本生成图片的英文提示词，"
				"要求与故事的情节、人物外观与气质完全吻合，保持同一人物的一致性（面部、发型、年龄、服饰等）。"
				"如有参考图，将作为身份一致性的最高约束。提示词需包含：场景/构图、主体外观细节、表情动作、光线镜头、风格与质感。"
				"禁止输出任何 Markdown，仅输出单段英文提示词。"
			)
			user_payload = (
				f"故事正文：\n{story_text}\n\n"
				f"补充场景（可选）：{scene or '无'}\n"
				f"人物设定（可选）：{roles or '无'}\n"
				"请输出最终英文提示词。"
			)
			resp = client.chat([
				{"role": "system", "content": prompt_instruct},
				{"role": "user", "content": user_payload},
			], temperature=max(0.4, self.temperature.get() - 0.2))
			self.img_txt_prompt.delete("1.0", END)
			self.img_txt_prompt.insert(END, resp.strip())
			self.status.set("已生成图片提示词（请检查后点击生成图片）")
		except Exception as e:
			messagebox.showerror("错误", str(e))
		finally:
			self.set_busy(False)

	def _on_img_extract_shots(self) -> None:
		"""从故事生成分镜列表"""
		story_text = self.output.get("1.0", END).strip()
		if not story_text:
			messagebox.showwarning("提示", "请先在'故事'页生成或粘贴正文内容，然后再生成分镜")
			return
		try:
			self.set_busy(True)
			self.status.set("根据故事生成分镜中...")
			client = DeepSeekClient(
				api_key=_sanitize(self.api_key.get()),
				base_url=_sanitize(self.base_url.get()),
				model=_sanitize(self.model.get()),
			)
			inst = (
				"请把以下故事正文拆解为适合生成插图/分镜的'镜头清单'，使用中文简洁编号列出 6-12 条，"
				"每条包含：场景/主体/动作/情绪/关键物件/光线镜头（如 close-up、wide shot）。"
				"格式：每行一个分镜，格式为'序号. 场景描述 / 主体 / 动作 / 情绪 / 光线镜头'。只输出清单，不要其他文字。"
			)
			resp = client.chat([
				{"role": "system", "content": inst},
				{"role": "user", "content": story_text},
			], temperature=max(0.4, self.temperature.get() - 0.2))
			
			# 解析分镜列表
			shots = []
			shot_lines = []  # 保留带序号的原始行
			for line in resp.strip().split('\n'):
				line = line.strip()
				if line and (line[0].isdigit() or line.startswith('•') or line.startswith('-')):
					shot_lines.append(line)
					# 移除序号提取内容
					if '.' in line:
						shot_text = line.split('.', 1)[1].strip()
					elif line.startswith('•') or line.startswith('-'):
						shot_text = line[1:].strip()
					else:
						shot_text = line
					shots.append(shot_text)
			
			# 更新所有分镜显示框
			if shots:
				self.img_txt_all_shots.config(state=NORMAL)
				self.img_txt_all_shots.delete("1.0", END)
				self.img_txt_all_shots.insert("1.0", "\n".join(shot_lines))
				self.img_txt_all_shots.config(state=DISABLED)
				
				# 更新分镜选择器
				self.shot_selector['values'] = [f"{i+1}. {shot[:60]}..." if len(shot) > 60 else f"{i+1}. {shot}" for i, shot in enumerate(shots)]
				self.shot_selector['state'] = 'readonly'
				self.shot_selector.current(0)
				# 保存完整的分镜列表
				self.parsed_shots = shots
				# 显示第一个分镜
				self._on_shot_selected(None)
			
			self.status.set(f"已生成 {len(shots)} 个分镜（可选择生成）")
		except Exception as e:
			messagebox.showerror("错误", str(e))
		finally:
			self.set_busy(False)
	
	def _on_shot_selected(self, event) -> None:
		"""当选择分镜时"""
		if not hasattr(self, 'parsed_shots') or not self.parsed_shots:
			return
		
		selected_index = self.shot_selector.current()
		if selected_index < 0 or selected_index >= len(self.parsed_shots):
			return
		
		self.status.set(f"已选择第 {selected_index+1} 个分镜")
	
	def _on_img_prompt_from_current_shot(self) -> None:
		"""从当前选中的分镜生成中文图片描述"""
		if not hasattr(self, 'parsed_shots') or not self.parsed_shots:
			messagebox.showwarning("提示", "请先生成分镜")
			return
		
		selected_index = self.shot_selector.current()
		if selected_index < 0 or selected_index >= len(self.parsed_shots):
			messagebox.showwarning("提示", "请先在下拉框中选择一个分镜")
			return
		
		current_shot = self.parsed_shots[selected_index]
		
		story_text = self.output.get("1.0", END).strip() if hasattr(self, 'output') else ""
		scene = self.img_entry_scene.get().strip() if hasattr(self, 'img_entry_scene') else ""
		roles = self.img_txt_roles.get("1.0", END).strip() if hasattr(self, 'img_txt_roles') else ""
		
		try:
			self.set_busy(True)
			self.status.set("根据分镜生成图片描述中...")
			client = DeepSeekClient(
				api_key=_sanitize(self.api_key.get()),
				base_url=_sanitize(self.base_url.get()),
				model=_sanitize(self.model.get()),
			)
			inst = (
				"你是资深视觉设计师。基于分镜描述与故事上下文，生成一段详细的中文图片描述，"
				"用于后续转换为英文提示词生成图片。要求：\n"
				"1. 描述要包含：场景环境、主体人物外观（发型、服饰、年龄、表情）、动作姿态、光线氛围、镜头角度、画面风格\n"
				"2. 确保人物与故事设定一致\n"
				"3. 使用中文，描述清晰、细节丰富\n"
				"4. 不要输出任何Markdown格式，只输出描述文字"
			)
			user = (
				f"当前分镜：\n{current_shot}\n\n"
				f"故事上下文：\n{story_text[:500] if story_text else '无'}\n\n"
				f"补充场景：{scene or '无'}\n人物设定：{roles or '无'}\n\n"
				"请生成详细的中文图片描述。"
			)
			resp = client.chat([
				{"role": "system", "content": inst},
				{"role": "user", "content": user},
			], temperature=max(0.5, self.temperature.get() - 0.1))
			
			self.img_txt_prompt_cn.delete("1.0", END)
			self.img_txt_prompt_cn.insert(END, resp.strip())
			self.status.set("已生成中文图片描述（可编辑）")
		except Exception as e:
			messagebox.showerror("错误", str(e))
		finally:
			self.set_busy(False)

	def _on_img_prompt_from_shots(self) -> None:
		shots = self.img_txt_shots.get("1.0", END).strip()
		if not shots:
			messagebox.showwarning("提示", "请先在左侧生成或填写分镜，再转为提示词")
			return
		story_text = self.output.get("1.0", END).strip()
		scene = self.img_entry_scene.get().strip() if hasattr(self, 'img_entry_scene') else ""
		roles = self.img_txt_roles.get("1.0", END).strip() if hasattr(self, 'img_txt_roles') else ""
		try:
			self.set_busy(True)
			self.status.set("根据分镜生成提示词中...")
			client = DeepSeekClient(
				api_key=_sanitize(self.api_key.get()),
				base_url=_sanitize(self.base_url.get()),
				model=_sanitize(self.model.get()),
			)
			inst = (
				"你是资深视觉提示词工程师。基于分镜清单与故事上下文，输出单段英文提示词用于文生图，"
				"确保人物与故事中的设定一致（面部/发型/年龄/服饰/气质），并与所选场景匹配。包含场景/构图/主体细节/表情动作/光线镜头/风格与质感。"
				"禁止 Markdown，仅输出英文提示词。"
			)
			user = (
				f"分镜清单：\n{shots}\n\n"
				f"故事上下文：\n{story_text}\n\n"
				f"补充场景：{scene or '无'}\n人物设定：{roles or '无'}\n"
				"请给出最终英文提示词。"
			)
			resp = client.chat([
				{"role": "system", "content": inst},
				{"role": "user", "content": user},
			], temperature=max(0.4, self.temperature.get() - 0.2))
			self.img_txt_prompt.delete("1.0", END)
			self.img_txt_prompt.insert(END, resp.strip())
			self.status.set("已根据分镜生成提示词")
		except Exception as e:
			messagebox.showerror("错误", str(e))
		finally:
			self.set_busy(False)

	def _update_img_preview(self) -> None:
		if not self.img_last_image:
			return
		max_w = max(300, self.page_image.winfo_width() - 80)
		max_h = max(300, self.page_image.winfo_height() - 220)
		img = self.img_last_image.copy()
		img.thumbnail((max_w, max_h))
		self.img_preview_photo = ImageTk.PhotoImage(img)
		self.img_preview.configure(image=self.img_preview_photo)

	def _on_img_save(self) -> None:
		if not self.img_last_image:
			return
		path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG","*.png"),("JPEG","*.jpg;*.jpeg"),("WEBP","*.webp")])
		if not path:
			return
		try:
			self.img_last_image.save(path)
			# 如果有当前项目，也保存到项目中
			if self.current_project:
				self.current_project.save_image(path)
				self.status.set(f"图片已保存到: {path} 和当前项目")
			else:
				self.status.set(f"图片已保存到: {path}")
			messagebox.showinfo("成功", f"已保存到: {path}")
		except Exception as e:
			messagebox.showerror("错误", str(e))
	
	def _auto_save_to_project(self) -> None:
		"""自动保存故事到当前项目（如果有）"""
		if not self.current_project:
			return
		
		story_content = self.output.get("1.0", END).strip()
		if not story_content or story_content == "生成中...":
			return
		
		try:
			# 保存故事和参数
			self.current_project.save_story(
				story_content,
				category=self.category.get(),
				requirement=self._get_prompt_content(),
				style=self.style.get(),
				target_chars=self.target_chars.get(),
			)
			# 在后台更新项目列表（不显示弹窗）
			if hasattr(self, 'project_tree'):
				self._refresh_project_list()
			if hasattr(self, 'status'):
				self.status.set(f"故事已自动保存到项目: {self.current_project.metadata['name']}")
		except Exception as e:
			# 静默失败，不打扰用户
			print(f"自动保存失败: {e}")
	
	# ==================== 风格选择功能 ====================
	
	def _show_style_menu(self) -> None:
		"""显示风格选择菜单"""
		menu = tk.Menu(self, tearoff=0)
		
		# 添加"清空风格"选项
		menu.add_command(label="🗑️ 清空所有风格", command=lambda: self.style.set(""))
		menu.add_separator()
		
		# 添加"手动输入"选项
		menu.add_command(label="✏️ 手动输入风格...", command=self._manual_input_style)
		menu.add_separator()
		
		# 添加预设风格选项（分组显示）
		menu.add_command(label="📚 --- 预设风格（点击追加） ---", state=DISABLED)
		for style_tag in self.preset_styles:
			menu.add_command(
				label=f"  {style_tag}",
				command=lambda s=style_tag: self._add_style_tag(s)
			)
		
		# 在按钮下方显示菜单
		try:
			x = self.btn_add_style.winfo_rootx()
			y = self.btn_add_style.winfo_rooty() + self.btn_add_style.winfo_height()
			menu.post(x, y)
		except:
			menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
	
	def _add_style_tag(self, tag: str) -> None:
		"""添加风格标签到风格说明"""
		current = self.style.get().strip()
		if not current:
			self.style.set(tag)
		else:
			# 检查是否已存在
			tags = [t.strip() for t in current.split("/")]
			if tag not in tags:
				self.style.set(current + "/" + tag)
		if hasattr(self, 'status'):
			self.status.set(f"已添加风格: {tag}")
	
	def _manual_input_style(self) -> None:
		"""手动输入自定义风格"""
		from tkinter import simpledialog
		custom_style = simpledialog.askstring(
			"手动输入风格",
			"请输入自定义风格标签:\n\n（例如：日系清新、赛博朋克、武侠风等）",
			initialvalue=""
		)
		if custom_style and custom_style.strip():
			self._add_style_tag(custom_style.strip())
	
	# ==================== 项目管理回调函数 ====================
	
	def _refresh_project_list(self) -> None:
		"""刷新项目列表"""
		try:
			# 清空列表
			for item in self.project_tree.get_children():
				self.project_tree.delete(item)
			
			# 加载项目
			projects = self.project_manager.list_projects()
			for proj in projects:
				self.project_tree.insert("", "end", values=(
					proj["name"],
					proj.get("category", ""),
					proj.get("story_length", 0),
					proj.get("image_count", 0),
					proj.get("updated_at", "")[:19].replace("T", " "),  # 格式化时间
				), tags=(proj["path"],))
			
			if hasattr(self, 'status'):
				self.status.set(f"已加载 {len(projects)} 个项目")
		except Exception as e:
			messagebox.showerror("错误", f"刷新项目列表失败: {e}")
	
	def _on_new_project(self) -> None:
		"""创建新项目"""
		# 弹出对话框让用户输入项目名称
		from tkinter import simpledialog
		project_name = simpledialog.askstring("新建项目", "请输入项目名称:")
		if not project_name or not project_name.strip():
			return
		
		try:
			self.current_project = self.project_manager.create_project(project_name.strip())
			self.lbl_current_project.config(text=f"当前项目: {project_name}", fg="#4CAF50")
			self.btn_save_story.config(state=NORMAL)
			self._refresh_project_list()
			if hasattr(self, 'status'):
				self.status.set(f"已创建项目: {project_name}")
			messagebox.showinfo("成功", f"项目已创建: {project_name}\n\n现在可以前往'故事生成'页面创作内容")
			# 切换到故事生成页面
			self.notebook.select(self.page_story)
		except Exception as e:
			messagebox.showerror("错误", f"创建项目失败: {e}")
	
	def _on_load_project(self) -> None:
		"""加载选中的项目"""
		selection = self.project_tree.selection()
		if not selection:
			messagebox.showwarning("提示", "请先选择一个项目")
			return
		
		try:
			# 获取项目路径
			item = selection[0]
			tags = self.project_tree.item(item, "tags")
			if not tags:
				return
			project_path = tags[0]
			
			# 加载项目
			self.current_project = self.project_manager.load_project(project_path)
			project_name = self.current_project.metadata.get("name", "")
			self.lbl_current_project.config(text=f"当前项目: {project_name}", fg="#4CAF50")
			self.btn_save_story.config(state=NORMAL)
			
			# 恢复故事内容到输出框
			story_content = self.current_project.load_story()
			if story_content:
				self.output.delete("1.0", END)
				self.output.insert(END, story_content)
				if hasattr(self, 'status'):
					self.status.set(f"已加载项目: {project_name} ({len(story_content)} 字)")
			else:
				if hasattr(self, 'status'):
					self.status.set(f"已加载项目: {project_name} (无故事内容)")
			
			# 恢复创作参数
			meta = self.current_project.metadata
			if meta.get("category"):
				self.category.set(meta["category"])
			if meta.get("requirement"):
				self.prompt_text.delete("1.0", END)
				self.prompt_text.insert("1.0", meta["requirement"])
				self.prompt_text.tag_remove("placeholder", "1.0", "end")
			if meta.get("style"):
				self.style.set(meta["style"])
			if meta.get("target_chars"):
				self.target_chars.set(meta["target_chars"])
			
			messagebox.showinfo("成功", f"项目已加载: {project_name}\n\n故事内容已恢复到输出区域")
			# 切换到故事生成页面
			self.notebook.select(self.page_story)
		except Exception as e:
			messagebox.showerror("错误", f"加载项目失败: {e}")
	
	def _on_save_story(self) -> None:
		"""保存当前故事到项目"""
		if not self.current_project:
			messagebox.showwarning("提示", "请先创建或加载一个项目")
			return
		
		story_content = self.output.get("1.0", END).strip()
		if not story_content:
			messagebox.showwarning("提示", "输出区域没有内容可保存")
			return
		
		try:
			# 保存故事和参数
			self.current_project.save_story(
				story_content,
				category=self.category.get(),
				requirement=self._get_prompt_content(),
				style=self.style.get(),
				target_chars=self.target_chars.get(),
			)
			self._refresh_project_list()
			if hasattr(self, 'status'):
				self.status.set(f"故事已保存到项目: {self.current_project.metadata['name']}")
			messagebox.showinfo("成功", f"故事已保存到项目\n\n字数: {len(story_content)}")
		except Exception as e:
			messagebox.showerror("错误", f"保存故事失败: {e}")
	
	def _on_delete_project(self) -> None:
		"""删除选中的项目"""
		selection = self.project_tree.selection()
		if not selection:
			messagebox.showwarning("提示", "请先选择一个项目")
			return
		
		# 获取项目信息
		item = selection[0]
		values = self.project_tree.item(item, "values")
		project_name = values[0] if values else "未知项目"
		tags = self.project_tree.item(item, "tags")
		if not tags:
			return
		project_path = tags[0]
		
		# 确认删除
		confirm = messagebox.askyesno(
			"确认删除",
			f"确定要删除项目 '{project_name}' 吗？\n\n这将永久删除项目文件夹及其所有内容（故事、图片等）。\n\n此操作不可恢复！",
			icon="warning"
		)
		if not confirm:
			return
		
		try:
			# 如果删除的是当前项目，清空当前项目
			if self.current_project and str(self.current_project.project_dir) == project_path:
				self.current_project = None
				self.lbl_current_project.config(text="未选择项目", fg="#888888")
				self.btn_save_story.config(state=DISABLED)
			
			self.project_manager.delete_project(project_path)
			self._refresh_project_list()
			if hasattr(self, 'status'):
				self.status.set(f"已删除项目: {project_name}")
			messagebox.showinfo("成功", f"项目已删除: {project_name}")
		except Exception as e:
			messagebox.showerror("错误", f"删除项目失败: {e}")
	
	# ==================== 章节管理功能 ====================
	
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
	
	def _generate_single_section(self, query: str, contexts: list[str], section_index: int) -> None:
		"""生成单个章节（无知识库）"""
		def task():
			try:
				self.set_busy(True)
				client = DeepSeekClient(
					api_key=_sanitize(self.api_key.get()),
					base_url=_sanitize(self.base_url.get()),
					model=_sanitize(self.model.get()),
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
		client = DeepSeekClient(
			api_key=_sanitize(self.api_key.get()),
			base_url=_sanitize(self.base_url.get()),
			model=_sanitize(self.model.get()),
		)
		self._do_generate_section(client, query, contexts, section_index)
	
	def _do_generate_section(self, client: DeepSeekClient, requirement: str, contexts: list[str], section_index: int) -> None:
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
		self.output.insert(END, f"\n{'='*50}\n")
		self.output.insert(END, f"【第 {section_index+1}/{total_sections} 章：{section['title']}】\n\n")
		self.output.see(END)
		
		# 构建提示词
		section_prompt = self._build_section_prompt(
			section=section,
			section_index=section_index,
			total_sections=total_sections,
			previous_content=self.generated_content,
			requirement=requirement,
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
		
		# 自动保存
		self._auto_save_to_project()
	
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
	
	def _auto_generate_all_sections(self, query: str, contexts: list[str], start_index: int) -> None:
		"""自动生成所有章节（无知识库）"""
		def task():
			try:
				self.set_busy(True)
				client = DeepSeekClient(
					api_key=_sanitize(self.api_key.get()),
					base_url=_sanitize(self.base_url.get()),
					model=_sanitize(self.model.get()),
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
				messagebox.showinfo("完成", f"所有章节已生成完成！\n\n共 {total_sections} 章，总字数：{len(self.generated_content)} 字")
			except Exception as e:
				import traceback
				self.output.insert(END, "\n自动生成出错:\n" + traceback.format_exc() + "\n")
				messagebox.showerror("错误", str(e))
			finally:
				self.set_busy(False)
		threading.Thread(target=task, daemon=True).start()
	
	def _auto_generate_all_sections_with_contexts(self, query: str, contexts: list[str], start_index: int) -> None:
		"""自动生成所有章节（带知识库）"""
		client = DeepSeekClient(
			api_key=_sanitize(self.api_key.get()),
			base_url=_sanitize(self.base_url.get()),
			model=_sanitize(self.model.get()),
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
		messagebox.showinfo("完成", f"所有章节已生成完成！\n\n共 {total_sections} 章，总字数：{len(self.generated_content)} 字")

if __name__ == "__main__":
	App().mainloop()
