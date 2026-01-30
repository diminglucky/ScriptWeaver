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


class VideoPromptMixin:
	"""Image video_ops 功能"""
	
	def _generate_video_prompt(self) -> str:
		"""
		根据当前分镜头描述生成适合即梦AI的视频提示词
		即梦AI特点：
		1. 强调动态元素和运动轨迹
		2. 细节描述要具体生动
		3. 包含氛围和情绪
		4. 适当的长度（80-150字为佳）
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
			# 分镜头格式：场景 | 人物动作 | 镜头 | 运镜 | 时长 | 转场 | 声音
			parts = [p.strip() for p in shot_desc.split('|')]
			
			# 提取各个部分
			scene_info = parts[0] if len(parts) > 0 else ""  # 场景
			action_info = parts[1] if len(parts) > 1 else ""  # 人物与动作
			shot_type = parts[2] if len(parts) > 2 else ""  # 镜头类型
			camera_movement = parts[3] if len(parts) > 3 else ""  # 运镜
			duration = parts[4] if len(parts) > 4 else "5秒"  # 时长
			transition = parts[5] if len(parts) > 5 else ""  # 转场
			sound = parts[6] if len(parts) > 6 else ""  # 声音
			
			# 如果格式不标准，就把整段当作动作描述
			if len(parts) < 2:
				action_info = shot_desc
			
			# === 构建即梦AI专用提示词 ===
			prompt_parts = []
			
			# 1. 场景环境（包含光线、氛围）
			if scene_info:
				# 提取场景中的环境细节
				scene_enhanced = self._enhance_scene_description(scene_info)
				prompt_parts.append(scene_enhanced)
			
			# 2. 核心动作（即梦AI的关键：明确的动作和运动）
			if action_info:
				# 强化动作描述，突出动态感
				action_enhanced = self._enhance_action_description(action_info)
				prompt_parts.append(action_enhanced)
			
			# 3. 镜头运动（增强动感）
			camera_desc = self._translate_camera_movement(camera_movement, shot_type)
			if camera_desc:
				prompt_parts.append(camera_desc)
			
			# 4. 视觉细节和氛围
			# 根据场景和动作，添加视觉增强
			visual_details = self._add_visual_atmosphere(scene_info, action_info, sound)
			if visual_details:
				prompt_parts.append(visual_details)
			
			# 5. 时长控制（明确告知AI）
			if "秒" in duration:
				prompt_parts.append(f"{duration}视频")
			else:
				prompt_parts.append("5秒视频")
			
			# 组合成最终提示词
			final_prompt = "，".join(filter(None, prompt_parts))
			
			# 长度优化（即梦AI建议80-150字）
			if len(final_prompt) > 150:
				# 优先保留场景和动作，简化其他部分
				final_prompt = "，".join([p for p in prompt_parts[:3] if p])
				if len(final_prompt) > 150:
					final_prompt = final_prompt[:150]
			elif len(final_prompt) < 40:
				# 如果太短，添加通用增强
				final_prompt += "，画面流畅自然，细节清晰"
			
			return final_prompt
			
		except Exception as e:
			print(f"生成视频提示词失败: {e}")
			import traceback
			traceback.print_exc()
			return "生成视频提示词时出错，请检查分镜头描述"
	
	
	def _enhance_scene_description(self, scene: str) -> str:
		"""增强场景描述，添加视觉细节"""
		# 添加光线、氛围等描述
		enhancements = {
			"清晨": "清晨柔和的阳光，空气清新",
			"黄昏": "黄昏暖色调光线，天空渐暗",
			"夜晚": "夜幕降临，灯光点点",
			"深夜": "深夜静谧，光影交错",
			"阴天": "阴沉天色，光线昏暗",
			"雨天": "雨水飘洒，地面湿润反光",
			"室内": "室内环境，自然光或灯光照明",
			"户外": "开阔的户外环境",
			"街道": "街道场景，行人车辆穿行",
			"公园": "公园绿意盎然，环境宜人",
		}
		
		enhanced = scene
		for keyword, description in enhancements.items():
			if keyword in scene and description not in scene:
				# 不重复添加，保持简洁
				break
		
		return enhanced
	
	
	def _enhance_action_description(self, action: str) -> str:
		"""增强动作描述，突出动态感"""
		# 即梦AI需要明确的动作动词
		action_verbs = [
			"走", "跑", "转身", "回头", "挥手", "点头", "摇头",
			"抬头", "低头", "微笑", "皱眉", "注视", "凝视", "眺望",
			"拿", "放", "推", "拉", "开", "关", "举", "抛",
			"坐", "站", "蹲", "跳", "爬", "飞", "游", "漂浮"
		]
		
		# 检查是否包含动作词，如果没有则适当补充动态描述
		has_action = any(verb in action for verb in action_verbs)
		
		if has_action:
			return action
		else:
			# 如果缺少明确动作，添加"进行着"之类的连接
			return action + "的动态过程"
	
	
	def _translate_camera_movement(self, movement: str, shot_type: str) -> str:
		"""翻译镜头运动为适合视频的描述"""
		camera_map = {
			"推进": "镜头缓慢向前推进",
			"推镜": "镜头向前推进靠近主体",
			"拉远": "镜头缓慢向后拉远",
			"拉镜": "镜头向后拉开视野",
			"平移": "镜头水平平稳移动",
			"跟随": "镜头跟随主体运动",
			"环绕": "镜头环绕主体旋转",
			"摇": "镜头左右摇动扫视",
			"摇镜": "镜头摇动",
			"升降": "镜头上下移动",
			"固定": "镜头保持稳定",
			"手持": "手持镜头自然晃动",
		}
		
		result = ""
		for key, value in camera_map.items():
			if key in movement:
				result = value
				break
		
		# 如果没有匹配到，但有运镜描述
		if not result and movement and movement != "固定":
			result = f"镜头{movement}"
		
		return result
	
	
	def _add_visual_atmosphere(self, scene: str, action: str, sound: str) -> str:
		"""根据场景和动作添加视觉氛围描述"""
		atmosphere_parts = []
		
		# 根据场景判断氛围
		if any(word in scene for word in ["夜", "深夜", "黑暗"]):
			atmosphere_parts.append("光影对比强烈")
		elif any(word in scene for word in ["清晨", "黎明", "日出"]):
			atmosphere_parts.append("光线柔和温暖")
		elif any(word in scene for word in ["黄昏", "日落", "傍晚"]):
			atmosphere_parts.append("暖色调光影")
		
		# 根据动作判断节奏
		if any(word in action for word in ["快", "急", "跑", "冲", "飞"]):
			atmosphere_parts.append("节奏快速")
		elif any(word in action for word in ["慢", "缓", "轻", "柔"]):
			atmosphere_parts.append("节奏缓慢")
		
		# 根据声音提示添加氛围
		if sound:
			if any(word in sound for word in ["紧张", "悬疑", "惊悚"]):
				atmosphere_parts.append("氛围紧张")
			elif any(word in sound for word in ["欢快", "轻松", "愉悦"]):
				atmosphere_parts.append("氛围轻松")
			elif any(word in sound for word in ["悲伤", "哀伤", "忧郁"]):
				atmosphere_parts.append("氛围忧郁")
		
		# 通用视觉增强
		atmosphere_parts.append("细节清晰")
		
		# 返回最多2个氛围描述，避免过长
		return "，".join(atmosphere_parts[:2]) if atmosphere_parts else ""
	
	
	
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

	
	