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


class ImageUIMainMixin:
	"""Image UI ui_main 功能"""
	
	def _build_image_page(self) -> None:
		"""构建图片生成页面，分为"创作"、"人物生成"和"配置"三个子标签页"""
		# Vars for image page
		self.img_prompt = tk.StringVar()
		self.img_size = tk.StringVar(value="1024x1024")
		self.img_seed = tk.StringVar(value="")
		self.img_ref_path = tk.StringVar(value="")
		self.img_api_key = tk.StringVar(value=os.getenv("OPENAI_API_KEY", ""))
		self.img_model = tk.StringVar(value=os.getenv("OPENAI_IMAGE_MODEL", "dall-e-3"))
		self.img_api_type = tk.StringVar(value="openai")  # API类型：openai 或 hunyuan
		self.img_last_image: Image.Image | None = None
		self.img_preview_photo: ImageTk.PhotoImage | None = None
		self.parsed_shots: list[str] = []  # 存储解析后的分镜列表
		
		# 人物生成相关变量
		self.character_list: list[dict] = []  # 存储提取的人物列表 [{"name": "张三", "description": "...", "photo_path": "..."}]
		self.character_last_image: Image.Image | None = None
		self.character_preview_photo: ImageTk.PhotoImage | None = None
		self.character_photos_dir = None  # 人物照片保存目录
		
		# 创建图片页面的内部Notebook - 简化版，配置已移至设置页面
		self.image_notebook = ttk.Notebook(self.page_image)
		self.image_notebook.pack(fill=BOTH, expand=True, padx=0, pady=0)
		
		# 创建两个子标签页（配置已移至统一设置页面）
		self.image_tab_character = tk.Frame(self.image_notebook, bg="#2b2b2b")
		self.image_tab_create = tk.Frame(self.image_notebook, bg="#2b2b2b")
		
		self.image_notebook.add(self.image_tab_character, text="  👥 人物描述  ")
		self.image_notebook.add(self.image_tab_create, text="  🎨 图片创作  ")
		
		# 构建各个标签页
		self._build_character_tab()
		self._build_image_create_tab()
	
	
	