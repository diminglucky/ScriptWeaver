"""人物处理功能"""

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
from ...helpers.character_prompt_builder import CharacterPromptBuilder
from ...widgets.character_manager import CharacterPhotoGallery
from ...helpers.character_sheet_builder import CharacterSheetBuilder


class CharacterUtilsMixin:
	"""人物 char_utils 功能"""
	
	def _prepare_character_enhanced_prompt(self, prompt_cn: str, selected_characters: list) -> str:
		"""准备包含人物信息的提示词
		注意：如果有参考人物照片，将使用图生图，不需要描述外貌
		"""
		if not selected_characters:
			return prompt_cn
		
		# 检查是否有参考人物照片（将使用图生图）
		has_photo = any(char.get("photo_path") for char in selected_characters)
		
		if has_photo:
			# 有照片时，只需要动态描述（动作、表情、场景）
			# 从原描述中移除人物外貌特征，保留动作和场景
			return f"基于参考图片中的人物，描述场景：\n{prompt_cn}\n\n注意：保持人物外貌不变，只改变动作、表情、场景。"
		else:
			# 没有照片时，需要完整的人物描述（文生图）
			char_descriptions = []
			for char in selected_characters:
				if char.get("description"):
					char_descriptions.append(f"【{char['name']}】{char['description']}")
			
			if char_descriptions:
				characters_text = "\n".join(char_descriptions)
				return f"人物特征（需保持一致）：\n{characters_text}\n\n场景描述：\n{prompt_cn}"
		
		return prompt_cn
	
	
	
	
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
		
		# 更新Canvas的滚动区域 - 确保图片可以完全滚动查看
		# 如果图片比Canvas大，设置滚动区域为图片尺寸
		# 如果图片比Canvas小，设置滚动区域为Canvas尺寸
		scroll_width = max(new_w, canvas_width)
		scroll_height = max(new_h, canvas_height)
		self.char_canvas.configure(scrollregion=(0, 0, scroll_width, scroll_height))
		
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
	
	
	
	
	def _load_project_characters(self) -> None:
		"""加载当前项目的所有人物信息（支持新旧两种数据格式）"""
		from ...models.character import Character, CharacterProfile, VisualFeatures, CharacterDNA
		
		self.character_list.clear()
		
		if not self.current_project:
			print("⚠️ 没有当前项目，无法加载人物信息")
			self._update_reference_character_list()
			return
		
		try:
			import json
			from pathlib import Path
			
			characters_dir = self.current_project.project_dir / "characters"
			
			if not characters_dir.exists():
				print(f"📁 项目尚无人物文件夹：{characters_dir}")
				self._update_reference_character_list()
				return
			
			characters_info_path = characters_dir / "characters_info.json"
			if not characters_info_path.exists():
				print(f"📋 项目中暂无保存的人物信息")
				self._update_reference_character_list()
				return
			
			with open(characters_info_path, 'r', encoding='utf-8') as f:
				characters_info = json.load(f)
			print(f"📖 已加载人物描述文件：{characters_info_path}")
			
			if not characters_info:
				self._update_reference_character_list()
				return
			
			loaded_count = 0
			
			if isinstance(characters_info, list):
				# 新格式：Character 对象列表
				for char_data in characters_info:
					try:
						if "profile" in char_data or "dna" in char_data:
							char = Character.from_dict(char_data)
						else:
							char = Character.from_legacy(char_data)
						
						if char.primary_photo and not Path(char.primary_photo).exists():
							print(f"⚠️ 照片不存在：{char.primary_photo}")
							char.primary_photo = ""
						
						self.character_list.append(char)
						loaded_count += 1
					except Exception as e:
						print(f"⚠️ 加载角色失败: {e}")
			else:
				# 旧格式
				for character_name, char_data in characters_info.items():
					description = char_data.get("description", "")
					photo_path = char_data.get("photo_path", "")
					
					if photo_path and not Path(photo_path).exists():
						photo_path = ""
					
					char = Character(name=character_name)
					char.description = description
					char.primary_photo = photo_path
					self.character_list.append(char)
					loaded_count += 1
			
			photo_count = sum(1 for c in self.character_list 
			                 if (isinstance(c, Character) and c.primary_photo) or 
			                    (isinstance(c, dict) and c.get("photo_path")))
			dna_count = sum(1 for c in self.character_list 
			               if isinstance(c, Character) and c.dna and c.dna.core_prompt)
			
			print(f"✅ 已加载 {loaded_count} 个人物（{photo_count} 有照片，{dna_count} 有DNA）")
			
			self._update_character_listbox()
			self._update_reference_character_list()
			
		except Exception as e:
			print(f"❌ 加载项目人物信息失败：{str(e)}")
			import traceback
			traceback.print_exc()
			self._update_reference_character_list()
	
	
	
	
	def _update_reference_character_list(self) -> None:
		"""更新图片创作页面的参考人物列表"""
		from ...models.character import Character
		from pathlib import Path
		
		self.ref_character_listbox.delete(0, END)
		self.ref_character_listbox.insert(END, "❌ 不使用参考")
		
		character_names = ["不使用参考"]
		for char in self.character_list:
			if isinstance(char, Character):
				photo_path = char.primary_photo
				name = char.name
				has_dna = bool(char.dna and char.dna.core_prompt)
			else:
				photo_path = char.get("photo_path", "")
				name = char.get("name", "")
				has_dna = bool(char.get("dna_prompt"))
			
			if photo_path and Path(photo_path).exists():
				character_names.append(name)
				# 显示DNA状态
				prefix = "🧬" if has_dna else "✅"
				self.ref_character_listbox.insert(END, f"{prefix} {name}")
		
		project_name = self.current_project.metadata.get("name", "未命名") if self.current_project else "无项目"
		print(f"📋 已更新参考人物列表 [{project_name}]：{character_names}")
	
	
	
	
	def _save_all_characters_info(self) -> bool:
		"""保存所有人物信息到characters_info.json（使用新格式）"""
		from ...models.character import Character
		
		try:
			import json
			from pathlib import Path
			
			if not self.current_project:
				print("⚠️ 没有当前项目，无法保存人物信息")
				return False
			
			characters_dir = self.current_project.project_dir / "characters"
			characters_dir.mkdir(parents=True, exist_ok=True)
			
			# 转换为可保存格式（新格式：列表）
			save_data = []
			for char in self.character_list:
				if isinstance(char, Character):
					save_data.append(char.to_dict())
				else:
					save_data.append({
						"name": char.get("name", ""),
						"description": char.get("description", ""),
						"primary_photo": char.get("photo_path", ""),
						"profile": char.get("character_profile", {}),
						"visual": char.get("visual_features", {}),
						"dna": {"core_prompt": char.get("dna_prompt", "")},
					})
			
			characters_info_path = characters_dir / "characters_info.json"
			with open(characters_info_path, 'w', encoding='utf-8') as f:
				json.dump(save_data, f, ensure_ascii=False, indent=2)
			
			print(f"💾 已保存 {len(save_data)} 个人物信息到：{characters_info_path}")
			return True
			
		except Exception as e:
			print(f"❌ 保存人物信息失败：{str(e)}")
			import traceback
			traceback.print_exc()
			return False
	
	
	
	
	def _on_view_character_gallery(self) -> None:
		"""打开人物照片画廊"""
		from ...models.character import Character
		
		selection = self.char_listbox.curselection()
		if not selection:
			messagebox.showwarning("提示", "请先选择一个人物！")
			return
		
		if not self.current_project:
			messagebox.showwarning("提示", "请先创建或打开一个项目！")
			return
		
		index = selection[0]
		character = self.character_list[index]
		
		if isinstance(character, Character):
			character_name = character.name
		else:
			character_name = character["name"]
		
		from pathlib import Path
		characters_dir = Path(self.current_project.project_dir) / "characters"
		
		try:
			gallery = CharacterPhotoGallery(
				parent=self,
				character_name=character_name,
				photos_dir=characters_dir,
				on_photo_select=lambda path: self.status.set(f"✅ 已选择照片: {path.name}")
			)
		except Exception as e:
			messagebox.showerror("错误", f"打开照片画廊失败：{str(e)}")
	
	
	
	