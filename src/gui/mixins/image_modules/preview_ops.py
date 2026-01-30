"""Image辅助功能"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, VERTICAL, Y, messagebox, filedialog
import tkinter as tk
from tkinter import ttk
import os
import threading
from pathlib import Path
from PIL import Image, ImageTk

from src.clients.deepseek_client import DeepSeekClient
from src.clients.image_client import OpenAIImageClient
from src.utils.text import sanitize as _sanitize
from ...helpers.image_styles import IMAGE_TYPES, HUNYUAN_STYLE_MAP
from ...helpers.image_helpers import ImagePromptHelper, DescriptionPromptBuilder
from ...helpers.character_prompt_builder import CharacterPromptBuilder
from ...helpers.character_sheet_builder import CharacterSheetBuilder


class PreviewOperationsMixin:
	"""Image preview_ops 功能"""
	
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

	
	