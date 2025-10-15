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


class ImageUICreateTabMixin:
	"""Image UI ui_create 功能"""
	
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
		# 使用配置文件中的图片类型列表
		self.combo_img_type = ttk.Combobox(grp_ctx_add, textvariable=self.img_type, font=("", 10), width=20,
										   values=IMAGE_TYPES)
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
	
	
	