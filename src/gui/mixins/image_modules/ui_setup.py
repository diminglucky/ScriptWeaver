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


class ImageUISetupTabMixin:
	"""Image UI ui_setup 功能"""
	
	def _build_image_setup_tab(self) -> None:
		"""构建图片API配置页面"""
		# 创建Canvas和滚动条来支持内容滚动
		from ...theme import Theme
		canvas = tk.Canvas(self.image_tab_setup, bg=Theme.BG_SECONDARY, highlightthickness=0)
		scrollbar = ttk.Scrollbar(self.image_tab_setup, orient="vertical", command=canvas.yview)
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
		usage_frame = tk.Frame(grp_api, bg=Theme.BG_SECONDARY)
		usage_frame.grid(row=0, column=0, columnspan=6, sticky="w", padx=6, pady=(4, 8))
		tk.Label(usage_frame, text="📌 用途：", fg="#FF9800", font=("", 9, "bold"), bg=Theme.BG_SECONDARY).pack(side=LEFT)
		tk.Label(usage_frame, text="分镜图片生成", fg=Theme.TEXT_SECONDARY, font=("", 9), bg=Theme.BG_SECONDARY).pack(side=LEFT, padx=(0, 3))
		tk.Label(usage_frame, text="•", fg=Theme.TEXT_SECONDARY, font=("", 9), bg=Theme.BG_SECONDARY).pack(side=LEFT)
		tk.Label(usage_frame, text="人物肖像生成", fg="#4CAF50", font=("", 9, "bold"), bg=Theme.BG_SECONDARY).pack(side=LEFT, padx=3)
		
		# API预设下拉框
		tk.Label(grp_api, text="API预设:").grid(row=1, column=0, sticky="e", padx=6, pady=4)
		self.img_api_preset = tk.StringVar(value="OpenAI (DALL-E)")
		self.img_api_presets = {
			"本地 Stable Diffusion": {
				"base_url": os.getenv("SD_BASE_URL", "http://localhost:7860"),
				"model": "sd-local",
				"key": "",
				"provider": "sd"
			},
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
		
		tk.Label(grp_api, text="提示: 可保存/删除自定义预设", fg=Theme.TEXT_SECONDARY, font=("", 9)).grid(row=1, column=4, sticky="w", padx=6)

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
		# 使用可编辑的下拉框：当为本地SD时将切换为只读并填充模型列表
		self.combo_img_model = ttk.Combobox(grp_api, textvariable=self.img_model, width=25)
		self.combo_img_model.grid(row=5, column=1, sticky="we", padx=6)
		self.combo_img_model.bind("<<ComboboxSelected>>", lambda e: self._on_sd_model_selected())
		tk.Button(grp_api, text="保存配置", command=self.save_img_api_config).grid(row=5, column=2, padx=6)
		tk.Button(grp_api, text="加载配置", command=self.load_img_api_config).grid(row=5, column=3, padx=6, sticky="w")
		# API测试按钮 - 与加载配置同行
		tk.Button(grp_api, text="API测试", command=self.on_test_image_api).grid(row=5, column=4, padx=6, sticky="w")
		# 刷新本地SD模型列表
		tk.Button(grp_api, text="刷新模型", command=self._load_sd_models).grid(row=5, column=5, padx=6, sticky="w")
		
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
		hint_frame = tk.Frame(grp_params, bg=Theme.BG_SECONDARY)
		hint_frame.grid(row=1, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 4))
		tk.Label(hint_frame, text="方形: ", fg=Theme.TEXT_SECONDARY, font=("", 9), bg=Theme.BG_SECONDARY).pack(side=LEFT)
		tk.Label(hint_frame, text="256x256, 512x512, 768x768, 1024x1024", fg="#90CAF9", font=("", 9), bg=Theme.BG_SECONDARY).pack(side=LEFT)
		
		hint_frame2 = tk.Frame(grp_params, bg=Theme.BG_SECONDARY)
		hint_frame2.grid(row=2, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 4))
		tk.Label(hint_frame2, text="竖版: ", fg=Theme.TEXT_SECONDARY, font=("", 9), bg=Theme.BG_SECONDARY).pack(side=LEFT)
		tk.Label(hint_frame2, text="1024x1792, 360x640, 720x1280, 1080x1920", fg="#A5D6A7", font=("", 9), bg=Theme.BG_SECONDARY).pack(side=LEFT)
		
		hint_frame3 = tk.Frame(grp_params, bg=Theme.BG_SECONDARY)
		hint_frame3.grid(row=3, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 6))
		tk.Label(hint_frame3, text="横版: ", fg=Theme.TEXT_SECONDARY, font=("", 9), bg=Theme.BG_SECONDARY).pack(side=LEFT)
		tk.Label(hint_frame3, text="1792x1024, 640x360, 1280x720, 1920x1080", fg="#FFCC80", font=("", 9), bg=Theme.BG_SECONDARY).pack(side=LEFT)
		
		# ========= Stable Diffusion 专用配置（仅在选择SD时显示）=========
		self.grp_sd_params = ttk.LabelFrame(scrollable_frame, text="⚙️ Stable Diffusion 专用配置")
		self.grp_sd_params.pack(fill="x", padx=15, pady=8)
		self.grp_sd_params.columnconfigure(1, weight=1)
		
		# 采样器（Sampler）
		tk.Label(self.grp_sd_params, text="采样器 (Sampler):").grid(row=0, column=0, sticky="e", padx=6, pady=4)
		self.sd_sampler = tk.StringVar(value="Euler a")
		self.combo_sd_sampler = ttk.Combobox(self.grp_sd_params, textvariable=self.sd_sampler,
											  values=[
												  "Euler a", "Euler", "LMS", "Heun", "DPM2", "DPM2 a",
												  "DPM++ 2S a", "DPM++ 2M", "DPM++ SDE", "DPM++ 2M SDE",
												  "DPM++ 2M Karras", "DPM++ SDE Karras", "DPM fast",
												  "LMS Karras", "DPM2 Karras", "DPM2 a Karras",
												  "DDIM", "PLMS"
											  ],
											  width=20, state="readonly")
		self.combo_sd_sampler.grid(row=0, column=1, sticky="w", padx=6, pady=4)
		tk.Label(self.grp_sd_params, text="影响生成速度和质量，推荐：Euler a / DPM++ 2M Karras",
				 fg=Theme.TEXT_SECONDARY, font=("", 9)).grid(row=0, column=2, columnspan=2, sticky="w", padx=6)
		
		# 采样步数（Steps）
		tk.Label(self.grp_sd_params, text="采样步数 (Steps):").grid(row=1, column=0, sticky="e", padx=6, pady=4)
		self.sd_steps = tk.IntVar(value=25)
		self.scale_sd_steps = tk.Scale(self.grp_sd_params, variable=self.sd_steps, from_=10, to=150,
									   orient="horizontal", length=200, showvalue=True)
		self.scale_sd_steps.grid(row=1, column=1, sticky="w", padx=6, pady=4)
		tk.Label(self.grp_sd_params, text="步数越高质量越好但速度越慢，推荐：20-30",
				 fg=Theme.TEXT_SECONDARY, font=("", 9)).grid(row=1, column=2, columnspan=2, sticky="w", padx=6)
		
		# CFG Scale
		tk.Label(self.grp_sd_params, text="CFG Scale:").grid(row=2, column=0, sticky="e", padx=6, pady=4)
		self.sd_cfg_scale = tk.DoubleVar(value=8.0)
		self.scale_sd_cfg = tk.Scale(self.grp_sd_params, variable=self.sd_cfg_scale, from_=1.0, to=30.0,
									 orient="horizontal", length=200, showvalue=True, resolution=0.5)
		self.scale_sd_cfg.grid(row=2, column=1, sticky="w", padx=6, pady=4)
		tk.Label(self.grp_sd_params, text="提示词遵循程度，越高越遵循提示词，推荐：7-12",
				 fg=Theme.TEXT_SECONDARY, font=("", 9)).grid(row=2, column=2, columnspan=2, sticky="w", padx=6)
		
		# 随机种子（Seed）
		tk.Label(self.grp_sd_params, text="随机种子 (Seed):").grid(row=3, column=0, sticky="e", padx=6, pady=4)
		self.sd_seed = tk.IntVar(value=-1)
		self.entry_sd_seed = tk.Entry(self.grp_sd_params, textvariable=self.sd_seed, width=15)
		self.entry_sd_seed.grid(row=3, column=1, sticky="w", padx=6, pady=4)
		tk.Label(self.grp_sd_params, text="-1 为随机，固定值可复现相同图片",
				 fg=Theme.TEXT_SECONDARY, font=("", 9)).grid(row=3, column=2, columnspan=2, sticky="w", padx=6)
		
		# 批次大小（Batch Size）- 强制固定为1，不可修改
		tk.Label(self.grp_sd_params, text="批次大小:").grid(row=4, column=0, sticky="e", padx=6, pady=4)
		self.sd_batch_size = tk.IntVar(value=1)
		tk.Label(self.grp_sd_params, text="1 (固定)", 
				 font=("", 10, "bold"), fg="#4CAF50").grid(row=4, column=1, sticky="w", padx=6, pady=4)
		tk.Label(self.grp_sd_params, text="为确保单人肖像生成，批次大小已固定为1",
				 fg=Theme.TEXT_SECONDARY, font=("", 9)).grid(row=4, column=2, columnspan=2, sticky="w", padx=6)
		
		# 降噪强度（Denoising Strength，仅img2img）
		tk.Label(self.grp_sd_params, text="降噪强度 (img2img):").grid(row=5, column=0, sticky="e", padx=6, pady=4)
		self.sd_denoising = tk.DoubleVar(value=0.4)
		self.scale_sd_denoising = tk.Scale(self.grp_sd_params, variable=self.sd_denoising, from_=0.0, to=1.0,
										   orient="horizontal", length=200, showvalue=True, resolution=0.05)
		self.scale_sd_denoising.grid(row=5, column=1, sticky="w", padx=6, pady=4)
		tk.Label(self.grp_sd_params, text="图生图时的变化程度，越高变化越大，推荐：0.3-0.5",
				 fg=Theme.TEXT_SECONDARY, font=("", 9)).grid(row=5, column=2, columnspan=2, sticky="w", padx=6)
		
		# VAE 选择
		tk.Label(self.grp_sd_params, text="VAE:").grid(row=6, column=0, sticky="e", padx=6, pady=4)
		self.sd_vae = tk.StringVar(value="Automatic")
		self.combo_sd_vae = ttk.Combobox(self.grp_sd_params, textvariable=self.sd_vae,
										 values=["Automatic", "None"],  # 会在加载模型时更新
										 width=25, state="readonly")
		self.combo_sd_vae.grid(row=6, column=1, sticky="w", padx=6, pady=4)
		tk.Button(self.grp_sd_params, text="刷新VAE列表", command=self._load_sd_vaes,
				  font=("", 9), bg="#607D8B", fg="white", relief=tk.FLAT, padx=8, pady=3).grid(row=6, column=2, padx=6, sticky="w")
		
		# CLIP Skip
		tk.Label(self.grp_sd_params, text="CLIP Skip:").grid(row=7, column=0, sticky="e", padx=6, pady=4)
		self.sd_clip_skip = tk.IntVar(value=1)
		self.scale_sd_clip = tk.Scale(self.grp_sd_params, variable=self.sd_clip_skip, from_=1, to=12,
									  orient="horizontal", length=200, showvalue=True)
		self.scale_sd_clip.grid(row=7, column=1, sticky="w", padx=6, pady=4)
		tk.Label(self.grp_sd_params, text="CLIP层跳过，通常保持1或2",
				 fg=Theme.TEXT_SECONDARY, font=("", 9)).grid(row=7, column=2, columnspan=2, sticky="w", padx=6)
		
		# 默认隐藏SD配置区域（当选择非SD API时）
		self.grp_sd_params.pack_forget()
		
		# 辅助功能API配置（分镜头生成和图片描述生成）
		grp_assist_api = ttk.LabelFrame(scrollable_frame, text="🤖 辅助功能 API 配置（使用聊天模型）")
		grp_assist_api.pack(fill="x", padx=15, pady=8)
		grp_assist_api.columnconfigure(1, weight=1)
		
		# 说明文字
		tk.Label(grp_assist_api, text="选择用于生成分镜头、图片描述和人物肖像的聊天API（使用故事生成页面配置的API Key）", 
				 fg=Theme.TEXT_SECONDARY, font=("", 9)).grid(row=0, column=0, columnspan=2, sticky="w", padx=6, pady=(4, 8))
		
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
		api_desc_frame = tk.Frame(grp_assist_api, bg=Theme.BG_SECONDARY)
		api_desc_frame.grid(row=3, column=1, sticky="w", padx=6, pady=4)
		tk.Label(api_desc_frame, text="使用", fg=Theme.TEXT_SECONDARY, font=("", 9), bg=Theme.BG_SECONDARY).pack(side=LEFT)
		tk.Label(api_desc_frame, text="上方「图片生成 API 配置」", fg="#4CAF50", font=("", 9, "bold"), bg=Theme.BG_SECONDARY).pack(side=LEFT)
		tk.Label(api_desc_frame, text="中的图片API", fg=Theme.TEXT_SECONDARY, font=("", 9), bg=Theme.BG_SECONDARY).pack(side=LEFT)
		
		# 保存按钮
		btn_save_assist_api = tk.Button(grp_assist_api, text="💾 保存辅助API配置", command=self._save_assist_api_config,
									   font=("", 9), bg="#4CAF50", fg="white", relief=tk.FLAT, padx=12, pady=4, cursor="hand2")
		btn_save_assist_api.grid(row=4, column=0, columnspan=2, padx=6, pady=(8, 4), sticky="we")
		
		# 测试日志输出区域（合理高度）
		grp_log = ttk.LabelFrame(scrollable_frame, text="📋 测试日志")
		grp_log.pack(fill="x", padx=15, pady=(8, 15))
		
		# 工具栏
		toolbar = tk.Frame(grp_log, bg=Theme.BG_CARD)
		toolbar.pack(fill="x", padx=5, pady=(5, 0))
		
		tk.Label(toolbar, text="💡 提示：点击上方'API测试'按钮查看详细测试结果", 
				fg=Theme.INFO, font=("", 9), bg=Theme.BG_CARD).pack(side=LEFT, padx=5)
		
		btn_clear_log = tk.Button(toolbar, text="🗑️ 清空日志", 
								  command=lambda: self.img_test_log.delete("1.0", END),
								  font=("", 9), bg="#607D8B", fg="white", 
								  relief=tk.FLAT, padx=12, pady=4, cursor="hand2")
		btn_clear_log.pack(side=RIGHT, padx=5)
		
		# 日志文本框容器（调整为更合理的高度200px）
		log_container = tk.Frame(grp_log, bg=Theme.SURFACE_DARK, relief=tk.SUNKEN, bd=1, height=200)
		log_container.pack(fill="both", padx=5, pady=5)
		log_container.pack_propagate(False)  # 防止子组件改变容器大小
		
		# 添加滚动条
		scroll_y = tk.Scrollbar(log_container, orient="vertical")
		scroll_y.pack(side=RIGHT, fill="y")
		
		# 日志文本框 - 固定高度
		self.img_test_log = tk.Text(log_container, wrap="word", 
									yscrollcommand=scroll_y.set,
									bg=Theme.SURFACE_DARK, fg="#d4d4d4", 
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

	def _load_sd_models(self) -> None:
		"""当选择本地SD时，从SD WebUI拉取模型列表并填入下拉框（异步执行避免卡顿）。"""
		# 仅在选择了本地SD时有效
		provider = None
		if hasattr(self, 'img_api_preset') and hasattr(self, 'img_api_presets'):
			preset = self.img_api_preset.get()
			provider = self.img_api_presets.get(preset, {}).get('provider')
		if provider != 'sd':
			return
		
		if hasattr(self, 'status'):
			self.status.set("正在加载SD模型列表...")
		
		def _fetch_models():
			try:
				from src.clients.sd_client import StableDiffusionClient
				base_url = self.img_base_url.get().strip() if hasattr(self, 'img_base_url') else ''
				client = StableDiffusionClient(base_url or None)
				models = client.get_models() or []
				current = client.get_current_model() or self.img_model.get()
				
				# 在主线程更新UI
				def _update_ui():
					if hasattr(self, 'combo_img_model'):
						self.combo_img_model['values'] = tuple(models)
						self.combo_img_model['state'] = 'readonly'
						if current:
							self.img_model.set(current)
					if hasattr(self, 'status'):
						self.status.set(f"✅ 已加载 {len(models)} 个SD模型")
				
				self.after(0, _update_ui)
			except Exception as e:
				def _show_error():
					if hasattr(self, 'status'):
						self.status.set(f"❌ 加载SD模型失败: {e}")
				self.after(0, _show_error)
		
		# 在后台线程执行
		import threading
		threading.Thread(target=_fetch_models, daemon=True).start()

	def _on_sd_model_selected(self) -> None:
		"""在本地SD下选择模型时，异步切换模型（避免界面卡顿）。"""
		# 仅在本地SD时生效
		provider = None
		if hasattr(self, 'img_api_preset') and hasattr(self, 'img_api_presets'):
			preset = self.img_api_preset.get()
			provider = self.img_api_presets.get(preset, {}).get('provider')
		if provider != 'sd':
			return
		
		model_name = self.img_model.get().strip()
		if not model_name:
			return
		
		if hasattr(self, 'status'):
			self.status.set(f"正在切换到模型: {model_name}...")
		
		def _switch_model():
			try:
				from src.clients.sd_client import StableDiffusionClient
				base_url = self.img_base_url.get().strip() if hasattr(self, 'img_base_url') else ''
				client = StableDiffusionClient(base_url or None)
				switched = client.set_model(model_name)
				
				def _update_status():
					if hasattr(self, 'status'):
						if switched:
							self.status.set(f"✅ 已切换到模型: {model_name}")
						else:
							self.status.set(f"❌ 切换模型失败: {model_name}")
				
				self.after(0, _update_status)
			except Exception as e:
				def _show_error():
					if hasattr(self, 'status'):
						self.status.set(f"❌ 切换模型异常: {e}")
				self.after(0, _show_error)
		
		# 在后台线程执行
		import threading
		threading.Thread(target=_switch_model, daemon=True).start()

	
	