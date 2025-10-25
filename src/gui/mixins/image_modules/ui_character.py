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


class ImageUICharacterTabMixin:
	"""Image UI ui_character 功能"""
	
	def _build_character_tab(self) -> None:
		"""构建人物生成页面"""
		# 两列布局
		body = ttk.Frame(self.image_tab_character)
		body.pack(fill=BOTH, expand=True, padx=10, pady=10)
		left = ttk.Frame(body)
		left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
		
		# 右侧：使用Canvas实现滚动
		right_container = ttk.Frame(body)
		right_container.grid(row=0, column=1, sticky="nsew")
		
		# 创建Canvas和滚动条
		char_canvas = tk.Canvas(right_container, bg=Theme.SURFACE_DARK, highlightthickness=0)
		char_v_scroll = ttk.Scrollbar(right_container, orient="vertical", command=char_canvas.yview)
		char_canvas.configure(yscrollcommand=char_v_scroll.set)
		
		# 布局Canvas和滚动条
		char_canvas.pack(side=LEFT, fill=BOTH, expand=True)
		char_v_scroll.pack(side=RIGHT, fill=Y)
		
		# 创建可滚动的内容Frame
		right = ttk.Frame(char_canvas)
		char_canvas_window = char_canvas.create_window(0, 0, window=right, anchor="nw")
		
		# 绑定事件以更新滚动区域
		def _on_right_configure(event):
			char_canvas.configure(scrollregion=char_canvas.bbox("all"))
			# 设置canvas窗口宽度以匹配canvas宽度
			canvas_width = event.width
			char_canvas.itemconfig(char_canvas_window, width=canvas_width)
		
		def _on_canvas_configure(event):
			# 当canvas大小变化时，更新内部窗口宽度
			canvas_width = event.width
			char_canvas.itemconfig(char_canvas_window, width=canvas_width)
		
		right.bind("<Configure>", _on_right_configure)
		char_canvas.bind("<Configure>", _on_canvas_configure)
		
		# 绑定鼠标滚轮 - 改进版
		def _on_mousewheel(event):
			# macOS和Windows有不同的滚轮事件处理
			if event.num == 5 or event.delta < 0:
				char_canvas.yview_scroll(1, "units")
			elif event.num == 4 or event.delta > 0:
				char_canvas.yview_scroll(-1, "units")
		
		# 保存引用以便后续绑定滚轮
		self._char_scroll_canvas = char_canvas
		self._char_scroll_right_frame = right
		self._char_scroll_mousewheel_func = _on_mousewheel
		
		body.columnconfigure(0, weight=1)
		body.columnconfigure(1, weight=1)
		body.rowconfigure(0, weight=1)
		
		# 左侧：人物列表和操作
		grp_characters = ttk.LabelFrame(left, text="👥 故事人物列表", padding=(8, 5))
		grp_characters.pack(fill=BOTH, expand=True, padx=0, pady=(0, 8))
		
		# 提示信息
		tip_frame_main = tk.Frame(grp_characters, bg=Theme.BG_SECONDARY)
		tip_frame_main.pack(fill="x", padx=6, pady=(6, 8))
		
		tk.Label(tip_frame_main, text="📌 ", font=("", 10, "bold"), fg="#FF9800", bg=Theme.BG_SECONDARY).pack(side=LEFT)
		tk.Label(tip_frame_main, text="第一步：点击下方按钮提取人物，然后选择要生成照片的人物", 
				 font=("", 9), fg="#888888", bg=Theme.BG_SECONDARY).pack(side=LEFT)
		
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
										   command=self._on_extract_characters, width=15, style="Accent.TButton")
		self.char_btn_extract.pack(side=LEFT, padx=(0, 3))
		self.char_btn_refresh = ttk.Button(btn_frame, text="🔄 重新提取", 
										   command=self._on_extract_characters, width=12, state=DISABLED, style="TButton")
		self.char_btn_refresh.pack(side=LEFT, padx=(0, 3))
		
		# 第二行按钮
		btn_frame2 = ttk.Frame(grp_characters)
		btn_frame2.pack(fill="x", padx=6, pady=(0, 8))
		self.char_btn_edit_detail = ttk.Button(btn_frame2, text="✏️ 编辑人物详情", 
											   command=self._on_edit_character_detail, width=15, 
											   state=DISABLED, style="TButton")
		self.char_btn_edit_detail.pack(side=LEFT, padx=(0, 3))
		ttk.Label(btn_frame2, text="完善外观、服装等信息", font=("", 8), foreground="#888").pack(side=LEFT, padx=(5, 0))
		
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
											width=15, state=DISABLED, style="Accent.TButton")
		self.char_btn_gen_desc.pack(side=LEFT, padx=(0, 3))
		self.char_btn_copy_desc = ttk.Button(desc_btn_frame, text="📋 复制", 
											 command=self._on_copy_character_description,
											 width=10, state=DISABLED, style="TButton")
		self.char_btn_copy_desc.pack(side=LEFT, padx=(0, 3))
		
		# 右侧：生成参数和预览
		# 添加顶部提示
		tip_header = tk.Frame(right, bg="#1e3a5f", relief=tk.SOLID, borderwidth=1)
		tip_header.pack(fill="x", padx=0, pady=(0, 10))
		tk.Label(tip_header, text="🎨 ", font=("", 11, "bold"), fg="#4CAF50", bg="#1e3a5f").pack(side=LEFT, padx=(10, 0))
		tk.Label(tip_header, text="第二步：设置生成参数", font=("", 10, "bold"), fg="white", bg="#1e3a5f").pack(side=LEFT, padx=(0, 10), pady=8)
		
		grp_params = ttk.LabelFrame(right, text="🎨 第一步：基础设置", padding=(12, 8))
		grp_params.pack(fill="x", padx=0, pady=(0, 12))
		grp_params.columnconfigure(1, weight=1)
		
		# 图片类型/风格
		tk.Label(grp_params, text="图片类型:", font=("", 10)).grid(row=0, column=0, sticky="e", padx=(0, 8), pady=6)
		self.char_img_style = tk.StringVar(value="写实照片")
		self.char_combo_style = ttk.Combobox(grp_params, textvariable=self.char_img_style, font=("", 10),
											 values=("写实照片", "淘宝照片", "证件照", "日系动漫", "3D渲染", "水彩画", "油画", 
													 "中国风", "国风插画", "古风", "仙侠", "武侠"))
		self.char_combo_style.grid(row=0, column=1, sticky="we", padx=(0, 6), pady=6)
		
		# 分隔线
		separator1 = tk.Frame(grp_params, height=1, bg="#444444")
		separator1.grid(row=1, column=0, columnspan=2, sticky="ew", pady=10)
		
		# 第二步标题
		step2_label = tk.Label(grp_params, text="📐 第二步：视角选择", font=("", 10, "bold"), fg="#4CAF50")
		step2_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=0, pady=(8, 4))
		
		# 视角选择
		self.char_view_angle = tk.StringVar(value="front")
		view_frame = tk.Frame(grp_params, bg=Theme.BG_SECONDARY, relief=tk.SOLID, borderwidth=1)
		view_frame.grid(row=3, column=0, columnspan=2, sticky="we", padx=0, pady=6)
		
		angles = [("👤 正面", "front"), ("👥 侧面", "side"), ("🔙 背面", "back"), ("🔄 斜侧", "three-quarter")]
		for i, (label, value) in enumerate(angles):
			rb = tk.Radiobutton(view_frame, text=label, variable=self.char_view_angle, value=value,
							   bg=Theme.BG_SECONDARY, fg="white", selectcolor="#4CAF50", font=("", 10),
							   activebackground="#2b2b2b", activeforeground="#4CAF50",
							   indicatoron=0, width=12, relief=tk.FLAT, bd=2)
			rb.pack(side=LEFT, padx=2, pady=2, fill="x", expand=True)
		
		# 分隔线
		separator2 = tk.Frame(grp_params, height=1, bg="#444444")
		separator2.grid(row=4, column=0, columnspan=2, sticky="ew", pady=10)
		
		# 第三步标题
		step3_label = tk.Label(grp_params, text="😊 第三步：表情选择", font=("", 10, "bold"), fg="#FF9800")
		step3_label.grid(row=5, column=0, columnspan=2, sticky="w", padx=0, pady=(8, 4))
		
		# 表情选择
		self.char_expression = tk.StringVar(value="neutral")
		expr_frame = tk.Frame(grp_params, bg=Theme.BG_SECONDARY, relief=tk.SOLID, borderwidth=1)
		expr_frame.grid(row=6, column=0, columnspan=2, sticky="we", padx=0, pady=6)
		
		expressions = [
			("😐 中性", "neutral"),
			("😊 开心", "happy"),
			("😢 悲伤", "sad"),
			("😠 愤怒", "angry"),
			("😮 惊讶", "surprised")
		]
		
		for i, (label, value) in enumerate(expressions):
			rb = tk.Radiobutton(expr_frame, text=label, variable=self.char_expression, value=value,
							   bg=Theme.BG_SECONDARY, fg="white", selectcolor="#FF9800", font=("", 10),
							   activebackground="#2b2b2b", activeforeground="#FF9800",
							   indicatoron=0, width=10, relief=tk.FLAT, bd=2)
			rb.pack(side=LEFT, padx=2, pady=2, fill="x", expand=True)
		
		# 分隔线
		separator3 = tk.Frame(grp_params, height=1, bg="#444444")
		separator3.grid(row=7, column=0, columnspan=2, sticky="ew", pady=10)
		
		# 批量生成选项
		batch_title = tk.Label(grp_params, text="⚡ 批量生成选项", font=("", 10, "bold"), fg="#2196F3")
		batch_title.grid(row=8, column=0, columnspan=2, sticky="w", padx=0, pady=(8, 4))
		
		batch_frame = tk.Frame(grp_params, bg="#1e3a5f", relief=tk.SOLID, borderwidth=1)
		batch_frame.grid(row=9, column=0, columnspan=2, sticky="we", padx=0, pady=6)
		
		self.char_batch_generate = tk.BooleanVar(value=False)
		batch_angle_check = tk.Checkbutton(batch_frame, text="🎯 批量生成三视图（正面+侧面+背面）", 
										   variable=self.char_batch_generate,
										   bg="#1e3a5f", fg="#4CAF50", selectcolor="#2b2b2b", 
										   font=("", 10, "bold"), activebackground="#1e3a5f", activeforeground="#4CAF50")
		batch_angle_check.pack(anchor="w", pady=(8, 4), padx=10)
		
		self.char_batch_expressions = tk.BooleanVar(value=False)
		batch_expr_check = tk.Checkbutton(batch_frame, text="😊 批量生成多表情（中性+开心+悲伤+愤怒+惊讶）", 
										  variable=self.char_batch_expressions,
										  bg="#1e3a5f", fg="#FF9800", selectcolor="#2b2b2b", 
										  font=("", 10, "bold"), activebackground="#1e3a5f", activeforeground="#FF9800")
		batch_expr_check.pack(anchor="w", pady=(4, 8), padx=10)
		
		# 分隔线
		separator4 = tk.Frame(grp_params, height=1, bg="#444444")
		separator4.grid(row=10, column=0, columnspan=2, sticky="ew", pady=10)
		
		# 服装/造型变体
		variant_title = tk.Label(grp_params, text="👔 第四步：服装造型（可选）", font=("", 10, "bold"), fg="#9C27B0")
		variant_title.grid(row=11, column=0, columnspan=2, sticky="w", padx=0, pady=(8, 4))
		
		variant_frame = tk.Frame(grp_params, bg=Theme.BG_SECONDARY, relief=tk.SOLID, borderwidth=1)
		variant_frame.grid(row=12, column=0, columnspan=2, sticky="we", padx=0, pady=6)
		
		# 变体模式选择
		self.char_variant_mode = tk.StringVar(value="none")
		variant_mode_frame = tk.Frame(variant_frame, bg=Theme.BG_SECONDARY)
		variant_mode_frame.pack(fill="x", pady=(0, 5))
		
		tk.Radiobutton(variant_mode_frame, text="默认", variable=self.char_variant_mode, value="none",
					   bg=Theme.BG_SECONDARY, fg="white", selectcolor="#444444", font=("", 9)).pack(side=LEFT, padx=(0, 8))
		tk.Radiobutton(variant_mode_frame, text="预设变体", variable=self.char_variant_mode, value="preset",
					   bg=Theme.BG_SECONDARY, fg="white", selectcolor="#444444", font=("", 9)).pack(side=LEFT, padx=(0, 8))
		tk.Radiobutton(variant_mode_frame, text="自定义", variable=self.char_variant_mode, value="custom",
					   bg=Theme.BG_SECONDARY, fg="white", selectcolor="#444444", font=("", 9)).pack(side=LEFT)
		
		# 预设变体选择
		self.char_variant_preset = tk.StringVar(value="casual")
		preset_frame = tk.Frame(variant_frame, bg=Theme.BG_SECONDARY)
		preset_frame.pack(fill="x", pady=(0, 5))
		
		variants = [
			("👔 正装", "formal"),
			("👕 休闲", "casual"),
			("🏃 运动", "sport"),
			("🎭 古装", "traditional"),
			("🎨 艺术", "artistic"),
			("💼 职业", "professional")
		]
		
		for i, (label, value) in enumerate(variants):
			tk.Radiobutton(preset_frame, text=label, variable=self.char_variant_preset, value=value,
						   bg=Theme.BG_SECONDARY, fg="white", selectcolor="#444444", font=("", 8)).pack(side=LEFT, padx=(0, 5))
		
		# 自定义变体描述
		self.char_variant_custom = tk.Entry(variant_frame, font=("", 9), bg="#3c3c3c", fg="white", relief=tk.SOLID, borderwidth=1)
		self.char_variant_custom.pack(fill="x")
		self.char_variant_custom.insert(0, "例如：穿着白色婚纱、戴着黑框眼镜...")
		self.char_variant_custom.bind("<FocusIn>", lambda e: self.char_variant_custom.delete(0, tk.END) if self.char_variant_custom.get().startswith("例如") else None)
		
		# 提示信息移到variant_frame底部
		tip_variant = tk.Label(variant_frame, text="💡 提示：变体会改变服装/发型/配饰，但保持基本外貌特征", 
							   font=("", 9), fg="#FFA500", bg=Theme.BG_SECONDARY)
		tip_variant.pack(fill="x", pady=(5, 8), padx=10)
		
		# 分隔线
		separator5 = tk.Frame(grp_params, height=1, bg="#444444")
		separator5.grid(row=13, column=0, columnspan=2, sticky="ew", pady=10)
		
		# 额外描述
		extra_title = tk.Label(grp_params, text="✨ 第五步：额外细节（可选）", font=("", 10, "bold"), fg="#00BCD4")
		extra_title.grid(row=14, column=0, columnspan=2, sticky="w", padx=0, pady=(8, 4))
		
		self.char_txt_extra = tk.Text(grp_params, height=3, font=("", 10), 
									  wrap=tk.WORD, relief=tk.SOLID, borderwidth=1, bg=Theme.BG_SECONDARY, fg="white")
		self.char_txt_extra.grid(row=15, column=0, columnspan=2, sticky="we", padx=0, pady=6)
		
		tip_extra = tk.Label(grp_params, text="💡 可补充姿态、背景等细节（不包含服装和表情）", font=("", 9), fg="gray")
		tip_extra.grid(row=16, column=0, columnspan=2, sticky="w", padx=0)
		
		# 分隔线
		separator6 = tk.Frame(grp_params, height=1, bg="#444444")
		separator6.grid(row=17, column=0, columnspan=2, sticky="ew", pady=10)
		
		# 一致性级别选择
		consistency_title = tk.Label(grp_params, text="🎯 面部一致性级别（多角度生成时）", font=("", 10, "bold"), fg="#E91E63")
		consistency_title.grid(row=18, column=0, columnspan=2, sticky="w", padx=0, pady=(8, 4))
		
		self.char_consistency_level = tk.StringVar(value="high")
		consistency_frame = tk.Frame(grp_params, bg=Theme.BG_SECONDARY, relief=tk.SOLID, borderwidth=1)
		consistency_frame.grid(row=19, column=0, columnspan=2, sticky="we", padx=0, pady=6)
		
		consistency_options = [
			("🔥 最高 - 强力保持脸型五官", "high"),
			("⚡ 中等 - 平衡一致性", "medium"),
			("💨 较低 - 允许更多变化", "low")
		]
		
		for i, (label, value) in enumerate(consistency_options):
			rb = tk.Radiobutton(consistency_frame, text=label, variable=self.char_consistency_level, value=value,
							   bg=Theme.BG_SECONDARY, fg="white", selectcolor="#E91E63", font=("", 9),
							   activebackground="#2b2b2b", activeforeground="#E91E63",
							   indicatoron=0, width=18, relief=tk.FLAT, bd=2)
			rb.pack(side=LEFT, padx=2, pady=2, fill="x", expand=True)
		
		tip_consistency = tk.Label(grp_params, text="💡 推荐使用「最高」级别，确保瓜子脸不会变成方脸！", font=("", 9), fg="#FF9800")
		tip_consistency.grid(row=20, column=0, columnspan=2, sticky="w", padx=0)
		
		# 操作按钮 - 生成人物形象
		grp_actions = ttk.LabelFrame(right, text="🎨 第七步：生成人物形象", padding=(12, 10))
		grp_actions.pack(fill="x", padx=0, pady=(12, 12))
		
		# 生成类型选择
		type_frame = ttk.Frame(grp_actions)
		type_frame.pack(fill="x", padx=6, pady=(6, 3))
		
		ttk.Label(type_frame, text="生成类型：", font=("", 10, "bold")).pack(side=LEFT, padx=(0, 10))
		
		self.char_gen_type = tk.StringVar(value="standard")
		ttk.Radiobutton(type_frame, text="标准形象(1张)", variable=self.char_gen_type, value="standard").pack(side=LEFT, padx=5)
		ttk.Radiobutton(type_frame, text="表情库(7张)", variable=self.char_gen_type, value="expressions").pack(side=LEFT, padx=5)
		ttk.Radiobutton(type_frame, text="角度库(3张)", variable=self.char_gen_type, value="angles").pack(side=LEFT, padx=5)
		ttk.Radiobutton(type_frame, text="完整套装(11张)", variable=self.char_gen_type, value="full").pack(side=LEFT, padx=5)
		
		# 生成按钮行
		action_row = ttk.Frame(grp_actions)
		action_row.pack(fill="x", padx=6, pady=(6, 3))
		
		self.char_btn_gen_photo = ttk.Button(action_row, text="🎨 开始生成", 
											 command=self._on_generate_character_photo,
											 state=DISABLED, style="Accent.TButton")
		self.char_btn_gen_photo.pack(side=LEFT, padx=(0, 6), fill="x", expand=True)
		
		ttk.Button(action_row, text="📁 查看图片库", 
				   command=self._on_view_character_gallery,
				   style="TButton").pack(side=LEFT, fill="x", expand=True)
		
		# 第二行：保存和设定表
		action_row2 = ttk.Frame(grp_actions)
		action_row2.pack(fill="x", padx=6, pady=(3, 6))
		
		self.char_btn_save_photo = ttk.Button(action_row2, text="💾 保存当前", 
											  command=self._on_save_character_photo, 
											  state=DISABLED, style="TButton")
		self.char_btn_save_photo.pack(side=LEFT, padx=(0, 3), fill="x", expand=True)
		
		self.char_btn_generate_sheet = ttk.Button(action_row2, text="📋 生成设定表", 
												  command=self._on_generate_character_sheet,
												  state=DISABLED, style="TButton")
		self.char_btn_generate_sheet.pack(side=LEFT, fill="x", expand=True)
		
		# 预览区域
		grp_preview = ttk.LabelFrame(right, text="🖼️ 照片预览", padding=(12, 10))
		grp_preview.pack(fill=BOTH, expand=True, padx=0, pady=0)
		
		# 创建Canvas和滚动条
		preview_frame = ttk.Frame(grp_preview)
		preview_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
		
		v_scroll = ttk.Scrollbar(preview_frame, orient="vertical")
		h_scroll = ttk.Scrollbar(preview_frame, orient="horizontal")
		
		self.char_canvas = tk.Canvas(preview_frame, bg=Theme.BG_SECONDARY, 
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
		
		# 为照片预览Canvas绑定滚轮事件
		def _on_preview_mousewheel(event):
			"""照片预览区域的滚轮事件"""
			# macOS和Windows有不同的滚轮事件处理
			if event.num == 5 or event.delta < 0:
				self.char_canvas.yview_scroll(1, "units")
			elif event.num == 4 or event.delta > 0:
				self.char_canvas.yview_scroll(-1, "units")
		
		# 绑定滚轮事件到照片预览Canvas
		self.char_canvas.bind("<MouseWheel>", _on_preview_mousewheel)
		self.char_canvas.bind("<Button-4>", _on_preview_mousewheel)
		self.char_canvas.bind("<Button-5>", _on_preview_mousewheel)
		
		# 在UI完全构建后绑定滚轮事件
		def _bind_mousewheel_recursive(widget):
			"""递归绑定所有子控件的滚轮事件"""
			widget.bind("<MouseWheel>", self._char_scroll_mousewheel_func)
			widget.bind("<Button-4>", self._char_scroll_mousewheel_func)
			widget.bind("<Button-5>", self._char_scroll_mousewheel_func)
			try:
				for child in widget.winfo_children():
					_bind_mousewheel_recursive(child)
			except:
				pass
		
		# 延迟绑定，确保所有子控件已创建
		self.after(100, lambda: _bind_mousewheel_recursive(self._char_scroll_right_frame))
		# 也绑定到canvas
		self._char_scroll_canvas.bind("<MouseWheel>", self._char_scroll_mousewheel_func)
		self._char_scroll_canvas.bind("<Button-4>", self._char_scroll_mousewheel_func)
		self._char_scroll_canvas.bind("<Button-5>", self._char_scroll_mousewheel_func)
	
	
	