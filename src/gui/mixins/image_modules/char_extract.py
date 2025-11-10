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
from src.core.logging_config import get_logger

logger = get_logger(__name__)


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
				
				prompt = f"""请仔细阅读以下故事，提取所有出现的人物。
				
故事内容：
{story_text}

请以JSON格式返回人物列表，格式如下：
{{"characters": ["人物1", "人物2", "人物3"]}}

要求：
1. 提取所有有名字的人物（如：张三、李四、小明）
2. 也要提取有称呼的人物（如：妈妈、爸爸、老师、医生、老板、邻居、朋友）
3. 不要提取纯代词（如：他、她、某人、那个人）
4. 如果人物有多个称呼，选择最常用的一个（如：张医生、张主任 → 选张医生）
5. 按重要性排序，主要人物在前
6. 尽可能提取完整，不要遗漏重要人物
7. 最多提取20个人物
"""
				
				messages = [{"role": "user", "content": prompt}]
				response = client.chat(messages, temperature=0.3)
				
				# 解析JSON响应
				import json
				import re
				
				characters = []
				
				# 打印原始响应（用于调试）
				logger.info(f"AI响应原始内容: {response[:500]}...")
				
				# 尝试提取JSON（支持多种格式）
				json_patterns = [
					r'\{[\s\S]*?"characters"[\s\S]*?\}',  # 标准JSON格式
					r'```json\s*(\{[\s\S]*?\})\s*```',  # Markdown代码块
					r'```\s*(\{[\s\S]*?\})\s*```',  # 普通代码块
					r'\{.*?\}',  # 简单JSON
				]
				
				json_data = None
				for pattern in json_patterns:
					json_match = re.search(pattern, response, re.DOTALL)
					if json_match:
						try:
							json_str = json_match.group(1) if json_match.lastindex else json_match.group()
							json_data = json.loads(json_str)
							logger.info(f"成功解析JSON: {json_data}")
							break
						except json.JSONDecodeError as e:
							logger.warning(f"JSON解析失败，尝试下一个模式: {e}")
							continue
				
				if json_data:
					# 从JSON中提取人物列表
					characters = json_data.get("characters", [])
					# 如果characters是字符串，尝试解析
					if isinstance(characters, str):
						try:
							characters = json.loads(characters)
						except:
							characters = [characters]
				else:
					# 如果没有JSON，尝试从文本中提取人物名
					logger.info("未找到JSON格式，尝试从文本中提取人物名")
					lines = response.strip().split('\n')
					for line in lines:
						line = line.strip()
						# 跳过空行和明显的非人物名行
						if not line or len(line) > 20:
							continue
						
						# 移除序号、引号、Markdown标记等
						line = re.sub(r'^\d+[\.\、\s]*', '', line)  # 移除序号
						line = re.sub(r'^[-*•]\s*', '', line)  # 移除列表标记
						line = re.sub(r'^```.*?```', '', line)  # 移除代码块
						line = line.strip('"\'「」『』""''【】[]()（）').strip()
						
						# 过滤掉明显的非人物名
						skip_keywords = ['人物', '角色', 'character', 'characters', '列表', 'list', 
										'他', '她', '它', '他们', '她们', '某人', '有人', '这个人']
						if any(keyword in line for keyword in skip_keywords):
							continue
						
						# 检查是否是有效的人名（中文名通常2-4字，英文名可能更长）
						if line and 1 <= len(line) <= 15 and not line.startswith('{') and not line.startswith('['):
							# 去重
							if line not in characters:
								characters.append(line)
				
				# 去重并过滤空值
				characters = [c for c in characters if c and isinstance(c, str)]
				characters = list(dict.fromkeys(characters))  # 保持顺序的去重
				
				# 限制数量
				if len(characters) > 10:
					characters = characters[:10]
					logger.warning(f"人物数量超过10个，只保留前10个")
				
				if not characters:
					logger.warning("未提取到任何人物，请检查故事内容")
					self.after(0, lambda: messagebox.showwarning(
						"提示", 
						"未能从故事中提取到人物。\n\n可能原因：\n"
						"1. 故事中没有明确的人物名字\n"
						"2. AI返回格式不正确\n"
						"3. 故事内容为空或过短\n\n"
						"请检查故事内容，确保包含具体的人物名字。\n\n"
						f"AI返回内容预览：\n{response[:200]}..."
					))
					self.after(0, lambda: self.status.set("❌ 未提取到人物，请检查故事内容"))
					if hasattr(self, 'update_header_status'):
						self.after(0, lambda: self.update_header_status("提取失败", "❌"))
				else:
					logger.info(f"成功提取到 {len(characters)} 个人物: {characters}")
					
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
				import traceback
				error_msg = f"提取人物失败: {str(e)}"
				error_detail = traceback.format_exc()
				logger.error(f"提取人物时出错: {error_msg}\n{error_detail}")
				print(f"提取人物时出错: {error_msg}")
				print(error_detail)
				
				# 显示详细错误信息
				detailed_msg = f"{error_msg}\n\n详细错误信息：\n{error_detail[:500]}..."
				self.after(0, lambda: messagebox.showerror("错误", detailed_msg))
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
		"""更新人物下拉框（只显示名字）"""
		# 安全检查：确保UI组件已初始化
		if not hasattr(self, 'char_combobox'):
			logger.warning("char_combobox 尚未初始化，跳过更新")
			return
		
		# 收集所有人物名字
		names = [char["name"] for char in self.character_list]
		# 更新Combobox的值列表
		self.char_combobox['values'] = names
		# 如果有人物，默认选中第一个
		if names:
			self.char_combobox.current(0)
			# 触发选择事件以更新描述显示
			self._on_character_selected()
			
			# 更新图片创作页面的参考人物下拉框
			self._update_reference_character_list()
	
	
	
	
	def _on_character_selected(self, event=None) -> None:
		"""当选择人物时的回调"""
		# 安全检查：确保UI组件已初始化
		if not hasattr(self, 'char_combobox'):
			return
		
		# 获取选中的人物索引（兼容Combobox）
		index = self.char_combobox.current()
		if index < 0:
			return
		
		# 边界检查（防止索引越界）
		if index >= len(self.character_list):
			logger.warning(f"⚠️ 人物索引越界：index={index}, list_len={len(self.character_list)}")
			return
		
		character = self.character_list[index]
		character_name = character.get("name", "")
		
		# 记录日志
		logger.info(f"选择人物：{character_name} (索引: {index})")
		logger.info(f"人物描述长度：{len(character.get('description', ''))} 字符")
		
		# 更新特征描述文本框
		self.char_txt_desc.config(state=NORMAL)
		self.char_txt_desc.delete("1.0", END)
		
		description = character.get("description", "")
		if description:
			self.char_txt_desc.insert("1.0", description)
			if hasattr(self, 'char_btn_copy_desc'):
				self.char_btn_copy_desc.config(state=NORMAL)
			if hasattr(self, 'char_btn_gen_photo'):
				self.char_btn_gen_photo.config(state=NORMAL)
			logger.info(f"已加载人物\"{character_name}\"的描述")
		else:
			self.char_txt_desc.insert("1.0", f"尚未生成特征描述，点击下方按钮为\"{character_name}\"生成详细特征...")
			if hasattr(self, 'char_btn_copy_desc'):
				self.char_btn_copy_desc.config(state=DISABLED)
			if hasattr(self, 'char_btn_gen_photo'):
				self.char_btn_gen_photo.config(state=DISABLED)
			logger.warning(f"人物\"{character_name}\"的描述为空，需要生成")
		
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
						photo_path = char.get("photo_path")
						
						# 处理相对路径：转换为绝对路径
						photo_path_obj = Path(photo_path)
						if not photo_path_obj.is_absolute() and self.current_project:
							# 检查路径是否已经包含项目目录路径（避免重复拼接）
							photo_path_str = str(photo_path_obj).replace("\\", "/")
							project_dir_str = str(self.current_project.project_dir).replace("\\", "/")
							
							# 如果路径已经以项目目录开头，直接使用
							if photo_path_str.startswith(project_dir_str):
								photo_path_obj = Path(photo_path_str)
								logger.debug(f"路径已包含项目目录，直接使用：{photo_path_obj}")
							else:
								# 否则拼接项目目录
								photo_path_obj = self.current_project.project_dir / photo_path_obj
								logger.debug(f"相对路径转换为绝对路径：{photo_path} -> {photo_path_obj}")
						
						if photo_path_obj.exists():
							selected_characters.append({
								"name": char_name,
								"photo_path": str(photo_path_obj),  # 使用绝对路径用于打开
								"description": char.get("description", "")
							})
						else:
							logger.warning(f"人物照片不存在：{photo_path_obj}")
						break
		
		return selected_characters
	
	
	
	