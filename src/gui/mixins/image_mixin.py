"""
Image相关功能模块
"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, VERTICAL, Y, messagebox, filedialog
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
		"""构建图片生成页面，分为"创作"、"人物生成"和"配置"三个子标签页"""
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
		
		# 人物生成相关变量
		self.character_list: list[dict] = []  # 存储提取的人物列表 [{"name": "张三", "description": "...", "photo_path": "..."}]
		self.character_last_image: Image.Image | None = None
		self.character_preview_photo: ImageTk.PhotoImage | None = None
		self.character_photos_dir = None  # 人物照片保存目录
		
		# 创建图片页面的内部Notebook
		self.image_notebook = ttk.Notebook(self.page_image)
		self.image_notebook.pack(fill=BOTH, expand=True, padx=0, pady=0)
		
		# 创建三个子标签页
		self.image_tab_character = tk.Frame(self.image_notebook, bg="#2b2b2b")
		self.image_tab_create = tk.Frame(self.image_notebook, bg="#2b2b2b")
		self.image_tab_setup = tk.Frame(self.image_notebook, bg="#2b2b2b")
		
		self.image_notebook.add(self.image_tab_character, text="  👥 人物描述  ")
		self.image_notebook.add(self.image_tab_create, text="  🎨 图片创作  ")
		self.image_notebook.add(self.image_tab_setup, text="  ⚙️ 配置  ")
		
		# 构建各个标签页
		self._build_character_tab()
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

		# Left: 分镜头列表（合并版本）
		grp_shots = ttk.LabelFrame(left, text="🎬 分镜头列表（点击选择）", padding=(8, 5))
		grp_shots.pack(fill="both", expand=True, padx=0, pady=(0, 8))
		
		# 将所有按钮放在一行
		rowf = ttk.Frame(grp_shots)
		rowf.pack(fill="x", padx=6, pady=(6, 8))
		self.img_btn_recommend = ttk.Button(rowf, text="🤖 智能推荐", command=self._on_recommend_video_mode, width=10, takefocus=False)
		self.img_btn_recommend.pack(side=LEFT, padx=(0, 4))
		self.img_btn_extract_brief = ttk.Button(rowf, text="🎬 简短(8-12)", command=lambda: self._on_img_extract_shots(mode="brief"), width=11, takefocus=False)
		self.img_btn_extract_brief.pack(side=LEFT, padx=(0, 4))
		self.img_btn_extract_video = ttk.Button(rowf, text="🎬 平衡(15-25)", command=lambda: self._on_img_extract_shots(mode="video"), width=12, takefocus=False)
		self.img_btn_extract_video.pack(side=LEFT, padx=(0, 4))
		self.img_btn_extract_normal = ttk.Button(rowf, text="🎬 标准(15-22)", command=lambda: self._on_img_extract_shots(mode="normal"), width=12, takefocus=False)
		self.img_btn_extract_normal.pack(side=LEFT, padx=(0, 4))
		self.img_btn_extract_detailed = ttk.Button(rowf, text="🎬 精细(25-40)", command=lambda: self._on_img_extract_shots(mode="detailed"), width=12, takefocus=False)
		self.img_btn_extract_detailed.pack(side=LEFT, padx=(0, 4))
		
		# 使用Listbox显示分镜列表
		shots_list_frame = tk.Frame(grp_shots, bg="#2b2b2b")
		shots_list_frame.pack(fill="both", expand=True, padx=6, pady=(0, 6))
		
		# 添加滚动条
		shots_scrollbar = ttk.Scrollbar(shots_list_frame, orient="vertical")
		self.shots_listbox = tk.Listbox(shots_list_frame, font=("", 10), 
										 yscrollcommand=shots_scrollbar.set,
										 relief=tk.SOLID, borderwidth=1,
										 height=8, bg="#1e1e1e", fg="white",
										 selectbackground="#4CAF50", selectforeground="white")
		shots_scrollbar.config(command=self.shots_listbox.yview)
		
		self.shots_listbox.pack(side=LEFT, fill=BOTH, expand=True)
		shots_scrollbar.pack(side=RIGHT, fill="y")
		
		# 显示提示信息
		self.shots_listbox.insert(0, "点击上方按钮从故事生成分镜头列表...")
		self.shots_listbox.config(state=DISABLED)
		
		# 绑定选择事件
		self.shots_listbox.bind("<<ListboxSelect>>", self._on_shot_listbox_selected)
		
		# 图片类型与场景补充
		grp_ctx_add = ttk.LabelFrame(left, text="🎨 图片参数", padding=(8, 5))
		grp_ctx_add.pack(fill="x", padx=0, pady=(0, 8))
		grp_ctx_add.columnconfigure(1, weight=1)
		
		# 图片类型选择
		tk.Label(grp_ctx_add, text="图片类型:", font=("", 10)).grid(row=0, column=0, sticky="e", padx=(0, 8), pady=6)
		self.img_type = tk.StringVar(value="写实照片")
		# 扩展图片类型，包含更多中国风格；支持手动输入自定义类型
		self.combo_img_type = ttk.Combobox(grp_ctx_add, textvariable=self.img_type, font=("", 10), width=20,
										   values=("写实照片", "日系动漫", "3D渲染", "水彩画", "油画", "素描", 
												   "赛博朋克", "蒸汽朋克", "像素风", "中国风", "国风插画", 
												   "古风", "仙侠", "武侠", "水墨画", "工笔画", "敦煌壁画", 
												   "恐怖", "惊悚", "诡异", "悬疑", "玄幻", "科幻", "魔幻"))
		self.combo_img_type.grid(row=0, column=1, sticky="we", padx=(0, 6), pady=6)
		# 添加提示文字
		tk.Label(grp_ctx_add, text="（可手动输入自定义类型）", font=("", 8), fg="gray").grid(row=0, column=2, sticky="w", padx=4)
		
		tk.Label(grp_ctx_add, text="场景描述:", font=("", 10)).grid(row=1, column=0, sticky="e", padx=(0, 8), pady=6)
		self.img_entry_scene = ttk.Entry(grp_ctx_add, font=("", 10))
		self.img_entry_scene.grid(row=1, column=1, columnspan=2, sticky="we", padx=(0, 6), pady=6)
		tk.Label(grp_ctx_add, text="角色特征:", font=("", 10)).grid(row=2, column=0, sticky="ne", padx=(0, 8), pady=(6, 6))
		self.img_txt_roles = tk.Text(grp_ctx_add, height=3, font=("", 10), wrap=tk.WORD, relief=tk.SOLID, borderwidth=1)
		self.img_txt_roles.grid(row=2, column=1, columnspan=2, sticky="we", padx=(0, 6), pady=(6, 6))
		
		# Left: 创建标签页（图片描述 和 即梦AI提示词）
		prompt_notebook = ttk.Notebook(left)
		prompt_notebook.pack(fill="both", expand=True, padx=0, pady=0)
		
		# 第一个标签页：图片描述
		tab_img_desc = tk.Frame(prompt_notebook, bg="#2b2b2b")
		prompt_notebook.add(tab_img_desc, text="  💬 图片描述  ")
		
		self.img_txt_prompt_cn = tk.Text(tab_img_desc, height=10, font=("", 10), wrap=tk.WORD, relief=tk.SOLID, borderwidth=1)
		self.img_txt_prompt_cn.pack(fill="both", expand=True, padx=6, pady=(6, 8))
		rowp = ttk.Frame(tab_img_desc)
		rowp.pack(fill="x", padx=6, pady=(0, 6))
		self.img_btn_build_from_shot = ttk.Button(rowp, text="✨ 从当前分镜生成", command=self._on_img_prompt_from_current_shot, width=18)
		self.img_btn_build_from_shot.pack(side=LEFT, padx=(0, 3))
		self.img_btn_copy = ttk.Button(rowp, text="📋 复制", command=self._on_copy_img_prompt, width=8)
		self.img_btn_copy.pack(side=LEFT, padx=3)
		self.img_btn_clear = ttk.Button(rowp, text="🗑️ 清空", command=self._on_clear_img_prompt, width=8)
		self.img_btn_clear.pack(side=LEFT, padx=3)
		
		# 第二个标签页：即梦AI视频提示词
		tab_video_prompt = tk.Frame(prompt_notebook, bg="#2b2b2b")
		prompt_notebook.add(tab_video_prompt, text="  🎬 即梦AI提示词  ")
		
		# 简洁的提示信息（放在文本框上方）
		video_tip_label = tk.Label(tab_video_prompt, 
								   text="💡 复制下方提示词到即梦AI，使用生成的图片作为第一帧生成5秒视频", 
								   font=("", 9), fg="#888888", bg="#2b2b2b", anchor="w")
		video_tip_label.pack(fill="x", padx=6, pady=(6, 4))
		
		# 视频提示词文本框
		self.video_prompt_text = tk.Text(tab_video_prompt, height=10, font=("", 10), 
										 wrap=tk.WORD, relief=tk.SOLID, borderwidth=1,
										 bg="#1e1e1e", fg="#e0e0e0")
		self.video_prompt_text.pack(fill="both", expand=True, padx=6, pady=(0, 8))
		self.video_prompt_text.insert("1.0", "生成图片后，这里会自动显示适合即梦AI的视频提示词...")
		self.video_prompt_text.config(state=DISABLED)
		
		# 复制按钮
		video_btn_frame = ttk.Frame(tab_video_prompt)
		video_btn_frame.pack(fill="x", padx=6, pady=(0, 6))
		self.video_btn_copy = ttk.Button(video_btn_frame, text="📋 复制视频提示词", 
										  command=self._on_copy_video_prompt, width=20)
		self.video_btn_copy.pack(side=LEFT)

		# Right: 参考人物选择（移到这里，更显眼）
		grp_ref_characters = ttk.LabelFrame(right, text="🎭 参考人物", padding=(8, 5))
		grp_ref_characters.pack(fill="both", expand=False, padx=0, pady=(0, 8))
		
		# 使用Listbox支持多选
		ref_list_frame = tk.Frame(grp_ref_characters, bg="#2b2b2b")
		ref_list_frame.pack(fill="both", expand=True, padx=6, pady=6)
		
		self.ref_character_listbox = tk.Listbox(ref_list_frame, height=8, font=("", 10), 
												selectmode=tk.MULTIPLE, exportselection=False,
												bg="#1e1e1e", fg="white", selectbackground="#4CAF50",
												relief=tk.SOLID, borderwidth=1)
		self.ref_character_listbox.pack(side=LEFT, fill=BOTH, expand=True)
		
		ref_scrollbar = ttk.Scrollbar(ref_list_frame, orient=VERTICAL, command=self.ref_character_listbox.yview)
		ref_scrollbar.pack(side=RIGHT, fill=Y)
		self.ref_character_listbox.config(yscrollcommand=ref_scrollbar.set)

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
	
	def _build_character_tab(self) -> None:
		"""构建人物生成页面"""
		# 两列布局
		body = ttk.Frame(self.image_tab_character)
		body.pack(fill=BOTH, expand=True, padx=10, pady=10)
		left = ttk.Frame(body)
		left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
		right = ttk.Frame(body)
		right.grid(row=0, column=1, sticky="nsew")
		body.columnconfigure(0, weight=1)
		body.columnconfigure(1, weight=1)
		body.rowconfigure(0, weight=1)
		
		# 左侧：人物列表和操作
		grp_characters = ttk.LabelFrame(left, text="👥 故事人物列表", padding=(8, 5))
		grp_characters.pack(fill=BOTH, expand=True, padx=0, pady=(0, 8))
		
		# 提示信息
		tip_frame_main = tk.Frame(grp_characters, bg="#2b2b2b")
		tip_frame_main.pack(fill="x", padx=6, pady=(6, 8))
		
		tk.Label(tip_frame_main, text="📌 ", font=("", 10, "bold"), fg="#FF9800", bg="#2b2b2b").pack(side=LEFT)
		tk.Label(tip_frame_main, text="第一步：点击下方按钮提取人物，然后选择要生成照片的人物", 
				 font=("", 9), fg="#888888", bg="#2b2b2b").pack(side=LEFT)
		
		info_frame = tk.Frame(grp_characters, bg="#1e3a5f", relief=tk.SOLID, borderwidth=1)
		info_frame.pack(fill="x", padx=6, pady=(0, 8))
		tk.Label(info_frame, text="💾 ", font=("", 9), fg="#4CAF50", bg="#1e3a5f").pack(side=LEFT, padx=(6, 0))
		tk.Label(info_frame, text="照片自动保存到 ", font=("", 9), fg="white", bg="#1e3a5f").pack(side=LEFT)
		tk.Label(info_frame, text="当前项目/characters/", font=("", 9, "bold"), fg="#4CAF50", bg="#1e3a5f").pack(side=LEFT)
		tk.Label(info_frame, text=" 文件夹", font=("", 9), fg="white", bg="#1e3a5f").pack(side=LEFT, padx=(0, 6))
		
		# 按钮区域
		btn_frame = ttk.Frame(grp_characters)
		btn_frame.pack(fill="x", padx=6, pady=(0, 8))
		self.char_btn_extract = ttk.Button(btn_frame, text="🔍 提取故事人物", 
										   command=self._on_extract_characters, width=15)
		self.char_btn_extract.pack(side=LEFT, padx=(0, 3))
		self.char_btn_refresh = ttk.Button(btn_frame, text="🔄 重新提取", 
										   command=self._on_extract_characters, width=12, state=DISABLED)
		self.char_btn_refresh.pack(side=LEFT, padx=(0, 3))
		
		# 人物列表框（使用Listbox）
		list_frame = ttk.Frame(grp_characters)
		list_frame.pack(fill=BOTH, expand=True, padx=6, pady=(0, 6))
		
		# 添加滚动条
		scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
		self.char_listbox = tk.Listbox(list_frame, font=("", 10), 
									   yscrollcommand=scrollbar.set,
									   relief=tk.SOLID, borderwidth=1,
									   height=8)
		scrollbar.config(command=self.char_listbox.yview)
		
		self.char_listbox.pack(side=LEFT, fill=BOTH, expand=True)
		scrollbar.pack(side=RIGHT, fill="y")
		
		# 绑定选择事件
		self.char_listbox.bind("<<ListboxSelect>>", self._on_character_selected)
		
		# 人物特征描述区域
		grp_desc = ttk.LabelFrame(left, text="📝 人物特征描述", padding=(8, 5))
		grp_desc.pack(fill=BOTH, expand=True, padx=0, pady=0)
		
		# 特征描述文本框
		self.char_txt_desc = tk.Text(grp_desc, height=10, font=("", 10), 
									 wrap=tk.WORD, relief=tk.SOLID, borderwidth=1)
		self.char_txt_desc.pack(fill=BOTH, expand=True, padx=6, pady=(6, 8))
		self.char_txt_desc.insert("1.0", "第二步：从列表中选择一个人物，然后点击下方按钮生成该人物的特征描述...")
		self.char_txt_desc.config(state=DISABLED)
		
		# 特征描述按钮
		desc_btn_frame = ttk.Frame(grp_desc)
		desc_btn_frame.pack(fill="x", padx=6, pady=(0, 6))
		self.char_btn_gen_desc = ttk.Button(desc_btn_frame, text="✨ 生成特征描述", 
										    command=self._on_generate_character_description,
											width=15, state=DISABLED)
		self.char_btn_gen_desc.pack(side=LEFT, padx=(0, 3))
		self.char_btn_copy_desc = ttk.Button(desc_btn_frame, text="📋 复制", 
											 command=self._on_copy_character_description,
											 width=10, state=DISABLED)
		self.char_btn_copy_desc.pack(side=LEFT, padx=(0, 3))
		
		# 右侧：生成参数和预览
		grp_params = ttk.LabelFrame(right, text="🎨 生成参数", padding=(8, 5))
		grp_params.pack(fill="x", padx=0, pady=(0, 8))
		grp_params.columnconfigure(1, weight=1)
		
		# 图片风格
		tk.Label(grp_params, text="图片风格:", font=("", 10)).grid(row=0, column=0, sticky="e", padx=(0, 8), pady=6)
		self.char_img_style = tk.StringVar(value="写实照片")
		self.char_combo_style = ttk.Combobox(grp_params, textvariable=self.char_img_style, font=("", 10),
											 values=("写实照片", "日系动漫", "3D渲染", "水彩画", "油画", 
													 "中国风", "国风插画", "古风", "仙侠", "武侠"))
		self.char_combo_style.grid(row=0, column=1, sticky="we", padx=(0, 6), pady=6)
		
		# 额外描述
		tk.Label(grp_params, text="额外描述:", font=("", 10)).grid(row=1, column=0, sticky="ne", padx=(0, 8), pady=6)
		self.char_txt_extra = tk.Text(grp_params, height=3, font=("", 10), 
									  wrap=tk.WORD, relief=tk.SOLID, borderwidth=1)
		self.char_txt_extra.grid(row=1, column=1, sticky="we", padx=(0, 6), pady=6)
		tk.Label(grp_params, text="（可添加姿态、表情、场景等细节）", font=("", 8), fg="gray").grid(
			row=2, column=1, sticky="w", padx=(0, 6))
		
		# 操作按钮
		grp_actions = ttk.LabelFrame(right, text="🚀 第三步：生成人物照片", padding=(8, 5))
		grp_actions.pack(fill="x", padx=0, pady=(0, 8))
		action_row = ttk.Frame(grp_actions)
		action_row.pack(fill="x", padx=6, pady=6)
		self.char_btn_gen_photo = ttk.Button(action_row, text="🎨 生成人物照片", 
											 command=self._on_generate_character_photo,
											 state=DISABLED)
		self.char_btn_gen_photo.pack(side=LEFT, padx=(0, 6), fill="x", expand=True)
		self.char_btn_save_photo = ttk.Button(action_row, text="💾 保存照片", 
											  command=self._on_save_character_photo, 
											  state=DISABLED)
		self.char_btn_save_photo.pack(side=LEFT, fill="x", expand=True)
		
		# 预览区域
		grp_preview = ttk.LabelFrame(right, text="🖼️ 人物照片预览", padding=(8, 5))
		grp_preview.pack(fill=BOTH, expand=True, padx=0, pady=0)
		
		# 创建Canvas和滚动条
		preview_frame = ttk.Frame(grp_preview)
		preview_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
		
		v_scroll = ttk.Scrollbar(preview_frame, orient="vertical")
		h_scroll = ttk.Scrollbar(preview_frame, orient="horizontal")
		
		self.char_canvas = tk.Canvas(preview_frame, bg="#2b2b2b", 
									 yscrollcommand=v_scroll.set,
									 xscrollcommand=h_scroll.set,
									 highlightthickness=0)
		
		v_scroll.config(command=self.char_canvas.yview)
		h_scroll.config(command=self.char_canvas.xview)
		
		self.char_canvas.grid(row=0, column=0, sticky="nsew")
		v_scroll.grid(row=0, column=1, sticky="ns")
		h_scroll.grid(row=1, column=0, sticky="ew")
		
		preview_frame.grid_rowconfigure(0, weight=1)
		preview_frame.grid_columnconfigure(0, weight=1)
		
		self.char_preview = ttk.Label(self.char_canvas, 
									  text="人物照片预览区\n\n生成人物照片后\n将显示在这里", 
									  font=("", 10), foreground="#888888", anchor="center",
									  background="#2b2b2b")
		self.char_canvas_window = self.char_canvas.create_window(0, 0, window=self.char_preview, anchor="nw")
		
		# 绑定Canvas大小变化事件
		self.char_canvas.bind('<Configure>', self._on_char_canvas_configure)
	
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
		
		# 添加说明文字
		usage_frame = tk.Frame(grp_api, bg="#2b2b2b")
		usage_frame.grid(row=0, column=0, columnspan=6, sticky="w", padx=6, pady=(4, 8))
		tk.Label(usage_frame, text="📌 用途：", fg="#FF9800", font=("", 9, "bold"), bg="#2b2b2b").pack(side=LEFT)
		tk.Label(usage_frame, text="分镜图片生成", fg="gray", font=("", 9), bg="#2b2b2b").pack(side=LEFT, padx=(0, 3))
		tk.Label(usage_frame, text="•", fg="gray", font=("", 9), bg="#2b2b2b").pack(side=LEFT)
		tk.Label(usage_frame, text="人物肖像生成", fg="#4CAF50", font=("", 9, "bold"), bg="#2b2b2b").pack(side=LEFT, padx=3)
		
		# API预设下拉框
		tk.Label(grp_api, text="API预设:").grid(row=1, column=0, sticky="e", padx=6, pady=4)
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
		self.combo_img_api_preset.grid(row=1, column=1, sticky="w", padx=6)
		self.combo_img_api_preset.bind("<<ComboboxSelected>>", self._on_img_api_preset_selected)
		
		# 添加保存自定义API按钮
		btn_save_img_preset = tk.Button(grp_api, text="💾 保存为自定义预设", command=self._save_custom_image_preset, 
				  font=("", 9), bg="#607D8B", fg="white", relief=tk.FLAT, padx=8, pady=3, cursor="hand2")
		btn_save_img_preset.grid(row=1, column=2, padx=(6, 2))
		
		# 添加删除自定义图片API按钮
		btn_delete_img_preset = tk.Button(grp_api, text="🗑️", command=self._delete_custom_image_preset, 
				  font=("", 9), bg="#d32f2f", fg="white", relief=tk.FLAT, padx=8, pady=3, cursor="hand2")
		btn_delete_img_preset.grid(row=1, column=3, padx=(2, 6), sticky="w")
		
		tk.Label(grp_api, text="提示: 可保存/删除自定义预设", fg="gray", font=("", 9)).grid(row=1, column=4, sticky="w", padx=6)

		tk.Label(grp_api, text="API Key / SecretId:").grid(row=2, column=0, sticky="e", padx=6, pady=4)
		self.img_entry_key = tk.Entry(grp_api, textvariable=self.img_api_key, show="*")
		self.img_entry_key.grid(row=2, column=1, columnspan=4, sticky="we", padx=6)
		
		tk.Label(grp_api, text="SecretKey (仅腾讯混元):").grid(row=3, column=0, sticky="e", padx=6, pady=4)
		self.img_secret_key = tk.StringVar(value="")
		self.img_entry_secret_key = tk.Entry(grp_api, textvariable=self.img_secret_key, show="*")
		self.img_entry_secret_key.grid(row=3, column=1, columnspan=4, sticky="we", padx=6)
		
		tk.Label(grp_api, text="Base URL:").grid(row=4, column=0, sticky="e", padx=6, pady=4)
		self.img_base_url = tk.StringVar(value="https://api.openai.com/v1")
		self.img_entry_base_url = tk.Entry(grp_api, textvariable=self.img_base_url)
		self.img_entry_base_url.grid(row=4, column=1, columnspan=4, sticky="we", padx=6)
		
		tk.Label(grp_api, text="Model:").grid(row=5, column=0, sticky="e", padx=6, pady=4)
		self.img_entry_model = tk.Entry(grp_api, textvariable=self.img_model)
		self.img_entry_model.grid(row=5, column=1, sticky="we", padx=6)
		tk.Button(grp_api, text="保存配置", command=self.save_img_api_config).grid(row=5, column=2, padx=6)
		tk.Button(grp_api, text="加载配置", command=self.load_img_api_config).grid(row=5, column=3, padx=6, sticky="w")
		# API测试按钮 - 与加载配置同行
		tk.Button(grp_api, text="API测试", command=self.on_test_image_api).grid(row=5, column=4, padx=6, sticky="w")
		
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
		tk.Label(grp_assist_api, text="选择用于生成分镜头、图片描述和人物肖像的聊天API（使用故事生成页面配置的API Key）", 
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
		
		# 人物肖像生成API选择（文本处理部分）
		tk.Label(grp_assist_api, text="人物肖像生成API:").grid(row=3, column=0, sticky="e", padx=6, pady=4)
		# 添加说明性文字
		api_desc_frame = tk.Frame(grp_assist_api, bg="#2b2b2b")
		api_desc_frame.grid(row=3, column=1, sticky="w", padx=6, pady=4)
		tk.Label(api_desc_frame, text="使用", fg="gray", font=("", 9), bg="#2b2b2b").pack(side=LEFT)
		tk.Label(api_desc_frame, text="上方「图片生成 API 配置」", fg="#4CAF50", font=("", 9, "bold"), bg="#2b2b2b").pack(side=LEFT)
		tk.Label(api_desc_frame, text="中的图片API", fg="gray", font=("", 9), bg="#2b2b2b").pack(side=LEFT)
		
		# 保存按钮
		btn_save_assist_api = tk.Button(grp_assist_api, text="💾 保存辅助API配置", command=self._save_assist_api_config,
									   font=("", 9), bg="#4CAF50", fg="white", relief=tk.FLAT, padx=12, pady=4, cursor="hand2")
		btn_save_assist_api.grid(row=4, column=0, columnspan=2, padx=6, pady=(8, 4), sticky="we")
		
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
		"""生成图片（自动将中文翻译为英文，支持多人物参考）"""
		prompt_cn = self.img_txt_prompt_cn.get("1.0", END).strip()
		if not prompt_cn:
			messagebox.showwarning("提示", "请先生成或填写图片描述")
			return
		
		# 获取选中的参考人物
		selected_characters = self._get_selected_reference_characters()
		
		# 如果选择了参考人物，自动将他们的描述添加到提示词中，并强调一致性
		if selected_characters:
			char_descriptions = []
			for char in selected_characters:
				if char.get("description"):
					# 强化描述，明确说明要保持一致
					char_descriptions.append(f"【{char['name']}】必须严格保持以下外貌特征：{char['description']}")
			
			if char_descriptions:
				# 将人物描述添加到原提示词前面，并强调重要性
				characters_text = "\n".join(char_descriptions)
				prompt_cn = f"⚠️ 人物外貌一致性要求（最高优先级）：\n{characters_text}\n\n✅ 以上人物特征是强制约束，必须100%符合！画面中的这些人物外貌、服装、发型等所有特征必须与描述完全一致。\n\n场景描述：\n{prompt_cn}"
				print(f"✅ 已添加 {len(selected_characters)} 个参考人物的描述（强化一致性）")
		
		def task(prompt_cn=prompt_cn, selected_characters=selected_characters):
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
				# 检查是否有参考人物
				has_reference_characters = selected_characters and len(selected_characters) > 0
				
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
				)
				
				if has_reference_characters:
					inst += (
						f"\n⚠️ 特别重要：\n"
						f"- 如果描述中包含「人物外貌一致性要求」或「必须严格保持以下外貌特征」，这些是强制约束！\n"
						f"- 人物的外貌特征（面部、发型、服装、体型等）描述必须完整保留并放在提示词开头\n"
						f"- 使用强调性词汇如 \"MUST HAVE\", \"exactly as described\", \"consistent with\" 等\n"
						f"- 人物特征的权重最高，不可被其他元素稀释\n\n"
					)
				
				inst += f"6. 不要输出任何解释，只输出最终的英文提示词"
				
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
					
					# 生成即梦AI视频提示词
					video_prompt = self._generate_video_prompt()
					self.video_prompt_text.config(state=NORMAL)
					self.video_prompt_text.delete("1.0", END)
					self.video_prompt_text.insert("1.0", video_prompt)
					self.video_prompt_text.config(state=DISABLED)
				
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
					
					# 使用选中的参考人物照片（优先使用第一个）
					ref_image_path = None
					if selected_characters and selected_characters[0].get("photo_path"):
						ref_image_path = selected_characters[0]["photo_path"]
						char_names = [c["name"] for c in selected_characters]
						print(f"📸 使用参考人物：{', '.join(char_names)}")
					elif self.img_ref_path.get().strip():
						ref_image_path = self.img_ref_path.get().strip()
					
					if ref_image_path:
						self.status.set(f"📸 使用参考图片生成...（步骤2/3）")
						results = img_client.generate_with_reference(
							prompt=prompt_en, 
							reference_image_path=ref_image_path, 
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
				
				# 生成即梦AI视频提示词
				video_prompt = self._generate_video_prompt()
				self.video_prompt_text.config(state=NORMAL)
				self.video_prompt_text.delete("1.0", END)
				self.video_prompt_text.insert("1.0", video_prompt)
				self.video_prompt_text.config(state=DISABLED)
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

	def _on_recommend_video_mode(self) -> None:
		"""智能推荐视频模式"""
		story_text = self.output.get("1.0", END).strip()
		if not story_text:
			messagebox.showwarning("提示", "请先在'故事'页生成或粘贴故事内容")
			return
		
		# 分析故事特征
		story_length = len(story_text)
		
		# 统计场景转换关键词
		scene_keywords = ['突然', '这时', '随后', '接着', '然后', '于是', '转身', '走进', '来到', 
						  '回到', '看到', '听到', '发现', '意识到', '想起', '记得']
		scene_count = sum(story_text.count(kw) for kw in scene_keywords)
		
		# 统计情节复杂度关键词
		complexity_keywords = ['但是', '然而', '不料', '没想到', '原来', '竟然', '居然', 
							   '转折', '突变', '真相', '秘密', '回忆', '闪回']
		complexity_score = sum(story_text.count(kw) for kw in complexity_keywords)
		
		# 统计人物数量（粗略估计）
		character_keywords = ['他', '她', '我', '你', '他们', '她们', '我们']
		has_multiple_characters = sum(story_text.count(kw) for kw in character_keywords) > 20
		
		# 推荐逻辑
		recommendation = ""
		mode = ""
		reason = []
		
		if story_length < 1000:
			mode = "brief"
			recommendation = "🎬 简短视频(8-12)"
			reason.append(f"• 故事较短（{story_length}字）")
			reason.append("• 适合快节奏短视频")
			reason.append("• 8-12个镜头足够覆盖核心情节")
		elif story_length < 2500:
			if complexity_score > 5 or scene_count > 10:
				mode = "video"
				recommendation = "🎬 平衡视频(15-25) ⭐推荐"
				reason.append(f"• 故事长度适中（{story_length}字）")
				reason.append(f"• 情节有一定复杂度（转折词{complexity_score}个）")
				reason.append("• 15-25个镜头能完整呈现故事")
			else:
				mode = "normal"
				recommendation = "🎬 标准视频(15-22)"
				reason.append(f"• 故事长度标准（{story_length}字）")
				reason.append("• 情节相对简单流畅")
				reason.append("• 15-22个镜头刚好合适")
		elif story_length < 5000:
			if complexity_score > 8 or has_multiple_characters:
				mode = "detailed"
				recommendation = "🎬 精细视频(25-40)"
				reason.append(f"• 故事较长（{story_length}字）")
				reason.append(f"• 情节复杂（转折词{complexity_score}个，场景{scene_count}处）")
				reason.append("• 需要25-40个镜头细致呈现")
			else:
				mode = "video"
				recommendation = "🎬 平衡视频(15-25)"
				reason.append(f"• 故事较长（{story_length}字）")
				reason.append("• 情节适中，不太复杂")
				reason.append("• 15-25个镜头平衡完整性和精简度")
		else:
			mode = "detailed"
			recommendation = "🎬 精细视频(25-40)"
			reason.append(f"• 故事很长（{story_length}字）")
			reason.append(f"• 需要充足的镜头数量来完整叙事")
			reason.append("• 25-40个镜头才能展现所有重要时刻")
		
		# 显示推荐结果
		reason_text = "\n".join(reason)
		result = messagebox.askyesno(
			"智能推荐结果", 
			f"📊 故事分析：\n"
			f"字数：{story_length} 字\n"
			f"场景转换：约 {scene_count} 处\n"
			f"情节复杂度：{'高' if complexity_score > 8 else '中' if complexity_score > 4 else '低'}\n\n"
			f"💡 推荐模式：\n{recommendation}\n\n"
			f"📝 推荐理由：\n{reason_text}\n\n"
			f"是否立即使用推荐模式生成分镜？"
		)
		
		if result:
			# 用户确认，直接生成
			self._on_img_extract_shots(mode=mode)
		else:
			# 更新提示文字
			self.recommend_label.config(text=f"💡 推荐：{recommendation}")
			self.status.set(f"已分析故事，推荐使用 {recommendation}")

	def _on_img_build_prompt(self) -> None:
		story_text = self.output.get("1.0", END).strip()
		if not story_text:
			messagebox.showwarning("提示", "请先在'故事'页生成或粘贴正文内容，然后再提炼提示词")
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
			mode_name = "简短视频"
			inst = (
				"请把以下故事正文拆解为**简短视频分镜脚本**，生成8-12个关键镜头，"
				"**只选取最核心的场景**，快节奏叙述故事的主要情节和高潮时刻。\n\n"
				"每个镜头包含（用 | 分隔）：\n"
				"1. **场景**：地点、环境、时间\n"
				"2. **人物与动作**：主体、动作、表情\n"
				"3. **镜头**：特写CU/中景MS/全景WS/远景LS\n"
				"4. **运镜**：固定/推镜/拉镜/摇镜/跟随\n"
				"5. **时长**：如'3-5秒''8-10秒'\n"
				"6. **转场**：切/淡入淡出/闪白（最后写'结束'）\n"
				"7. **声音**：环境音/配乐/对白提示\n\n"
				"格式示例：\n"
				"1. 深夜街道，路灯昏暗 | 女主角快步行走，不时回头 | 全景(WS) | 跟随 | 4-5秒 | 淡入 | 紧张配乐，脚步声\n\n"
				"输出格式：序号. 场景 | 人物与动作 | 镜头 | 运镜 | 时长 | 转场 | 声音\n"
				"注意：只输出清单，不要其他文字。"
			)
		elif mode == "video":
			shot_count = "15-25"
			mode_name = "平衡视频"
			inst = (
				"请把以下故事正文拆解为**专业平衡视频分镜脚本**，生成15-25个镜头，"
				"在完整性和精简度之间找到平衡，适合大多数视频项目。\n\n"
				"每个镜头包含（用 | 分隔）：\n"
				"1. **场景**：具体地点、环境、时间（白天/夜晚/傍晚）\n"
				"2. **人物与动作**：主体、动作、表情状态\n"
				"3. **镜头**：特写CU/近景MS/中景MCU/全景WS/远景LS/过肩OTS/主观POV\n"
				"4. **运镜**：固定/推镜/拉镜/摇镜/跟随/环绕/升降（如'缓慢推进''快速拉远''平稳跟随'）\n"
				"5. **时长**：建议停留时间，如'3-5秒''8-10秒''瞬间闪过'\n"
				"6. **转场**：切/淡入淡出/叠化/闪白/黑场（最后一个写'结束'）\n"
				"7. **声音**：环境音/音乐情绪/对白提示/音效\n\n"
				"格式示例：\n"
				"1. 深夜城市街道，路灯昏暗，薄雾 | 空旷街道，远处车灯 | 远景(LS) | 缓慢右摇 | 5-6秒 | 淡入 | 低沉环境音，车声\n"
				"2. 公寓楼外景，三楼灯亮 | 窗帘后人影移动 | 中景(MCU) | 固定，缓慢推进 | 4-5秒 | 切 | 环境音渐弱\n\n"
				"输出格式：序号. 场景 | 人物与动作 | 镜头 | 运镜 | 时长 | 转场 | 声音\n"
				"注意：保持节奏流畅，情绪转折用不同镜头，关键情节特写+慢镜，过渡场景全景+快节奏。"
			)
		elif mode == "detailed":
			shot_count = "25-40"
			mode_name = "精细视频"
			inst = (
				"请把以下故事正文拆解为**极其详细的视频分镜脚本**，生成25-40个镜头，"
				"**细致分割每个场景、情节转折、人物表情变化**，力求电影级的完整叙事。\n\n"
				"分镜原则（确保完整性）：\n"
				"1. 场景转换必须新开分镜\n"
				"2. 人物表情或动作变化时新开分镜\n"
				"3. 情节转折点单独成镜\n"
				"4. 对话场景拆分多角度（正反打、过肩镜头）\n"
				"5. 氛围细节镜头独立展示\n"
				"6. 重要物件特写单独成镜\n\n"
				"每个镜头包含（用 | 分隔）：\n"
				"1. **场景**：具体地点、环境细节、时间\n"
				"2. **人物与动作**：主体、服饰、姿态、表情、具体动作\n"
				"3. **镜头**：大特写ECU/特写CU/近景MS/中景MCU/全景WS/远景LS/定场镜头/过肩OTS/主观POV/高角度/低角度\n"
				"4. **运镜**：固定/推镜/拉镜/摇镜/跟随/环绕/升降/摇臂（描述速度和感觉，如'极慢推进''快速环绕'）\n"
				"5. **时长**：精确的停留时间，如'2-3秒''5-7秒''10-15秒'\n"
				"6. **转场**：切/淡入淡出/叠化/擦除/闪白/闪黑/黑场（最后写'结束'）\n"
				"7. **声音**：环境音/配乐变化/对白内容/音效细节\n\n"
				"格式示例：\n"
				"1. 雨夜街角，霓虹灯闪烁，地面积水 | 女主角撑伞独行，黑色风衣，眼神疲惫 | 全景(WS) | 缓慢推进 | 6-8秒 | 淡入 | 雨声，远处车声，忧伤钢琴\n\n"
				"输出格式：序号. 场景 | 人物与动作 | 镜头 | 运镜 | 时长 | 转场 | 声音\n"
				"注意：只输出清单，覆盖所有重要时刻，追求电影级完整度。"
			)
		else:  # normal mode - 改为标准视频
			shot_count = "15-22"
			mode_name = "标准视频"
			inst = (
				"请把以下故事正文拆解为**标准视频分镜脚本**，生成15-22个镜头，"
				"完整覆盖故事情节，节奏适中，既保证叙事完整又不过于冗长。\n\n"
				"每个镜头包含（用 | 分隔）：\n"
				"1. **场景**：地点、环境、时间\n"
				"2. **人物与动作**：主体、动作、表情状态\n"
				"3. **镜头**：特写CU/近景MS/中景MCU/全景WS/远景LS/过肩OTS/主观POV\n"
				"4. **运镜**：固定/推镜/拉镜/摇镜/跟随/环绕/升降（如'缓慢推进''快速拉远'）\n"
				"5. **时长**：建议停留时间，如'3-5秒''8-10秒'\n"
				"6. **转场**：切/淡入淡出/叠化/闪白/黑场（最后一个写'结束'）\n"
				"7. **声音**：环境音/配乐情绪/对白/音效\n\n"
				"格式示例：\n"
				"1. 办公室走廊，夜晚，日光灯闪烁 | 男主角疲惫地走着，眼神空洞 | 中景(MCU) | 跟随移动 | 5-6秒 | 淡入 | 空调嗡嗡声，低沉配乐\n\n"
				"输出格式：序号. 场景 | 人物与动作 | 镜头 | 运镜 | 时长 | 转场 | 声音\n"
				"注意：只输出清单，覆盖完整故事线。"
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
				
				# 更新分镜列表框
				if shots:
					self.status.set(f"✅ 更新分镜显示...")
					
					# 更新Listbox
					self.shots_listbox.config(state=NORMAL)
					self.shots_listbox.delete(0, END)
					for i, shot in enumerate(shots):
						# 显示序号和分镜描述（限制长度以便阅读）
						display_text = f"{i+1}. {shot[:80]}..." if len(shot) > 80 else f"{i+1}. {shot}"
						self.shots_listbox.insert(END, display_text)
					
					# 保存完整的分镜列表
					self.parsed_shots = shots
					
					# 默认选中第一个分镜
					self.shots_listbox.selection_set(0)
					self.shots_listbox.activate(0)
					# 显示第一个分镜
					self._on_shot_listbox_selected(None)
					
					self.status.set(f"🎬 已生成{mode_name} {len(shots)} 个分镜（点击列表中的分镜即可选择）")
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
	
	def _on_shot_listbox_selected(self, event) -> None:
		"""当在Listbox中选择分镜时，自动识别并选择参考人物"""
		if not hasattr(self, 'parsed_shots') or not self.parsed_shots:
			return
		
		selection = self.shots_listbox.curselection()
		if not selection:
			return
		
		selected_index = selection[0]
		if selected_index < 0 or selected_index >= len(self.parsed_shots):
			return
		
		# 获取选中的分镜文本
		current_shot = self.parsed_shots[selected_index]
		
		# 显示状态
		self.status.set(f"已选择第 {selected_index+1} 个分镜，正在识别人物...")
		
		# 智能识别并自动选择参考人物（延迟执行以确保UI更新）
		self.after(50, lambda: self._auto_select_characters_from_shot(current_shot, ""))
	
	def _on_shot_selected(self, event) -> None:
		"""兼容性函数：当使用Combobox选择分镜时（已废弃，保留以防代码引用）"""
		# 此函数已被 _on_shot_listbox_selected 替代
		pass
	
	def _on_img_prompt_from_current_shot(self) -> None:
		"""从当前选中的分镜生成中文图片描述"""
		if not hasattr(self, 'parsed_shots') or not self.parsed_shots:
			messagebox.showwarning("提示", "请先生成分镜")
			return
		
		selection = self.shots_listbox.curselection()
		if not selection:
			messagebox.showwarning("提示", "请先在列表中选择一个分镜")
			return
		
		selected_index = selection[0]
		if selected_index < 0 or selected_index >= len(self.parsed_shots):
			messagebox.showwarning("提示", "请先在列表中选择一个分镜")
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
				
				# 智能识别并自动选择参考人物
				self.after(100, lambda: self._auto_select_characters_from_shot(current_shot, description))
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
			selection = self.shots_listbox.curselection() if hasattr(self, 'shots_listbox') else ()
			if selection and selection[0] >= 0 and selection[0] < len(self.parsed_shots):
				shot_desc = self.parsed_shots[selection[0]]
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
			selection = self.shots_listbox.curselection() if hasattr(self, 'shots_listbox') else ()
			if selection and selection[0] >= 0 and selection[0] < len(self.parsed_shots):
				import re
				shot_desc = self.parsed_shots[selection[0]]
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
	
	# ==================== 人物生成相关函数 ====================
	
	def _on_char_canvas_configure(self, event) -> None:
		"""处理人物照片Canvas大小变化事件"""
		if not self.character_last_image:
			return
		
		# 自动调整图片大小以适应Canvas
		canvas_width = event.width
		canvas_height = event.height
		
		img_width, img_height = self.character_last_image.size
		
		# 计算缩放比例
		width_ratio = canvas_width / img_width
		height_ratio = canvas_height / img_height
		scale_ratio = min(width_ratio, height_ratio, 1.0)  # 不放大，只缩小
		
		new_w = int(img_width * scale_ratio)
		new_h = int(img_height * scale_ratio)
		
		# 缩放图片
		img = self.character_last_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
		
		# 转换为PhotoImage
		self.character_preview_photo = ImageTk.PhotoImage(img)
		
		# 更新Label
		self.char_preview.configure(image=self.character_preview_photo, text="")
		
		# 更新Canvas的滚动区域
		self.char_canvas.configure(scrollregion=(0, 0, new_w, new_h))
		
		# 居中显示图片
		if new_w < canvas_width:
			x_offset = (canvas_width - new_w) // 2
		else:
			x_offset = 0
			
		if new_h < canvas_height:
			y_offset = (canvas_height - new_h) // 2
		else:
			y_offset = 0
		
		self.char_canvas.coords(self.char_canvas_window, x_offset, y_offset)
	
	def _on_extract_characters(self) -> None:
		"""从当前故事中提取人物列表"""
		import threading
		
		# 获取当前故事内容
		story_text = self.output.get("1.0", END).strip()
		if not story_text:
			messagebox.showwarning("提示", "请先生成故事内容！")
			return
		
		# 获取API配置
		selected_api = self.outline_gen_api.get() if hasattr(self, 'outline_gen_api') else "DeepSeek"
		if not hasattr(self, 'api_presets') or selected_api not in self.api_presets:
			messagebox.showerror("错误", f"未找到API配置: {selected_api}，请检查配置页面")
			return
		
		api_config = self.api_presets[selected_api]
		api_key = _sanitize(api_config.get("key", ""))
		if not api_key:
			messagebox.showwarning("提示", f"API Key 为空，请在'故事生成-配置'页面为 {selected_api} 填写后保存")
			return
		
		# 禁用按钮
		self.char_btn_extract.config(state=DISABLED)
		self.char_btn_refresh.config(state=DISABLED)
		self.status.set("🔍 正在分析故事，提取人物列表...")
		if hasattr(self, 'update_header_status'):
			self.update_header_status("提取人物中...", "🔍")
		
		def extract_thread():
			try:
				# 使用DeepSeek提取人物
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				
				prompt = f"""请从以下故事中提取所有关键人物的名字。
				
