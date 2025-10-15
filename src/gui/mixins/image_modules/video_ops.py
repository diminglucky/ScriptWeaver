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
from ...widgets.character_manager import CharacterPhotoGallery
from ...helpers.character_sheet_builder import CharacterSheetBuilder


class VideoPromptMixin:
	"""Image video_ops 功能"""
	
	def _generate_video_prompt(self) -> str:
		"""
		根据当前分镜头描述生成适合即梦AI的视频提示词
		返回生成的视频提示词文本
		"""
		try:
			# 获取当前选中的分镜描述
			shot_desc = ""
			if hasattr(self, 'parsed_shots') and self.parsed_shots:
				selection = self.shots_listbox.curselection() if hasattr(self, 'shots_listbox') else ()
				if selection and selection[0] >= 0 and selection[0] < len(self.parsed_shots):
					shot_desc = self.parsed_shots[selection[0]]
				
				if not shot_desc:
					# 如果没有分镜描述，尝试从提示词文本框获取
					shot_desc = self.img_txt_prompt_cn.get("1.0", END).strip()
				
				if not shot_desc:
					return "请先选择分镜头或输入图片描述"
			
			# 解析分镜头描述，提取关键信息
			# 分镜头格式通常是：场景 | 内容描述 | 镜头 | 运镜 | 时长
			parts = shot_desc.split('|')
			
			# 提取场景和内容描述
			scene_info = ""
			action_info = ""
			camera_info = ""
			
			if len(parts) >= 2:
				scene_info = parts[0].strip()  # 场景信息
				action_info = parts[1].strip()  # 动作/内容描述
				if len(parts) >= 4:
					camera_info = parts[3].strip()  # 运镜信息
			else:
				# 如果不是标准格式，就直接使用原始描述
				action_info = shot_desc
			
			# 生成即梦AI视频提示词
			# 即梦AI需要强调动作、运动和变化
			video_prompt_parts = []
			
			# 1. 场景设定
			if scene_info:
				video_prompt_parts.append(scene_info)
			
			# 2. 主要动作和变化（这是视频的核心）
			if action_info:
				# 提取动词和动作关键词
				action_keywords = self._extract_action_keywords(action_info)
				if action_keywords:
					video_prompt_parts.append(action_keywords)
				else:
					video_prompt_parts.append(action_info)
			
			# 3. 镜头运动
			camera_movements = {
				"推进": "镜头缓慢推进",
				"拉远": "镜头缓慢拉远",
				"平移": "镜头平稳移动",
				"跟随": "镜头跟随主体",
				"环绕": "镜头环绕",
				"固定": "镜头稳定",
				"摇": "镜头摇动",
				"升降": "镜头升降"
			}
			
			camera_desc = ""
			if camera_info:
				for key, value in camera_movements.items():
					if key in camera_info:
						camera_desc = value
						break
				if not camera_desc and camera_info != "固定":
					camera_desc = f"镜头{camera_info}"
			
			if camera_desc:
				video_prompt_parts.append(camera_desc)
			
			# 4. 添加视频生成的通用提示
			# 强调连贯性和流畅性
			video_enhancement = "画面流畅自然，动作连贯，光影变化自然，5秒视频"
			video_prompt_parts.append(video_enhancement)
			
			# 组合成最终提示词
			final_prompt = "，".join(video_prompt_parts)
			
			# 长度控制（即梦AI通常建议提示词不要太长）
			if len(final_prompt) > 200:
				# 如果太长，去掉一些修饰性内容
				final_prompt = "，".join(video_prompt_parts[:-1])
				if len(final_prompt) > 200:
					final_prompt = final_prompt[:200]
			
			return final_prompt
			
		except Exception as e:
			print(f"生成视频提示词失败: {e}")
			import traceback
			traceback.print_exc()
			return "生成视频提示词时出错，请检查分镜头描述"
	
	
	
	def _on_copy_video_prompt(self) -> None:
		"""复制视频提示词到剪贴板"""
		try:
			text = self.video_prompt_text.get("1.0", END).strip()
			if text and text != "生成图片后，这里会自动显示适合即梦AI的视频提示词...":
				self.clipboard_clear()
				self.clipboard_append(text)
				self.status.set("✅ 视频提示词已复制到剪贴板，可以粘贴到即梦AI中使用")
				messagebox.showinfo("提示", "视频提示词已复制！\n\n请：\n1. 打开即梦AI\n2. 上传刚生成的图片作为首帧\n3. 粘贴提示词\n4. 生成5秒视频")
			else:
				messagebox.showwarning("提示", "请先生成图片，然后会自动生成视频提示词")
		except Exception as e:
			messagebox.showerror("错误", f"复制失败: {str(e)}")

	
	