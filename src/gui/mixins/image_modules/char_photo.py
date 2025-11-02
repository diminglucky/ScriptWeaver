"""人物处理功能"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, VERTICAL, Y, BOTTOM, messagebox, filedialog
import tkinter as tk
from tkinter import ttk
import os
import threading
from pathlib import Path
from PIL import Image, ImageTk

from src.clients.deepseek_client import DeepSeekClient
from src.clients.image_client import OpenAIImageClient
from src.utils.text import sanitize as _sanitize
from ...helpers.character_prompt_builder import CharacterPromptBuilder
from ...widgets.character_manager import CharacterPhotoGallery
from ...helpers.character_sheet_builder import CharacterSheetBuilder
from .handlers import (
    CharacterPhotoHandler,
    CharacterPhotoGenerator,
    CharacterPhotoSaver,
    CharacterPhotoPreview
)

from src.core.logging_config import get_logger

logger = get_logger(__name__)


class CharacterPhotoMixin:
	"""人物 char_photo 功能"""
	
	def _on_generate_character_photo(self) -> None:
		"""生成选中人物的照片"""
		CharacterPhotoHandler.handle_generate_photo(self)
	
	def _update_character_photo_preview(self, img: Image.Image) -> None:
		"""更新人物照片预览"""
		CharacterPhotoPreview.update_preview(self, img)
	
	def _auto_save_character_photo(self, index: int, img: Image.Image, character_name: str) -> str:
		"""自动保存人物照片到当前项目的characters文件夹，并保存描述信息"""
		return CharacterPhotoSaver.auto_save_photo(self, index, img, character_name)
	
	def _auto_save_character_photo_with_name(self, img: Image.Image, character_name: str, filename: str) -> str:
		"""自动保存人物照片（支持自定义文件名，用于多角度生成）"""
		return CharacterPhotoSaver.auto_save_photo_with_name(self, img, character_name, filename)
	
	def _show_image_fullsize(self, img_path) -> None:
		"""显示图片的全尺寸查看窗口"""
		CharacterPhotoPreview.show_fullsize(self, img_path)
	
	def _on_view_character_gallery(self) -> None:
		"""查看人物图片库"""
		selection = self.char_listbox.curselection()
		if not selection:
			messagebox.showwarning("提示", "请先从列表中选择一个人物！")
			return
		
		index = selection[0]
		character = self.character_list[index]
		character_name = character["name"]
		
		# 检查当前项目
		if not self.current_project:
			messagebox.showwarning("提示", "请先创建或打开一个项目！")
			return
		
		# 获取人物图片目录
		char_dir = self.current_project.project_dir / "characters"
		
		if not char_dir.exists():
			messagebox.showinfo("提示", f"还没有生成\"{character_name}\"的照片")
			return
		
		# 查找该人物的所有图片
		import re
		clean_name = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', character_name)
		char_images = list(char_dir.glob(f"{clean_name}*.png"))
		
		if not char_images:
			messagebox.showinfo("提示", f"还没有生成\"{character_name}\"的照片")
			return
		
		# 创建图片库窗口
		gallery_window = tk.Toplevel(self)
		gallery_window.title(f"{character_name} - 图片库")
		gallery_window.geometry("900x700")
		
		# 标题
		title_frame = ttk.Frame(gallery_window)
		title_frame.pack(fill="x", padx=20, pady=15)
		
		ttk.Label(title_frame, text=f"🎨 {character_name} 的图片库", 
				 font=("", 14, "bold")).pack(side=LEFT)
		ttk.Label(title_frame, text=f"共 {len(char_images)} 张图片", 
				 font=("", 11)).pack(side=RIGHT)
		
		# 创建可滚动区域
		canvas = tk.Canvas(gallery_window, bg="#2b2b2b")
		scrollbar = ttk.Scrollbar(gallery_window, orient=VERTICAL, command=canvas.yview)
		scrollable_frame = ttk.Frame(canvas)
		
		scrollable_frame.bind(
			"<Configure>",
			lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
		)
		
		canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
		canvas.configure(yscrollcommand=scrollbar.set)
		
		card_refs = []
		col_count = 3
		
		def refresh_gallery():
			"""刷新图片库显示"""
			updated_images = list(char_dir.glob(f"{clean_name}*.png"))
			
			for widget in title_frame.winfo_children():
				if isinstance(widget, ttk.Label) and "共" in widget.cget("text"):
					widget.config(text=f"共 {len(updated_images)} 张图片")
			
			for widget in scrollable_frame.winfo_children():
				widget.destroy()
			card_refs.clear()
			
			if not updated_images:
				ttk.Label(scrollable_frame, text="📭 该人物已无照片", 
						 font=("", 14)).grid(row=0, column=0, columnspan=3, pady=50)
				return
			
			load_images(updated_images)
		
		def load_images(images_list):
			"""加载并显示图片"""
			for idx, img_path in enumerate(sorted(images_list)):
				row = idx // col_count
				col = idx % col_count
				
				card = ttk.Frame(scrollable_frame, relief="solid", borderwidth=1)
				card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
				card_refs.append(card)
				
				try:
					if not img_path.exists():
						ttk.Label(card, text=f"文件不存在:\n{img_path.name}", 
								 foreground="red").pack(pady=20)
						continue
					
					img = Image.open(img_path)
					img.thumbnail((250, 250), Image.Resampling.LANCZOS)
					photo = ImageTk.PhotoImage(img)
					
					img_label = tk.Label(card, image=photo, bg="#1e1e1e", cursor="hand2")
					img_label.image = photo
					img_label.pack(padx=5, pady=5)
					
					def create_zoom_handler(path):
						def on_click(event):
							self._show_image_fullsize(path)
						return on_click
					
					img_label.bind("<Button-1>", create_zoom_handler(img_path))
					
					# 文件名标签
					ttk.Label(card, text=img_path.name, font=("", 9)).pack(pady=5)
					
					# 删除按钮
					def delete_image():
						if messagebox.askyesno("确认", f"确定要删除图片\n{img_path.name}吗？"):
							try:
								img_path.unlink()
								logger.info(f"已删除图片: {img_path}")
								refresh_gallery()
							except Exception as e:
								logger.error(f"删除图片失败: {e}")
								messagebox.showerror("错误", f"删除失败: {e}")
					
					ttk.Button(card, text="🗑️ 删除", command=delete_image, width=10).pack(pady=5)
					
				except Exception as e:
					logger.error(f"加载图片失败 {img_path}: {e}")
					ttk.Label(card, text=f"加载失败:\n{img_path.name}", 
							 foreground="red").pack(pady=20)
		
		load_images(char_images)
		
		canvas.pack(side=LEFT, fill=BOTH, expand=True)
		scrollbar.pack(side=RIGHT, fill=Y)
		
		def on_close():
			canvas.unbind_all("<MouseWheel>")
			gallery_window.destroy()
		
		gallery_window.protocol("WM_DELETE_WINDOW", on_close)
	
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
	