故事内容：
{story_text}

请以JSON格式返回人物列表，格式如下：
{{"characters": ["人物1", "人物2", "人物3"]}}

要求：
1. 只提取有具体名字的人物
2. 不要提取"他"、"她"、"某人"等代词
3. 按重要性排序，主要人物在前
4. 最多提取10个人物
"""
				
				messages = [{"role": "user", "content": prompt}]
				response = client.chat(messages, temperature=0.3)
				
				# 解析JSON响应
				import json
				import re
				
				# 尝试提取JSON
				json_match = re.search(r'\{.*\}', response, re.DOTALL)
				if json_match:
					data = json.loads(json_match.group())
					characters = data.get("characters", [])
				else:
					# 如果没有JSON，尝试从文本中提取人物名
					characters = []
					lines = response.strip().split('\n')
					for line in lines:
						line = line.strip()
						# 移除序号、引号等
						line = re.sub(r'^\d+[\.\、\s]*', '', line)
						line = line.strip('"\'「」『』""''').strip()
						if line and len(line) <= 10:  # 人名通常不会太长
							characters.append(line)
				
				# 更新人物列表
				self.character_list = [{"name": name, "description": ""} for name in characters]
				
				# 更新UI（在主线程中）
				self.after(0, lambda: self._update_character_listbox())
				self.after(0, lambda: self.status.set(f"✅ 成功提取到 {len(characters)} 个人物"))
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("人物提取完成", "✅"))
				
			except Exception as e:
				error_msg = f"提取人物失败: {str(e)}"
				print(f"提取人物时出错: {error_msg}")
				self.after(0, lambda: messagebox.showerror("错误", error_msg))
				self.after(0, lambda: self.status.set("❌ 提取人物失败"))
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("提取失败", "❌"))
			finally:
				self.after(0, lambda: self.char_btn_extract.config(state=NORMAL))
				self.after(0, lambda: self.char_btn_refresh.config(state=NORMAL))
		
		threading.Thread(target=extract_thread, daemon=True).start()
	
	def _update_character_listbox(self) -> None:
		"""更新人物列表框"""
		self.char_listbox.delete(0, END)
		for char in self.character_list:
			self.char_listbox.insert(END, char["name"])
		
		if self.character_list:
			# 默认选中第一个
			self.char_listbox.selection_set(0)
			self.char_listbox.event_generate("<<ListboxSelect>>")
			
			# 更新图片创作页面的参考人物下拉框
			self._update_reference_character_list()
	
	def _on_character_selected(self, event=None) -> None:
		"""当选择人物时的回调"""
		selection = self.char_listbox.curselection()
		if not selection:
			return
		
		index = selection[0]
		
		# 边界检查
		if index < 0 or index >= len(self.character_list):
			print(f"⚠️ 人物索引越界：index={index}, list_len={len(self.character_list)}")
			return
		
		character = self.character_list[index]
		
		# 更新特征描述文本框
		self.char_txt_desc.config(state=NORMAL)
		self.char_txt_desc.delete("1.0", END)
		
		if character["description"]:
			self.char_txt_desc.insert("1.0", character["description"])
			self.char_btn_copy_desc.config(state=NORMAL)
			self.char_btn_gen_photo.config(state=NORMAL)
		else:
			self.char_txt_desc.insert("1.0", f"尚未生成特征描述，点击下方按钮为\"{character['name']}\"生成详细特征...")
			self.char_btn_copy_desc.config(state=DISABLED)
			self.char_btn_gen_photo.config(state=DISABLED)
		
		self.char_txt_desc.config(state=DISABLED)
		
		# 启用生成特征描述按钮
		self.char_btn_gen_desc.config(state=NORMAL)
	
	def _on_generate_character_description(self) -> None:
		"""生成选中人物的特征描述"""
		import threading
		
		selection = self.char_listbox.curselection()
		if not selection:
			return
		
		index = selection[0]
		character = self.character_list[index]
		character_name = character["name"]
		
		# 获取故事内容
		story_text = self.output.get("1.0", END).strip()
		
		# 获取API配置
		selected_api = self.outline_gen_api.get() if hasattr(self, 'outline_gen_api') else "DeepSeek"
		if not hasattr(self, 'api_presets') or selected_api not in self.api_presets:
			messagebox.showerror("错误", f"未找到API配置: {selected_api}")
			return
		
		api_config = self.api_presets[selected_api]
		api_key = _sanitize(api_config.get("key", ""))
		if not api_key:
			messagebox.showwarning("提示", f"API Key 为空，请在'故事生成-配置'页面配置")
			return
		
		# 禁用按钮
		self.char_btn_gen_desc.config(state=DISABLED)
		self.status.set(f"✨ 正在分析\"{character_name}\"的特征...")
		if hasattr(self, 'update_header_status'):
			self.update_header_status(f"生成特征描述...", "✨")
		
		def generate_desc_thread():
			try:
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				
				prompt = f"""请从以下故事中提取"{character_name}"的详细外貌特征描述。

