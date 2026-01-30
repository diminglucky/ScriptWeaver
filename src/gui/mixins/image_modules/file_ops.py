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


class FileOperationsMixin:
	"""Image file_ops 功能"""
	
	def _img_choose_ref(self) -> None:
		path = filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg;*.webp;*.bmp"),("All","*.*")])
		if path:
			self.img_ref_path.set(path)
	
	
	
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
	
	
	