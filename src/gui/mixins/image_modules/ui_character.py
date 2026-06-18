"""Image UI构建"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, VERTICAL, Y, messagebox, filedialog
import tkinter as tk
from tkinter import ttk
import os
from PIL import Image, ImageTk
import logging

from src.clients.deepseek_client import DeepSeekClient
from src.clients.image_client import OpenAIImageClient
from src.utils.text import sanitize as _sanitize
from ...helpers.image_styles import IMAGE_TYPES, HUNYUAN_STYLE_MAP
from ...theme import Theme


logger = logging.getLogger(__name__)


class ImageUICharacterTabMixin:
	"""Image UI ui_character 功能"""
	
	def _build_character_tab(self) -> None:
		"""构建人物生成页面"""
		T = Theme
		bg_canvas = T.BG_SECONDARY
		bg_panel = T.BG_TERTIARY
		bg_surface = T.SURFACE
		bg_accent = T.BG_SELECTED
		text_primary = T.TEXT_PRIMARY
		text_secondary = T.TEXT_SECONDARY
		divider = T.DIVIDER
		ui_font = (T.FONT_FAMILY, T.FONT_SIZE_NORMAL)
		small_font = (T.FONT_FAMILY, T.FONT_SIZE_SMALL)
		title_font = (T.FONT_FAMILY, T.FONT_SIZE_NORMAL, "bold")
		option_font = (T.FONT_FAMILY, T.FONT_SIZE_NORMAL)
		hint_font = (T.FONT_FAMILY, T.FONT_SIZE_SMALL)

		def _option_grid(parent, options, variable, selectcolor, *, columns=3):
			for col in range(columns):
				parent.columnconfigure(col, weight=1, uniform=str(parent))
			for idx, (label, value) in enumerate(options):
				rb = tk.Radiobutton(
					parent,
					text=label,
					variable=variable,
					value=value,
					bg=bg_panel,
					fg=text_primary,
					selectcolor=selectcolor,
					font=option_font,
					activebackground=bg_panel,
					activeforeground=selectcolor,
					indicatoron=0,
					relief=tk.FLAT,
					bd=1,
					padx=8,
					pady=7,
					anchor="center",
					justify="center",
				)
				rb.grid(row=idx // columns, column=idx % columns, sticky="ew", padx=3, pady=3)

		# 两列布局
		body = ttk.Frame(self.image_tab_character)
		body.pack(fill=BOTH, expand=True, padx=10, pady=10)
		left_container = ttk.Frame(body)
		left_container.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

		left_canvas = tk.Canvas(left_container, bg=bg_canvas, highlightthickness=0)
		left_v_scroll = ttk.Scrollbar(left_container, orient="vertical", command=left_canvas.yview)
		left_canvas.configure(yscrollcommand=left_v_scroll.set)
		left_canvas.pack(side=LEFT, fill=BOTH, expand=True)
		left_v_scroll.pack(side=RIGHT, fill=Y)

		left = ttk.Frame(left_canvas)
		left_canvas_window = left_canvas.create_window(0, 0, window=left, anchor="nw")

		def _on_left_configure(event):
			left_canvas.configure(scrollregion=left_canvas.bbox("all"))
			left_canvas.itemconfig(left_canvas_window, width=event.width)

		def _on_left_canvas_configure(event):
			left_canvas.itemconfig(left_canvas_window, width=event.width)

		left.bind("<Configure>", _on_left_configure)
		left_canvas.bind("<Configure>", _on_left_canvas_configure)

		def _on_left_mousewheel(event):
			if event.num == 5 or event.delta < 0:
				left_canvas.yview_scroll(1, "units")
			elif event.num == 4 or event.delta > 0:
				left_canvas.yview_scroll(-1, "units")

		self._char_left_scroll_canvas = left_canvas
		self._char_left_scroll_frame = left
		self._char_left_scroll_mousewheel_func = _on_left_mousewheel
		
		# 右侧：使用Canvas实现滚动
		right_container = ttk.Frame(body)
		right_container.grid(row=0, column=1, sticky="nsew")
		
		# 创建Canvas和滚动条
		char_canvas = tk.Canvas(right_container, bg=bg_canvas, highlightthickness=0)
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
		tip_frame_main = tk.Frame(grp_characters, bg=bg_panel)
		tip_frame_main.pack(fill="x", padx=6, pady=(6, 8))
		
		tk.Label(tip_frame_main, text="📌 ", font=title_font, fg="#FF9800", bg=bg_panel).pack(side=LEFT)
		tk.Label(tip_frame_main, text="第一步：点击下方按钮提取人物，然后选择要生成照片的人物", 
				 font=small_font, fg=text_secondary, bg=bg_panel).pack(side=LEFT)
		
		info_frame = tk.Frame(grp_characters, bg=bg_accent, relief=tk.SOLID, borderwidth=1)
		info_frame.pack(fill="x", padx=6, pady=(0, 8))
		tk.Label(info_frame, text="💾 ", font=small_font, fg=T.SUCCESS, bg=bg_accent).pack(side=LEFT, padx=(6, 0))
		tk.Label(info_frame, text="照片自动保存到 ", font=small_font, fg=text_primary, bg=bg_accent).pack(side=LEFT)
		tk.Label(info_frame, text="当前项目/characters/", font=(T.FONT_FAMILY, T.FONT_SIZE_SMALL, "bold"), fg=T.SUCCESS, bg=bg_accent).pack(side=LEFT)
		tk.Label(info_frame, text=" 文件夹", font=small_font, fg=text_primary, bg=bg_accent).pack(side=LEFT, padx=(0, 6))
		
		# 按钮区域和模型选择
		btn_frame = ttk.Frame(grp_characters)
		btn_frame.pack(fill="x", padx=6, pady=(0, 8))
		
		# 第一行：提取按钮
		btn_row1 = ttk.Frame(btn_frame)
		btn_row1.pack(fill="x", pady=(0, 6))
		
		self.char_btn_extract = ttk.Button(btn_row1, text="🔍 提取故事人物", 
										   command=self._on_extract_characters, width=15)
		self.char_btn_extract.pack(side=LEFT, padx=(0, 3))
		self.char_btn_refresh = ttk.Button(btn_row1, text="🔄 重新提取", 
										   command=self._on_extract_characters, width=12, state=DISABLED)
		self.char_btn_refresh.pack(side=LEFT, padx=(0, 3))
		
		# 第二行：模型选择
		model_row = ttk.Frame(btn_frame)
		model_row.pack(fill="x")
		
		tk.Label(model_row, text="🤖 模型:", font=title_font, bg=bg_panel, fg=Theme.TEXT_PRIMARY).pack(side=LEFT, padx=(0, 6))
		self.char_model_var = tk.StringVar(value="claude-sonnet-4-5")
		self.combo_char_model = ttk.Combobox(model_row, textvariable=self.char_model_var, width=20,
											 values=["正在加载..."],
											 state="readonly", font=ui_font)
		self.combo_char_model.pack(side=LEFT, fill="x", expand=True)
		
		# Character photo generation API selector
		draw_api_row = ttk.Frame(btn_frame)
		draw_api_row.pack(fill="x", pady=(6, 0))
		tk.Label(draw_api_row, text="绘图API:", font=title_font, bg=bg_panel, fg=Theme.TEXT_PRIMARY).pack(side=LEFT, padx=(0, 6))
		if hasattr(self, 'img_api_providers') and self.img_api_providers:
			provider_names = list(self.img_api_providers.keys())
		elif hasattr(self, 'img_api_presets') and self.img_api_presets:
			provider_names = list(self.img_api_presets.keys())
		else:
			provider_names = []
		default_provider = ""
		if hasattr(self, 'quick_image_api'):
			default_provider = (self.quick_image_api.get() or "").strip()
		if not default_provider and hasattr(self, 'img_api_preset'):
			default_provider = (self.img_api_preset.get() or "").strip()
		if not default_provider and provider_names:
			default_provider = provider_names[0]
		if provider_names and default_provider not in provider_names:
			default_provider = provider_names[0]
		self.char_draw_api_var = tk.StringVar(value=default_provider)
		self.combo_char_draw_api = ttk.Combobox(
			draw_api_row,
			textvariable=self.char_draw_api_var,
			width=20,
			values=provider_names if provider_names else [""],
			state="readonly",
			font=ui_font,
		)
		self.combo_char_draw_api.pack(side=LEFT, fill="x", expand=True)
		self.combo_char_draw_api.bind("<<ComboboxSelected>>", self._on_character_draw_api_changed)
		tk.Label(
			btn_frame,
			text="图片模型请在 设置 -> 图片生成 API -> 模型 中选择并保存。",
			font=small_font,
			fg=text_secondary,
			bg=bg_panel,
			anchor="w",
		).pack(fill="x", pady=(4, 0))
		
		# 人物列表框（使用Listbox）
		list_frame = ttk.Frame(grp_characters)
		list_frame.pack(fill=BOTH, expand=True, padx=6, pady=(0, 6))
		
		# 添加滚动条
		scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
		self.char_listbox = tk.Listbox(
			list_frame,
			font=ui_font,
			yscrollcommand=scrollbar.set,
			relief=tk.SOLID,
			borderwidth=1,
			height=8,
			bg=bg_surface,
			fg=text_primary,
			selectbackground=T.PRIMARY,
			selectforeground=text_primary,
		)
		scrollbar.config(command=self.char_listbox.yview)
		
		self.char_listbox.pack(side=LEFT, fill=BOTH, expand=True)
		scrollbar.pack(side=RIGHT, fill="y")
		
		# 绑定选择事件
		self.char_listbox.bind("<<ListboxSelect>>", self._on_character_selected)
		
		# 人物外貌设计区域（角色DNA）
		grp_desc = ttk.LabelFrame(left, text="🧬 人物外貌设计 (角色DNA)", padding=(8, 5))
		grp_desc.pack(fill=BOTH, expand=True, padx=0, pady=0)
		
		# 特征描述文本框
		self.char_txt_desc = tk.Text(
			grp_desc,
			height=10,
			font=ui_font,
			wrap=tk.WORD,
			relief=tk.SOLID,
			borderwidth=1,
			bg=bg_surface,
			fg=text_primary,
			insertbackground=text_primary,
			selectbackground=T.PRIMARY,
			selectforeground=text_primary,
		)
		self.char_txt_desc.pack(fill=BOTH, expand=True, padx=6, pady=(6, 8))
		self.char_txt_desc.insert("1.0", "第二步：选择人物后，AI将根据角色设定创造性地设计外貌，并生成「角色DNA」用于保持一致性...")
		self.char_txt_desc.config(state=DISABLED)
		
		# 特征描述按钮
		desc_btn_frame = ttk.Frame(grp_desc)
		desc_btn_frame.pack(fill="x", padx=6, pady=(0, 6))
		self.char_btn_gen_desc = ttk.Button(desc_btn_frame, text="🧬 设计外貌", 
										    command=self._on_generate_character_description,
											width=15, state=DISABLED)
		self.char_btn_gen_desc.pack(side=LEFT, padx=(0, 3))
		self.char_btn_copy_desc = ttk.Button(desc_btn_frame, text="📋 复制", 
											 command=self._on_copy_character_description,
											 width=10, state=DISABLED)
		self.char_btn_copy_desc.pack(side=LEFT, padx=(0, 3))
		
		# 右侧：生成参数和预览
		# 添加顶部提示
		tip_header = tk.Frame(right, bg=bg_accent, relief=tk.SOLID, borderwidth=1)
		tip_header.pack(fill="x", padx=0, pady=(0, 10))
		tk.Label(tip_header, text="🎨 ", font=(T.FONT_FAMILY, T.FONT_SIZE_NORMAL, "bold"), fg=T.SUCCESS, bg=bg_accent).pack(side=LEFT, padx=(10, 0))
		tk.Label(tip_header, text="第二步：设置生成参数", font=title_font, fg=text_primary, bg=bg_accent).pack(side=LEFT, padx=(0, 10), pady=8)
		
		grp_params = ttk.LabelFrame(right, text="🎨 第一步：基础设置", padding=(12, 8))
		grp_params.pack(fill="x", padx=0, pady=(0, 12))
		grp_params.columnconfigure(1, weight=1)
		
		# 图片类型/风格
		tk.Label(grp_params, text="图片类型:", font=ui_font).grid(row=0, column=0, sticky="e", padx=(0, 8), pady=6)
		self.char_img_style = tk.StringVar(value="写实照片")
		self.char_combo_style = ttk.Combobox(grp_params, textvariable=self.char_img_style, font=ui_font,
											 values=("写实照片", "淘宝照片", "证件照", "日系动漫", "3D渲染", "水彩画", "油画", 
													 "中国风", "国风插画", "古风", "仙侠", "武侠"))
		self.char_combo_style.grid(row=0, column=1, sticky="we", padx=(0, 6), pady=6)
		
		# 分隔线
		separator1 = tk.Frame(grp_params, height=1, bg=divider)
		separator1.grid(row=1, column=0, columnspan=2, sticky="ew", pady=10)
		
		# 第二步标题
		step2_label = tk.Label(grp_params, text="📐 第二步：视角选择", font=title_font, fg="#4CAF50")
		step2_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=0, pady=(8, 4))
		
		# 视角选择
		self.char_view_angle = tk.StringVar(value="front")
		view_frame = tk.Frame(grp_params, bg=bg_panel, relief=tk.SOLID, borderwidth=1)
		view_frame.grid(row=3, column=0, columnspan=2, sticky="we", padx=0, pady=6)
		
		angles = [("👤 正面", "front"), ("👥 侧面", "side"), ("🔙 背面", "back"), ("🔄 斜侧", "three-quarter")]
		_option_grid(view_frame, angles, self.char_view_angle, "#4CAF50", columns=4)
		
		# 分隔线
		separator2 = tk.Frame(grp_params, height=1, bg=divider)
		separator2.grid(row=4, column=0, columnspan=2, sticky="ew", pady=10)
		
		# 第三步标题
		step3_label = tk.Label(grp_params, text="😊 第三步：表情选择", font=title_font, fg="#FF9800")
		step3_label.grid(row=5, column=0, columnspan=2, sticky="w", padx=0, pady=(8, 4))
		
		# 表情选择
		self.char_expression = tk.StringVar(value="neutral")
		expr_frame = tk.Frame(grp_params, bg=bg_panel, relief=tk.SOLID, borderwidth=1)
		expr_frame.grid(row=6, column=0, columnspan=2, sticky="we", padx=0, pady=6)
		
		expressions = [
			("😐 中性", "neutral"),
			("😊 开心", "happy"),
			("😢 悲伤", "sad"),
			("😠 愤怒", "angry"),
			("😮 惊讶", "surprised")
		]
		
		_option_grid(expr_frame, expressions, self.char_expression, "#FF9800", columns=5)
		
		# 分隔线
		separator3 = tk.Frame(grp_params, height=1, bg=divider)
		separator3.grid(row=7, column=0, columnspan=2, sticky="ew", pady=10)
		
		# 批量生成选项
		batch_title = tk.Label(grp_params, text="⚡ 批量生成选项", font=title_font, fg="#2196F3")
		batch_title.grid(row=8, column=0, columnspan=2, sticky="w", padx=0, pady=(8, 4))
		
		batch_frame = tk.Frame(grp_params, bg=bg_accent, relief=tk.SOLID, borderwidth=1)
		batch_frame.grid(row=9, column=0, columnspan=2, sticky="we", padx=0, pady=6)
		
		self.char_batch_generate = tk.BooleanVar(value=False)
		batch_angle_check = tk.Checkbutton(
			batch_frame,
			text="🎯 批量生成三视图（正面+侧面+背面）",
			variable=self.char_batch_generate,
			bg=bg_accent,
			fg="#4CAF50",
			selectcolor=bg_panel,
			font=title_font,
			activebackground=bg_accent,
			activeforeground="#4CAF50",
		)
		batch_angle_check.pack(anchor="w", pady=(10, 5), padx=14)
		
		self.char_batch_expressions = tk.BooleanVar(value=False)
		batch_expr_check = tk.Checkbutton(
			batch_frame,
			text="😊 批量生成多表情（中性+开心+悲伤+愤怒+惊讶）",
			variable=self.char_batch_expressions,
			bg=bg_accent,
			fg="#FF9800",
			selectcolor=bg_panel,
			font=title_font,
			activebackground=bg_accent,
			activeforeground="#FF9800",
		)
		batch_expr_check.pack(anchor="w", pady=(5, 10), padx=14)
		
		# 分隔线
		separator4 = tk.Frame(grp_params, height=1, bg=divider)
		separator4.grid(row=10, column=0, columnspan=2, sticky="ew", pady=10)
		
		# 服装/造型变体
		variant_title = tk.Label(grp_params, text="👔 第四步：服装造型（可选）", font=title_font, fg="#9C27B0")
		variant_title.grid(row=11, column=0, columnspan=2, sticky="w", padx=0, pady=(8, 4))
		
		variant_frame = tk.Frame(grp_params, bg=bg_panel, relief=tk.SOLID, borderwidth=1)
		variant_frame.grid(row=12, column=0, columnspan=2, sticky="we", padx=0, pady=6)
		
		# 变体模式选择
		self.char_variant_mode = tk.StringVar(value="none")
		variant_mode_frame = tk.Frame(variant_frame, bg=bg_panel)
		variant_mode_frame.pack(fill="x", pady=(8, 6), padx=8)
		
		tk.Radiobutton(variant_mode_frame, text="默认", variable=self.char_variant_mode, value="none",
					   bg=bg_panel, fg=text_primary, selectcolor=divider, font=option_font,
					   activebackground=bg_panel, activeforeground=text_primary, padx=4, pady=4).pack(side=LEFT, padx=(0, 14))
		tk.Radiobutton(variant_mode_frame, text="预设变体", variable=self.char_variant_mode, value="preset",
					   bg=bg_panel, fg=text_primary, selectcolor=divider, font=option_font,
					   activebackground=bg_panel, activeforeground=text_primary, padx=4, pady=4).pack(side=LEFT, padx=(0, 14))
		tk.Radiobutton(variant_mode_frame, text="自定义", variable=self.char_variant_mode, value="custom",
					   bg=bg_panel, fg=text_primary, selectcolor=divider, font=option_font,
					   activebackground=bg_panel, activeforeground=text_primary, padx=4, pady=4).pack(side=LEFT)
		
		# 预设变体选择
		self.char_variant_preset = tk.StringVar(value="casual")
		preset_frame = tk.Frame(variant_frame, bg=bg_panel)
		preset_frame.pack(fill="x", pady=(0, 8), padx=8)
		
		variants = [
			("👔 正装", "formal"),
			("👕 休闲", "casual"),
			("🏃 运动", "sport"),
			("🎭 古装", "traditional"),
			("🎨 艺术", "artistic"),
			("💼 职业", "professional")
		]
		
		_option_grid(preset_frame, variants, self.char_variant_preset, divider, columns=3)
		
		# 自定义变体描述
		self.char_variant_custom = tk.Entry(
			variant_frame,
			font=ui_font,
			bg=bg_surface,
			fg=text_primary,
			insertbackground=text_primary,
			relief=tk.SOLID,
			borderwidth=1,
		)
		self.char_variant_custom.pack(fill="x", padx=8, pady=(0, 4), ipady=4)
		self.char_variant_custom.insert(0, "例如：穿着白色婚纱、戴着黑框眼镜...")
		# 修复Entry颜色问题
		if hasattr(self, '_fix_entry_colors'):
			self._fix_entry_colors(self.char_variant_custom)
		self.char_variant_custom.bind("<FocusIn>", lambda e: self.char_variant_custom.delete(0, tk.END) if self.char_variant_custom.get().startswith("例如") else None)
		
		# 提示信息移到variant_frame底部
		tip_variant = tk.Label(
			variant_frame,
			text="💡 提示：变体会改变服装/发型/配饰，但保持基本外貌特征",
			font=hint_font,
			fg="#FFA500",
			bg=bg_panel,
		)
		tip_variant.pack(fill="x", pady=(5, 8), padx=10)
		
		# 分隔线
		separator5 = tk.Frame(grp_params, height=1, bg=divider)
		separator5.grid(row=13, column=0, columnspan=2, sticky="ew", pady=10)
		
		# 额外描述
		extra_title = tk.Label(grp_params, text="✨ 第五步：额外细节（可选）", font=title_font, fg="#00BCD4")
		extra_title.grid(row=14, column=0, columnspan=2, sticky="w", padx=0, pady=(8, 4))
		
		self.char_txt_extra = tk.Text(
			grp_params,
			height=3,
			font=ui_font,
			wrap=tk.WORD,
			relief=tk.SOLID,
			borderwidth=1,
			bg=bg_surface,
			fg=text_primary,
			insertbackground=text_primary,
			selectbackground=T.PRIMARY,
			selectforeground=text_primary,
		)
		self.char_txt_extra.grid(row=15, column=0, columnspan=2, sticky="we", padx=0, pady=6)
		
		tip_extra = tk.Label(grp_params, text="💡 可补充姿态、背景等细节（不包含服装和表情）", font=hint_font, fg=text_secondary)
		tip_extra.grid(row=16, column=0, columnspan=2, sticky="w", padx=0)
		
		# 分隔线
		separator6 = tk.Frame(grp_params, height=1, bg=divider)
		separator6.grid(row=17, column=0, columnspan=2, sticky="ew", pady=10)
		
		# 一致性级别选择
		consistency_title = tk.Label(grp_params, text="🎯 面部一致性级别（多角度生成时）", font=title_font, fg="#E91E63")
		consistency_title.grid(row=18, column=0, columnspan=2, sticky="w", padx=0, pady=(8, 4))
		
		self.char_consistency_level = tk.StringVar(value="high")
		consistency_frame = tk.Frame(grp_params, bg=bg_panel, relief=tk.SOLID, borderwidth=1)
		consistency_frame.grid(row=19, column=0, columnspan=2, sticky="we", padx=0, pady=6)
		
		consistency_options = [
			("🔥 最高 - 强力保持脸型五官", "high"),
			("⚡ 中等 - 平衡一致性", "medium"),
			("💨 较低 - 允许更多变化", "low")
		]
		
		_option_grid(consistency_frame, consistency_options, self.char_consistency_level, "#E91E63", columns=3)
		
		tip_consistency = tk.Label(grp_params, text="💡 推荐使用「最高」级别，确保瓜子脸不会变成方脸！", font=hint_font, fg="#FF9800")
		tip_consistency.grid(row=20, column=0, columnspan=2, sticky="w", padx=0)
		
		# 操作按钮
		grp_actions = ttk.LabelFrame(right, text="🚀 第七步：生成照片", padding=(12, 10))
		grp_actions.pack(fill="x", padx=0, pady=(12, 12))
		
		# 第一行：生成和保存
		action_row = ttk.Frame(grp_actions)
		action_row.pack(fill="x", padx=6, pady=(6, 3))
		self.char_btn_gen_photo = ttk.Button(action_row, text="🎨 生成人物照片", 
											 command=self._on_generate_character_photo,
											 state=DISABLED)
		self.char_btn_gen_photo.pack(side=LEFT, padx=(0, 6), fill="x", expand=True)
		self.char_btn_save_photo = ttk.Button(action_row, text="💾 保存照片", 
											  command=self._on_save_character_photo, 
											  state=DISABLED)
		self.char_btn_save_photo.pack(side=LEFT, fill="x", expand=True)
		
		# 第二行：一键三视图（新功能）
		action_row2 = ttk.Frame(grp_actions)
		action_row2.pack(fill="x", padx=6, pady=(0, 3))
		
		self.char_btn_turnaround = ttk.Button(action_row2, text="🎯 一键三视图（参考图）", 
											  command=self._on_generate_turnaround_sheet,
											  state=DISABLED)
		self.char_btn_turnaround.pack(side=LEFT, fill="x", expand=True)
		
		# 提示
		tk.Label(action_row2, text="← 用于保持一致性", font=hint_font, fg="#4CAF50").pack(side=LEFT, padx=(8, 0))
		
		# 第三行：查看照片管理和生成设定表
		action_row3 = ttk.Frame(grp_actions)
		action_row3.pack(fill="x", padx=6, pady=(0, 6))
		
		self.char_btn_view_gallery = ttk.Button(action_row3, text="🖼️ 查看所有照片", 
												command=self._on_view_character_gallery,
												state=DISABLED)
		self.char_btn_view_gallery.pack(side=LEFT, fill="x", expand=True, padx=(0, 3))
		
		self.char_btn_generate_sheet = ttk.Button(action_row3, text="📋 生成角色设定表", 
												  command=self._on_generate_character_sheet,
												  state=DISABLED)
		self.char_btn_generate_sheet.pack(side=LEFT, fill="x", expand=True, padx=(3, 0))
		
		# 预览区域
		grp_preview = ttk.LabelFrame(right, text="🖼️ 照片预览", padding=(12, 10))
		grp_preview.pack(fill=BOTH, expand=True, padx=0, pady=0)
		
		# 创建Canvas和滚动条
		preview_frame = ttk.Frame(grp_preview)
		preview_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
		
		v_scroll = ttk.Scrollbar(preview_frame, orient="vertical")
		h_scroll = ttk.Scrollbar(preview_frame, orient="horizontal")
		
		self.char_canvas = tk.Canvas(preview_frame, bg=bg_panel, 
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
		
		self.char_preview = ttk.Label(
			self.char_canvas,
			text="人物照片预览区\n\n生成人物照片后\n将显示在这里",
			font=ui_font,
			foreground=text_secondary,
			anchor="center",
			background=bg_panel,
		)
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
		def _bind_mousewheel_recursive(widget, handler):
			"""递归绑定所有子控件的滚轮事件"""
			widget.bind("<MouseWheel>", handler)
			widget.bind("<Button-4>", handler)
			widget.bind("<Button-5>", handler)
			try:
				for child in widget.winfo_children():
					_bind_mousewheel_recursive(child, handler)
			except Exception as e:
				logger.debug("Failed to bind mousewheel recursively on %s: %s", widget, e)
		
		# 延迟绑定，确保所有子控件已创建
		self.after(100, lambda: _bind_mousewheel_recursive(self._char_scroll_right_frame, self._char_scroll_mousewheel_func))
		self.after(100, lambda: _bind_mousewheel_recursive(self._char_left_scroll_frame, self._char_left_scroll_mousewheel_func))
		# 也绑定到canvas
		self._char_scroll_canvas.bind("<MouseWheel>", self._char_scroll_mousewheel_func)
		self._char_scroll_canvas.bind("<Button-4>", self._char_scroll_mousewheel_func)
		self._char_scroll_canvas.bind("<Button-5>", self._char_scroll_mousewheel_func)
		self._char_left_scroll_canvas.bind("<MouseWheel>", self._char_left_scroll_mousewheel_func)
		self._char_left_scroll_canvas.bind("<Button-4>", self._char_left_scroll_mousewheel_func)
		self._char_left_scroll_canvas.bind("<Button-5>", self._char_left_scroll_mousewheel_func)

	def _on_character_draw_api_changed(self, _event=None) -> None:
		"""Sync runtime image API when the character-tab image provider changes."""
		provider_name = ""
		if hasattr(self, 'char_draw_api_var'):
			provider_name = (self.char_draw_api_var.get() or "").strip()
		if not provider_name:
			return

		try:
			if hasattr(self, 'quick_image_api'):
				self.quick_image_api.set(provider_name)
			if hasattr(self, 'img_api_preset'):
				self.img_api_preset.set(provider_name)
			if hasattr(self, '_sync_img_runtime_from_config'):
				self._sync_img_runtime_from_config(provider_name)
			if hasattr(self, 'status'):
				current_model = self.img_model.get().strip() if hasattr(self, 'img_model') else ""
				model_hint = f" ({current_model})" if current_model else ""
				self.status.set(f"已切换绘图API: {provider_name}{model_hint}")
		except Exception as e:
			logger.debug("failed to switch character draw api: %s", e)