故事内容：
{story_text}

请详细描述"{character_name}"的外貌特征，包括：
1. 性别、年龄段
2. 面部特征（脸型、五官、表情等）
3. 身材体型
4. 发型发色
5. 穿着打扮
6. 其他显著特征

要求：
- 描述要具体、生动，适合用于生成人物肖像画
- 只描述外貌，不要包含性格、经历等内容
- 字数控制在150-300字
- 如果故事中没有明确描述某些特征，可以根据人物设定合理推测
"""
				
				messages = [{"role": "user", "content": prompt}]
				response = client.chat(messages, temperature=0.7)
				
				# 更新人物描述
				self.character_list[index]["description"] = response.strip()
				
				# 更新UI
				self.after(0, lambda: self._update_character_description_display(index))
				self.after(0, lambda: self.status.set(f"✅ 已生成\"{character_name}\"的特征描述"))
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("特征描述完成", "✅"))
				
			except Exception as e:
				error_msg = f"生成特征描述失败: {str(e)}"
				print(f"生成特征描述时出错: {error_msg}")
				self.after(0, lambda: messagebox.showerror("错误", error_msg))
				self.after(0, lambda: self.status.set("❌ 生成特征描述失败"))
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("生成失败", "❌"))
			finally:
				self.after(0, lambda: self.char_btn_gen_desc.config(state=NORMAL))
		
		threading.Thread(target=generate_desc_thread, daemon=True).start()
	
	def _update_character_description_display(self, index: int) -> None:
		"""更新特征描述显示"""
		character = self.character_list[index]
		
		self.char_txt_desc.config(state=NORMAL)
		self.char_txt_desc.delete("1.0", END)
		self.char_txt_desc.insert("1.0", character["description"])
		self.char_txt_desc.config(state=DISABLED)
		
		# 启用相关按钮
		self.char_btn_copy_desc.config(state=NORMAL)
		self.char_btn_gen_photo.config(state=NORMAL)
	
	def _on_copy_character_description(self) -> None:
		"""复制特征描述到剪贴板"""
		description = self.char_txt_desc.get("1.0", END).strip()
		if description:
			self.clipboard_clear()
			self.clipboard_append(description)
			self.status.set("📋 特征描述已复制到剪贴板")
	
	def _on_generate_character_photo(self) -> None:
		"""生成选中人物的照片"""
		print("🔔 _on_generate_character_photo 被调用")
		
		import threading
		from src.clients.hunyuan_image_client import HunyuanImageClient
		import base64
		from io import BytesIO
		
		selection = self.char_listbox.curselection()
		print(f"📋 当前选择: {selection}")
		
		if not selection:
			print("⚠️ 没有选择人物")
			messagebox.showwarning("提示", "请先从列表中选择一个人物！")
			return
		
		index = selection[0]
		character = self.character_list[index]
		character_name = character["name"]
		description = character.get("description", "")
		
		print(f"👤 选中人物: {character_name}")
		print(f"📝 描述长度: {len(description) if description else 0}")
		
		if not description:
			messagebox.showwarning("提示", "请先生成人物特征描述！")
			return
		
		# 检查当前项目
		if not self.current_project:
			messagebox.showwarning("提示", "请先创建或打开一个项目，人物照片需要保存到项目中！")
			return
		
		print(f"📁 当前项目: {self.current_project}")
		
		# 获取图片风格和额外描述
		style = self.char_img_style.get()
		extra_desc = self.char_txt_extra.get("1.0", END).strip()
		
		# 禁用按钮
		self.char_btn_gen_photo.config(state=DISABLED)
		self.status.set(f"🎨 正在生成\"{character_name}\"的照片...")
		if hasattr(self, 'update_header_status'):
			self.update_header_status(f"生成人物照片...", "🎨")
		
		def generate_photo_thread():
			try:
				print(f"\n{'='*60}\n开始生成人物照片: {character_name}\n{'='*60}")
				
				# 检查是否配置了API
				img_api_type = self.img_api_type.get() if hasattr(self, 'img_api_type') else "openai"
				print(f"图片API类型: {img_api_type}")
				
				if img_api_type == "hunyuan":
					# 使用腾讯混元
					print("使用腾讯混元API")
					secret_id = self.hunyuan_secret_id.get() if hasattr(self, 'hunyuan_secret_id') else ""
					secret_key = self.hunyuan_secret_key.get() if hasattr(self, 'hunyuan_secret_key') else ""
					
					if not secret_id or not secret_key:
						print("腾讯混元API密钥未配置")
						self.after(0, lambda: messagebox.showerror("错误", "请先在配置页面设置腾讯混元API密钥"))
						self.after(0, lambda: self.status.set("❌ 未配置API密钥"))
						if hasattr(self, 'update_header_status'):
							self.after(0, lambda: self.update_header_status("未配置API", "❌"))
						return
					
					# 构建提示词（优化为单人全身照）
					prompt_parts = []
					
					# 最强调：单人全身照
					prompt_parts.append("一个人")
					prompt_parts.append("单人全身照")
					prompt_parts.append("从头到脚完整展示")
					prompt_parts.append("站立姿势")
					
					# 默认中国人外貌（除非描述中明确说明是外国人）
					if not any(keyword in description for keyword in ["外国", "欧美", "美国", "英国", "法国", "德国", "日本", "韩国", "俄罗斯", "非洲", "印度", "阿拉伯"]):
						prompt_parts.append("中国人")
						prompt_parts.append("东亚面孔")
						prompt_parts.append("中国人特征")
					
					# 添加人物特征描述
					prompt_parts.append(description)
					
					# 添加额外描述
					if extra_desc:
						prompt_parts.append(extra_desc)
					
					# 风格关键词
					style_keywords = {
						"写实照片": "高清摄影",
						"日系动漫": "动漫风",
						"3D渲染": "3D渲染",
						"水彩画": "水彩",
						"油画": "油画质感",
						"中国风": "中国风",
						"国风插画": "国风插画",
						"古风": "古风",
						"仙侠": "仙侠",
						"武侠": "武侠"
					}.get(style, style)
					
					prompt_parts.append(style_keywords)
					
					# 明确说明不要的内容
					prompt_parts.append("纯色背景")
					prompt_parts.append("人物居中")
					
					full_prompt = "，".join(prompt_parts)
					
					# 限制字符数（腾讯混元限制256字符）
					if len(full_prompt) > 256:
						# 保留核心部分：单人全身照 + 特征描述
						core_prompt = f"一个人，单人全身照，从头到脚完整展示，{description[:180]}，{style_keywords}"
						full_prompt = core_prompt[:256]
					
					self.after(0, lambda: self.status.set(f"🚀 正在调用腾讯混元API生成\"{character_name}\"的照片..."))
					
					client = HunyuanImageClient(secret_id=secret_id, secret_key=secret_key)
					result = client.generate(
						prompt=full_prompt,
						resolution="1024:1024",
						style="201"
					)
					
					# 解析base64图片
					img_base64 = result["ResultImage"]
					img_data = base64.b64decode(img_base64)
					img = Image.open(BytesIO(img_data))
					
				else:
					# 使用OpenAI DALL-E或兼容API
					print("使用OpenAI或兼容API")
					api_key = self.img_api_key.get()
					base_url = self.img_base_url.get() if hasattr(self, 'img_base_url') and self.img_base_url.get() else None
					model = self.img_model.get() if hasattr(self, 'img_model') else "dall-e-3"
					
					print(f"API Key存在: {bool(api_key)}, Base URL: {base_url}, Model: {model}")
					
					if not api_key:
						print("图片API密钥未配置")
						self.after(0, lambda: messagebox.showerror("错误", "请先在'图片生成-配置'页面设置API密钥"))
						self.after(0, lambda: self.status.set("❌ 未配置API密钥"))
						if hasattr(self, 'update_header_status'):
							self.after(0, lambda: self.update_header_status("未配置API", "❌"))
						return
					
					# 构建提示词（优化为单人全身照）
					prompt_parts = []
					
					# 最强调：单人全身照（英文更准确）
					prompt_parts.append("single person")
					prompt_parts.append("full body portrait")
					prompt_parts.append("standing pose")
					prompt_parts.append("head to toe")
					prompt_parts.append("complete figure")
					
					# 默认中国人外貌（除非描述中明确说明是外国人）
					if not any(keyword in description for keyword in ["外国", "欧美", "美国", "英国", "法国", "德国", "日本", "韩国", "俄罗斯", "非洲", "印度", "阿拉伯", "American", "European", "Western", "Japanese", "Korean"]):
						prompt_parts.append("Chinese person")
						prompt_parts.append("East Asian features")
						prompt_parts.append("Asian face")
					
					# 添加人物特征描述
					prompt_parts.append(description)
					
					# 添加额外描述
					if extra_desc:
						prompt_parts.append(extra_desc)
					
					# 添加风格
					prompt_parts.append(f"{style}风格")
					
					# 画面要求
					prompt_parts.append("centered composition")
					prompt_parts.append("simple background")
					prompt_parts.append("high quality")
					prompt_parts.append("detailed")
					
					full_prompt = "，".join(prompt_parts)
					
					print(f"生成提示词: {full_prompt[:100]}...")
					
					self.after(0, lambda: self.status.set(f"🚀 正在调用图片API生成\"{character_name}\"的照片..."))
					
					print(f"创建OpenAIImageClient...")
					client = OpenAIImageClient(api_key=api_key, base_url=base_url, model=model)
					print(f"调用generate方法...")
					results = client.generate(full_prompt, size="1024x1024")
					print(f"收到结果: {len(results) if results else 0} 张图片")
					
					# 获取第一张图片
					if results:
						img = results[0].image
					else:
						raise RuntimeError("API未返回任何图片")
				
				# 保存图片到内存
				self.character_last_image = img
				
				# 在主线程中执行保存和更新操作
				def update_ui_and_save():
					# 自动保存到characters文件夹
					saved_path = self._auto_save_character_photo(index, img, character_name)
					# 更新预览
					self._update_character_photo_preview(img)
					# 更新状态
					if saved_path:
						# 获取项目名称
						if self.current_project:
							project_name = self.current_project.metadata.get("name", "未命名项目")
						else:
							project_name = "未知项目"
						self.status.set(f"✅ 成功生成并保存\"{character_name}\"的照片到项目 [{project_name}]")
					else:
						self.status.set(f"✅ 成功生成\"{character_name}\"的照片（保存失败：请先创建项目）")
					# 启用保存按钮
					self.char_btn_save_photo.config(state=NORMAL)
					# 更新参考人物列表
					self._update_reference_character_list()
					# 更新顶部状态
					if hasattr(self, 'update_header_status'):
						self.update_header_status("照片生成完成", "✅")
				
				self.after(0, update_ui_and_save)
				
			except Exception as e:
				import traceback
				error_detail = traceback.format_exc()
				error_msg = f"生成照片失败: {str(e)}"
				print(f"\n{'='*60}\n生成人物照片时发生错误：\n{error_detail}\n{'='*60}\n")
				
				# 显示更详细的错误信息
				if "401" in str(e) or "authentication" in str(e).lower():
					error_msg = "API密钥无效或已过期，请检查配置"
				elif "timeout" in str(e).lower():
					error_msg = "API请求超时，请检查网络连接"
				elif "rate" in str(e).lower() or "quota" in str(e).lower():
					error_msg = "API配额用尽或请求频率过高"
				
				self.after(0, lambda msg=error_msg: messagebox.showerror("生成失败", msg))
				self.after(0, lambda: self.status.set("❌ 生成照片失败"))
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("生成失败", "❌"))
			finally:
				self.after(0, lambda: self.char_btn_gen_photo.config(state=NORMAL))
		
		threading.Thread(target=generate_photo_thread, daemon=True).start()
	
	def _load_project_characters(self) -> None:
		"""加载当前项目的人物照片和描述到参考列表"""
		# 清空之前的人物列表
		self.character_list.clear()
		
		if not self.current_project:
			print("⚠️ 没有当前项目，无法加载人物照片")
			self._update_reference_character_list()
			return
		
		try:
			import json
			from pathlib import Path
			
			# 获取项目的 characters 文件夹
			characters_dir = self.current_project.project_dir / "characters"
			
			if not characters_dir.exists():
				print(f"📁 项目尚无人物照片文件夹：{characters_dir}")
				self._update_reference_character_list()
				return
			
			# 读取人物描述信息
			characters_info_path = characters_dir / "characters_info.json"
			characters_info = {}
			if characters_info_path.exists():
				try:
					with open(characters_info_path, 'r', encoding='utf-8') as f:
						characters_info = json.load(f)
					print(f"📖 已加载人物描述文件：{characters_info_path}")
				except Exception as e:
					print(f"⚠️ 读取人物描述文件失败：{str(e)}")
			
			# 扫描所有 PNG 图片
			character_photos = list(characters_dir.glob("*.png"))
			
			if not character_photos:
				print(f"📋 项目中暂无人物照片")
				self._update_reference_character_list()
				return
			
			# 将照片信息和描述添加到 character_list
			for photo_path in character_photos:
				character_name = photo_path.stem  # 文件名（不含扩展名）
				
				# 从 JSON 获取描述信息
				description = ""
				if character_name in characters_info:
					description = characters_info[character_name].get("description", "")
				
				self.character_list.append({
					"name": character_name,
					"description": description,
					"photo_path": str(photo_path)
				})
			
			print(f"✅ 已加载项目人物照片：{[p.stem for p in character_photos]}")
			
			# 显示人物描述预览
			for char in self.character_list:
				if char["description"]:
					desc_preview = char["description"][:50] + "..." if len(char["description"]) > 50 else char["description"]
					print(f"   📝 {char['name']}: {desc_preview}")
			
			# 更新列表框显示
			self._update_character_listbox()
			
			# 更新参考人物列表
			self._update_reference_character_list()
			
		except Exception as e:
			print(f"❌ 加载项目人物照片失败：{str(e)}")
			import traceback
			traceback.print_exc()
			self._update_reference_character_list()
	
	def _update_reference_character_list(self) -> None:
		"""更新图片创作页面的参考人物列表（仅当前项目，支持多选）"""
		# 清空列表框
		self.ref_character_listbox.delete(0, END)
		
		# 添加"不使用参考"选项
		self.ref_character_listbox.insert(END, "❌ 不使用参考")
		
		# 只显示当前项目中已生成照片的人物
		character_names = ["不使用参考"]
		for char in self.character_list:
			photo_path = char.get("photo_path")
			if photo_path:
				# 验证照片文件是否存在
				from pathlib import Path
				if Path(photo_path).exists():
					character_names.append(char["name"])
					self.ref_character_listbox.insert(END, f"✅ {char['name']}")
				else:
					print(f"⚠️ 人物照片不存在：{photo_path}")
		
		# 获取项目名称
		if self.current_project:
			project_name = self.current_project.metadata.get("name", "未命名项目")
		else:
			project_name = "无项目"
		print(f"📋 已更新参考人物列表 [项目: {project_name}]：{character_names}")
	
	def _get_selected_reference_characters(self) -> list:
		"""获取选中的参考人物列表"""
		selected_indices = self.ref_character_listbox.curselection()
		selected_characters = []
		
		for idx in selected_indices:
			item_text = self.ref_character_listbox.get(idx)
			# 去除前面的emoji和空格
			if item_text.startswith("✅ "):
				char_name = item_text[2:].strip()
				# 查找对应人物的照片路径和描述
				for char in self.character_list:
					if char["name"] == char_name and char.get("photo_path"):
						selected_characters.append({
							"name": char_name,
							"photo_path": char["photo_path"],
							"description": char.get("description", "")
						})
						break
		
		return selected_characters
	
	def _auto_select_characters_from_shot(self, shot_text: str, description: str = "") -> None:
		"""智能识别分镜中的人物并自动选中（支持名字、别名、特征匹配）"""
		try:
			print(f"\n{'='*60}")
			print(f"🤖 开始智能识别人物")
			print(f"{'='*60}")
			
			# 清空当前选择
			self.ref_character_listbox.selection_clear(0, END)
			
			# 获取所有可用的人物及其描述
			if not self.character_list:
				print(f"⚠️ 人物列表为空")
				return
			
			available_characters = []
			for char in self.character_list:
				if char.get("photo_path"):
					available_characters.append({
						"name": char["name"],
						"description": char.get("description", "")
					})
			
			print(f"📋 可用人物数量：{len(available_characters)}")
			for char in available_characters:
				desc_preview = char["description"][:50] + "..." if len(char["description"]) > 50 else char["description"]
				print(f"   - {char['name']}: {desc_preview}")
			
			if not available_characters:
				print(f"⚠️ 没有已生成照片的人物")
				return
			
			# 合并分镜和描述文本
			search_text = f"{shot_text} {description}"
			print(f"\n📝 搜索文本长度：{len(search_text)} 字")
			print(f"📝 搜索文本前300字：{search_text[:300]}...")
			
			# 识别文本中提到的人物
			mentioned_characters = []
			
			for char in available_characters:
				char_name = char["name"]
				char_desc = char["description"]
				matched_reasons = []
				
				# 方法1: 直接匹配人物名字
				if char_name in search_text:
					matched_reasons.append(f"名字匹配")
				
				# 方法2: 从人物描述中提取关键特征词并匹配
				# 提取职业、身份、角色
				identity_keywords = []
				for keyword in ["主角", "我", "实习生", "护士", "医生", "老人", "阿姨", "大妈", 
				               "女孩", "男孩", "年轻人", "中年", "老年", "小孩", "孩子",
				               "病人", "患者", "家属", "访客", "保安", "清洁工",
				               "教师", "学生", "司机", "服务员", "经理", "老板"]:
					if keyword in char_desc:
						identity_keywords.append(keyword)
				
				# 检查这些关键词是否在搜索文本中
				for keyword in identity_keywords:
					if keyword in search_text:
						matched_reasons.append(f"身份特征'{keyword}'匹配")
						break
				
				# 方法3: 提取年龄特征
				import re
				age_pattern = re.search(r'(\d{1,2})\s*岁', char_desc)
				if age_pattern:
					age = age_pattern.group(1)
					if f"{age}岁" in search_text or f"{age}岁" in search_text:
						matched_reasons.append(f"年龄'{age}岁'匹配")
				
				# 方法4: 提取外貌特征（发型、发色）
				appearance_keywords = []
				for keyword in ["短发", "长发", "齐肩", "卷发", "直发", "马尾", "辫子",
				               "黑发", "白发", "金发", "棕发", "红发",
				               "眼镜", "胡须", "瘦", "胖", "高", "矮"]:
					if keyword in char_desc and keyword in search_text:
						appearance_keywords.append(keyword)
				
				if appearance_keywords:
					matched_reasons.append(f"外貌特征{appearance_keywords}匹配")
				
				# 方法5: 提取服装特征
				clothing_keywords = []
				for keyword in ["白大褂", "护士服", "制服", "西装", "衬衫", "T恤", "裙子", "裤子"]:
					if keyword in char_desc and keyword in search_text:
						clothing_keywords.append(keyword)
				
				if clothing_keywords:
					matched_reasons.append(f"服装特征{clothing_keywords}匹配")
				
				# 如果有任何匹配，添加到识别列表
				if matched_reasons:
					mentioned_characters.append(char_name)
					print(f"✅ 识别到人物【{char_name}】：{' | '.join(matched_reasons)}")
			
			# 如果没有识别到人物，不做任何选择
			if not mentioned_characters:
				print(f"💡 未在分镜中识别到已生成照片的人物")
				print(f"   提示：可能是人物描述与分镜描述差异较大")
				print(f"{'='*60}\n")
				return
			
			# 在列表框中选中这些人物
			selected_count = 0
			for idx in range(self.ref_character_listbox.size()):
				item_text = self.ref_character_listbox.get(idx)
				if item_text.startswith("✅ "):
					char_name = item_text[2:].strip()
					if char_name in mentioned_characters:
						self.ref_character_listbox.selection_set(idx)
						selected_count += 1
						print(f"🎯 在列表第{idx}行选中：{char_name}")
			
			# 显示提示信息
			if mentioned_characters:
				char_names = "、".join(mentioned_characters)
				self.status.set(f"✅ 已自动选择参考人物：{char_names}")
				print(f"🎭 智能识别并选中 {selected_count} 个人物：{char_names}")
			
			print(f"{'='*60}\n")
			
		except Exception as e:
			print(f"⚠️ 自动选择参考人物时出错：{str(e)}")
			import traceback
			traceback.print_exc()
	
	def _update_character_photo_preview(self, img: Image.Image) -> None:
		"""更新人物照片预览"""
		canvas_width = self.char_canvas.winfo_width()
		canvas_height = self.char_canvas.winfo_height()
		
		# 如果Canvas还没有初始化大小，使用默认值
		if canvas_width <= 1:
			canvas_width = 400
		if canvas_height <= 1:
			canvas_height = 400
		
		img_width, img_height = img.size
		
		# 计算缩放比例
		width_ratio = canvas_width / img_width
		height_ratio = canvas_height / img_height
		scale_ratio = min(width_ratio, height_ratio, 1.0)
		
		new_w = int(img_width * scale_ratio)
		new_h = int(img_height * scale_ratio)
		
		# 缩放图片
		resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
		
		# 转换为PhotoImage
		self.character_preview_photo = ImageTk.PhotoImage(resized_img)
		
		# 更新Label
		self.char_preview.configure(image=self.character_preview_photo, text="")
		
		# 更新Canvas的滚动区域
		self.char_canvas.configure(scrollregion=(0, 0, new_w, new_h))
		
		# 居中显示
		if new_w < canvas_width:
			x_offset = (canvas_width - new_w) // 2
		else:
			x_offset = 0
		
		if new_h < canvas_height:
			y_offset = (canvas_height - new_h) // 2
		else:
			y_offset = 0
		
		self.char_canvas.coords(self.char_canvas_window, x_offset, y_offset)
	
	def _auto_save_character_photo(self, index: int, img: Image.Image, character_name: str) -> str:
		"""自动保存人物照片到当前项目的characters文件夹，并保存描述信息"""
		try:
			import re
			import json
			from pathlib import Path
			
			# 检查是否有当前项目
			if not self.current_project:
				messagebox.showwarning("提示", "请先创建或打开一个项目，人物照片将保存到项目目录中")
				return ""
			
			# 确定保存目录：项目目录/characters/
			self.character_photos_dir = self.current_project.project_dir / "characters"
			
			# 确保文件夹存在
			if not self.character_photos_dir.exists():
				print(f"📁 创建人物照片文件夹：{self.character_photos_dir}")
			self.character_photos_dir.mkdir(parents=True, exist_ok=True)
			
			# 验证文件夹创建成功
			if not self.character_photos_dir.exists():
				print(f"❌ 文件夹创建失败：{self.character_photos_dir}")
				return ""
			
			# 生成文件名（只使用人物名称，不加时间戳，这样同一人物会覆盖旧照片）
			clean_name = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', character_name)
			filename = f"{clean_name}.png"
			
			save_path = self.character_photos_dir / filename
			print(f"💾 准备保存到：{save_path}")
			
			img.save(str(save_path))
			
			# 验证文件保存成功
			if not save_path.exists():
				print(f"❌ 文件保存失败：{save_path}")
				return ""
			
			# 更新人物列表中的照片路径
			self.character_list[index]["photo_path"] = str(save_path)
			
			# 保存人物描述到 JSON 文件
			characters_info_path = self.character_photos_dir / "characters_info.json"
			
			# 读取现有的描述信息（如果存在）
			characters_info = {}
			if characters_info_path.exists():
				try:
					with open(characters_info_path, 'r', encoding='utf-8') as f:
						characters_info = json.load(f)
				except:
					pass
			
			# 更新当前人物的描述
			characters_info[character_name] = {
				"description": self.character_list[index].get("description", ""),
				"photo_path": str(save_path)
			}
			
			# 保存到文件
			with open(characters_info_path, 'w', encoding='utf-8') as f:
				json.dump(characters_info, f, ensure_ascii=False, indent=2)
			
			print(f"✅ 人物照片已自动保存到项目：{save_path}")
			print(f"📊 文件大小：{save_path.stat().st_size / 1024:.2f} KB")
			print(f"💾 人物描述已保存到：{characters_info_path}")
			return str(save_path)
			
		except Exception as e:
			print(f"❌ 自动保存失败：{str(e)}")
			import traceback
			traceback.print_exc()
			return ""
	
	def _on_save_character_photo(self) -> None:
		"""额外保存人物照片副本（可选）"""
		if not self.character_last_image:
			messagebox.showwarning("提示", "没有可保存的照片")
			return
		
		selection = self.char_listbox.curselection()
		if not selection:
			return
		
		index = selection[0]
		character = self.character_list[index]
		character_name = character["name"]
		
		# 弹出保存对话框，允许用户保存副本到其他位置
		file_path = filedialog.asksaveasfilename(
			defaultextension=".png",
			filetypes=[("PNG图片", "*.png"), ("JPEG图片", "*.jpg"), ("所有文件", "*.*")],
			initialfile=f"{character_name}_photo.png"
		)
		
		if file_path:
			try:
				self.character_last_image.save(file_path)
				self.status.set(f"✅ 照片副本已保存：{file_path}")
				messagebox.showinfo("成功", f"照片副本已保存到：\n{file_path}")
			except Exception as e:
				messagebox.showerror("错误", f"保存失败：{str(e)}")
	
	def _generate_video_prompt(self) -> str:
		"""
		根据当前分镜头描述生成适合即梦AI的视频提示词
		返回生成的视频提示词文本
		"""
		try:
			# 获取当前选中的分镜描述
			shot_desc = ""
			if hasattr(self, 'parsed_shots') and self.parsed_shots:
				selection = self.shots_listbox.curselection() if hasattr(self, 'shots_listbox') else ()
				if selection and selection[0] >= 0 and selection[0] < len(self.parsed_shots):
					shot_desc = self.parsed_shots[selection[0]]
				
				if not shot_desc:
					# 如果没有分镜描述，尝试从提示词文本框获取
					shot_desc = self.img_txt_prompt_cn.get("1.0", END).strip()
				
				if not shot_desc:
					return "请先选择分镜头或输入图片描述"
			
			# 解析分镜头描述，提取关键信息
			# 分镜头格式通常是：场景 | 内容描述 | 镜头 | 运镜 | 时长
			parts = shot_desc.split('|')
			
			# 提取场景和内容描述
			scene_info = ""
			action_info = ""
			camera_info = ""
			
			if len(parts) >= 2:
				scene_info = parts[0].strip()  # 场景信息
				action_info = parts[1].strip()  # 动作/内容描述
				if len(parts) >= 4:
					camera_info = parts[3].strip()  # 运镜信息
			else:
				# 如果不是标准格式，就直接使用原始描述
				action_info = shot_desc
			
			# 生成即梦AI视频提示词
			# 即梦AI需要强调动作、运动和变化
			video_prompt_parts = []
			
			# 1. 场景设定
			if scene_info:
				video_prompt_parts.append(scene_info)
			
			# 2. 主要动作和变化（这是视频的核心）
			if action_info:
				# 提取动词和动作关键词
				action_keywords = self._extract_action_keywords(action_info)
				if action_keywords:
					video_prompt_parts.append(action_keywords)
				else:
					video_prompt_parts.append(action_info)
			
			# 3. 镜头运动
			camera_movements = {
				"推进": "镜头缓慢推进",
				"拉远": "镜头缓慢拉远",
				"平移": "镜头平稳移动",
				"跟随": "镜头跟随主体",
				"环绕": "镜头环绕",
				"固定": "镜头稳定",
				"摇": "镜头摇动",
				"升降": "镜头升降"
			}
			
			camera_desc = ""
			if camera_info:
				for key, value in camera_movements.items():
					if key in camera_info:
						camera_desc = value
						break
				if not camera_desc and camera_info != "固定":
					camera_desc = f"镜头{camera_info}"
			
			if camera_desc:
				video_prompt_parts.append(camera_desc)
			
			# 4. 添加视频生成的通用提示
			# 强调连贯性和流畅性
			video_enhancement = "画面流畅自然，动作连贯，光影变化自然，5秒视频"
			video_prompt_parts.append(video_enhancement)
			
			# 组合成最终提示词
			final_prompt = "，".join(video_prompt_parts)
			
			# 长度控制（即梦AI通常建议提示词不要太长）
			if len(final_prompt) > 200:
				# 如果太长，去掉一些修饰性内容
				final_prompt = "，".join(video_prompt_parts[:-1])
				if len(final_prompt) > 200:
					final_prompt = final_prompt[:200]
			
			return final_prompt
			
		except Exception as e:
			print(f"生成视频提示词失败: {e}")
			import traceback
			traceback.print_exc()
			return "生成视频提示词时出错，请检查分镜头描述"
	
	def _extract_action_keywords(self, text: str) -> str:
		"""
		从文本中提取动作关键词，强化视频动态效果
		"""
		# 动作动词列表
		action_verbs = [
			"走", "跑", "跳", "飞", "转", "摇", "晃", "飘", "落", "升",
			"推", "拉", "开", "关", "举", "放", "拿", "抓", "扔", "接",
			"看", "望", "盯", "瞄", "眨", "笑", "哭", "叫", "喊", "说",
			"吹", "吸", "呼", "吐", "咬", "舔", "吞", "咽", "吃", "喝",
			"站", "坐", "躺", "蹲", "跪", "趴", "靠", "倚", "挂", "吊",
			"打", "踢", "砸", "撞", "碰", "触", "摸", "抚", "拍", "敲",
			"写", "画", "涂", "刻", "印", "盖", "贴", "撕", "剪", "切",
			"流", "滴", "洒", "泼", "溅", "喷", "射", "发", "出", "入",
			"动", "摆", "挥", "舞", "扭", "摇", "震", "颤", "抖", "晃",
			"变", "化", "换", "转", "改", "移", "迁", "搬", "挪", "移动",
			"闪", "现", "消", "散", "聚", "合", "分", "裂", "破", "碎",
			"亮", "暗", "明", "灭", "燃", "烧", "冒", "腾", "升起", "降落",
			"进", "出", "上", "下", "前", "后", "左", "右", "来", "去",
			"推开", "拉开", "打开", "关闭", "抬起", "放下", "睁开", "闭上",
			"转身", "回头", "低头", "抬头", "侧身", "弯腰", "起身", "坐下"
		]
		
		# 查找文本中的动作词
		found_actions = []
		for verb in action_verbs:
			if verb in text:
				# 找到动作词及其上下文
				index = text.find(verb)
				# 提取动作词前后的词语
				start = max(0, index - 3)
				end = min(len(text), index + len(verb) + 5)
				context = text[start:end]
				found_actions.append(context)
		
		# 如果找到动作，强化描述
		if found_actions:
			# 去重并组合
			unique_actions = list(dict.fromkeys(found_actions))
			return "，".join(unique_actions[:3])  # 最多保留3个动作描述
		
		return text
	
	def _on_copy_video_prompt(self) -> None:
		"""复制视频提示词到剪贴板"""
		try:
			text = self.video_prompt_text.get("1.0", END).strip()
			if text and text != "生成图片后，这里会自动显示适合即梦AI的视频提示词...":
				self.clipboard_clear()
				self.clipboard_append(text)
				self.status.set("✅ 视频提示词已复制到剪贴板，可以粘贴到即梦AI中使用")
				messagebox.showinfo("提示", "视频提示词已复制！\n\n请：\n1. 打开即梦AI\n2. 上传刚生成的图片作为首帧\n3. 粘贴提示词\n4. 生成5秒视频")
			else:
				messagebox.showwarning("提示", "请先生成图片，然后会自动生成视频提示词")
		except Exception as e:
			messagebox.showerror("错误", f"复制失败: {str(e)}")

