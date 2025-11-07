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
	
	def _extract_single_character_info(self, response: str, target_name: str) -> str:
		"""从AI返回的内容中提取目标人物的信息（如果包含多个人物）"""
		import re
		
		# 检查是否包含多个人物的标识（人名作为标题）
		lines = response.split('\n')
		
		# 如果响应中没有出现其他人名作为标题，直接返回
		# 检测格式：单独一行只有人名，或者 "===人名===" 这样的标题
		name_pattern = re.compile(r'^[=\s]*([^：\s]+?)[=\s]*$')
		detected_names = []
		
		for line in lines:
			line_stripped = line.strip()
			if line_stripped and not any(marker in line_stripped for marker in ['性别', '年龄', '发型', '体型', '服装', '特征']):
				match = name_pattern.match(line_stripped)
				if match and len(line_stripped) <= 10:  # 人名通常不超过10字
					detected_names.append(match.group(1))
		
		# 如果没有检测到多个人名标题，直接返回原内容
		if len(detected_names) <= 1:
			print(f"[OK] 响应格式正常，未检测到多人物")
			return response
		
		# 检测到多个人物，尝试提取目标人物的部分
		print(f"[WARN] 检测到多个人物标题: {detected_names}")
		print(f"[TARGET] 尝试提取目标人物: {target_name}")
		
		# 找到目标人物的起始行
		target_start = -1
		target_end = len(lines)
		
		for i, line in enumerate(lines):
			line_stripped = line.strip()
			if target_name in line_stripped and not any(marker in line_stripped for marker in ['性别', '年龄', '发型', '体型', '服装', '特征']):
				target_start = i
				print(f"[FOUND] 目标人物起始行: {i}")
				break
		
		if target_start == -1:
			print(f"[ERROR] 未找到目标人物 {target_name}，返回原内容")
			return response
		
		# 找到下一个人物的起始行（作为结束标记）
		for i in range(target_start + 1, len(lines)):
			line_stripped = lines[i].strip()
			# 检查是否是另一个人物的标题
			if line_stripped and name_pattern.match(line_stripped):
				potential_name = name_pattern.match(line_stripped).group(1)
				if potential_name != target_name and potential_name in detected_names:
					target_end = i
					print(f"[FOUND] 下一个人物起始行: {i}")
					break
		
		# 提取目标人物的内容（跳过人名标题行）
		extracted_lines = []
		for i in range(target_start + 1, target_end):
			line = lines[i].strip()
			if line:  # 跳过空行
				extracted_lines.append(line)
		
		result = '\n'.join(extracted_lines)
		print(f"[SUCCESS] 成功提取目标人物信息，共 {len(extracted_lines)} 行")
		return result if result else response
	
	def _on_generate_character_description(self) -> None:
		"""生成选中人物的特征描述"""
		import threading
		
		# 获取选中的人物索引（兼容Combobox）
		index = self.char_combobox.current()
		if index < 0:
			return
		
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
				
				prompt = f"""【重要】只分析"{character_name}"一个人物的外貌，不要包含其他人物！

故事内容：
{story_text}

分析目标：仅分析【{character_name}】
⚠️ 注意：故事中可能有多个人物，但你只需要分析【{character_name}】这一个人！

任务要求：
1. 仔细阅读故事，逐字逐句搜索关于【{character_name}】的所有外貌描述
2. 特别关注：外貌、穿着、发型、表情、动作、神态等细节
3. 如果故事中未明确描述某项，根据角色的年龄/性别/职业/背景/性格合理推测
4. 推测要符合常识，要具体明确，不要写"未知"或"不确定"

输出格式（严格按照以下格式，不要添加人名标题，每项都要详细描述）：

性别：[男/女]

年龄：[具体数字或范围，如：25岁、30-35岁]

脸型：[具体描述，如：瓜子脸、圆脸、方脸、长脸、鹅蛋脸等，如果故事有描述则使用故事描述]

肤色：[具体描述，如：白皙、自然、小麦色、偏黑等，如果故事有描述则使用故事描述]

眼睛：[详细描述，如：大眼睛、双眼皮、丹凤眼、单眼皮、深邃的眼神、疲惫的眼神等，包括颜色和形状]

发型：[详细描述长度、颜色、样式，如：披肩长发、黑色、微卷；短发、棕色、齐刘海等]

体型：[具体描述，如：瘦弱、苗条、匀称、健壮、丰满、微胖等，可补充身高信息]

服装：[详细描述风格和具体样式，如：休闲装、白色T恤和牛仔裤；正装、深色西装；居家便服、宽松的棉质长袖等]

特征：[详细描述2-3个最显著的外貌特征，如：面容憔悴、黑眼圈深重；圆脸、大眼睛、酒窝；高鼻梁、薄嘴唇、严肃的表情等]

推测指南（当故事中未明确描述时）：
- 儿童(10岁)→圆脸或娃娃脸，短发/马尾，校服/运动装，活泼的表情
- 学生(16-22岁)→青春的面容，校服/休闲装，清爽的发型
- 职场(25-45岁)→成熟的面容，正装/商务休闲，干练的发型
- 年长(60岁+)→皱纹、花白头发，朴素的服装
- 中国人物→默认黑发黑眼，黄皮肤

重要要求：
✓ 只返回【{character_name}】的信息，不要包含其他人物
✓ 每项都要详细、具体、清晰，不要用模糊词汇
✗ 不要写"未知"、"不确定"、"未提及"等
✓ 优先使用故事中的具体描述，如果故事没有则根据角色特点合理推测
✓ 描述要具体可感，能够让人脑海中形成清晰的形象

正确示例（只有{character_name}一个人，描述详细清晰）：
性别：女
年龄：30-35岁
脸型：瓜子脸，颧骨稍高
肤色：偏白，但因疲惫略显暗淡
眼睛：双眼皮，大眼睛，眼袋明显，眼神疲惫
发型：披肩长发，黑色，微卷，略显凌乱
体型：中等，偏瘦，约165cm
服装：居家便服，宽松的棉质长袖，浅灰色，舒适休闲
特征：面容憔悴，黑眼圈深重，嘴唇略显干燥，整体透露疲惫感
"""
				
				messages = [{"role": "user", "content": prompt}]
				response = client.chat(messages, temperature=0.7)
				
				# 后处理：检查是否包含多个人物
				response_cleaned = self._extract_single_character_info(response.strip(), character_name)
				
				# 更新人物描述
				self.character_list[index]["description"] = response_cleaned
				
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
	
	
	
	