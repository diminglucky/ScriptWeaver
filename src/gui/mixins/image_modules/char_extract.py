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


class CharacterExtractMixin:
	"""人物 char_extract 功能"""
	
	def _on_extract_characters(self) -> None:
		"""从当前故事中提取人物列表"""
		import threading
		
		# 获取当前故事内容
		story_text = self.output.get("1.0", END).strip()
		if not story_text:
			messagebox.showwarning("提示", "请先生成故事内容！")
			return
		
		# 获取API配置
		selected_api = self.outline_gen_api.get() if hasattr(self, 'outline_gen_api') else "DeepSeek"
		if not hasattr(self, 'api_presets') or selected_api not in self.api_presets:
			messagebox.showerror("错误", f"未找到API配置: {selected_api}，请检查配置页面")
			return
		
		api_config = self.api_presets[selected_api]
		api_key = _sanitize(api_config.get("key", ""))
		if not api_key:
			messagebox.showwarning("提示", f"API Key 为空，请在'故事生成-配置'页面为 {selected_api} 填写后保存")
			return
		
		# 禁用按钮
		if hasattr(self, 'char_btn_extract'):
			self.char_btn_extract.config(state=DISABLED)
		if hasattr(self, 'char_btn_refresh'):
			self.char_btn_refresh.config(state=DISABLED)
		self.status.set("🔍 正在分析故事，提取人物列表...")
		if hasattr(self, 'update_header_status'):
			self.update_header_status("提取人物中...", "🔍")
		
		def extract_thread():
			try:
				# 使用DeepSeek提取人物
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				
				prompt = f"""请从以下故事中提取所有关键人物的名字。
				
故事内容：
{story_text}

请以JSON格式返回人物列表，格式如下：
{{"characters": ["人物1", "人物2", "人物3"]}}

要求：
1. 只提取有具体名字的人物
2. 不要提取"他"、"她"、"某人"等代词
3. 按重要性排序，主要人物在前
4. 最多提取10个人物
"""
				
				messages = [{"role": "user", "content": prompt}]
				response = client.chat(messages, temperature=0.3)
				
				# 解析JSON响应
				import json
				import re
				
				# 尝试提取JSON
				json_match = re.search(r'\{.*\}', response, re.DOTALL)
				if json_match:
					data = json.loads(json_match.group())
					characters = data.get("characters", [])
				else:
					# 如果没有JSON，尝试从文本中提取人物名
					characters = []
					lines = response.strip().split('\n')
					for line in lines:
						line = line.strip()
						# 移除序号、引号等
						line = re.sub(r'^\d+[\.\、\s]*', '', line)
						line = line.strip('"\'「」『』""''').strip()
						if line and len(line) <= 10:  # 人名通常不会太长
							characters.append(line)
				
				# 更新人物列表
				self.character_list = [{"name": name, "description": "", "photo_path": ""} for name in characters]
				
				# 立即保存到项目文件
				self.after(0, lambda: self._save_all_characters_info())
				
				# 更新UI（在主线程中）
				self.after(0, lambda: self._update_character_listbox())
				self.after(0, lambda: self.status.set(f"✅ 成功提取到 {len(characters)} 个人物并已保存"))
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("人物提取完成并保存", "✅"))
				
			except Exception as e:
				error_msg = f"提取人物失败: {str(e)}"
				print(f"提取人物时出错: {error_msg}")
				self.after(0, lambda: messagebox.showerror("错误", error_msg))
				self.after(0, lambda: self.status.set("❌ 提取人物失败"))
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("提取失败", "❌"))
			finally:
				if hasattr(self, 'char_btn_extract'):
					self.after(0, lambda: self.char_btn_extract.config(state=NORMAL))
				if hasattr(self, 'char_btn_refresh'):
					self.after(0, lambda: self.char_btn_refresh.config(state=NORMAL))
		
		threading.Thread(target=extract_thread, daemon=True).start()
	
	
	
	
	def _update_character_listbox(self) -> None:
		"""更新人物列表框"""
		self.char_listbox.delete(0, END)
		for char in self.character_list:
			self.char_listbox.insert(END, char["name"])
		
		if self.character_list:
			# 默认选中第一个
			self.char_listbox.selection_set(0)
			self.char_listbox.event_generate("<<ListboxSelect>>")
			
			# 更新图片创作页面的参考人物下拉框
			self._update_reference_character_list()
	
	
	
	
	def _on_character_selected(self, event=None) -> None:
		"""当选择人物时的回调"""
		selection = self.char_listbox.curselection()
		if not selection:
			return
		
		index = selection[0]
		
		# 边界检查
		if index < 0 or index >= len(self.character_list):
			print(f"⚠️ 人物索引越界：index={index}, list_len={len(self.character_list)}")
			return
		
		character = self.character_list[index]
		
		# 更新特征描述文本框
		self.char_txt_desc.config(state=NORMAL)
		self.char_txt_desc.delete("1.0", END)
		
		if character["description"]:
			self.char_txt_desc.insert("1.0", character["description"])
			if hasattr(self, 'char_btn_copy_desc'):
				self.char_btn_copy_desc.config(state=NORMAL)
			if hasattr(self, 'char_btn_gen_photo'):
				self.char_btn_gen_photo.config(state=NORMAL)
		else:
			self.char_txt_desc.insert("1.0", f"尚未生成特征描述，点击下方按钮为\"{character['name']}\"生成详细特征...")
			if hasattr(self, 'char_btn_copy_desc'):
				self.char_btn_copy_desc.config(state=DISABLED)
			if hasattr(self, 'char_btn_gen_photo'):
				self.char_btn_gen_photo.config(state=DISABLED)
		
		self.char_txt_desc.config(state=DISABLED)
		
		# 启用查看照片画廊和生成设定表按钮（只要有项目就可以使用）
		if self.current_project:
			if hasattr(self, 'char_btn_view_gallery'):
				self.char_btn_view_gallery.config(state=NORMAL)
			if hasattr(self, 'char_btn_generate_sheet'):
				self.char_btn_generate_sheet.config(state=NORMAL)
			if hasattr(self, 'char_btn_edit_detail'):
				self.char_btn_edit_detail.config(state=NORMAL)
		else:
			if hasattr(self, 'char_btn_view_gallery'):
				self.char_btn_view_gallery.config(state=DISABLED)
			if hasattr(self, 'char_btn_generate_sheet'):
				self.char_btn_generate_sheet.config(state=DISABLED)
			if hasattr(self, 'char_btn_edit_detail'):
				self.char_btn_edit_detail.config(state=DISABLED)
		
		# 启用生成特征描述按钮
		if hasattr(self, 'char_btn_gen_desc'):
			self.char_btn_gen_desc.config(state=NORMAL)
	
	
	
	
	def _get_selected_reference_characters(self) -> list:
		"""获取选中的参考人物列表"""
		# 检查 UI 组件是否存在
		if not hasattr(self, 'ref_character_listbox'):
			print(f"⚠️ ref_character_listbox 不存在，返回空列表")
			return []
		
		selected_indices = self.ref_character_listbox.curselection()
		selected_characters = []
		
		for idx in selected_indices:
			item_text = self.ref_character_listbox.get(idx)
			# 去除前面的emoji和空格
			if item_text.startswith("✅ "):
				char_name = item_text[2:].strip()
				# 查找对应人物的照片路径和描述
				for char in self.character_list:
					if char["name"] == char_name and char.get("photo_path"):
						selected_characters.append({
							"name": char_name,
							"photo_path": char["photo_path"],
							"description": char.get("description", "")
						})
						break
		
		return selected_characters
	
	
	
	