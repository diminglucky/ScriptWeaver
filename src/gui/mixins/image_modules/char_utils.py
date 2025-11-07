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
		"""加载当前项目的所有人物信息（包括没有照片的人物）"""
		import json
		from pathlib import Path
		from src.core.logging_config import get_logger
		
		logger = get_logger(__name__)
		
		# 记录加载开始
		logger.info("=== 开始加载项目人物数据 ===")
		
		# 清空之前的人物列表
		old_count = len(self.character_list) if hasattr(self, 'character_list') else 0
		self.character_list.clear()
		logger.info(f"已清空人物列表（之前有 {old_count} 个人物）")
		
		if not self.current_project:
			logger.warning("⚠️ 没有当前项目，无法加载人物信息")
			self._update_reference_character_list()
			return
		
		try:
			# 获取项目的 characters 文件夹
			characters_dir = self.current_project.project_dir / "characters"
			logger.info(f"项目路径：{self.current_project.project_dir}")
			logger.info(f"人物文件夹路径：{characters_dir}")
			
			if not characters_dir.exists():
				logger.warning(f"📁 项目尚无人物文件夹：{characters_dir}")
				self._update_reference_character_list()
				return
			
			# 读取人物描述信息（这是主要数据源）
			characters_info_path = characters_dir / "characters_info.json"
			characters_info_raw = {}
			
			logger.info(f"检查人物信息文件：{characters_info_path}")
			logger.info(f"文件是否存在：{characters_info_path.exists()}")
			
			if characters_info_path.exists():
				try:
					with open(characters_info_path, 'r', encoding='utf-8') as f:
						characters_info_raw = json.load(f)
					logger.info(f"📖 已加载人物描述文件：{characters_info_path}")
					logger.info(f"JSON内容类型：{type(characters_info_raw)}")
					logger.info(f"JSON内容长度：{len(characters_info_raw) if isinstance(characters_info_raw, dict) else 'N/A'}")
					logger.debug(f"JSON内容预览：{str(characters_info_raw)[:200]}...")
				except Exception as e:
					logger.error(f"⚠️ 读取人物描述文件失败：{str(e)}", exc_info=True)
			else:
				logger.warning(f"人物信息文件不存在：{characters_info_path}")
			
			if not characters_info_raw:
				logger.warning(f"📋 项目中暂无保存的人物信息")
				self._update_reference_character_list()
				return
			
			# 处理不同的JSON格式
			# 格式1: {"name1": {"description": "...", "photo_path": "..."}, "name2": {...}}
			# 格式2: {"characters": {"name1": {...}, "name2": {...}}}
			characters_info = {}
			if "characters" in characters_info_raw and isinstance(characters_info_raw["characters"], dict):
				# 格式2：嵌套格式
				characters_info = characters_info_raw["characters"]
				logger.info("📋 检测到嵌套格式JSON，已提取characters字段")
			else:
				# 格式1：扁平格式
				characters_info = characters_info_raw
				logger.info("📋 使用扁平格式JSON")
			
			logger.info(f"处理后的characters_info包含 {len(characters_info)} 个键")
			logger.debug(f"键列表：{list(characters_info.keys())}")
			
			# 从JSON加载所有人物（包括没有照片的）
			loaded_count = 0
			skipped_count = 0
			
			for character_name, char_data in characters_info.items():
				# 跳过无效的键（如"characters"本身）
				if character_name == "characters":
					logger.warning(f"跳过无效键：'characters'")
					skipped_count += 1
					continue
				
				if not isinstance(char_data, dict):
					logger.warning(f"跳过无效数据：{character_name} (类型: {type(char_data)})")
					skipped_count += 1
					continue
				
				# 处理不同的数据格式
				if isinstance(char_data, str):
					# 如果char_data是字符串，说明格式不对，跳过
					logger.warning(f"跳过字符串格式数据：{character_name}")
					skipped_count += 1
					continue
				
				description = char_data.get("description", "")
				photo_path = char_data.get("photo_path", "")
				
				logger.debug(f"加载人物：{character_name}，描述长度：{len(description)}，照片路径（原始）：{photo_path}")
				
				# 处理照片路径：如果是相对路径，转换为绝对路径；如果是绝对路径，验证是否存在
				if photo_path:
					photo_path_obj = Path(photo_path)
					
					# 判断是绝对路径还是相对路径
					if photo_path_obj.is_absolute():
						# 绝对路径：检查是否已经包含项目目录（避免重复拼接）
						photo_path_str = str(photo_path_obj).replace("\\", "/")
						project_dir_str = str(self.current_project.project_dir).replace("\\", "/")
						
						# 如果路径已经以项目目录开头，直接使用
						if photo_path_str.startswith(project_dir_str):
							# 已经是正确的绝对路径，直接使用
							logger.debug(f"绝对路径已包含项目目录，直接使用：{photo_path_obj}")
						else:
							# 绝对路径不在项目目录下，记录警告但保留
							logger.warning(f"照片路径不在项目目录下：{photo_path_obj}")
					else:
						# 相对路径：转换为绝对路径（相对于项目目录）
						# 检查路径是否已经包含项目目录路径（避免重复拼接）
						photo_path_str = str(photo_path_obj).replace("\\", "/")
						project_dir_str = str(self.current_project.project_dir).replace("\\", "/")
						
						# 如果路径已经以项目目录开头，直接使用
						if photo_path_str.startswith(project_dir_str):
							photo_path_obj = Path(photo_path_str)
							logger.debug(f"路径已包含项目目录，直接使用：{photo_path_obj}")
						else:
							# 检查路径是否以"characters"开头（标准相对路径）
							if photo_path_str.startswith("characters/"):
								absolute_path = self.current_project.project_dir / photo_path_obj
							else:
								# 否则假设是相对于项目目录的路径
								absolute_path = self.current_project.project_dir / photo_path_obj
							photo_path_obj = absolute_path
							logger.debug(f"相对路径转换为绝对路径：{photo_path} -> {photo_path_obj}")
					
					# 验证照片文件是否存在
					if photo_path_obj.exists():
						# 保存为相对路径（相对于项目目录）
						try:
							relative_path = photo_path_obj.relative_to(self.current_project.project_dir)
							photo_path = str(relative_path).replace("\\", "/")
							logger.debug(f"照片路径（相对）：{photo_path}")
						except ValueError:
							# 如果无法转换为相对路径，保持绝对路径但记录警告
							logger.warning(f"照片路径不在项目目录下，使用绝对路径：{photo_path_obj}")
							photo_path = str(photo_path_obj).replace("\\", "/")
					else:
						logger.warning(f"⚠️ 照片文件不存在：{photo_path_obj}")
						photo_path = ""  # 重置为空
				
				self.character_list.append({
					"name": character_name,
					"description": description,
					"photo_path": photo_path  # 保存相对路径
				})
				loaded_count += 1
			
			# 统计有照片的人物数量
			photo_count = sum(1 for char in self.character_list if char.get("photo_path"))
			
			logger.info(f"✅ 已加载 {loaded_count} 个人物（其中 {photo_count} 个有照片），跳过 {skipped_count} 个无效项")
			
			# 显示人物列表
			character_names = [char['name'] for char in self.character_list]
			logger.info(f"✅ 已加载项目人物：{character_names}")
			
			# 显示人物描述预览
			for char in self.character_list:
				desc_preview = char["description"][:80] + "..." if len(char["description"]) > 80 else char["description"]
				if desc_preview:
					logger.debug(f"   📝 {char['name']}: {desc_preview}")
				else:
					logger.debug(f"   📝 {char['name']}: （尚无描述）")
			
			# 更新列表框显示
			if hasattr(self, '_update_character_listbox'):
				self._update_character_listbox()
				logger.info(f"已更新人物列表框，当前显示 {len(self.character_list)} 个人物")
			else:
				logger.warning("_update_character_listbox 方法不存在")
			
			# 更新参考人物列表
			self._update_reference_character_list()
			
			logger.info("=== 人物数据加载完成 ===")
			
		except Exception as e:
			logger.error(f"❌ 加载项目人物信息失败：{str(e)}", exc_info=True)
			print(f"❌ 加载项目人物信息失败：{str(e)}")
			import traceback
			traceback.print_exc()
			self._update_reference_character_list()
	
	
	
	
	def _update_reference_character_list(self) -> None:
		"""更新图片创作页面的参考人物列表（仅当前项目，支持多选）"""
		# 检查 UI 组件是否存在
		if not hasattr(self, 'ref_character_listbox'):
			print(f"⚠️ ref_character_listbox 不存在，跳过更新")
			return
		
		# 清空列表框
		self.ref_character_listbox.delete(0, END)
		
		# 添加"不使用参考"选项
		self.ref_character_listbox.insert(END, "❌ 不使用参考")
		
		# 只显示当前项目中已生成照片的人物
		character_names = ["不使用参考"]
		for char in self.character_list:
			photo_path = char.get("photo_path")
			if photo_path:
				# 验证照片文件是否存在（处理相对路径）
				from pathlib import Path
				photo_path_obj = Path(photo_path)
				
				# 如果是相对路径，转换为绝对路径（相对于项目目录）
				if not photo_path_obj.is_absolute() and self.current_project:
					# 检查路径是否已经包含项目目录路径（避免重复拼接）
					photo_path_str = str(photo_path_obj).replace("\\", "/")
					project_dir_str = str(self.current_project.project_dir).replace("\\", "/")
					
					# 如果路径已经以项目目录开头，直接使用
					if photo_path_str.startswith(project_dir_str):
						photo_path_obj = Path(photo_path_str)
					else:
						# 否则拼接项目目录
						photo_path_obj = self.current_project.project_dir / photo_path_obj
				
				if photo_path_obj.exists():
					character_names.append(char["name"])
					self.ref_character_listbox.insert(END, f"✅ {char['name']}")
				else:
					logger.warning(f"⚠️ 人物照片不存在：{photo_path_obj}")
		
		# 获取项目名称
		if self.current_project:
			project_name = self.current_project.metadata.get("name", "未命名项目")
		else:
			project_name = "无项目"
		print(f"📋 已更新参考人物列表 [项目: {project_name}]：{character_names}")
	
	
	
	
	def _save_all_characters_info(self) -> bool:
		"""保存所有人物信息到characters_info.json（包括没有照片的人物）"""
		try:
			import json
			from pathlib import Path
			
			# 检查是否有当前项目
			if not self.current_project:
				print("⚠️ 没有当前项目，无法保存人物信息")
				return False
			
			# 确定保存目录
			characters_dir = self.current_project.project_dir / "characters"
			characters_dir.mkdir(parents=True, exist_ok=True)
			
			# 构建保存数据（确保photo_path是相对路径）
			characters_info = {}
			for char in self.character_list:
				char_name = char.get("name", "")
				if char_name:
					photo_path = char.get("photo_path", "")
					# 如果photo_path是绝对路径，转换为相对路径
					if photo_path:
						try:
							photo_path_obj = Path(photo_path)
							if photo_path_obj.is_absolute():
								# 尝试转换为相对路径
								try:
									relative_path = photo_path_obj.relative_to(self.current_project.project_dir)
									photo_path = str(relative_path).replace("\\", "/")
									logger.debug(f"转换绝对路径为相对路径: {photo_path_obj} -> {photo_path}")
								except ValueError:
									# 如果无法转换为相对路径（不在项目目录下），保持原样但记录警告
									logger.warning(f"照片路径不在项目目录下: {photo_path_obj}")
									photo_path = str(photo_path_obj).replace("\\", "/")
						except Exception as e:
							logger.warning(f"处理照片路径时出错: {e}")
					
					characters_info[char_name] = {
						"description": char.get("description", ""),
						"photo_path": photo_path
					}
			
			# 保存到文件
			characters_info_path = characters_dir / "characters_info.json"
			with open(characters_info_path, 'w', encoding='utf-8') as f:
				json.dump(characters_info, f, ensure_ascii=False, indent=2)
			
			print(f"💾 已保存 {len(characters_info)} 个人物信息到：{characters_info_path}")
			return True
			
		except Exception as e:
			print(f"❌ 保存人物信息失败：{str(e)}")
			import traceback
			traceback.print_exc()
			return False
	
	
	
	
	def _on_view_character_gallery(self) -> None:
		"""打开人物照片画廊"""
		# 获取选中的人物索引（兼容Combobox）
		index = self.char_combobox.current()
		if index < 0:
			messagebox.showwarning("提示", "请先从下拉框中选择一个人物！")
			return
		
		if not self.current_project:
			messagebox.showwarning("提示", "请先创建或打开一个项目！")
			return
		
		character = self.character_list[index]
		character_name = character["name"]
		
		# 获取characters目录
		from pathlib import Path
		characters_dir = Path(self.current_project.project_dir) / "characters"
		
		# 打开照片画廊
		try:
			gallery = CharacterPhotoGallery(
				parent=self,
				character_name=character_name,
				photos_dir=characters_dir,
				on_photo_select=lambda path: self.status.set(f"✅ 已选择照片: {path.name}")
			)
		except Exception as e:
			messagebox.showerror("错误", f"打开照片画廊失败：{str(e)}")
	
	
	
	