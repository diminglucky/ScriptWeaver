"""Image UI构建"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, VERTICAL, Y, messagebox, filedialog
import tkinter as tk
from tkinter import ttk
import os
from PIL import Image, ImageTk

from src.clients.deepseek_client import DeepSeekClient
from src.clients.image_client import OpenAIImageClient
from src.utils.text import sanitize as _sanitize
from ...helpers.image_styles import IMAGE_TYPES, HUNYUAN_STYLE_MAP
from ...theme import Theme


class ImageUICreateTabMixin:
	"""Image UI ui_create 功能"""
	
	def _build_image_create_tab(self) -> None:
		"""构建图片创作页面"""
		T = Theme
		bg_panel = T.BG_TERTIARY
		bg_surface = T.SURFACE
		text_primary = T.TEXT_PRIMARY
		text_secondary = T.TEXT_SECONDARY
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
		self.img_btn_recommend = ttk.Button(rowf, text="🤖 智能推荐", command=self._on_recommend_video_mode, width=14, takefocus=False)
		self.img_btn_recommend.pack(side=LEFT, padx=(0, 4))
		self.img_btn_director = ttk.Button(rowf, text="🎞️ 导演脚本包", command=self._on_generate_director_package, width=16, takefocus=False)
		self.img_btn_director.pack(side=LEFT, padx=(0, 4))
		self.img_btn_extract_brief = ttk.Button(rowf, text="🎬 简短(8-12秒)", command=lambda: self._on_img_extract_shots(mode="brief"), width=16, takefocus=False)
		self.img_btn_extract_brief.pack(side=LEFT, padx=(0, 4))
		self.img_btn_extract_video = ttk.Button(rowf, text="🎬 平衡(15-25秒)", command=lambda: self._on_img_extract_shots(mode="video"), width=17, takefocus=False)
		self.img_btn_extract_video.pack(side=LEFT, padx=(0, 4))
		self.img_btn_extract_normal = ttk.Button(rowf, text="🎬 标准(15-22秒)", command=lambda: self._on_img_extract_shots(mode="normal"), width=17, takefocus=False)
		self.img_btn_extract_normal.pack(side=LEFT, padx=(0, 4))
		self.img_btn_extract_detailed = ttk.Button(rowf, text="🎬 精细(25-40秒)", command=lambda: self._on_img_extract_shots(mode="detailed"), width=17, takefocus=False)
		self.img_btn_extract_detailed.pack(side=LEFT, padx=(0, 4))
		
		# 使用Listbox显示分镜列表
		shots_list_frame = tk.Frame(grp_shots, bg=bg_panel)
		shots_list_frame.pack(fill="both", expand=True, padx=6, pady=(0, 6))
		
		# 添加滚动条
		shots_scrollbar = ttk.Scrollbar(shots_list_frame, orient="vertical")
		self.shots_listbox = tk.Listbox(
			shots_list_frame,
			font=("", 10),
			yscrollcommand=shots_scrollbar.set,
			relief=tk.SOLID,
			borderwidth=1,
			height=8,
			bg=bg_surface,
			fg=text_primary,
			selectbackground=T.PRIMARY,
			selectforeground=text_primary,
		)
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
		# 使用配置文件中的图片类型列表
		self.combo_img_type = ttk.Combobox(grp_ctx_add, textvariable=self.img_type, font=("", 10), width=20,
										   values=IMAGE_TYPES)
		self.combo_img_type.grid(row=0, column=1, sticky="we", padx=(0, 6), pady=6)
		# 添加提示文字
		tk.Label(grp_ctx_add, text="（可手动输入自定义类型）", font=("", 8), fg=text_secondary).grid(row=0, column=2, sticky="w", padx=4)
		
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
		tab_img_desc = tk.Frame(prompt_notebook, bg=bg_panel)
		prompt_notebook.add(tab_img_desc, text="  💬 图片描述  ")
		
		# 提示词输入区域（带✨补全按钮）
		prompt_input_frame = tk.Frame(tab_img_desc, bg=bg_panel)
		prompt_input_frame.pack(fill="both", expand=True, padx=6, pady=(6, 8))
		
		self.img_txt_prompt_cn = tk.Text(
			prompt_input_frame,
			height=10,
			font=("", 10),
			wrap=tk.WORD,
			relief=tk.SOLID,
			borderwidth=1,
			bg=bg_surface,
			fg=text_primary,
			insertbackground=text_primary,
			selectbackground=T.PRIMARY,
			selectforeground=text_primary,
		)
		self.img_txt_prompt_cn.pack(side=LEFT, fill="both", expand=True)
		
		# ✨ AI补全按钮（竖排在右侧）
		enhance_frame = tk.Frame(prompt_input_frame, bg=bg_panel)
		enhance_frame.pack(side=RIGHT, fill="y", padx=(4, 0))
		
		self.btn_enhance_prompt = tk.Button(
			enhance_frame, text="✨", font=("", 14), 
			command=self._on_enhance_prompt,
			bg="#4CAF50", fg="white", relief=tk.FLAT,
			width=2, height=1, cursor="hand2"
		)
		self.btn_enhance_prompt.pack(pady=(0, 4))
		
		# 添加提示标签
		tk.Label(enhance_frame, text="AI\n补全", font=("", 8), bg=bg_panel, fg=text_secondary).pack()
		
		rowp = ttk.Frame(tab_img_desc)
		rowp.pack(fill="x", padx=6, pady=(0, 6))
		self.img_btn_build_from_shot = ttk.Button(rowp, text="✨ 从当前分镜生成", command=self._on_img_prompt_from_current_shot, width=20)
		self.img_btn_build_from_shot.pack(side=LEFT, padx=(0, 3))
		self.img_btn_copy = ttk.Button(rowp, text="📋 复制", command=self._on_copy_img_prompt, width=10)
		self.img_btn_copy.pack(side=LEFT, padx=3)
		self.img_btn_clear = ttk.Button(rowp, text="🗑️ 清空", command=self._on_clear_img_prompt, width=10)
		self.img_btn_clear.pack(side=LEFT, padx=3)
		
		# 第二个标签页：即梦AI视频提示词
		tab_video_prompt = tk.Frame(prompt_notebook, bg=bg_panel)
		prompt_notebook.add(tab_video_prompt, text="  🎬 即梦AI提示词  ")
		
		# 视频提示词文本框
		self.video_prompt_text = tk.Text(
			tab_video_prompt,
			height=10,
			font=("", 10),
			wrap=tk.WORD,
			relief=tk.SOLID,
			borderwidth=1,
			bg=bg_surface,
			fg=text_primary,
			insertbackground=text_primary,
			selectbackground=T.PRIMARY,
			selectforeground=text_primary,
		)
		self.video_prompt_text.pack(fill="both", expand=True, padx=6, pady=(0, 8))
		self.video_prompt_text.insert("1.0", "生成图片后，这里会自动显示适合即梦AI的视频提示词...")
		self.video_prompt_text.config(state=DISABLED)
		
		# 视频操作按钮
		video_btn_frame = ttk.Frame(tab_video_prompt)
		video_btn_frame.pack(fill="x", padx=6, pady=(0, 6))
		
		self.video_btn_copy = ttk.Button(video_btn_frame, text="📋 复制提示词", 
										  command=self._on_copy_video_prompt, width=15)
		self.video_btn_copy.pack(side=LEFT, padx=(0, 4))
		
		self.video_btn_export = ttk.Button(video_btn_frame, text="📦 导出视频工作流", 
										   command=self._export_video_workflow, width=18)
		self.video_btn_export.pack(side=LEFT)
		
		# 提示
		tk.Label(video_btn_frame, text="← 导出完整制作资料", font=("", 9), fg=text_secondary).pack(side=LEFT, padx=(8, 0))

		# Right: 参考人物选择（移到这里，更显眼）
		grp_ref_characters = ttk.LabelFrame(right, text="🎭 参考人物", padding=(8, 5))
		grp_ref_characters.pack(fill="both", expand=False, padx=0, pady=(0, 8))
		
		# 使用Listbox支持多选
		ref_list_frame = tk.Frame(grp_ref_characters, bg=bg_panel)
		ref_list_frame.pack(fill="both", expand=True, padx=6, pady=6)
		
		self.ref_character_listbox = tk.Listbox(
			ref_list_frame,
			height=8,
			font=("", 10),
			selectmode=tk.MULTIPLE,
			exportselection=False,
			bg=bg_surface,
			fg=text_primary,
			selectbackground=T.PRIMARY,
			selectforeground=text_primary,
			relief=tk.SOLID,
			borderwidth=1,
		)
		self.ref_character_listbox.pack(side=LEFT, fill=BOTH, expand=True)
		
		ref_scrollbar = ttk.Scrollbar(ref_list_frame, orient=VERTICAL, command=self.ref_character_listbox.yview)
		ref_scrollbar.pack(side=RIGHT, fill=Y)
		self.ref_character_listbox.config(yscrollcommand=ref_scrollbar.set)

		grp_actions = ttk.LabelFrame(right, text="🚀 操作", padding=(8, 5))
		grp_actions.pack(fill="x", padx=0, pady=(0, 8))
		
		# 第一行：单张图片操作
		action_row = ttk.Frame(grp_actions)
		action_row.pack(fill="x", padx=6, pady=(6, 3))
		action_row.columnconfigure(0, weight=1)
		action_row.columnconfigure(1, weight=1)
		action_row.columnconfigure(2, weight=1)
		
		# 预览提示词按钮
		self.img_btn_preview = ttk.Button(action_row, text="👁️ 预览", command=self._on_preview_prompt)
		self.img_btn_preview.grid(row=0, column=0, padx=(0, 3), sticky="ew")
		
		self.img_btn_gen = ttk.Button(action_row, text="🎨 生成图片", command=self._on_img_generate)
		self.img_btn_gen.grid(row=0, column=1, padx=3, sticky="ew")
		self.img_btn_save = ttk.Button(action_row, text="💾 保存", command=self._on_img_save, state=DISABLED)
		self.img_btn_save.grid(row=0, column=2, padx=(3, 0), sticky="ew")
		
		# 第二行：批量操作（新功能）
		batch_row = ttk.Frame(grp_actions)
		batch_row.pack(fill="x", padx=6, pady=(3, 6))
		
		self.btn_batch_generate = ttk.Button(
			batch_row, 
			text="🚀 批量生成所有分镜", 
			command=self._on_batch_generate_all_shots
		)
		self.btn_batch_generate.pack(fill="x")
		
		# 提示标签
		tk.Label(
			batch_row,
			text="💡 使用角色三视图作为参考，保持人物一致性",
			font=("", 9),
			fg=text_secondary,
		).pack(anchor="w", pady=(4, 0))

		grp_preview = ttk.LabelFrame(right, text="🖼️ 预览", padding=(8, 5))
		grp_preview.pack(fill=BOTH, expand=True, padx=0, pady=0)
		
		# 创建Canvas和滚动条用于图片预览
		preview_frame = ttk.Frame(grp_preview)
		preview_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
		
		# 创建垂直和水平滚动条
		v_scroll = ttk.Scrollbar(preview_frame, orient="vertical")
		h_scroll = ttk.Scrollbar(preview_frame, orient="horizontal")
		
		# 创建Canvas
		self.img_canvas = tk.Canvas(preview_frame, bg=bg_panel, 
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
		self.img_preview = ttk.Label(
			self.img_canvas,
			text="图片预览区\n\n点击\"生成图片\"后\n图片将显示在这里",
			font=("", 10),
			foreground=text_secondary,
			anchor="center",
			background=bg_panel,
		)
		self.img_canvas_window = self.img_canvas.create_window(0, 0, window=self.img_preview, anchor="nw")
		
		# 绑定Canvas大小变化事件，自动调整图片显示
		self.img_canvas.bind('<Configure>', self._on_canvas_configure)
	
	
	
