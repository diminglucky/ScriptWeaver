"""
负责分镜头提取和管理
"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, VERTICAL, Y, messagebox, filedialog
import tkinter as tk
from tkinter import ttk
import os
from PIL import Image, ImageTk

from src.clients.deepseek_client import DeepSeekClient
from src.clients.image_client import OpenAIImageClient
from src.utils.text import sanitize as _sanitize
from ...helpers.image_styles import IMAGE_TYPES, HUNYUAN_STYLE_MAP
from ...helpers.image_helpers import ImagePromptHelper, DescriptionPromptBuilder


class ShotManagerMixin:
	"""负责分镜头提取和管理"""

	@staticmethod
	def _parse_shot_response(response_text: str) -> list[str]:
		"""解析分镜响应文本，提取纯分镜描述列表"""
		shots: list[str] = []
		for line in response_text.strip().split('\n'):
			line = line.strip()
			if not line:
				continue
			if line[0].isdigit() or line.startswith('•') or line.startswith('-'):
				if '.' in line:
					shot_text = line.split('.', 1)[1].strip()
				elif line.startswith('•') or line.startswith('-'):
					shot_text = line[1:].strip()
				else:
					shot_text = line
				if shot_text:
					shots.append(shot_text)
		return shots
	
	def _on_recommend_video_mode(self) -> None:
		"""智能推荐视频模式"""
		story_text = self.output.get("1.0", END).strip()
		if not story_text:
			messagebox.showwarning("提示", "请先在'故事'页生成或粘贴故事内容")
			return
		
		# 分析故事特征
		story_length = len(story_text)
		
		# 统计场景转换关键词
		scene_keywords = ['突然', '这时', '随后', '接着', '然后', '于是', '转身', '走进', '来到', 
						  '回到', '看到', '听到', '发现', '意识到', '想起', '记得']
		scene_count = sum(story_text.count(kw) for kw in scene_keywords)
		
		# 统计情节复杂度关键词
		complexity_keywords = ['但是', '然而', '不料', '没想到', '原来', '竟然', '居然', 
							   '转折', '突变', '真相', '秘密', '回忆', '闪回']
		complexity_score = sum(story_text.count(kw) for kw in complexity_keywords)
		
		# 统计人物数量（粗略估计）
		character_keywords = ['他', '她', '我', '你', '他们', '她们', '我们']
		has_multiple_characters = sum(story_text.count(kw) for kw in character_keywords) > 20
		
		# 推荐逻辑
		recommendation = ""
		mode = ""
		reason = []
		
		if story_length < 1000:
			mode = "brief"
			recommendation = "🎬 简短视频(8-12)"
			reason.append(f"• 故事较短（{story_length}字）")
			reason.append("• 适合快节奏短视频")
			reason.append("• 8-12个镜头足够覆盖核心情节")
		elif story_length < 2500:
			if complexity_score > 5 or scene_count > 10:
				mode = "video"
				recommendation = "🎬 平衡视频(15-25) ⭐推荐"
				reason.append(f"• 故事长度适中（{story_length}字）")
				reason.append(f"• 情节有一定复杂度（转折词{complexity_score}个）")
				reason.append("• 15-25个镜头能完整呈现故事")
			else:
				mode = "normal"
				recommendation = "🎬 标准视频(15-22)"
				reason.append(f"• 故事长度标准（{story_length}字）")
				reason.append("• 情节相对简单流畅")
				reason.append("• 15-22个镜头刚好合适")
		elif story_length < 5000:
			if complexity_score > 8 or has_multiple_characters:
				mode = "detailed"
				recommendation = "🎬 精细视频(25-40)"
				reason.append(f"• 故事较长（{story_length}字）")
				reason.append(f"• 情节复杂（转折词{complexity_score}个，场景{scene_count}处）")
				reason.append("• 需要25-40个镜头细致呈现")
			else:
				mode = "video"
				recommendation = "🎬 平衡视频(15-25)"
				reason.append(f"• 故事较长（{story_length}字）")
				reason.append("• 情节适中，不太复杂")
				reason.append("• 15-25个镜头平衡完整性和精简度")
		else:
			mode = "detailed"
			recommendation = "🎬 精细视频(25-40)"
			reason.append(f"• 故事很长（{story_length}字）")
			reason.append(f"• 需要充足的镜头数量来完整叙事")
			reason.append("• 25-40个镜头才能展现所有重要时刻")
		
		# 显示推荐结果
		reason_text = "\n".join(reason)
		result = messagebox.askyesno(
			"智能推荐结果", 
			f"📊 故事分析：\n"
			f"字数：{story_length} 字\n"
			f"场景转换：约 {scene_count} 处\n"
			f"情节复杂度：{'高' if complexity_score > 8 else '中' if complexity_score > 4 else '低'}\n\n"
			f"💡 推荐模式：\n{recommendation}\n\n"
			f"📝 推荐理由：\n{reason_text}\n\n"
			f"是否立即使用推荐模式生成分镜？"
		)
		
		if result:
			# 用户确认，直接生成
			self._on_img_extract_shots(mode=mode)
		else:
			self._ui(self.status.set, f"💡 推荐使用 {recommendation}")

	
	def _on_img_extract_shots(self, mode="normal") -> None:
		"""从故事生成分镜列表
		
		Args:
			mode: 分镜详细程度
				- "brief": 大致版，8-12个分镜，覆盖主要情节
				- "normal": 标准版，12-20个分镜（保持兼容）
				- "detailed": 详细版，20-30个分镜，细致分割每个场景
				- "video": 视频版，10-15个分镜，专为视频制作优化
		"""
		story_text = self.output.get("1.0", END).strip()
		if not story_text:
			messagebox.showwarning("提示", "请先在'故事'页生成或粘贴正文内容，然后再生成分镜")
			return
		
		# 分镜生成：根据模型路由选择 API
		fallback_provider = None
		if hasattr(self, 'quick_story_api'):
			fallback_provider = self.quick_story_api.get()
		if not fallback_provider and hasattr(self, 'api_preset'):
			fallback_provider = self.api_preset.get()
		fallback_model = None
		if hasattr(self, 'story_model_var'):
			fallback_model = self.story_model_var.get()
		elif hasattr(self, 'model'):
			fallback_model = self.model.get()
		
		api_config = self._resolve_task_api("image_shot_extract", fallback_provider=fallback_provider, fallback_model=fallback_model)
		selected_api = api_config.get("provider", "")
		api_key = _sanitize(api_config.get("key", ""))
		base_url = _sanitize(api_config.get("base_url", ""))
		model = _sanitize(api_config.get("model", ""))
		
		if not api_key:
			messagebox.showwarning("提示", f"请先在故事生成页面配置 {selected_api} 的API Key")
			return
		
		# 根据模式设置不同的提示词
		if mode == "brief":
			shot_count = "8-12"
			mode_name = "简短视频"
			inst = (
				"请把以下故事正文拆解为**简短视频分镜脚本**，生成8-12个关键镜头，"
				"**只选取最核心的场景**，快节奏叙述故事的主要情节和高潮时刻。\n\n"
				"每个镜头包含（用 | 分隔）：\n"
				"1. **场景**：地点、环境、时间\n"
				"2. **人物与动作**：主体、动作、表情\n"
				"3. **镜头**：特写CU/中景MS/全景WS/远景LS\n"
				"4. **运镜**：固定/推镜/拉镜/摇镜/跟随\n"
				"5. **时长**：如'3-5秒''8-10秒'\n"
				"6. **转场**：切/淡入淡出/闪白（最后写'结束'）\n"
				"7. **声音**：环境音/配乐/对白提示\n\n"
				"格式示例：\n"
				"1. 深夜街道，路灯昏暗 | 女主角快步行走，不时回头 | 全景(WS) | 跟随 | 4-5秒 | 淡入 | 紧张配乐，脚步声\n\n"
				"输出格式：序号. 场景 | 人物与动作 | 镜头 | 运镜 | 时长 | 转场 | 声音\n"
				"注意：只输出清单，不要其他文字。"
			)
		elif mode == "video":
			shot_count = "15-25"
			mode_name = "平衡视频"
			inst = (
				"请把以下故事正文拆解为**专业平衡视频分镜脚本**，生成15-25个镜头，"
				"在完整性和精简度之间找到平衡，适合大多数视频项目。\n\n"
				"每个镜头包含（用 | 分隔）：\n"
				"1. **场景**：具体地点、环境、时间（白天/夜晚/傍晚）\n"
				"2. **人物与动作**：主体、动作、表情状态\n"
				"3. **镜头**：特写CU/近景MS/中景MCU/全景WS/远景LS/过肩OTS/主观POV\n"
				"4. **运镜**：固定/推镜/拉镜/摇镜/跟随/环绕/升降（如'缓慢推进''快速拉远''平稳跟随'）\n"
				"5. **时长**：建议停留时间，如'3-5秒''8-10秒''瞬间闪过'\n"
				"6. **转场**：切/淡入淡出/叠化/闪白/黑场（最后一个写'结束'）\n"
				"7. **声音**：环境音/音乐情绪/对白提示/音效\n\n"
				"格式示例：\n"
				"1. 深夜城市街道，路灯昏暗，薄雾 | 空旷街道，远处车灯 | 远景(LS) | 缓慢右摇 | 5-6秒 | 淡入 | 低沉环境音，车声\n"
				"2. 公寓楼外景，三楼灯亮 | 窗帘后人影移动 | 中景(MCU) | 固定，缓慢推进 | 4-5秒 | 切 | 环境音渐弱\n\n"
				"输出格式：序号. 场景 | 人物与动作 | 镜头 | 运镜 | 时长 | 转场 | 声音\n"
				"注意：保持节奏流畅，情绪转折用不同镜头，关键情节特写+慢镜，过渡场景全景+快节奏。"
			)
		elif mode == "detailed":
			shot_count = "25-40"
			mode_name = "精细视频"
			inst = (
				"请把以下故事正文拆解为**极其详细的视频分镜脚本**，生成25-40个镜头，"
				"**细致分割每个场景、情节转折、人物表情变化**，力求电影级的完整叙事。\n\n"
				"分镜原则（确保完整性）：\n"
				"1. 场景转换必须新开分镜\n"
				"2. 人物表情或动作变化时新开分镜\n"
				"3. 情节转折点单独成镜\n"
				"4. 对话场景拆分多角度（正反打、过肩镜头）\n"
				"5. 氛围细节镜头独立展示\n"
				"6. 重要物件特写单独成镜\n\n"
				"每个镜头包含（用 | 分隔）：\n"
				"1. **场景**：具体地点、环境细节、时间\n"
				"2. **人物与动作**：主体、服饰、姿态、表情、具体动作\n"
				"3. **镜头**：大特写ECU/特写CU/近景MS/中景MCU/全景WS/远景LS/定场镜头/过肩OTS/主观POV/高角度/低角度\n"
				"4. **运镜**：固定/推镜/拉镜/摇镜/跟随/环绕/升降/摇臂（描述速度和感觉，如'极慢推进''快速环绕'）\n"
				"5. **时长**：精确的停留时间，如'2-3秒''5-7秒''10-15秒'\n"
				"6. **转场**：切/淡入淡出/叠化/擦除/闪白/闪黑/黑场（最后写'结束'）\n"
				"7. **声音**：环境音/配乐变化/对白内容/音效细节\n\n"
				"格式示例：\n"
				"1. 雨夜街角，霓虹灯闪烁，地面积水 | 女主角撑伞独行，黑色风衣，眼神疲惫 | 全景(WS) | 缓慢推进 | 6-8秒 | 淡入 | 雨声，远处车声，忧伤钢琴\n\n"
				"输出格式：序号. 场景 | 人物与动作 | 镜头 | 运镜 | 时长 | 转场 | 声音\n"
				"注意：只输出清单，覆盖所有重要时刻，追求电影级完整度。"
			)
		else:  # normal mode - 改为标准视频
			shot_count = "15-22"
			mode_name = "标准视频"
			inst = (
				"请把以下故事正文拆解为**标准视频分镜脚本**，生成15-22个镜头，"
				"完整覆盖故事情节，节奏适中，既保证叙事完整又不过于冗长。\n\n"
				"每个镜头包含（用 | 分隔）：\n"
				"1. **场景**：地点、环境、时间\n"
				"2. **人物与动作**：主体、动作、表情状态\n"
				"3. **镜头**：特写CU/近景MS/中景MCU/全景WS/远景LS/过肩OTS/主观POV\n"
				"4. **运镜**：固定/推镜/拉镜/摇镜/跟随/环绕/升降（如'缓慢推进''快速拉远'）\n"
				"5. **时长**：建议停留时间，如'3-5秒''8-10秒'\n"
				"6. **转场**：切/淡入淡出/叠化/闪白/黑场（最后一个写'结束'）\n"
				"7. **声音**：环境音/配乐情绪/对白/音效\n\n"
				"格式示例：\n"
				"1. 办公室走廊，夜晚，日光灯闪烁 | 男主角疲惫地走着，眼神空洞 | 中景(MCU) | 跟随移动 | 5-6秒 | 淡入 | 空调嗡嗡声，低沉配乐\n\n"
				"输出格式：序号. 场景 | 人物与动作 | 镜头 | 运镜 | 时长 | 转场 | 声音\n"
				"注意：只输出清单，覆盖完整故事线。"
			)
		
		# 在后台线程中执行耗时操作
		def task():
			try:
				self.set_busy(True)
				self._ui(self.status.set, f"🎬 正在使用 {selected_api} 生成{mode_name}分镜（目标{shot_count}个）...")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status(f"生成{mode_name}分镜...", "🎬")
				
				client = DeepSeekClient(
					api_key=api_key,
					base_url=base_url,
					model=model,
				)
				
				self._ui(self.status.set, f"🤖 {selected_api} 正在分析故事并生成{mode_name}分镜...")
				
				resp = client.chat([
					{"role": "system", "content": inst},
					{"role": "user", "content": story_text},
				], temperature=max(0.4, self.temperature.get() - 0.2))
				
				self._ui(self.status.set, "📋 解析分镜头列表...")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("解析分镜中...", "📋")
				
				# 解析分镜列表
				shots = self._parse_shot_response(resp)
				
				# 更新分镜列表框
				if shots:
					self._ui(self.status.set, f"✅ 更新分镜显示...")
					
					def update_shots_ui():
						# 更新Listbox
						self.shots_listbox.config(state=NORMAL)
						self.shots_listbox.delete(0, END)
						for i, shot in enumerate(shots):
							# 显示序号和分镜描述（限制长度以便阅读）
							display_text = f"{i+1}. {shot[:80]}..." if len(shot) > 80 else f"{i+1}. {shot}"
							self.shots_listbox.insert(END, display_text)
						
						# 保存完整的分镜列表
						self.parsed_shots = shots
						
						# 默认选中第一个分镜
						self.shots_listbox.selection_set(0)
						self.shots_listbox.activate(0)
						# 显示第一个分镜
						self._on_shot_listbox_selected(None)
						
						self._ui(self.status.set, f"🎬 已生成{mode_name} {len(shots)} 个分镜（点击列表中的分镜即可选择）")
						# 更新顶部状态栏
						if hasattr(self, 'update_header_status'):
							self.update_header_status("分镜生成完成", "✅")
					
					self._ui(update_shots_ui)
			except Exception as e:
				self._ui(messagebox.showerror, "错误", str(e))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("分镜生成失败", "❌")
			finally:
				self.set_busy(False)
		
		import threading
		threading.Thread(target=task, daemon=True).start()
	
	
	def _on_shot_listbox_selected(self, event) -> None:
		"""当在Listbox中选择分镜时，自动识别并选择参考人物"""
		if not hasattr(self, 'parsed_shots') or not self.parsed_shots:
			return
		
		selection = self.shots_listbox.curselection()
		if not selection:
			return
		
		selected_index = selection[0]
		if selected_index < 0 or selected_index >= len(self.parsed_shots):
			return
		
		# 获取选中的分镜文本
		current_shot = self.parsed_shots[selected_index]
		
		# 显示状态
		self._ui(self.status.set, f"已选择第 {selected_index+1} 个分镜，正在识别人物...")
		
		# 智能识别并自动选择参考人物（延迟执行以确保UI更新）
		self.after(50, lambda: self._auto_select_characters_from_shot(current_shot, ""))
	
	
	def _on_shot_selected(self, event) -> None:
		"""兼容性函数：当使用Combobox选择分镜时（已废弃，保留以防代码引用）"""
		# 此函数已被 _on_shot_listbox_selected 替代
		pass
	
	
	def _on_img_prompt_from_current_shot(self) -> None:
		"""从当前选中的分镜生成中文图片描述"""
		if not hasattr(self, 'parsed_shots') or not self.parsed_shots:
			messagebox.showwarning("提示", "请先生成分镜")
			return
		
		selection = self.shots_listbox.curselection()
		if not selection:
			messagebox.showwarning("提示", "请先在列表中选择一个分镜")
			return
		
		selected_index = selection[0]
		if selected_index < 0 or selected_index >= len(self.parsed_shots):
			messagebox.showwarning("提示", "请先在列表中选择一个分镜")
			return
		
		current_shot = self.parsed_shots[selected_index]
		
		story_text = self.output.get("1.0", END).strip() if hasattr(self, 'output') else ""
		scene = self.img_entry_scene.get().strip() if hasattr(self, 'img_entry_scene') else ""
		roles = self.img_txt_roles.get("1.0", END).strip() if hasattr(self, 'img_txt_roles') else ""
		img_type = self.img_type.get() if hasattr(self, 'img_type') else "写实照片"
		
		# 根据图片类型定义不同的风格描述
		style_instructions = {
			"写实照片": "高清摄影作品，写实风格，自然光线，真实质感，细节丰富",
			"日系动漫": "日系动漫风格，精美作画，色彩鲜艳，人物可爱，动漫渲染",
			"3D渲染": "3D渲染，高品质建模，精致材质，专业渲染，光影逼真",
			"水彩画": "水彩画风格，色彩柔和，笔触自然，艺术感强，优雅细腻",
			"油画": "油画质感，笔触厚重，色彩浓郁，古典艺术风格，富有层次",
			"素描": "素描风格，线条流畅，黑白灰调，光影明确，艺术素描",
			"赛博朋克": "赛博朋克风格，霓虹灯光，未来科技感，暗黑氛围，高科技元素",
			"蒸汽朋克": "蒸汽朋克风格，机械齿轮，复古科技，维多利亚时代，工业美学",
			"像素风": "像素艺术风格，8bit/16bit画风，复古游戏美术，像素化",
			"中国风": "中国传统绘画风格，水墨意境，古典韵味，诗意氛围，传统美学",
			"国风插画": "国风插画，现代中国美学，精美线条，典雅色彩，细腻构图",
			"古风": "古风，传统汉服，古代建筑，历史氛围，唐宋美学，诗意画面",
			"仙侠": "仙侠奇幻，修仙世界，天宫仙境，飘逸衣袍，仙气缭绕，云雾山水",
			"武侠": "武侠江湖，侠客剑客，轻功飞跃，竹林烟雨，山水意境，武林氛围",
			"水墨画": "中国水墨画，笔墨韵味，黑白灰调，留白意境，禅意美学，传统笔法",
			"工笔画": "工笔重彩，精细笔法，传统颜料，古典构图，细腻刻画，层次丰富",
			"敦煌壁画": "敦煌壁画风格，飞天仙女，佛教艺术，唐代色彩，壁画质感，古典神圣",
			"恐怖": "恐怖氛围，阴暗诡异，诡谲光影，惊悚元素，不安情绪，恐惧感",
			"惊悚": "惊悚风格，悬疑紧张，戏剧化光影，神秘阴影，紧张氛围，惊心动魄",
			"诡异": "诡异风格，超现实，异世界感，诡谲氛围，不祥预兆，怪异细节",
			"悬疑": "悬疑风格，黑色电影，戏剧阴影，侦探美学，推理氛围，谜团感",
			"玄幻": "玄幻奇幻，神秘元素，灵兽异兽，磅礴山水，修真世界，灵力光芒",
			"科幻": "科幻未来，高科技，太空场景，先进文明，霓虹光效，未来都市",
			"魔幻": "魔幻世界，神话生物，魔法森林，神秘光芒，奇幻冒险，魔法元素"
		}
		
		style_desc = style_instructions.get(img_type, f"{img_type}风格")
		
		# 检测是否使用腾讯混元（根据preset或provider判断）
		is_hunyuan = False
		if hasattr(self, 'img_api_preset'):
			preset_name = self.img_api_preset.get()
			if "腾讯混元" in preset_name or "hunyuan" in preset_name.lower():
				is_hunyuan = True
		
		# 🎯 获取是否有参考照片（需要在task函数外部定义，以便inst使用）
		selected_characters = self._get_selected_reference_characters()
		has_photo = any(char.get("photo_path") for char in selected_characters if char)
		
		# 根据API类型和是否有照片设置不同的描述详细程度
		if is_hunyuan:
			# 腾讯混元：简洁版，200字以内
			char_limit = "180字以内"
			if has_photo:
				# 图生图模式：只描述动态元素
				inst = (
					f"你是专业视觉设计师。这是图生图模式，参考图片已包含人物外貌。\n"
					f"生成简洁的中文图片描述，用于腾讯混元生成【{img_type}】风格的图片。\n\n"
					f"【风格】{style_desc}\n\n"
					f"【只描述动态元素】：\n"
					f"1. 动作：具体动作（站立、行走、坐下、蹲下、转身等）、手部动作\n"
					f"2. 表情：具体表情（微笑、严肃、惊讶、沉思、悲伤等）、眼神\n"
					f"3. 姿势：身体姿态（挺胸、驼背、放松、紧张等）\n"
					f"4. 场景：地点、物品、光线、氛围\n"
					f"5. 镜头：景别（全身照/中景/特写）、角度\n\n"
					f"【禁止描述】：不要描述年龄、性别、发型、脸型、肤色、体型、服装等外貌特征。\n\n"
					f"【格式示例】：站立、双手插兜、微笑、办公室、自然光、全身照、中景平视\n\n"
					f"要求：控制在{char_limit}，只输出描述文本。"
				)
			else:
				# 文生图模式：完整描述
				inst = (
					f"你是专业视觉设计师。基于分镜描述，生成简洁精确的中文图片描述，"
					f"用于腾讯混元生成【{img_type}】风格的图片。\n\n"
					f"【风格】{style_desc}\n\n"
					f"【描述元素】：\n"
					f"1. 人物（如有）：年龄、性别、发型、服饰、表情、动作、姿势\n"
					f"2. 环境：地点、主要物品、色调\n"
					f"3. 光线：光源、时间、氛围\n"
					f"4. 镜头：景别（全身照/中景/特写）、角度、构图\n\n"
					f"【格式】简洁短语，用顿号和逗号连接。\n"
					f"示例：25岁女性、黑色长发、白色医生制服、疲惫眼神、双手插口袋、站立、深夜医院走廊、"
					f"白墙灰地板、顶部日光灯、中景平视、寂静压抑\n\n"
					f"要求：控制在{char_limit}，如有人物设定请按名字匹配特征，只描述当前分镜中出现的人物。"
				)
		else:
			# OpenAI/DALL-E等
			if has_photo:
				# 图生图模式：只描述动态元素
				char_limit = "200-300字"
				inst = (
					f"你是专业视觉设计师。这是图生图模式，参考图片已包含人物外貌。\n"
					f"生成中文图片描述，用于生成高质量的【{img_type}】风格图片。\n\n"
					f"【风格】{style_desc}\n\n"
					f"【只描述动态元素】：\n"
					f"1. 动作：具体动作（站立、行走、坐下、蹲下、转身、跑步等）、手部动作、身体姿势\n"
					f"2. 表情：具体表情（微笑、严肃、惊讶、沉思、悲伤、愤怒等）、眼神方向\n"
					f"3. 场景环境：地点、主要物品、背景、光线、天气、氛围\n"
					f"4. 镜头：景别（全身照/中景/特写）、角度（平视/俯视/仰视）、构图\n\n"
					f"【禁止描述】：不要描述年龄、性别、发型、脸型、肤色、体型、身高、服装款式颜色等外貌特征。\n\n"
					f"【输出要求】：\n"
					f"- 长度：{char_limit}，自然流畅\n"
					f"- 格式：流畅的中文段落\n"
					f"- 重点突出动作、表情、场景\n"
					f"- 必须明确指定镜头景别（全身照/中景/特写）"
				)
			else:
				# 文生图模式：完整描述
				char_limit = "300-400字"
				inst = (
					f"你是专业视觉设计师。基于分镜描述，生成简洁精确的中文图片描述，"
					f"用于生成高质量的【{img_type}】风格图片。\n\n"
					f"【风格】{style_desc}\n\n"
					f"【核心元素】\n"
					f"1. 人物（如有）：年龄、性别、发型、服饰、表情、动作、姿势\n"
					f"2. 环境：地点、主要物品、色调\n"
					f"3. 光线：光源、时间、氛围\n"
					f"4. 镜头：景别（全身照/中景/特写）、角度、构图\n\n"
					f"【输出要求】\n"
					f"- 长度：{char_limit}，自然流畅\n"
					f"- 如有人物设定，按名字匹配特征\n"
					f"- 只描述当前分镜中的人物\n"
					f"- 必须明确指定镜头景别"
				)
		
		# 图片描述生成：根据模型路由选择 API
		fallback_provider = None
		if hasattr(self, 'quick_story_api'):
			fallback_provider = self.quick_story_api.get()
		if not fallback_provider and hasattr(self, 'api_preset'):
			fallback_provider = self.api_preset.get()
		fallback_model = None
		if hasattr(self, 'story_model_var'):
			fallback_model = self.story_model_var.get()
		elif hasattr(self, 'model'):
			fallback_model = self.model.get()
		
		api_config = self._resolve_task_api("image_shot_to_desc", fallback_provider=fallback_provider, fallback_model=fallback_model)
		selected_api = api_config.get("provider", "")
		api_key = _sanitize(api_config.get("key", ""))
		base_url = _sanitize(api_config.get("base_url", ""))
		model = _sanitize(api_config.get("model", ""))
		
		if not api_key:
			messagebox.showwarning("提示", f"请先在故事生成页面配置 {selected_api} 的API Key")
			return
		
		# 在后台线程中执行耗时操作
		def task():
			try:
				self.set_busy(True)
				
				# 🎯 检查是否有参考人物照片（图生图模式）
				selected_characters = self._get_selected_reference_characters()
				has_photo = any(char.get("photo_path") for char in selected_characters if char)
				
				mode_text = "图生图（只生成动作表情）" if has_photo else "文生图（完整描述）"
				self._ui(self.status.set, f"📸 正在使用 {selected_api} 生成图片描述（{mode_text}，第{selected_index+1}个分镜）...")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("生成图片描述...", "📸")
				client = DeepSeekClient(
					api_key=api_key,
					base_url=base_url,
					model=model,
				)
				# 根据API类型调整上下文长度
				context_length = 500 if is_hunyuan else 1000
				
				# 构建用户提示词
				user_parts = [f"【目标图片类型】{img_type}\n"]
				
				# 🎯 根据是否有照片，使用不同的提示策略
				if has_photo:
					# 图生图模式：只生成动态元素
					char_names = [c['name'] for c in selected_characters if c.get('name')]
					user_parts.append(f"【图生图模式】参考图片已包含人物外貌（{', '.join(char_names)}），只需描述动态元素。\n\n")
					user_parts.append(f"【重要】不要描述人物的外貌特征（年龄、性别、发型、脸型、肤色、体型、服装等静态特征）。\n")
					user_parts.append(f"只描述：\n")
					user_parts.append(f"1. 动作（站立、行走、坐下、转身等具体动作）\n")
					user_parts.append(f"2. 表情（微笑、严肃、惊讶、沉思等具体表情）\n")
					user_parts.append(f"3. 姿势（手部动作、身体姿态）\n")
					user_parts.append(f"4. 场景环境（地点、物品、光线、氛围）\n")
					user_parts.append(f"5. 镜头景别（全身照/中景/特写）\n\n")
				elif roles:
					user_parts.append(f"【‼️ 人物设定档案 - 必须严格遵守】\n{roles}\n\n")
					user_parts.append(f"⚠️ 人物一致性规则（极其重要）：\n")
					user_parts.append(f"1. **人物-特征绑定**：以上每个人物的名字与其外貌、服饰特征是永久绑定的\n")
					user_parts.append(f"2. **按名字匹配**：当分镜中提到某个人物的名字时，必须使用该人物在设定中的所有特征\n")
					user_parts.append(f"3. **选择性出现**：只描述当前分镜中实际出现的人物，未出现的人物不要描述\n")
					user_parts.append(f"4. **再次出现一致**：如果某人物在前面的场景没出现，但在当前场景出现，必须使用设定中该人物的特征\n")
					user_parts.append(f"5. **多人物区分**：如果场景中有多个人物，要清楚区分每个人，按各自的名字使用对应的特征\n")
					user_parts.append(f"6. **特征不混淆**：绝不允许将A人物的特征用在B人物身上，每个人物的特征独立且固定\n\n")
					user_parts.append(f"例如：\n")
					user_parts.append(f"- 如果分镜说「李明走进房间」→ 只描述李明，使用李明的设定特征\n")
					user_parts.append(f"- 如果分镜说「王芳和李明对话」→ 描述两人，分别使用各自的设定特征\n")
					user_parts.append(f"- 如果分镜说「一个空房间」→ 不描述任何人物，只描述环境\n")
					user_parts.append(f"- 如果王芳在前3个场景没出现，第5个场景才出现 → 第5个场景中王芳的特征与设定完全一致\n\n")
				else:
					user_parts.append(f"【人物设定】从故事上下文和分镜描述中提取人物特征，为每个人物建立档案，")
					user_parts.append(f"并在该人物每次出现时保持特征一致。不同人物要清楚区分，不要混淆。\n\n")
				
				# 当前分镜
				user_parts.append(f"【当前分镜描述】\n{current_shot}\n\n")
				
				# 故事上下文
				user_parts.append(f"【故事上下文】\n{story_text[:context_length] if story_text else '无相关上下文'}\n\n")
				
				# 场景设定
				if scene:
					user_parts.append(f"【场景设定】\n{scene}\n\n")
				
				# 一致性强调（只在文生图模式下添加）
				if not has_photo:
					user_parts.append(f"【描述生成要求】\n")
					user_parts.append(f"1. **识别当前场景人物**：仔细阅读当前分镜描述，识别场景中出现的具体人物（根据名字或角色）\n")
					user_parts.append(f"2. **匹配人物特征**：为每个出现的人物，从人物设定档案中找到对应的特征\n")
					user_parts.append(f"3. **只描述在场人物**：只描述当前分镜中实际出现的人物，不在场的人物不要提及\n")
					user_parts.append(f"4. **保持特征一致**：每个人物的年龄、性别、发型、发色、肤色、体型、五官、服饰必须与设定完全一致\n")
					user_parts.append(f"5. **动态元素变化**：根据分镜要求，只改变表情、动作、姿态等动态元素，静态特征保持不变\n")
					user_parts.append(f"6. **多人物区分**：如果场景中有多人，要清楚描述每个人的特征，不要混淆或遗漏\n")
					user_parts.append(f"7. **服饰一致**：除非分镜明确说明换装，否则服装款式、颜色、材质保持一致\n")
					user_parts.append(f"8. **细节补充**：如果设定中缺少某些细节，可适当添加，但要符合该人物的身份和场景，且后续保持一致\n\n")
				
				# 生成要求
				user_parts.append(f"请生成中文图片描述（{char_limit}），体现{img_type}风格。")
				
				user = "".join(user_parts)
				resp = client.chat([
				{"role": "system", "content": inst},
				{"role": "user", "content": user},
				], temperature=max(0.5, self.temperature.get() - 0.1))
				
				self._ui(self.status.set, "✅ 更新图片描述...")
			
				description = resp.strip()
			
				# 根据API类型限制描述长度
				max_desc_length = 200 if is_hunyuan else 500
				if len(description) > max_desc_length:
					# 在句号、逗号或顿号处截断
					truncated = description[:max_desc_length]
					last_punct = max(truncated.rfind('。'), truncated.rfind('，'), truncated.rfind('、'))
					if last_punct > int(max_desc_length * 0.8):
						description = truncated[:last_punct + 1]
					else:
						description = truncated
			
				self._ui(self.img_txt_prompt_cn.delete, "1.0", END)
				self._ui(self.img_txt_prompt_cn.insert, END, description)
			
				# 显示字数统计
				char_count = len(description)
				api_type = "腾讯混元简洁版" if is_hunyuan else "精简版"
				self._ui(self.status.set, f"✨ 已生成【{img_type}】{api_type}图片描述（{char_count}字，可编辑后生成）")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("图片描述完成", "✅")
			
				# 智能识别并自动选择参考人物
				self.after(100, lambda: self._auto_select_characters_from_shot(current_shot, description))
			except Exception as e:
				self._ui(messagebox.showerror, "错误", str(e))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("生成描述失败", "❌")
			finally:
				self.set_busy(False)
		
		import threading
		threading.Thread(target=task, daemon=True).start()

	
	def _on_batch_generate_all_shots(self) -> None:
		"""批量生成所有分镜的图片（借鉴自 DirectorAI）
		
		功能：
		1. 自动为每个分镜生成图片描述
		2. 使用角色三视图作为参考保持一致性
		3. 支持中断和恢复
		"""
		if not hasattr(self, 'parsed_shots') or not self.parsed_shots:
			messagebox.showwarning("提示", "请先生成分镜列表")
			return
		
		if not self.current_project:
			messagebox.showwarning("提示", "请先创建或打开一个项目")
			return
		
		shot_count = len(self.parsed_shots)
		
		# 确认对话框
		result = messagebox.askyesno(
			"批量生成确认",
			f"即将为 {shot_count} 个分镜生成图片\n\n"
			f"⚠️ 注意事项：\n"
			f"• 每张图片需要调用API，会产生费用\n"
			f"• 预计耗时：{shot_count * 15}-{shot_count * 30} 秒\n"
			f"• 生成过程中可以取消\n\n"
			f"是否继续？"
		)
		
		if not result:
			return
		
		# 获取参考人物（如果有三视图，优先使用）
		reference_images = []
		for char in self.character_list:
			if isinstance(char, dict):
				if char.get("turnaround_image"):
					reference_images.append(char["turnaround_image"])
				elif char.get("photo_path"):
					reference_images.append(char["photo_path"])
			else:
				if hasattr(char, 'turnaround_image') and char.turnaround_image:
					reference_images.append(char.turnaround_image)
				elif hasattr(char, 'primary_photo') and char.primary_photo:
					reference_images.append(char.primary_photo)
		
		# 保存中断标志
		self._batch_cancelled = False
		
		# 禁用按钮
		if hasattr(self, 'btn_batch_generate'):
			self.btn_batch_generate.config(state=DISABLED, text="⏳ 生成中...")
		
		def batch_generate_thread():
			generated_count = 0
			failed_count = 0
			
			try:
				import time
				from pathlib import Path
				
				shots_dir = self.current_project.project_dir / "shots"
				shots_dir.mkdir(parents=True, exist_ok=True)
				
				for i, shot in enumerate(self.parsed_shots):
					# 检查是否被取消
					if self._batch_cancelled:
						self.after(0, lambda: self._ui(self.status.set, f"⚠️ 批量生成已取消，已完成 {generated_count}/{shot_count}"))
						break
					
					# 更新进度
					self.after(0, lambda idx=i, total=shot_count: self._ui(self.status.set, 
						f"🎨 [{idx+1}/{total}] 正在生成第 {idx+1} 个分镜的图片..."
					))
					if hasattr(self, 'update_header_status'):
						self.after(0, lambda idx=i, total=shot_count: self.update_header_status(
							f"[{idx+1}/{total}] 批量生成...", "🎨"
						))
					
					try:
						# 选择当前分镜
						self.after(0, lambda idx=i: self.shots_listbox.selection_clear(0, END))
						self.after(0, lambda idx=i: self.shots_listbox.selection_set(idx))
						time.sleep(0.1)
						
						# 生成图片描述
						self._generate_shot_description_sync(shot, i)
						time.sleep(0.5)
						
						# 生成图片
						self._generate_shot_image_sync(i, reference_images)
						
						generated_count += 1
						
						# 短暂延迟，避免API限流
						time.sleep(1)
						
					except Exception as e:
						print(f"❌ 分镜 {i+1} 生成失败: {e}")
						failed_count += 1
						continue
				
				# 完成
				def on_complete():
					self._ui(self.status.set, f"✅ 批量生成完成！成功 {generated_count} 张，失败 {failed_count} 张")
					if hasattr(self, 'update_header_status'):
						self.update_header_status("批量完成", "✅")
					
					messagebox.showinfo(
						"批量生成完成",
						f"生成结果：\n\n"
						f"✅ 成功：{generated_count} 张\n"
						f"❌ 失败：{failed_count} 张\n\n"
						f"保存位置：{shots_dir}"
					)
				
				self.after(0, on_complete)
				
			except Exception as e:
				import traceback
				traceback.print_exc()
				self.after(0, lambda: messagebox.showerror("错误", f"批量生成失败: {e}"))
			finally:
				if hasattr(self, 'btn_batch_generate'):
					self.after(0, lambda: self.btn_batch_generate.config(state=NORMAL, text="🚀 批量生成所有分镜"))
		
		import threading
		threading.Thread(target=batch_generate_thread, daemon=True).start()
	
	def _generate_shot_description_sync(self, shot: str, index: int) -> str:
		"""同步生成单个分镜的图片描述"""
		# 分镜转描述：根据模型路由选择 API
		fallback_provider = None
		if hasattr(self, 'quick_story_api'):
			fallback_provider = self.quick_story_api.get()
		if not fallback_provider and hasattr(self, 'api_preset'):
			fallback_provider = self.api_preset.get()
		fallback_model = None
		if hasattr(self, 'story_model_var'):
			fallback_model = self.story_model_var.get()
		elif hasattr(self, 'model'):
			fallback_model = self.model.get()
		
		api_config = self._resolve_task_api("image_shot_to_desc", fallback_provider=fallback_provider, fallback_model=fallback_model)
		api_key = _sanitize(api_config.get("key", ""))
		base_url = _sanitize(api_config.get("base_url", ""))
		model = _sanitize(api_config.get("model", ""))
		
		if not api_key:
			return shot  # 如果没有API Key，直接使用分镜文本
		
		# 简化的描述生成
		img_type = self.img_type.get() if hasattr(self, 'img_type') else "写实照片"
		
		client = DeepSeekClient(api_key=api_key, base_url=base_url, model=model)
		
		inst = f"将以下分镜转换为简洁的图片描述，用于生成【{img_type}】风格的图片。只输出描述，200字以内。"
		resp = client.chat([
			{"role": "system", "content": inst},
			{"role": "user", "content": shot},
		], temperature=0.5)
		
		description = resp.strip()
		
		# 更新UI
		self.after(0, lambda: self.img_txt_prompt_cn.delete("1.0", END))
		self.after(0, lambda d=description: self.img_txt_prompt_cn.insert(END, d))
		
		return description
	
	def _generate_shot_image_sync(self, index: int, reference_images: list = None) -> None:
		"""同步生成单个分镜的图片"""
		import time
		old_count = 0
		if self.current_project:
			shots_dir = self.current_project.project_dir / "shots"
			if shots_dir.exists():
				old_count = len(list(shots_dir.glob("*.png")))
		self.after(0, self._on_img_generate)
		for _ in range(90):
			time.sleep(1)
			if hasattr(self, '_batch_cancelled') and self._batch_cancelled:
				break
			if self.current_project:
				shots_dir = self.current_project.project_dir / "shots"
				if shots_dir.exists() and len(list(shots_dir.glob("*.png"))) > old_count:
					time.sleep(0.5)
					break
			if hasattr(self, '_is_busy') and not self._is_busy:
				break
	
	def _cancel_batch_generation(self) -> None:
		"""取消批量生成"""
		self._batch_cancelled = True
		self._ui(self.status.set, "⏳ 正在取消批量生成...")
	
	def _on_img_prompt_from_shots(self) -> None:
		"""从分镜列表生成提示词"""
		if not hasattr(self, 'parsed_shots') or not self.parsed_shots:
			messagebox.showwarning("提示", "请先生成分镜列表")
			return
		shots = "\n".join(self.parsed_shots)
		story_text = self.output.get("1.0", END).strip() if hasattr(self, 'output') else ""
		scene = self.img_entry_scene.get().strip() if hasattr(self, 'img_entry_scene') else ""
		roles = self.img_txt_roles.get("1.0", END).strip() if hasattr(self, 'img_txt_roles') else ""
		
		def task():
			try:
				self.set_busy(True)
				self._ui(self.status.set, "根据分镜生成提示词中...")
				fallback_provider = None
				if hasattr(self, 'quick_story_api'):
					fallback_provider = self.quick_story_api.get()
				if not fallback_provider and hasattr(self, 'api_preset'):
					fallback_provider = self.api_preset.get()
				fallback_model = None
				if hasattr(self, 'story_model_var'):
					fallback_model = self.story_model_var.get()
				elif hasattr(self, 'model'):
					fallback_model = self.model.get()
				
				api_config = self._resolve_task_api("image_prompt_from_shots", fallback_provider=fallback_provider, fallback_model=fallback_model)
				if not _sanitize(api_config.get("key", "")):
					self._ui(messagebox.showwarning, "提示", "请先在设置页配置用于生成提示词的API Key")
					return
				client = DeepSeekClient(
					api_key=_sanitize(api_config.get("key", "")),
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				inst = (
					"你是资深视觉提示词工程师。基于分镜清单与故事上下文，输出单段英文提示词用于文生图，"
					"确保人物与故事中的设定一致（面部/发型/年龄/服饰/气质），并与所选场景匹配。包含场景/构图/主体细节/表情动作/光线镜头/风格与质感。"
					"禁止 Markdown，仅输出英文提示词。"
				)
				user = (
					f"分镜清单：\n{shots}\n\n"
					f"故事上下文：\n{story_text}\n\n"
					f"补充场景：{scene or '无'}\n人物设定：{roles or '无'}\n"
					"请给出最终英文提示词。"
				)
				resp = client.chat([
					{"role": "system", "content": inst},
					{"role": "user", "content": user},
				], temperature=max(0.4, self.temperature.get() - 0.2))
				self._ui(self.img_txt_prompt.delete, "1.0", END)
				self._ui(self.img_txt_prompt.insert, END, resp.strip())
				self._ui(self.status.set, "已根据分镜生成提示词")
			except Exception as e:
				self._ui(messagebox.showerror, "错误", str(e))
			finally:
				self.set_busy(False)
		
		import threading
		threading.Thread(target=task, daemon=True).start()

	
	def _auto_select_characters_from_shot(self, shot_text: str, description: str = "") -> None:
		"""智能识别分镜中的人物并自动选中（支持名字、别名、特征匹配）"""
		try:
			print(f"\n{'='*60}")
			print(f"🤖 开始智能识别人物")
			print(f"{'='*60}")
			
			# 清空当前选择
			self.ref_character_listbox.selection_clear(0, END)
			
			# 获取所有可用的人物及其描述
			if not self.character_list:
				print(f"⚠️ 人物列表为空")
				return
			
			available_characters = []
			for char in self.character_list:
				try:
					from ...models.character import Character
				except Exception:
					Character = None
				if Character and isinstance(char, Character):
					photo_path = char.primary_photo
					name = char.name
					description = char.description or ""
				else:
					photo_path = char.get("photo_path") if isinstance(char, dict) else ""
					name = char.get("name", "") if isinstance(char, dict) else ""
					description = char.get("description", "") if isinstance(char, dict) else ""
				if photo_path:
					available_characters.append({
						"name": name,
						"description": description
					})
			
			print(f"📋 可用人物数量：{len(available_characters)}")
			for char in available_characters:
				desc_preview = char["description"][:50] + "..." if len(char["description"]) > 50 else char["description"]
				print(f"   - {char['name']}: {desc_preview}")
			
			if not available_characters:
				print(f"⚠️ 没有已生成照片的人物")
				return
			
			# 合并分镜和描述文本
			search_text = f"{shot_text} {description}"
			print(f"\n📝 搜索文本长度：{len(search_text)} 字")
			print(f"📝 搜索文本前300字：{search_text[:300]}...")
			
			# 识别文本中提到的人物
			mentioned_characters = []
			
			for char in available_characters:
				char_name = char["name"]
				char_desc = char["description"]
				matched_reasons = []
				
				# 方法1: 直接匹配人物名字
				if char_name in search_text:
					matched_reasons.append(f"名字匹配")
				
				# 方法2: 从人物描述中提取关键特征词并匹配
				# 提取职业、身份、角色
				identity_keywords = []
				for keyword in ["主角", "我", "实习生", "护士", "医生", "老人", "阿姨", "大妈", 
				               "女孩", "男孩", "年轻人", "中年", "老年", "小孩", "孩子",
				               "病人", "患者", "家属", "访客", "保安", "清洁工",
				               "教师", "学生", "司机", "服务员", "经理", "老板"]:
					if keyword in char_desc:
						identity_keywords.append(keyword)
				
				# 检查这些关键词是否在搜索文本中
				for keyword in identity_keywords:
					if keyword in search_text:
						matched_reasons.append(f"身份特征'{keyword}'匹配")
						break
				
				# 方法3: 提取年龄特征
				import re
				age_pattern = re.search(r'(\d{1,2})\s*岁', char_desc)
				if age_pattern:
					age = age_pattern.group(1)
					if f"{age}岁" in search_text or f"{age}岁" in search_text:
						matched_reasons.append(f"年龄'{age}岁'匹配")
				
				# 方法4: 提取外貌特征（发型、发色）
				appearance_keywords = []
				for keyword in ["短发", "长发", "齐肩", "卷发", "直发", "马尾", "辫子",
				               "黑发", "白发", "金发", "棕发", "红发",
				               "眼镜", "胡须", "瘦", "胖", "高", "矮"]:
					if keyword in char_desc and keyword in search_text:
						appearance_keywords.append(keyword)
				
				if appearance_keywords:
					matched_reasons.append(f"外貌特征{appearance_keywords}匹配")
				
				# 方法5: 提取服装特征
				clothing_keywords = []
				for keyword in ["白大褂", "护士服", "制服", "西装", "衬衫", "T恤", "裙子", "裤子"]:
					if keyword in char_desc and keyword in search_text:
						clothing_keywords.append(keyword)
				
				if clothing_keywords:
					matched_reasons.append(f"服装特征{clothing_keywords}匹配")
				
				# 如果有任何匹配，添加到识别列表
				if matched_reasons:
					mentioned_characters.append(char_name)
					print(f"✅ 识别到人物【{char_name}】：{' | '.join(matched_reasons)}")
			
			# 如果没有识别到人物，不做任何选择
			if not mentioned_characters:
				print(f"💡 未在分镜中识别到已生成照片的人物")
				print(f"   提示：可能是人物描述与分镜描述差异较大")
				print(f"{'='*60}\n")
				return
			
			# 在列表框中选中这些人物
			selected_count = 0
			for idx in range(self.ref_character_listbox.size()):
				item_text = self.ref_character_listbox.get(idx)
				if item_text.startswith(("✅ ", "🧬 ")):
					char_name = item_text[2:].strip()
					if char_name in mentioned_characters:
						self.ref_character_listbox.selection_set(idx)
						selected_count += 1
						print(f"🎯 在列表第{idx}行选中：{char_name}")
			
			# 显示提示信息
			if mentioned_characters:
				char_names = "、".join(mentioned_characters)
				self._ui(self.status.set, f"✅ 已自动选择参考人物：{char_names}")
				print(f"🎭 智能识别并选中 {selected_count} 个人物：{char_names}")
			
			print(f"{'='*60}\n")
			
		except Exception as e:
			print(f"⚠️ 自动选择参考人物时出错：{str(e)}")
			import traceback
			traceback.print_exc()
	
	
