"""
Image相关功能模块
"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, messagebox, filedialog
import tkinter as tk
from tkinter import ttk
import os
from PIL import Image, ImageTk

from src.clients.deepseek_client import DeepSeekClient
from src.clients.image_client import OpenAIImageClient
from ..utils import sanitize as _sanitize


class ImageMixin:
	"""Image管理功能"""
	
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
		self.image_tab_create = tk.Frame(self.image_notebook, bg="#2b2b2b")
		self.image_tab_setup = tk.Frame(self.image_notebook, bg="#2b2b2b")
		
		self.image_notebook.add(self.image_tab_create, text="  ✍️ 创作  ")
		self.image_notebook.add(self.image_tab_setup, text="  ⚙️ 配置  ")
		
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
		
		# 第一行按钮：主要的分镜生成按钮
		rowf1 = ttk.Frame(grp_shots)
		rowf1.pack(fill="x", padx=6, pady=(0, 4))
		self.img_btn_extract_brief = ttk.Button(rowf1, text="📝 大致(8-12)", command=lambda: self._on_img_extract_shots(mode="brief"), width=14)
		self.img_btn_extract_brief.pack(side=LEFT, padx=(0, 3))
		self.img_btn_extract_normal = ttk.Button(rowf1, text="📝 标准(12-20)", command=lambda: self._on_img_extract_shots(mode="normal"), width=14)
		self.img_btn_extract_normal.pack(side=LEFT, padx=(0, 3))
		self.img_btn_extract_detailed = ttk.Button(rowf1, text="📝 详细(20-30)", command=lambda: self._on_img_extract_shots(mode="detailed"), width=14)
		self.img_btn_extract_detailed.pack(side=LEFT, padx=(0, 3))
		self.img_btn_extract_video = ttk.Button(rowf1, text="🎬 视频版(10-15)", command=lambda: self._on_img_extract_shots(mode="video"), width=14)
		self.img_btn_extract_video.pack(side=LEFT, padx=(0, 3))
		
		# 第二行按钮：辅助功能按钮
		rowf2 = ttk.Frame(grp_shots)
		rowf2.pack(fill="x", padx=6, pady=(0, 6))
		tk.Label(rowf2, text="💡 视频版包含镜头时长、运镜、转场、音效等视频制作要素", font=("", 9), fg="#90CAF9", bg="#2b2b2b").pack(side=LEFT)
		self.img_btn_copy_shots = ttk.Button(rowf2, text="📋 恢复", command=self._on_copy_shots, width=8)
		self.img_btn_copy_shots.pack(side=RIGHT, padx=(3, 0))
		self.img_btn_clear_shots = ttk.Button(rowf2, text="🗑️ 清空", command=self._on_clear_shots, width=8)
		self.img_btn_clear_shots.pack(side=RIGHT, padx=3)
		
		# 合并：选择分镜 + 图片类型与场景补充
		grp_ctx_add = ttk.LabelFrame(left, text="🎯 选择要生成的分镜", padding=(8, 5))
		grp_ctx_add.pack(fill="x", padx=0, pady=(0, 8))
		grp_ctx_add.columnconfigure(1, weight=1)
		
		# 分镜选择
		tk.Label(grp_ctx_add, text="分镜:", font=("", 10)).grid(row=0, column=0, sticky="e", padx=(0, 8), pady=(6, 6))
		self.shot_selector = ttk.Combobox(grp_ctx_add, state="disabled", font=("", 10))
		self.shot_selector.grid(row=0, column=1, columnspan=2, sticky="we", padx=(0, 6), pady=(6, 6))
		self.shot_selector.bind("<<ComboboxSelected>>", self._on_shot_selected)
		
		# 图片类型选择
		tk.Label(grp_ctx_add, text="图片类型:", font=("", 10)).grid(row=1, column=0, sticky="e", padx=(0, 8), pady=6)
		self.img_type = tk.StringVar(value="写实照片")
		# 扩展图片类型，包含更多中国风格；支持手动输入自定义类型
		self.combo_img_type = ttk.Combobox(grp_ctx_add, textvariable=self.img_type, font=("", 10), width=20,
										   values=("写实照片", "日系动漫", "3D渲染", "水彩画", "油画", "素描", 
											       "赛博朋克", "蒸汽朋克", "像素风", "中国风", "国风插画", 
												   "古风", "仙侠", "武侠", "水墨画", "工笔画", "敦煌壁画", 
												   "恐怖", "惊悚", "诡异", "悬疑", "玄幻", "科幻", "魔幻"))
		self.combo_img_type.grid(row=1, column=1, sticky="we", padx=(0, 6), pady=6)
		# 添加提示文字
		tk.Label(grp_ctx_add, text="（可手动输入自定义类型）", font=("", 8), fg="gray").grid(row=1, column=2, sticky="w", padx=4)
		
		tk.Label(grp_ctx_add, text="场景描述:", font=("", 10)).grid(row=2, column=0, sticky="e", padx=(0, 8), pady=6)
		self.img_entry_scene = ttk.Entry(grp_ctx_add, font=("", 10))
		self.img_entry_scene.grid(row=2, column=1, columnspan=2, sticky="we", padx=(0, 6), pady=6)
		tk.Label(grp_ctx_add, text="角色特征:", font=("", 10)).grid(row=3, column=0, sticky="ne", padx=(0, 8), pady=(6, 6))
		self.img_txt_roles = tk.Text(grp_ctx_add, height=3, font=("", 10), wrap=tk.WORD, relief=tk.SOLID, borderwidth=1)
		self.img_txt_roles.grid(row=3, column=1, columnspan=2, sticky="we", padx=(0, 6), pady=(6, 6))

		# Left: 提示词（中文）
		grp_prompt = ttk.LabelFrame(left, text="💬 图片描述（中文，可编辑）", padding=(8, 5))
		grp_prompt.pack(fill="both", expand=True, padx=0, pady=0)
		self.img_txt_prompt_cn = tk.Text(grp_prompt, height=10, font=("", 10), wrap=tk.WORD, relief=tk.SOLID, borderwidth=1)
		self.img_txt_prompt_cn.pack(fill="both", expand=True, padx=6, pady=(6, 8))
		rowp = ttk.Frame(grp_prompt)
		rowp.pack(fill="x", padx=6, pady=(0, 6))
		self.img_btn_build_from_shot = ttk.Button(rowp, text="✨ 从当前分镜生成", command=self._on_img_prompt_from_current_shot, width=18)
		self.img_btn_build_from_shot.pack(side=LEFT, padx=(0, 3))
		self.img_btn_copy = ttk.Button(rowp, text="📋 复制", command=self._on_copy_img_prompt, width=8)
		self.img_btn_copy.pack(side=LEFT, padx=3)
		self.img_btn_clear = ttk.Button(rowp, text="🗑️ 清空", command=self._on_clear_img_prompt, width=8)
		self.img_btn_clear.pack(side=LEFT, padx=3)

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
		
		# 创建Canvas和滚动条用于图片预览
		preview_frame = ttk.Frame(grp_preview)
		preview_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
		
		# 创建垂直和水平滚动条
		v_scroll = ttk.Scrollbar(preview_frame, orient="vertical")
		h_scroll = ttk.Scrollbar(preview_frame, orient="horizontal")
		
		# 创建Canvas
		self.img_canvas = tk.Canvas(preview_frame, bg="#2b2b2b", 
									 yscrollcommand=v_scroll.set,
									 xscrollcommand=h_scroll.set,
									 highlightthickness=0)
		
		# 配置滚动条
		v_scroll.config(command=self.img_canvas.yview)
		h_scroll.config(command=self.img_canvas.xview)
		
		# 布局
		self.img_canvas.grid(row=0, column=0, sticky="nsew")
		v_scroll.grid(row=0, column=1, sticky="ns")
		h_scroll.grid(row=1, column=0, sticky="ew")
		
		preview_frame.grid_rowconfigure(0, weight=1)
		preview_frame.grid_columnconfigure(0, weight=1)
		
		# 在Canvas上创建图片显示区域
		self.img_preview = ttk.Label(self.img_canvas, text="图片预览区\n\n点击\"生成图片\"后\n图片将显示在这里", 
									  font=("", 10), foreground="#888888", anchor="center",
									  background="#2b2b2b")
		self.img_canvas_window = self.img_canvas.create_window(0, 0, window=self.img_preview, anchor="nw")
		
		# 绑定Canvas大小变化事件，自动调整图片显示
		self.img_canvas.bind('<Configure>', self._on_canvas_configure)
	
	def _build_image_setup_tab(self) -> None:
		"""构建图片API配置页面"""
		# 创建Canvas和滚动条来支持内容滚动
		canvas = tk.Canvas(self.image_tab_setup, bg="#2b2b2b", highlightthickness=0)
		scrollbar = ttk.Scrollbar(self.image_tab_setup, orient="vertical", command=canvas.yview)
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
			if event.delta:
				canvas.yview_scroll(int(-1 * event.delta), "units")
			elif event.num == 4:
				canvas.yview_scroll(-1, "units")
			elif event.num == 5:
				canvas.yview_scroll(1, "units")
		
		# 鼠标进入Canvas区域时绑定滚轮事件
		def _bind_mousewheel(event):
			canvas.bind_all("<MouseWheel>", _on_mousewheel)
			canvas.bind_all("<Button-4>", _on_mousewheel)
			canvas.bind_all("<Button-5>", _on_mousewheel)
		
		# 鼠标离开Canvas区域时解绑滚轮事件
		def _unbind_mousewheel(event):
			canvas.unbind_all("<MouseWheel>")
			canvas.unbind_all("<Button-4>")
			canvas.unbind_all("<Button-5>")
		
		canvas.bind("<Enter>", _bind_mousewheel)
		canvas.bind("<Leave>", _unbind_mousewheel)
		
		canvas.pack(side="left", fill="both", expand=True)
		scrollbar.pack(side="right", fill="y")
		
		# API 配置组
		grp_api = ttk.LabelFrame(scrollable_frame, text="🎨 图片生成 API 配置")
		grp_api.pack(fill="x", padx=15, pady=(15, 8))
		grp_api.columnconfigure(1, weight=1)
		grp_api.columnconfigure(5, weight=1)
		
		# API预设下拉框
		tk.Label(grp_api, text="API预设:").grid(row=0, column=0, sticky="e", padx=6, pady=4)
		self.img_api_preset = tk.StringVar(value="OpenAI (DALL-E)")
		self.img_api_presets = {
			"OpenAI (DALL-E)": {
				"base_url": "https://api.openai.com/v1",
				"model": "dall-e-3",
				"key": "",
				"provider": "openai"
			},
			"腾讯混元": {
				"base_url": "https://hunyuan.tencentcloudapi.com",
				"model": "hunyuan-turbo",
				"key": "",
				"provider": "hunyuan",
				"secret_key": ""
			},
			"Azure OpenAI": {
				"base_url": "https://YOUR_RESOURCE.openai.azure.com",
				"model": "dall-e-3",
				"key": "",
				"provider": "openai"
			},
			"Stability AI": {
				"base_url": "https://api.stability.ai/v1",
				"model": "stable-diffusion-xl-1024-v1-0",
				"key": "",
				"provider": "openai"
			},
			"Midjourney API": {
				"base_url": "https://api.midjourneyapi.io/v1",
				"model": "midjourney",
				"key": "",
				"provider": "openai"
			},
			"自定义": {
				"base_url": "",
				"model": "",
				"key": "",
				"provider": "openai"
			}
		}
		
		# 加载自定义图片API预设
		self._load_custom_image_presets()
		
		self.combo_img_api_preset = ttk.Combobox(grp_api, textvariable=self.img_api_preset, 
												  values=list(self.img_api_presets.keys()),
												  state="readonly", width=20)
		self.combo_img_api_preset.grid(row=0, column=1, sticky="w", padx=6)
		self.combo_img_api_preset.bind("<<ComboboxSelected>>", self._on_img_api_preset_selected)
		
		# 添加保存自定义API按钮
		btn_save_img_preset = tk.Button(grp_api, text="💾 保存为自定义预设", command=self._save_custom_image_preset, 
				  font=("", 9), bg="#607D8B", fg="white", relief=tk.FLAT, padx=8, pady=3, cursor="hand2")
		btn_save_img_preset.grid(row=0, column=2, padx=(6, 2))
		
		# 添加删除自定义图片API按钮
		btn_delete_img_preset = tk.Button(grp_api, text="🗑️", command=self._delete_custom_image_preset, 
				  font=("", 9), bg="#d32f2f", fg="white", relief=tk.FLAT, padx=8, pady=3, cursor="hand2")
		btn_delete_img_preset.grid(row=0, column=3, padx=(2, 6), sticky="w")
		
		tk.Label(grp_api, text="提示: 可保存/删除自定义预设", fg="gray", font=("", 9)).grid(row=0, column=4, sticky="w", padx=6)

		tk.Label(grp_api, text="API Key / SecretId:").grid(row=1, column=0, sticky="e", padx=6, pady=4)
		self.img_entry_key = tk.Entry(grp_api, textvariable=self.img_api_key, show="*")
		self.img_entry_key.grid(row=1, column=1, columnspan=4, sticky="we", padx=6)
		
		tk.Label(grp_api, text="SecretKey (仅腾讯混元):").grid(row=2, column=0, sticky="e", padx=6, pady=4)
		self.img_secret_key = tk.StringVar(value="")
		self.img_entry_secret_key = tk.Entry(grp_api, textvariable=self.img_secret_key, show="*")
		self.img_entry_secret_key.grid(row=2, column=1, columnspan=4, sticky="we", padx=6)
		
		tk.Label(grp_api, text="Base URL:").grid(row=3, column=0, sticky="e", padx=6, pady=4)
		self.img_base_url = tk.StringVar(value="https://api.openai.com/v1")
		self.img_entry_base_url = tk.Entry(grp_api, textvariable=self.img_base_url)
		self.img_entry_base_url.grid(row=3, column=1, columnspan=4, sticky="we", padx=6)
		
		tk.Label(grp_api, text="Model:").grid(row=4, column=0, sticky="e", padx=6, pady=4)
		self.img_entry_model = tk.Entry(grp_api, textvariable=self.img_model)
		self.img_entry_model.grid(row=4, column=1, sticky="we", padx=6)
		tk.Button(grp_api, text="保存配置", command=self.save_img_api_config).grid(row=4, column=2, padx=6)
		tk.Button(grp_api, text="加载配置", command=self.load_img_api_config).grid(row=4, column=3, padx=6, sticky="w")
		# API测试按钮 - 与加载配置同行
		tk.Button(grp_api, text="API测试", command=self.on_test_image_api).grid(row=4, column=4, padx=6, sticky="w")
		
		# 图片参数设置
		grp_params = ttk.LabelFrame(scrollable_frame, text="📐 图片参数")
		grp_params.pack(fill="x", padx=15, pady=8)
		grp_params.columnconfigure(1, weight=1)
		
		# 图片尺寸
		tk.Label(grp_params, text="图片尺寸:").grid(row=0, column=0, sticky="e", padx=6, pady=4)
		self.img_combo_size = ttk.Combobox(grp_params, textvariable=self.img_size, 
										   values=(
											   "256x256", "512x512", "768x768",
											   "1024x1024", "1024x1792", "1792x1024",
											   "640x360", "1280x720", "1920x1080",
											   "360x640", "720x1280", "1080x1920"
										   ), 
										   width=15, state="readonly")
		self.img_combo_size.grid(row=0, column=1, sticky="w", padx=6, pady=4)
		
		# 提示文字
		hint_frame = tk.Frame(grp_params, bg="#2b2b2b")
		hint_frame.grid(row=1, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 4))
		tk.Label(hint_frame, text="方形: ", fg="gray", font=("", 9), bg="#2b2b2b").pack(side=LEFT)
		tk.Label(hint_frame, text="256x256, 512x512, 768x768, 1024x1024", fg="#90CAF9", font=("", 9), bg="#2b2b2b").pack(side=LEFT)
		
		hint_frame2 = tk.Frame(grp_params, bg="#2b2b2b")
		hint_frame2.grid(row=2, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 4))
		tk.Label(hint_frame2, text="竖版: ", fg="gray", font=("", 9), bg="#2b2b2b").pack(side=LEFT)
		tk.Label(hint_frame2, text="1024x1792, 360x640, 720x1280, 1080x1920", fg="#A5D6A7", font=("", 9), bg="#2b2b2b").pack(side=LEFT)
		
		hint_frame3 = tk.Frame(grp_params, bg="#2b2b2b")
		hint_frame3.grid(row=3, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 6))
		tk.Label(hint_frame3, text="横版: ", fg="gray", font=("", 9), bg="#2b2b2b").pack(side=LEFT)
		tk.Label(hint_frame3, text="1792x1024, 640x360, 1280x720, 1920x1080", fg="#FFCC80", font=("", 9), bg="#2b2b2b").pack(side=LEFT)
		
		# 辅助功能API配置（分镜头生成和图片描述生成）
		grp_assist_api = ttk.LabelFrame(scrollable_frame, text="🤖 辅助功能 API 配置（使用聊天模型）")
		grp_assist_api.pack(fill="x", padx=15, pady=8)
		grp_assist_api.columnconfigure(1, weight=1)
		
		# 说明文字
		tk.Label(grp_assist_api, text="选择用于生成分镜头和图片描述的聊天API（使用故事生成页面配置的API Key）", 
				 fg="gray", font=("", 9)).grid(row=0, column=0, columnspan=2, sticky="w", padx=6, pady=(4, 8))
		
		# 分镜头生成API选择
		tk.Label(grp_assist_api, text="分镜头生成API:").grid(row=1, column=0, sticky="e", padx=6, pady=4)
		self.shot_gen_api = tk.StringVar(value="DeepSeek")
		self.combo_shot_gen_api = ttk.Combobox(grp_assist_api, textvariable=self.shot_gen_api, 
											   values=["DeepSeek"],  # 初始值，会在加载配置时更新
											   state="readonly", width=30)
		self.combo_shot_gen_api.grid(row=1, column=1, sticky="w", padx=6, pady=4)
		
		# 图片描述生成API选择
		tk.Label(grp_assist_api, text="图片描述生成API:").grid(row=2, column=0, sticky="e", padx=6, pady=4)
		self.desc_gen_api = tk.StringVar(value="DeepSeek")
		self.combo_desc_gen_api = ttk.Combobox(grp_assist_api, textvariable=self.desc_gen_api,
											   values=["DeepSeek"],  # 初始值，会在加载配置时更新
											   state="readonly", width=30)
		self.combo_desc_gen_api.grid(row=2, column=1, sticky="w", padx=6, pady=4)
		
		# 保存按钮
		btn_save_assist_api = tk.Button(grp_assist_api, text="💾 保存辅助API配置", command=self._save_assist_api_config,
									   font=("", 9), bg="#4CAF50", fg="white", relief=tk.FLAT, padx=12, pady=4, cursor="hand2")
		btn_save_assist_api.grid(row=3, column=0, columnspan=2, padx=6, pady=(8, 4), sticky="we")
		
		# 测试日志输出区域（合理高度）
		grp_log = ttk.LabelFrame(scrollable_frame, text="📋 测试日志")
		grp_log.pack(fill="x", padx=15, pady=(8, 15))
		
		# 工具栏
		toolbar = tk.Frame(grp_log, bg="#2b2b2b")
		toolbar.pack(fill="x", padx=5, pady=(5, 0))
		
		tk.Label(toolbar, text="💡 提示：点击上方'API测试'按钮查看详细测试结果", 
				fg="#90CAF9", font=("", 9), bg="#2b2b2b").pack(side=LEFT, padx=5)
		
		btn_clear_log = tk.Button(toolbar, text="🗑️ 清空日志", 
								  command=lambda: self.img_test_log.delete("1.0", END),
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
		self.img_test_log = tk.Text(log_container, wrap="word", 
									yscrollcommand=scroll_y.set,
									bg="#1e1e1e", fg="#d4d4d4", 
									font=("Consolas", 10), relief=tk.FLAT,
									padx=10, pady=10)
		self.img_test_log.pack(fill="both", expand=True)
		scroll_y.config(command=self.img_test_log.yview)
		
		# 初始提示信息
		self.img_test_log.insert("1.0", "欢迎使用AI图片生成平台！\n\n")
		self.img_test_log.insert(END, "📝 使用说明：\n")
		self.img_test_log.insert(END, "1. 配置好上方的API信息\n")
		self.img_test_log.insert(END, "2. 点击'API测试'按钮测试连接\n")
		self.img_test_log.insert(END, "3. 测试结果会显示在此区域\n\n")
		self.img_test_log.insert(END, "准备就绪，可以开始测试了... ✨\n")
		
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
		
		def task(prompt_cn=prompt_cn):
			try:
				self.img_btn_gen.configure(state=DISABLED)
				self.status.set("🎨 准备生成图片...（初始化）")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("准备生成图片...", "🎨")
				
				# 获取图片类型
				img_type = self.img_type.get() if hasattr(self, 'img_type') else "写实照片"
				
				self.status.set(f"📝 正在翻译【{img_type}】风格图片描述为英文...（步骤1/3）")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("翻译提示词 (1/3)", "📝")
				
				# 根据图片类型定义英文风格关键词
				style_keywords = {
					"写实照片": "photorealistic, high quality photography, natural lighting, realistic, detailed, 8K",
					"日系动漫": "anime style, Japanese animation, vibrant colors, cel shading, anime artwork, high quality anime",
					"3D渲染": "3D render, CGI, high quality rendering, octane render, unreal engine, detailed textures",
					"水彩画": "watercolor painting, soft colors, artistic, traditional art, watercolor style, delicate brushstrokes",
					"油画": "oil painting, thick brushstrokes, classical art style, rich colors, fine art, painterly",
					"素描": "sketch style, pencil drawing, line art, monochrome, artistic sketch, detailed linework",
					"赛博朋克": "cyberpunk style, neon lights, futuristic, dark atmosphere, high-tech, sci-fi",
					"蒸汽朋克": "steampunk style, gears and machinery, Victorian era, retro-futuristic, industrial aesthetic",
					"像素风": "pixel art style, 8-bit/16-bit graphics, retro game art, pixelated",
					"中国风": "Chinese traditional painting style, ink wash painting, classical Chinese art, poetic atmosphere",
					"国风插画": "Chinese style illustration, modern Chinese aesthetic, delicate line art, traditional colors, elegant composition",
					"古风": "ancient Chinese style, traditional hanfu, classical architecture, historical atmosphere, Tang/Song dynasty aesthetic",
					"仙侠": "Chinese xianxia fantasy, immortal cultivator, celestial scenery, flowing robes, mystical clouds, jade palace",
					"武侠": "Chinese wuxia, martial arts, sword fighting, ancient warrior, bamboo forest, misty mountains",
					"水墨画": "Chinese ink wash painting, sumi-e style, black ink, minimal colors, artistic brushwork, zen aesthetic",
					"工笔画": "Chinese gongbi painting, meticulous brushwork, fine details, traditional pigments, classical composition",
					"敦煌壁画": "Dunhuang murals style, ancient Buddhist art, flying apsaras, Tang dynasty colors, religious iconography",
					"恐怖": "horror style, dark atmosphere, creepy, eerie lighting, disturbing, scary, gothic",
					"惊悚": "thriller style, suspenseful, tense atmosphere, dramatic lighting, mysterious shadows, unsettling",
					"诡异": "uncanny style, bizarre, surreal, otherworldly, strange atmosphere, unsettling details",
					"悬疑": "mystery style, noir atmosphere, dramatic shadows, suspenseful composition, detective aesthetic",
					"玄幻": "Chinese xuanhuan fantasy, mystical elements, magical creatures, spiritual energy, epic landscape",
					"科幻": "sci-fi style, futuristic technology, space setting, advanced civilization, neon lights, cybernetic",
					"魔幻": "fantasy style, magical world, mythical creatures, enchanted forest, ethereal glow, epic adventure"
				}
				
				# 如果是自定义类型且不在预设中，使用通用关键词
				style_keyword = style_keywords.get(img_type, f"{img_type} style, artistic, high quality, detailed")
				
				# 1. 先将中文翻译为英文提示词
				# 使用故事生成的API来翻译（因为需要文本生成能力）
				story_api_key = _sanitize(self.api_key.get())
				if not story_api_key:
					messagebox.showerror("错误", "请先在'故事生成'页面配置API Key（用于翻译提示词）")
					return
				
				print(f"DEBUG: 使用故事API翻译，API Key长度: {len(story_api_key)}")
				
				client = DeepSeekClient(
					api_key=story_api_key,
					base_url=_sanitize(self.base_url.get()),
					model=_sanitize(self.model.get()),
				)
				inst = (
					f"你是专业的图片提示词翻译专家。请将中文图片描述翻译为适合DALL-E、Stable Diffusion等AI绘图工具的英文提示词。\n"
					f"目标风格：{img_type}\n"
					f"风格关键词：{style_keyword}\n"
					f"要求：\n"
					f"1. 保留核心细节（场景、人物、动作、光线、镜头、风格等），但要简洁\n"
					f"2. 确保翻译体现【{img_type}】的风格特点\n"
					f"3. 使用专业的图像生成术语（如 cinematic lighting, wide shot, close-up等）\n"
					f"4. 输出纯英文，不要任何中文或其他语言\n"
					f"5. 控制在500个英文单词以内，优先保留最重要的视觉元素\n"
					f"6. 不要输出任何解释，只输出最终的英文提示词"
				)
				
				# 如果中文描述过长，先截断
				max_cn_length = 800
				prompt_cn_for_translate = prompt_cn
				if len(prompt_cn_for_translate) > max_cn_length:
					prompt_cn_for_translate = prompt_cn_for_translate[:max_cn_length] + "..."
				
				prompt_en = client.chat([
					{"role": "system", "content": inst},
					{"role": "user", "content": f"图片类型：{img_type}\n\n请翻译以下中文图片描述为简洁的英文提示词：\n\n{prompt_cn_for_translate}"},
				], temperature=0.3)
				
				# 过滤可能违反内容策略的词汇
				sensitive_words = [
					'blood', 'bloody', 'gore', 'gory', 'violence', 'violent', 'death', 'dead', 'corpse',
					'kill', 'murder', 'suicide', 'weapon', 'gun', 'knife', 'explosion', 'bomb',
					'torture', 'mutilation', 'dismember', 'decapitate', 'horrific', 'gruesome'
				]
				
				# 温和替换敏感词
				replacements = {
					'blood': 'red liquid', 'bloody': 'stained', 'gore': 'dramatic scene',
					'violence': 'intense action', 'violent': 'intense', 'death': 'ending',
					'dead': 'motionless', 'corpse': 'figure', 'kill': 'defeat', 
					'murder': 'incident', 'suicide': 'tragedy', 'weapon': 'tool',
					'gun': 'device', 'knife': 'blade', 'explosion': 'burst',
					'bomb': 'device', 'torture': 'suffering', 'mutilation': 'injury',
					'dismember': 'separate', 'decapitate': 'remove', 
					'horrific': 'dramatic', 'gruesome': 'intense'
				}
				
				prompt_en_filtered = prompt_en
				for word, replacement in replacements.items():
					import re
					# 使用正则表达式进行大小写不敏感的替换
					pattern = re.compile(re.escape(word), re.IGNORECASE)
					prompt_en_filtered = pattern.sub(replacement, prompt_en_filtered)
				
				# 添加安全后缀
				prompt_en = prompt_en_filtered + ", artistic style, cinematic composition, professional photography"
				
				# 检查英文提示词长度，如果太长则截断（保留在1000字符以内）
				max_en_length = 1000
				if len(prompt_en) > max_en_length:
					# 在句号或逗号处截断，保持完整性
					truncated = prompt_en[:max_en_length]
					last_punct = max(truncated.rfind('.'), truncated.rfind(','))
					if last_punct > 800:
						prompt_en = truncated[:last_punct + 1]
					else:
						prompt_en = truncated
				
				# 2. 根据当前预设选择API提供商
				current_preset = self.img_api_preset.get()
				provider = self.img_api_presets.get(current_preset, {}).get("provider", "openai")
				
				print(f"DEBUG: 当前图片API预设: {current_preset}, 提供商: {provider}")
				print(f"DEBUG: 翻译后的英文提示词长度: {len(prompt_en)}")
				print(f"DEBUG: 英文提示词前100字符: {prompt_en[:100]}...")
				
				self.status.set(f"🖼️ 翻译完成，正在调用图片生成API...（步骤2/3）")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("正在生成图片 (2/3)", "🎨")
				
				# 3. 使用对应的客户端生成图片
				if provider == "hunyuan":
					# 使用腾讯混元API
					from src.clients.hunyuan_image_client import HunyuanImageClient
					
					self.status.set(f"🎨 使用腾讯混元API生成【{img_type}】风格图片...（步骤2/3）")
					# 更新顶部状态栏
					if hasattr(self, 'update_header_status'):
						self.update_header_status("腾讯混元生成中 (2/3)", "🎨")
					
					secret_id = self.img_api_key.get().strip()
					secret_key = self.img_secret_key.get().strip()
					
					if not secret_id or not secret_key:
						messagebox.showerror("错误", "请先配置腾讯混元的SecretId和SecretKey")
						return
					
					# 根据图片类型映射腾讯混元的style参数
					hunyuan_style_map = {
						"写实照片": "201",  # 日系动漫风格（腾讯混元默认，也适合写实）
						"日系动漫": "201",  # 日系动漫风格
						"3D渲染": "201",
						"水彩画": "201",
						"油画": "201",
						"素描": "201",
						"赛博朋克": "201",
						"蒸汽朋克": "201",
						"像素风": "201",
						"中国风": "201",
						"国风插画": "201",
						"古风": "201",
						"仙侠": "201",
						"武侠": "201",
						"水墨画": "201",
						"工笔画": "201",
						"敦煌壁画": "201",
						"恐怖": "201",
						"惊悚": "201",
						"诡异": "201",
						"悬疑": "201",
						"玄幻": "201",
						"科幻": "201",
						"魔幻": "201"
					}
					
					hunyuan_style = hunyuan_style_map.get(img_type, "201")
					
					hunyuan_client = HunyuanImageClient(
						secret_id=secret_id,
						secret_key=secret_key
					)
					
					# 腾讯混元支持中文，使用中文风格描述
					# 定义中文风格描述
					style_desc_cn = {
						"写实照片": "高清摄影，写实风格，自然光线，真实质感",
						"日系动漫": "日系动漫风格，精美作画，色彩鲜艳",
						"3D渲染": "3D渲染，高品质建模，精致材质",
						"水彩画": "水彩画风格，色彩柔和，艺术感强",
						"油画": "油画质感，笔触厚重，色彩浓郁",
						"素描": "素描风格，线条流畅，黑白灰调",
						"赛博朋克": "赛博朋克风格，霓虹灯光，未来科技感",
						"蒸汽朋克": "蒸汽朋克风格，机械齿轮，复古科技",
						"像素风": "像素艺术风格，复古游戏美术",
						"中国风": "中国传统绘画风格，水墨意境，古典韵味",
						"国风插画": "国风插画，现代中国美学，线条精美，色彩典雅",
						"古风": "古风，传统服饰，古代建筑，历史氛围，唐宋美学",
						"仙侠": "仙侠奇幻，修仙者，天宫仙境，飘逸长袍，仙气缭绕",
						"武侠": "武侠江湖，武林高手，剑客，竹林，烟雨山水",
						"水墨画": "中国水墨画，笔墨韵味，黑白灰调，禅意美学",
						"工笔画": "工笔重彩，精细笔法，传统颜料，古典构图",
						"敦煌壁画": "敦煌壁画风格，飞天，佛教艺术，唐代色彩",
						"恐怖": "恐怖氛围，阴暗诡异，诡谲光影，惊悚元素",
						"惊悚": "惊悚风格，悬疑紧张，戏剧化光影，神秘阴影",
						"诡异": "诡异风格，超现实，异世界，诡谲氛围",
						"悬疑": "悬疑风格，黑色电影，戏剧阴影，侦探美学",
						"玄幻": "玄幻奇幻，神秘元素，灵兽异兽，磅礴山水",
						"科幻": "科幻未来，高科技，太空场景，先进文明，霓虹",
						"魔幻": "魔幻世界，神话生物，魔法森林，神秘光芒"
					}.get(img_type, f"{img_type}风格")
					
					# 腾讯混元API限制：Prompt最多256个UTF-8字符
					# 优化策略：使用关键词密集型描述，保证信息量
					
					# 简短风格关键词（用于腾讯混元）
					style_keywords_short = {
						"写实照片": "高清摄影",
						"日系动漫": "动漫风",
						"3D渲染": "3D渲染",
						"水彩画": "水彩",
						"油画": "油画质感",
						"素描": "素描",
						"赛博朋克": "赛博朋克",
						"蒸汽朋克": "蒸汽朋克",
						"像素风": "像素艺术",
						"中国风": "中国风",
						"国风插画": "国风插画",
						"古风": "古风",
						"仙侠": "仙侠",
						"武侠": "武侠",
						"水墨画": "水墨",
						"工笔画": "工笔",
						"敦煌壁画": "敦煌壁画",
						"恐怖": "恐怖",
						"惊悚": "惊悚",
						"诡异": "诡异",
						"悬疑": "悬疑",
						"玄幻": "玄幻",
						"科幻": "科幻",
						"魔幻": "魔幻"
					}.get(img_type, img_type)
					
					# 智能处理描述长度
					self.status.set(f"⚙️ 优化提示词以适配腾讯混元API...（字符限制256）")
					
					max_base_length = 230  # 为风格关键词留空间
					
					# 使用新变量避免闭包作用域问题
					processed_prompt = prompt_cn
					if len(prompt_cn) > max_base_length:
						# 优先截断，但保留完整的关键信息
						# 尝试在逗号或句号处截断
						truncated = prompt_cn[:max_base_length]
						last_punct = max(truncated.rfind('，'), truncated.rfind('。'), truncated.rfind(','))
						if last_punct > 180:  # 如果能找到合适的断点
							processed_prompt = truncated[:last_punct]
						else:
							processed_prompt = truncated
					
					# 组合风格关键词
					if style_keywords_short:
						enhanced_prompt = f"{processed_prompt}，{style_keywords_short}"
					else:
						enhanced_prompt = processed_prompt
					
					# 最终检查，确保不超过256字符
					if len(enhanced_prompt) > 256:
						# 如果还是超长，优先保证主描述
						enhanced_prompt = enhanced_prompt[:256]
					
					# 腾讯混元的分辨率格式是用冒号分隔，且只支持特定分辨率
					# 将常见分辨率映射到腾讯混元支持的分辨率
					size_mapping = {
						"512x512": "768:768",
						"768x768": "768:768",
						"1024x1024": "1024:1024",
						"1024x1792": "1080:1920",  # 映射到接近的16:9竖版
						"1792x1024": "1920:1080",  # 映射到接近的16:9横版
						"720x1280": "720:1280",
						"1280x720": "1280:720",
						"1080x1920": "1080:1920",
						"1920x1080": "1920:1080"
					}
					current_size = self.img_size.get()
					resolution = size_mapping.get(current_size, "1024:1024")
					
					self.status.set(f"🚀 正在调用腾讯混元API生成图片...（分辨率{resolution.replace(':', 'x')}）")
					
					result = hunyuan_client.generate(
						prompt=enhanced_prompt,  # 使用优化后的中文提示词
						resolution=resolution,
						style=hunyuan_style,
						rsp_img_type="base64"
					)
					
					self.status.set(f"✅ 处理生成结果...（步骤3/3）")
					# 更新顶部状态栏
					if hasattr(self, 'update_header_status'):
						self.update_header_status("处理结果 (3/3)", "✅")
					
					self.img_last_image = result.image
					self._update_img_preview()
					self.img_btn_save.configure(state=NORMAL)
					self.status.set(f"✨ 【{img_type}】风格图片生成成功！使用腾讯混元模型")
					# 更新顶部状态栏
					if hasattr(self, 'update_header_status'):
						self.update_header_status("图片生成完成", "✅")
					# 自动保存图片到项目
					self._auto_save_image_to_project()
				
				else:
					# 使用OpenAI兼容API
					model_name = self.img_model.get().strip() or "dall-e-3"
					img_api_key = self.img_api_key.get().strip()
					img_base_url = self.img_base_url.get().strip() if hasattr(self, 'img_base_url') else None
					
					print(f"DEBUG: 使用OpenAI兼容API")
					print(f"DEBUG: 模型: {model_name}")
					print(f"DEBUG: API Key长度: {len(img_api_key)}")
					print(f"DEBUG: Base URL: {img_base_url}")
					print(f"DEBUG: 图片尺寸: {self.img_size.get()}")
					
					if not img_api_key:
						messagebox.showerror("错误", "请先配置图片生成API Key")
						return
					
					self.status.set(f"🎨 使用OpenAI API生成【{img_type}】风格图片...（模型：{model_name}）")
					# 更新顶部状态栏
					if hasattr(self, 'update_header_status'):
						self.update_header_status("OpenAI生成中 (2/3)", "🎨")
					
					img_client = OpenAIImageClient(
						api_key=img_api_key, 
						model=model_name,
						base_url=img_base_url
					)
					
					if self.img_ref_path.get().strip():
						self.status.set(f"📸 使用参考图片生成...（步骤2/3）")
						results = img_client.generate_with_reference(
							prompt=prompt_en, 
							reference_image_path=self.img_ref_path.get().strip(), 
							size=self.img_size.get()
						)
					else:
						self.status.set(f"🚀 正在调用OpenAI API生成图片...（大小：{self.img_size.get()}）")
						results = img_client.generate(prompt=prompt_en, size=self.img_size.get(), n=1)
					
					if not results:
						messagebox.showerror("错误", "生成失败")
						return
					
					self.status.set(f"✅ 处理生成结果...（步骤3/3）")
					# 更新顶部状态栏
					if hasattr(self, 'update_header_status'):
						self.update_header_status("处理结果 (3/3)", "✅")
					
					self.img_last_image = results[0].image
					self._update_img_preview()
					self.img_btn_save.configure(state=NORMAL)
					self.status.set(f"✨ 【{img_type}】风格图片生成成功！提示词：{prompt_en[:40]}...")
					# 更新顶部状态栏
					if hasattr(self, 'update_header_status'):
						self.update_header_status("图片生成完成", "✅")
					# 自动保存图片到项目
					self._auto_save_image_to_project()
			except Exception as e:
				import traceback
				error_detail = traceback.format_exc()
				print(f"图片生成错误详情：\n{error_detail}")
				messagebox.showerror("错误", f"{str(e)}\n\n详细错误请查看控制台")
				self.status.set("❌ 图片生成失败，请检查配置和网络")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("图片生成失败", "❌")
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

	def _on_img_extract_shots(self, mode="normal") -> None:
		"""从故事生成分镜列表
		
		Args:
			mode: 分镜详细程度
				- "brief": 大致版，8-12个分镜，覆盖主要情节
				- "normal": 标准版，12-20个分镜（保持兼容）
				- "detailed": 详细版，20-30个分镜，细致分割每个场景
				- "video": 视频版，10-15个分镜，专为视频制作优化
		"""
		story_text = self.output.get("1.0", END).strip()
		if not story_text:
			messagebox.showwarning("提示", "请先在'故事'页生成或粘贴正文内容，然后再生成分镜")
			return
		
		# 获取选中的分镜头生成API配置
		selected_api = self.shot_gen_api.get() if hasattr(self, 'shot_gen_api') else "DeepSeek"
		if selected_api not in self.api_presets:
			messagebox.showerror("错误", f"未找到API预设: {selected_api}")
			return
		
		api_config = self.api_presets[selected_api]
		api_key = _sanitize(api_config.get("key", ""))
		base_url = _sanitize(api_config.get("base_url", ""))
		model = _sanitize(api_config.get("model", ""))
		
		if not api_key:
			messagebox.showwarning("提示", f"请先在故事生成页面配置 {selected_api} 的API Key")
			return
		
		# 根据模式设置不同的提示词
		if mode == "brief":
			shot_count = "8-12"
			mode_name = "大致版"
			inst = (
				"请把以下故事正文拆解为适合生成插图/分镜的'镜头清单'，使用中文简洁编号列出 5-8 条核心分镜，"
				"**只选取最关键、最具代表性的场景**，概括整个故事的主要情节转折和高潮时刻。\n\n"
				"每条包含：\n"
				"- 场景：具体地点和环境\n"
				"- 主体：人物或主要对象\n"
				"- 动作：正在发生的行为\n"
				"- 情绪：情感氛围\n"
				"- 光线/镜头：如 close-up（特写）、wide shot（全景）、low angle（低角度）等\n\n"
				"输出格式：每行一个分镜，格式为'序号. 场景 / 主体 / 动作 / 情绪 / 光线镜头'。\n"
				"注意：只输出清单，不要其他说明文字或解释。"
			)
		elif mode == "video":
			shot_count = "10-15"
			mode_name = "视频版"
			inst = (
				"请把以下故事正文拆解为**专业视频制作分镜脚本**，生成10-15个镜头，"
				"每个镜头都要考虑视频拍摄和剪辑的实际需求，确保镜头之间流畅连贯。\n\n"
				"每个镜头必须包含以下要素：\n"
				"1. **场景描述**：具体地点、环境、时间（如：白天/傍晚/夜晚）\n"
				"2. **人物与动作**：主体是谁，在做什么，表情状态\n"
				"3. **镜头类型**：特写(CU)/近景(MS)/中景(MCU)/全景(WS)/远景(LS)/过肩(OTS)/主观视角(POV)\n"
				"4. **运镜方式**：固定镜头/推镜/拉镜/摇镜/跟随/环绕/升降，如'缓慢推进''快速拉远''左摇''跟随人物'\n"
				"5. **镜头时长**：建议停留时间，如'3-5秒''8-10秒''瞬间闪过'\n"
				"6. **转场效果**：与下一镜头的衔接方式，如'切''淡入淡出''叠化''闪白''黑场'（最后一个镜头写'结束'）\n"
				"7. **声音提示**（可选）：环境音、音乐情绪、对白提示，如'紧张配乐''环境安静''人物对白'\n\n"
				"输出格式（每个镜头一行，用' | '分隔各要素）：\n"
				"序号. 场景描述 | 人物与动作 | 镜头类型 | 运镜方式 | 时长 | 转场 | 声音\n\n"
				"示例：\n"
				"1. 深夜城市街道，路灯昏暗 | 空无一人的街道，远处车灯闪烁 | 远景(LS) | 缓慢右摇 | 5-6秒 | 淡入淡出 | 低沉环境音，远处汽车声\n"
				"2. 公寓楼外景，三楼窗户亮灯 | 窗帘后有人影移动 | 中景(MCU) | 固定，缓慢推进 | 4-5秒 | 切 | 环境音渐弱\n\n"
				"注意事项：\n"
				"- 每个镜头都要考虑视频的流畅性和节奏感\n"
				"- 情绪转折处使用不同的镜头和运镜方式\n"
				"- 关键情节用特写+慢运镜，过渡场景用全景+快节奏\n"
				"- 只输出分镜清单，不要其他解释说明"
			)
		elif mode == "detailed":
			shot_count = "20-30"
			mode_name = "详细版"
			inst = (
				"请把以下故事正文拆解为极其详细的'分镜头清单'，使用中文编号列出 15-25 条分镜，"
				"**尽可能细致地分割每个场景、每个情节转折、每个重要细节**，"
				"确保故事的每个重要瞬间都有对应的分镜。\n\n"
				"分镜原则：\n"
				"1. 场景转换时必须新开分镜\n"
				"2. 人物表情或动作有明显变化时新开分镜\n"
				"3. 情节转折点必须单独成镜\n"
				"4. 重要对话场景可拆分为多个分镜（不同角度）\n"
				"5. 氛围营造的细节镜头也要包含\n\n"
				"每条分镜包含：\n"
				"- 场景：具体地点和环境细节\n"
				"- 主体：人物或主要对象（包括服饰、姿态）\n"
				"- 动作：正在发生的具体行为或状态\n"
				"- 情绪：人物情感或场景氛围\n"
				"- 光线/镜头：如 extreme close-up（大特写）、close-up（特写）、medium shot（中景）、"
				"wide shot（全景）、establishing shot（定场镜头）、high angle（高角度）、low angle（低角度）、"
				"POV（主观视角）、over-the-shoulder（过肩镜头）等\n\n"
				"输出格式：每行一个分镜，格式为'序号. 场景 / 主体 / 动作 / 情绪 / 光线镜头'。\n"
				"注意：只输出清单，不要其他说明文字。尽量覆盖故事的所有重要时刻。"
			)
		else:  # normal mode (保持向后兼容)
			shot_count = "12-20"
			mode_name = "标准版"
			inst = (
				"请把以下故事正文拆解为适合生成插图/分镜的'镜头清单'，使用中文简洁编号列出 8-12 条，"
				"每条包含：场景/主体/动作/情绪/关键物件/光线镜头（如 close-up、wide shot）。"
				"格式：每行一个分镜，格式为'序号. 场景描述 / 主体 / 动作 / 情绪 / 光线镜头'。只输出清单，不要其他文字。"
			)
		
		# 在后台线程中执行耗时操作
		def task():
			try:
				self.set_busy(True)
				self.status.set(f"🎬 正在使用 {selected_api} 生成{mode_name}分镜（目标{shot_count}个）...")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status(f"生成{mode_name}分镜...", "🎬")
				
				client = DeepSeekClient(
					api_key=api_key,
					base_url=base_url,
					model=model,
				)
				
				self.status.set(f"🤖 {selected_api} 正在分析故事并生成{mode_name}分镜...")
				
				resp = client.chat([
					{"role": "system", "content": inst},
					{"role": "user", "content": story_text},
				], temperature=max(0.4, self.temperature.get() - 0.2))
				
				self.status.set("📋 解析分镜头列表...")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("解析分镜中...", "📋")
				
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
					self.status.set(f"✅ 更新分镜显示...")
					
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
				
				self.status.set(f"🎬 已生成{mode_name} {len(shots)} 个分镜（可在下拉框中选择）")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("分镜生成完成", "✅")
			except Exception as e:
				messagebox.showerror("错误", str(e))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("分镜生成失败", "❌")
			finally:
				self.set_busy(False)
		
		import threading
		threading.Thread(target=task, daemon=True).start()
	
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
		img_type = self.img_type.get() if hasattr(self, 'img_type') else "写实照片"
		
		# 根据图片类型定义不同的风格描述
		style_instructions = {
			"写实照片": "高清摄影作品，写实风格，自然光线，真实质感，细节丰富",
			"日系动漫": "日系动漫风格，精美作画，色彩鲜艳，人物可爱，动漫渲染",
			"3D渲染": "3D渲染，高品质建模，精致材质，专业渲染，光影逼真",
			"水彩画": "水彩画风格，色彩柔和，笔触自然，艺术感强，优雅细腻",
			"油画": "油画质感，笔触厚重，色彩浓郁，古典艺术风格，富有层次",
			"素描": "素描风格，线条流畅，黑白灰调，光影明确，艺术素描",
			"赛博朋克": "赛博朋克风格，霓虹灯光，未来科技感，暗黑氛围，高科技元素",
			"蒸汽朋克": "蒸汽朋克风格，机械齿轮，复古科技，维多利亚时代，工业美学",
			"像素风": "像素艺术风格，8bit/16bit画风，复古游戏美术，像素化",
			"中国风": "中国传统绘画风格，水墨意境，古典韵味，诗意氛围，传统美学",
			"国风插画": "国风插画，现代中国美学，精美线条，典雅色彩，细腻构图",
			"古风": "古风，传统汉服，古代建筑，历史氛围，唐宋美学，诗意画面",
			"仙侠": "仙侠奇幻，修仙世界，天宫仙境，飘逸衣袍，仙气缭绕，云雾山水",
			"武侠": "武侠江湖，侠客剑客，轻功飞跃，竹林烟雨，山水意境，武林氛围",
			"水墨画": "中国水墨画，笔墨韵味，黑白灰调，留白意境，禅意美学，传统笔法",
			"工笔画": "工笔重彩，精细笔法，传统颜料，古典构图，细腻刻画，层次丰富",
			"敦煌壁画": "敦煌壁画风格，飞天仙女，佛教艺术，唐代色彩，壁画质感，古典神圣",
			"恐怖": "恐怖氛围，阴暗诡异，诡谲光影，惊悚元素，不安情绪，恐惧感",
			"惊悚": "惊悚风格，悬疑紧张，戏剧化光影，神秘阴影，紧张氛围，惊心动魄",
			"诡异": "诡异风格，超现实，异世界感，诡谲氛围，不祥预兆，怪异细节",
			"悬疑": "悬疑风格，黑色电影，戏剧阴影，侦探美学，推理氛围，谜团感",
			"玄幻": "玄幻奇幻，神秘元素，灵兽异兽，磅礴山水，修真世界，灵力光芒",
			"科幻": "科幻未来，高科技，太空场景，先进文明，霓虹光效，未来都市",
			"魔幻": "魔幻世界，神话生物，魔法森林，神秘光芒，奇幻冒险，魔法元素"
		}
		
		style_desc = style_instructions.get(img_type, f"{img_type}风格")
		
		# 检测是否使用腾讯混元（根据preset或provider判断）
		is_hunyuan = False
		if hasattr(self, 'img_api_preset'):
			preset_name = self.img_api_preset.get()
			if "腾讯混元" in preset_name or "hunyuan" in preset_name.lower():
				is_hunyuan = True
		
		# 根据API类型设置不同的描述详细程度
		if is_hunyuan:
			# 腾讯混元：简洁版，200字以内（因为API有256字符限制）
			char_limit = "200字以内"
			detail_level = "精简但极其精准"
			inst = (
				f"你是资深视觉设计师和电影摄影师。基于分镜描述与故事上下文，生成一段超高密度、信息丰富的中文图片描述，"
				f"用于腾讯混元生成【{img_type}】风格的图片。要求：\n\n"
				f"【风格】{style_desc}\n\n"
				f"【必须包含的细节】：\n"
				f"1. 人物：具体年龄、性别、发型发色、肤色、体型、五官特征、完整服饰描述（颜色+款式+材质）、"
				f"精确表情（眼神+嘴角+眉头）、详细动作（身体姿势+手部动作+站姿或坐姿）\n"
				f"2. 环境：具体地点、墙面材质和颜色、地面类型、重要物品的详细描述、空间层次\n"
				f"3. 光线：光源类型和方向、具体时间、天气、色温、阴影形态\n"
				f"4. 镜头：具体镜头类型（特写/中景/全景）、拍摄角度（平视/俯视/仰视）、景深、构图方式\n"
				f"5. 氛围：整体情绪基调\n\n"
				f"【格式】使用简洁有力的短语，用顿号和逗号连接，每个词都要有具体含义。\n"
				f"例如：'25岁女性、黑色长发过肩、白色医生制服带胸牌、疲惫眼神眉头紧锁、双手插口袋、站立微驼背、深夜医院走廊、"
				f"白墙灰绿色地板、顶部惨白日光灯部分闪烁、走廊尽头红色安全出口标志、中景平视浅景深人物居中、寂静压抑氛围'\n\n"
				f"【要求】\n"
				f"- 控制在{char_limit}，但必须包含所有关键视觉元素\n"
				f"- 每个描述都要具体精确，避免'很'、'非常'等模糊词\n"
				f"- 颜色、材质、尺寸都要明确\n"
				f"- 符合【{img_type}】风格特点\n"
				f"- **人物一致性（极其重要）**：\n"
				f"  · 如果提供了人物设定档案，必须严格按名字匹配每个人物的特征\n"
				f"  · 只描述当前分镜中出现的人物，不在场的人物不描述\n"
				f"  · 每个人物的外貌、服饰、体型等特征必须与设定完全一致\n"
				f"  · 多人物场景要清楚区分每个人，不要混淆特征\n"
				f"- 只输出描述文本，不要任何格式标记或解释"
			)
		else:
			# OpenAI/DALL-E等：精简版（避免提示词过长）
			char_limit = "300-500字"
			detail_level = "详细但精炼，重点突出核心视觉元素"
			inst = (
				f"你是专业视觉设计师。基于分镜描述与故事上下文，生成一段**精炼而准确**的中文图片描述，"
				f"用于生成高质量的【{img_type}】风格图片。\n\n"
				
				f"【风格定位】{style_desc}\n\n"
				
				f"【核心要求】\n"
				f"1. 人物（如有）：年龄、性别、发型发色、面容、表情、服饰（颜色+款式）、姿态动作\n"
				f"2. 环境：具体地点、主要物品、空间感、材质色彩\n"
				f"3. 光线：光源类型、时间、天气、主色调\n"
				f"4. 镜头：景别（特写/中景/全景）、角度（平视/俯视/仰视）、构图\n"
				f"5. 氛围：整体情绪基调\n\n"
				
				f"【人物一致性规则】\n"
				f"- 如提供人物设定，必须严格按名字匹配特征（年龄、发型、服饰等）\n"
				f"- 只描述当前分镜中出现的人物\n"
				f"- 多人物时清楚区分，不混淆特征\n"
				f"- 每次出现保持静态特征一致，只改变表情动作\n\n"
				
				f"【输出要求】\n"
				f"1. 长度：{char_limit}，简洁精炼\n"
				f"2. 格式：流畅的中文段落，不用Markdown\n"
				f"3. 具体：使用具体颜色、数字，避免'很'、'非常'等模糊词\n"
				f"4. 风格：体现【{img_type}】美学特征"
			)
		
		# 获取选中的图片描述生成API配置
		selected_api = self.desc_gen_api.get() if hasattr(self, 'desc_gen_api') else "DeepSeek"
		if selected_api not in self.api_presets:
			messagebox.showerror("错误", f"未找到API预设: {selected_api}")
			return
		
		api_config = self.api_presets[selected_api]
		api_key = _sanitize(api_config.get("key", ""))
		base_url = _sanitize(api_config.get("base_url", ""))
		model = _sanitize(api_config.get("model", ""))
		
		if not api_key:
			messagebox.showwarning("提示", f"请先在故事生成页面配置 {selected_api} 的API Key")
			return
		
		# 在后台线程中执行耗时操作
		def task():
			try:
				self.set_busy(True)
				self.status.set(f"📸 正在使用 {selected_api} 生成{'精简' if is_hunyuan else '详细'}图片描述（第{selected_index+1}个分镜）...")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("生成图片描述...", "📸")
				client = DeepSeekClient(
					api_key=api_key,
					base_url=base_url,
					model=model,
				)
				# 根据API类型调整上下文长度
				context_length = 500 if is_hunyuan else 1000
				
				# 构建用户提示词，强调人物一致性
				user_parts = [f"【目标图片类型】{img_type}\n"]
				
				# 人物一致性要求（最重要，放在前面）
				if roles:
					user_parts.append(f"【‼️ 人物设定档案 - 必须严格遵守】\n{roles}\n\n")
					user_parts.append(f"⚠️ 人物一致性规则（极其重要）：\n")
					user_parts.append(f"1. **人物-特征绑定**：以上每个人物的名字与其外貌、服饰特征是永久绑定的\n")
					user_parts.append(f"2. **按名字匹配**：当分镜中提到某个人物的名字时，必须使用该人物在设定中的所有特征\n")
					user_parts.append(f"3. **选择性出现**：只描述当前分镜中实际出现的人物，未出现的人物不要描述\n")
					user_parts.append(f"4. **再次出现一致**：如果某人物在前面的场景没出现，但在当前场景出现，必须使用设定中该人物的特征\n")
					user_parts.append(f"5. **多人物区分**：如果场景中有多个人物，要清楚区分每个人，按各自的名字使用对应的特征\n")
					user_parts.append(f"6. **特征不混淆**：绝不允许将A人物的特征用在B人物身上，每个人物的特征独立且固定\n\n")
					user_parts.append(f"例如：\n")
					user_parts.append(f"- 如果分镜说「李明走进房间」→ 只描述李明，使用李明的设定特征\n")
					user_parts.append(f"- 如果分镜说「王芳和李明对话」→ 描述两人，分别使用各自的设定特征\n")
					user_parts.append(f"- 如果分镜说「一个空房间」→ 不描述任何人物，只描述环境\n")
					user_parts.append(f"- 如果王芳在前3个场景没出现，第5个场景才出现 → 第5个场景中王芳的特征与设定完全一致\n\n")
				else:
					user_parts.append(f"【人物设定】从故事上下文和分镜描述中提取人物特征，为每个人物建立档案，")
					user_parts.append(f"并在该人物每次出现时保持特征一致。不同人物要清楚区分，不要混淆。\n\n")
				
				# 当前分镜
				user_parts.append(f"【当前分镜描述】\n{current_shot}\n\n")
				
				# 故事上下文
				user_parts.append(f"【故事上下文】\n{story_text[:context_length] if story_text else '无相关上下文'}\n\n")
				
				# 场景设定
				if scene:
					user_parts.append(f"【场景设定】\n{scene}\n\n")
				
				# 一致性强调
				user_parts.append(f"【描述生成要求】\n")
				user_parts.append(f"1. **识别当前场景人物**：仔细阅读当前分镜描述，识别场景中出现的具体人物（根据名字或角色）\n")
				user_parts.append(f"2. **匹配人物特征**：为每个出现的人物，从人物设定档案中找到对应的特征\n")
				user_parts.append(f"3. **只描述在场人物**：只描述当前分镜中实际出现的人物，不在场的人物不要提及\n")
				user_parts.append(f"4. **保持特征一致**：每个人物的年龄、性别、发型、发色、肤色、体型、五官、服饰必须与设定完全一致\n")
				user_parts.append(f"5. **动态元素变化**：根据分镜要求，只改变表情、动作、姿态等动态元素，静态特征保持不变\n")
				user_parts.append(f"6. **多人物区分**：如果场景中有多人，要清楚描述每个人的特征，不要混淆或遗漏\n")
				user_parts.append(f"7. **服饰一致**：除非分镜明确说明换装，否则服装款式、颜色、材质保持一致\n")
				user_parts.append(f"8. **细节补充**：如果设定中缺少某些细节，可适当添加，但要符合该人物的身份和场景，且后续保持一致\n\n")
				
				# 生成要求
				user_parts.append(f"【生成要求】\n")
				user_parts.append(f"请基于以上信息，生成{detail_level}的中文图片描述（{char_limit}），")
				user_parts.append(f"充分体现【{img_type}】风格的视觉特点，同时严格保持人物一致性。")
				
				user = "".join(user_parts)
				resp = client.chat([
					{"role": "system", "content": inst},
					{"role": "user", "content": user},
				], temperature=max(0.5, self.temperature.get() - 0.1))
				
				self.status.set("✅ 更新图片描述...")
				
				description = resp.strip()
				
				# 根据API类型限制描述长度
				max_desc_length = 200 if is_hunyuan else 500
				if len(description) > max_desc_length:
					# 在句号、逗号或顿号处截断
					truncated = description[:max_desc_length]
					last_punct = max(truncated.rfind('。'), truncated.rfind('，'), truncated.rfind('、'))
					if last_punct > int(max_desc_length * 0.8):
						description = truncated[:last_punct + 1]
					else:
						description = truncated
				
				self.img_txt_prompt_cn.delete("1.0", END)
				self.img_txt_prompt_cn.insert(END, description)
				
				# 显示字数统计
				char_count = len(description)
				api_type = "腾讯混元简洁版" if is_hunyuan else "精简版"
				self.status.set(f"✨ 已生成【{img_type}】{api_type}图片描述（{char_count}字，可编辑后生成）")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("图片描述完成", "✅")
			except Exception as e:
				messagebox.showerror("错误", str(e))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("生成描述失败", "❌")
			finally:
				self.set_busy(False)
		
		import threading
		threading.Thread(target=task, daemon=True).start()

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

	def _on_canvas_configure(self, event=None) -> None:
		"""Canvas大小变化时重新缩放图片"""
		if self.img_last_image:
			self._update_img_preview()
	
	def _update_img_preview(self) -> None:
		"""更新图片预览，支持自适应缩放和滚动"""
		if not self.img_last_image:
			return
		
		# 获取Canvas的实际可用尺寸
		canvas_width = self.img_canvas.winfo_width()
		canvas_height = self.img_canvas.winfo_height()
		
		# 如果Canvas还未初始化完成，使用默认值
		if canvas_width <= 1:
			canvas_width = 400
		if canvas_height <= 1:
			canvas_height = 400
		
		# 获取原始图片尺寸
		orig_w, orig_h = self.img_last_image.size
		
		# 计算缩放比例，保持宽高比
		# 给边距留出一些空间
		max_w = canvas_width - 20
		max_h = canvas_height - 20
		
		# 计算缩放比例（取较小的比例以确保图片完全显示）
		scale_w = max_w / orig_w
		scale_h = max_h / orig_h
		scale = min(scale_w, scale_h, 1.0)  # 不放大，只缩小
		
		# 如果原图太大，进行缩放；否则显示原尺寸
		if scale < 1.0:
			new_w = int(orig_w * scale)
			new_h = int(orig_h * scale)
			img = self.img_last_image.copy()
			img.thumbnail((new_w, new_h), Image.Resampling.LANCZOS)
		else:
			# 图片较小，直接显示原图
			img = self.img_last_image.copy()
			new_w, new_h = orig_w, orig_h
		
		# 转换为PhotoImage
		self.img_preview_photo = ImageTk.PhotoImage(img)
		
		# 更新Label
		self.img_preview.configure(image=self.img_preview_photo, text="")
		
		# 更新Canvas的滚动区域
		self.img_canvas.configure(scrollregion=(0, 0, new_w, new_h))
		
		# 居中显示图片
		if new_w < canvas_width:
			x_offset = (canvas_width - new_w) // 2
		else:
			x_offset = 0
			
		if new_h < canvas_height:
			y_offset = (canvas_height - new_h) // 2
		else:
			y_offset = 0
		
		self.img_canvas.coords(self.img_canvas_window, x_offset, y_offset)

	def _auto_save_image_to_project(self) -> None:
		"""自动保存图片到当前项目，使用分镜头描述作为文件名"""
		if not self.img_last_image:
			return
		
		if not self.current_project:
			# 如果没有当前项目，不自动保存
			return
		
		try:
			import re
			import tempfile
			from datetime import datetime
			
			# 获取当前选中的分镜描述作为文件名
			filename = "image"
			if hasattr(self, 'parsed_shots') and self.parsed_shots:
				selected_index = self.shot_selector.current() if hasattr(self, 'shot_selector') else -1
				if selected_index >= 0 and selected_index < len(self.parsed_shots):
					shot_desc = self.parsed_shots[selected_index]
					# 清理文件名：移除特殊字符，只保留中文、英文、数字和空格
					clean_name = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', shot_desc)
					# 限制长度，避免文件名过长
					clean_name = clean_name[:50].strip()
					if clean_name:
						filename = clean_name
			
			# 添加时间戳避免重名
			timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
			filename = f"{filename}_{timestamp}.png"
			
			# 先保存到临时文件
			with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
				self.img_last_image.save(tmp.name, "PNG")
				temp_path = tmp.name
			
			# 保存到项目
			saved_path = self.current_project.save_image(temp_path, filename)
			
			# 删除临时文件
			import os
			os.unlink(temp_path)
			
			self.status.set(f"✅ 图片已自动保存到项目: {filename}")
			print(f"图片已自动保存: {saved_path}")
			
		except Exception as e:
			print(f"自动保存图片失败: {e}")
			# 自动保存失败不弹窗，只打印日志
	
	def _on_img_save(self) -> None:
		"""手动保存图片到用户选择的位置"""
		if not self.img_last_image:
			return
		
		# 默认文件名建议
		default_name = "image.png"
		if hasattr(self, 'parsed_shots') and self.parsed_shots:
			selected_index = self.shot_selector.current() if hasattr(self, 'shot_selector') else -1
			if selected_index >= 0 and selected_index < len(self.parsed_shots):
				import re
				shot_desc = self.parsed_shots[selected_index]
				clean_name = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', shot_desc)
				clean_name = clean_name[:50].strip()
				if clean_name:
					from datetime import datetime
					timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
					default_name = f"{clean_name}_{timestamp}.png"
		
		path = filedialog.asksaveasfilename(
			defaultextension=".png", 
			initialfile=default_name,
			filetypes=[("PNG","*.png"),("JPEG","*.jpg;*.jpeg"),("WEBP","*.webp")]
		)
		if not path:
			return
		try:
			self.img_last_image.save(path)
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
	
	def _add_style_tag(self, tag) -> None:
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
	

