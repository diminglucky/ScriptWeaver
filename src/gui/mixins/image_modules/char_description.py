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


class CharacterDescriptionMixin:
	"""人物 char_description 功能"""
	
	def _on_generate_character_description(self) -> None:
		"""生成选中人物的特征描述"""
		import threading
		
		selection = self.char_listbox.curselection()
		if not selection:
			return
		
		index = selection[0]
		character = self.character_list[index]
		character_name = character["name"]
		
		# 获取故事内容
		story_text = self.output.get("1.0", END).strip()
		
		# 获取API配置
		selected_api = self.outline_gen_api.get() if hasattr(self, 'outline_gen_api') else "DeepSeek"
		if not hasattr(self, 'api_presets') or selected_api not in self.api_presets:
			messagebox.showerror("错误", f"未找到API配置: {selected_api}")
			return
		
		api_config = self.api_presets[selected_api]
		api_key = _sanitize(api_config.get("key", ""))
		if not api_key:
			messagebox.showwarning("提示", f"API Key 为空，请在'故事生成-配置'页面配置")
			return
		
		# 禁用按钮
		self.char_btn_gen_desc.config(state=DISABLED)
		self.status.set(f"✨ 正在分析\"{character_name}\"的特征...")
		if hasattr(self, 'update_header_status'):
			self.update_header_status(f"生成特征描述...", "✨")
		
		def generate_desc_thread():
			try:
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				
				prompt = f"""请从以下故事中提取"{character_name}"的详细外貌特征描述。

故事内容：
{story_text}

请详细描述"{character_name}"的外貌特征，包括：
1. 性别、年龄段
2. 面部特征（脸型、五官、表情等）
3. 身材体型
4. 发型发色
5. 穿着打扮
6. 其他显著特征

要求：
- 描述要具体、生动，适合用于生成人物肖像画
- 只描述外貌，不要包含性格、经历等内容
- 字数控制在150-300字
- 如果故事中没有明确描述某些特征，可以根据人物设定合理推测
"""
				
				messages = [{"role": "user", "content": prompt}]
				response = client.chat(messages, temperature=0.7)
				
				# 更新人物描述
				self.character_list[index]["description"] = response.strip()
				
				# 保存到项目文件
				self.after(0, lambda: self._save_all_characters_info())
				
				# 更新UI
				self.after(0, lambda: self._update_character_description_display(index))
				self.after(0, lambda: self.status.set(f"✅ 已生成\"{character_name}\"的特征描述并保存"))
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("特征描述完成", "✅"))
				
			except Exception as e:
				error_msg = f"生成特征描述失败: {str(e)}"
				print(f"生成特征描述时出错: {error_msg}")
				self.after(0, lambda: messagebox.showerror("错误", error_msg))
				self.after(0, lambda: self.status.set("❌ 生成特征描述失败"))
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("生成失败", "❌"))
			finally:
				self.after(0, lambda: self.char_btn_gen_desc.config(state=NORMAL))
		
		threading.Thread(target=generate_desc_thread, daemon=True).start()
	
	
	
	
	def _update_character_description_display(self, index: int) -> None:
		"""更新特征描述显示"""
		character = self.character_list[index]
		
		self.char_txt_desc.config(state=NORMAL)
		self.char_txt_desc.delete("1.0", END)
		self.char_txt_desc.insert("1.0", character["description"])
		self.char_txt_desc.config(state=DISABLED)
		
		# 启用相关按钮
		self.char_btn_copy_desc.config(state=NORMAL)
		self.char_btn_gen_photo.config(state=NORMAL)
	
	
	
	
	def _on_copy_character_description(self) -> None:
		"""复制特征描述到剪贴板"""
		description = self.char_txt_desc.get("1.0", END).strip()
		if description:
			self.clipboard_clear()
			self.clipboard_append(description)
			self.status.set("📋 特征描述已复制到剪贴板")
	
	
	
	