"""
负责图片生成核心逻辑
"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, VERTICAL, Y, messagebox, filedialog
import tkinter as tk
from tkinter import ttk
import os
import re
from PIL import Image, ImageTk

from src.clients.deepseek_client import DeepSeekClient
from src.clients.image_client import OpenAIImageClient
from src.utils.text import sanitize as _sanitize
from ...helpers.image_styles import IMAGE_TYPES, HUNYUAN_STYLE_MAP
from ...helpers.image_helpers import ImagePromptHelper, DescriptionPromptBuilder


class ImageGeneratorMixin:
	"""负责图片生成核心逻辑"""
	
	def _is_policy_rejection_error(self, err: Exception) -> bool:
		"""Check whether an image error is caused by safety/policy rejection."""
		err_text = str(err).lower()
		keywords = (
			"blocked",
			"safety",
			"policy",
			"moderation",
			"content_violation",
			"content policy",
			"not allowed",
		)
		return any(k in err_text for k in keywords)

	def _build_safe_retry_prompt(self, prompt_en: str) -> str:
		"""Build a stricter low-risk prompt for one retry when blocked."""
		safe_prompt = ImagePromptHelper.sanitize_prompt(prompt_en, aggressive=True)
		safe_prompt = re.sub(
			r"\b(child|children|kid|kids|teen|teenage|young girl|young boy)\b",
			"adult",
			safe_prompt,
			flags=re.IGNORECASE,
		)
		safe_prompt = re.sub(
			r"\b(sexy|seductive|nude|nudity|lingerie)\b",
			"fully clothed",
			safe_prompt,
			flags=re.IGNORECASE,
		)
		safe_prompt = re.sub(
			r"\b(weapon|knife|gun|blood|gore|corpse)\b",
			"",
			safe_prompt,
			flags=re.IGNORECASE,
		)
		safe_prompt = re.sub(r"\s+", " ", safe_prompt).strip(" ,.")
		return ImagePromptHelper.truncate_text(safe_prompt, 600, prefer_punct=True)

	def _translate_prompt_to_english(self, prompt_cn: str, img_type: str, selected_characters: list) -> str:
		"""将中文提示词翻译为英文"""
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
		
		api_config = self._resolve_task_api("image_prompt_translate", fallback_provider=fallback_provider, fallback_model=fallback_model)
		if not _sanitize(api_config.get("key", "")):
			raise ValueError("请先在设置页配置用于翻译的API Key")
		
		client = DeepSeekClient(
			api_key=_sanitize(api_config.get("key", "")),
			base_url=_sanitize(api_config.get("base_url", "")),
			model=_sanitize(api_config.get("model", "")),
		)
		
		# 检查是否有参考人物照片（图生图模式）
		has_photo = any(char.get("photo_path") for char in selected_characters if char)
		
		# 使用辅助类构建翻译指令
		inst = ImagePromptHelper.build_translation_instruction(img_type, has_reference_characters=has_photo, is_img2img=has_photo)
		
		# 截断过长的中文描述
		prompt_cn_for_translate = ImagePromptHelper.truncate_text(prompt_cn, 800)
		
		# 调用翻译
		prompt_en = client.chat([
			{"role": "system", "content": inst},
			{"role": "user", "content": f"图片类型：{img_type}\n\n请翻译以下中文图片描述为简洁的英文提示词：\n\n{prompt_cn_for_translate}"},
		], temperature=0.3)
		
		# 过滤敏感词并添加安全后缀
		prompt_en = ImagePromptHelper.filter_sensitive_words(prompt_en)
		prompt_en = ImagePromptHelper.add_safety_suffix(prompt_en)
		
		# 截断过长的英文提示词
		prompt_en = ImagePromptHelper.truncate_text(prompt_en, 1000, prefer_punct=True)
		
		return prompt_en
	
	
	def _generate_with_hunyuan(self, prompt_cn: str, img_type: str) -> Image.Image:
		"""使用腾讯混元API生成图片"""
		from src.clients.hunyuan_image_client import HunyuanImageClient
		
		secret_id = self.img_api_key.get().strip()
		secret_key = self.img_secret_key.get().strip()
		
		if not secret_id or not secret_key:
			raise ValueError("请先配置腾讯混元的SecretId和SecretKey")
		
		# 优化提示词以适配腾讯混元
		enhanced_prompt = ImagePromptHelper.optimize_for_hunyuan(prompt_cn, img_type)
		
		# 映射分辨率
		resolution = ImagePromptHelper.map_size_for_hunyuan(self.img_size.get())
		
		# 获取风格参数
		hunyuan_style = HUNYUAN_STYLE_MAP.get(img_type, "201")
		
		# 调用API
		hunyuan_client = HunyuanImageClient(
			secret_id=secret_id,
			secret_key=secret_key
		)
		
		self._ui(self.status.set, f"🚀 正在调用腾讯混元API生成图片...（分辨率{resolution.replace(':', 'x')}）")
		
		result = hunyuan_client.generate(
			prompt=enhanced_prompt,
			resolution=resolution,
			style=hunyuan_style,
			rsp_img_type="base64"
		)
		
		return result.image
	
	
	def _generate_with_openai(self, prompt_en: str, selected_characters: list) -> Image.Image:
		"""使用OpenAI兼容API生成图片"""
		model_name = self.img_model.get().strip() or "dall-e-3"
		img_api_key = self.img_api_key.get().strip()
		img_base_url = self.img_base_url.get().strip() if hasattr(self, 'img_base_url') else None
		
		if not img_api_key:
			raise ValueError("请先配置图片生成API Key")
		
		img_client = OpenAIImageClient(
			api_key=img_api_key, 
			model=model_name,
			base_url=img_base_url
		)
		
		# 使用选中的参考人物照片（优先使用第一个）
		ref_image_path = None
		if selected_characters and selected_characters[0].get("photo_path"):
			ref_image_path = selected_characters[0]["photo_path"]
			char_names = [c["name"] for c in selected_characters]
			print(f"📸 使用参考人物：{', '.join(char_names)}")
		elif self.img_ref_path.get().strip():
			ref_image_path = self.img_ref_path.get().strip()
		
		# 调用API
		if ref_image_path:
			self._ui(self.status.set, f"📸 使用参考图片生成...")
			results = img_client.generate_with_reference(
				prompt=prompt_en, 
				reference_image_path=ref_image_path, 
				size=self.img_size.get()
			)
		else:
			self._ui(self.status.set, f"🚀 正在调用OpenAI API生成图片...（大小：{self.img_size.get()}）")
			results = img_client.generate(prompt=prompt_en, size=self.img_size.get(), n=1)
		
		if not results:
			raise ValueError("生成失败")
		
		return results[0].image
	
	
	def _on_img_generate(self) -> None:
		"""生成图片（重构简化版）"""
		prompt_cn = self.img_txt_prompt_cn.get("1.0", END).strip()
		if not prompt_cn:
			messagebox.showwarning("提示", "请先生成或填写图片描述")
			return
		
		# 获取图片类型和选中的参考人物
		img_type = self.img_type.get() if hasattr(self, 'img_type') else "写实照片"
		selected_characters = self._get_selected_reference_characters()
		
		# 准备包含人物信息的提示词
		prompt_cn = self._prepare_character_enhanced_prompt(prompt_cn, selected_characters)
		
		def task(prompt_cn=prompt_cn, selected_characters=selected_characters, img_type=img_type):
			try:
				self._ui(self.img_btn_gen.configure, state=DISABLED)
				self._ui(self.status.set, "🎨 准备生成图片...")
				self._header_status("准备生成图片...", "🎨")
				
				# 步骤1: 判断使用哪个API提供商
				current_preset = self.img_api_preset.get()
				provider = self.img_api_type.get() if hasattr(self, 'img_api_type') else None
				if not provider:
					provider = self.img_api_presets.get(current_preset, {}).get("provider")
				if not provider:
					provider = "openai"
				
				self._ui(self.status.set, f"📝 正在翻译【{img_type}】风格图片描述为英文...（步骤1/3）")
				# 更新顶部状态栏
				self._header_status("翻译提示词 (1/3)", "📝")
				
				# 根据图片类型定义英文风格关键词
				style_keywords = {
					"写实照片": "photorealistic, high quality photography, natural lighting, realistic, detailed, 8K",
					"日系动漫": "anime style, Japanese animation, vibrant colors, cel shading, anime artwork, high quality anime",
					"3D渲染": "3D render, CGI, high quality rendering, octane render, unreal engine, detailed textures",
					"水彩画": "watercolor painting, soft colors, artistic, traditional art, watercolor style, delicate brushstrokes",
					"油画": "oil painting, thick brushstrokes, classical art style, rich colors, fine art, painterly",
					"素描": "sketch style, pencil drawing, line art, monochrome, artistic sketch, detailed linework",
					"赛博朋克": "cyberpunk style, neon lights, futuristic, dark atmosphere, high-tech, sci-fi",
					"蒸汽朋克": "steampunk style, gears and machinery, Victorian era, retro-futuristic, industrial aesthetic",
					"像素风": "pixel art style, 8-bit/16-bit graphics, retro game art, pixelated",
					"中国风": "Chinese traditional painting style, ink wash painting, classical Chinese art, poetic atmosphere",
					"国风插画": "Chinese style illustration, modern Chinese aesthetic, delicate line art, traditional colors, elegant composition",
					"古风": "ancient Chinese style, traditional hanfu, classical architecture, historical atmosphere, Tang/Song dynasty aesthetic",
					"仙侠": "Chinese xianxia fantasy, immortal cultivator, celestial scenery, flowing robes, mystical clouds, jade palace",
					"武侠": "Chinese wuxia, martial arts, sword fighting, ancient warrior, bamboo forest, misty mountains",
					"水墨画": "Chinese ink wash painting, sumi-e style, black ink, minimal colors, artistic brushwork, zen aesthetic",
					"工笔画": "Chinese gongbi painting, meticulous brushwork, fine details, traditional pigments, classical composition",
					"敦煌壁画": "Dunhuang murals style, ancient Buddhist art, flying apsaras, Tang dynasty colors, religious iconography",
					"恐怖": "horror style, dark atmosphere, creepy, eerie lighting, disturbing, scary, gothic",
					"惊悚": "thriller style, suspenseful, tense atmosphere, dramatic lighting, mysterious shadows, unsettling",
					"诡异": "uncanny style, bizarre, surreal, otherworldly, strange atmosphere, unsettling details",
					"悬疑": "mystery style, noir atmosphere, dramatic shadows, suspenseful composition, detective aesthetic",
					"玄幻": "Chinese xuanhuan fantasy, mystical elements, magical creatures, spiritual energy, epic landscape",
					"科幻": "sci-fi style, futuristic technology, space setting, advanced civilization, neon lights, cybernetic",
					"魔幻": "fantasy style, magical world, mythical creatures, enchanted forest, ethereal glow, epic adventure"
				}
				
				# 如果是自定义类型且不在预设中，使用通用关键词
				style_keyword = style_keywords.get(img_type, f"{img_type} style, artistic, high quality, detailed")
				
				# 1. 先将中文翻译为英文提示词
				# 使用模型路由选择翻译模型
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
				
				api_config = self._resolve_task_api("image_prompt_translate", fallback_provider=fallback_provider, fallback_model=fallback_model)
				if not _sanitize(api_config.get("key", "")):
					self._ui(messagebox.showerror, "错误", "请先在设置页配置用于翻译的API Key")
					return
				
				client = DeepSeekClient(
					api_key=_sanitize(api_config.get("key", "")),
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				# 检查是否有参考人物
				has_reference_characters = selected_characters and len(selected_characters) > 0
				
				# 🎯 简化翻译指令，去除过度强调
				inst = (
					f"将中文图片描述翻译为简洁自然的英文提示词，用于{img_type}风格的AI图片生成。\n\n"
					f"要求：\n"
					f"1. 保留核心视觉元素：人物、场景、动作、光线、镜头\n"
					f"2. 使用自然的描述性语言，避免堆砌关键词\n"
					f"3. 体现{img_type}的美学特点，添加风格词：{style_keyword}\n"
					f"4. 控制在200个英文单词以内\n"
					f"5. 只输出英文提示词，不要解释\n"
				)
				
				if has_reference_characters:
					inst += (
						f"\n注意：如果有人物描述，请准确翻译人物特征（年龄、性别、发型、服装等），保持自然流畅。\n"
					)
				
				# 如果中文描述过长，先截断
				max_cn_length = 800
				prompt_cn_for_translate = prompt_cn
				if len(prompt_cn_for_translate) > max_cn_length:
					prompt_cn_for_translate = prompt_cn_for_translate[:max_cn_length] + "..."
				
				prompt_en = client.chat([
					{"role": "system", "content": inst},
					{"role": "user", "content": f"图片类型：{img_type}\n\n请翻译以下中文图片描述为简洁的英文提示词：\n\n{prompt_cn_for_translate}"},
				], temperature=0.3)
				
				# 过滤可能违反内容策略的词汇
				sensitive_words = [
					'blood', 'bloody', 'gore', 'gory', 'violence', 'violent', 'death', 'dead', 'corpse',
					'kill', 'murder', 'suicide', 'weapon', 'gun', 'knife', 'explosion', 'bomb',
					'torture', 'mutilation', 'dismember', 'decapitate', 'horrific', 'gruesome'
				]
				
				# 温和替换敏感词
				replacements = {
					'blood': 'red liquid', 'bloody': 'stained', 'gore': 'dramatic scene',
					'violence': 'intense action', 'violent': 'intense', 'death': 'ending',
					'dead': 'motionless', 'corpse': 'figure', 'kill': 'defeat', 
					'murder': 'incident', 'suicide': 'tragedy', 'weapon': 'tool',
					'gun': 'device', 'knife': 'blade', 'explosion': 'burst',
					'bomb': 'device', 'torture': 'suffering', 'mutilation': 'injury',
					'dismember': 'separate', 'decapitate': 'remove', 
					'horrific': 'dramatic', 'gruesome': 'intense'
				}
				
				prompt_en_filtered = prompt_en
				for word, replacement in replacements.items():
					import re
					# 使用正则表达式进行大小写不敏感的替换
					pattern = re.compile(re.escape(word), re.IGNORECASE)
					prompt_en_filtered = pattern.sub(replacement, prompt_en_filtered)
				
				# 添加安全后缀
				prompt_en = prompt_en_filtered + ", artistic style, cinematic composition, professional photography"
				
				# 检查英文提示词长度，如果太长则截断（保留在1000字符以内）
				max_en_length = 1000
				if len(prompt_en) > max_en_length:
					# 在句号或逗号处截断，保持完整性
					truncated = prompt_en[:max_en_length]
					last_punct = max(truncated.rfind('.'), truncated.rfind(','))
					if last_punct > 800:
						prompt_en = truncated[:last_punct + 1]
					else:
						prompt_en = truncated
				
				# 2. 根据当前预设选择API提供商
				current_preset = self.img_api_preset.get()
				provider = self.img_api_type.get() if hasattr(self, 'img_api_type') else None
				if not provider:
					provider = self.img_api_presets.get(current_preset, {}).get("provider")
				if not provider:
					provider = "openai"
				
				# 翻译完成，准备生成图片
				
				self._ui(self.status.set, f"🖼️ 翻译完成，正在调用图片生成API...（步骤2/3）")
				# 更新顶部状态栏
				self._header_status("正在生成图片 (2/3)", "🎨")
				
				# 3. 使用对应的客户端生成图片
				if provider == "hunyuan":
					# 使用腾讯混元API
					from src.clients.hunyuan_image_client import HunyuanImageClient
					
					self._ui(self.status.set, f"🎨 使用腾讯混元API生成【{img_type}】风格图片...（步骤2/3）")
					# 更新顶部状态栏
					self._header_status("腾讯混元生成中 (2/3)", "🎨")
					
					secret_id = self.img_api_key.get().strip()
					secret_key = self.img_secret_key.get().strip()
					
					if not secret_id or not secret_key:
						self._ui(messagebox.showerror, "错误", "请先配置腾讯混元的SecretId和SecretKey")
						return
					
					# 根据图片类型映射腾讯混元的style参数
					hunyuan_style_map = {
						"写实照片": "201",  # 日系动漫风格（腾讯混元默认，也适合写实）
						"日系动漫": "201",  # 日系动漫风格
						"3D渲染": "201",
						"水彩画": "201",
						"油画": "201",
						"素描": "201",
						"赛博朋克": "201",
						"蒸汽朋克": "201",
						"像素风": "201",
						"中国风": "201",
						"国风插画": "201",
						"古风": "201",
						"仙侠": "201",
						"武侠": "201",
						"水墨画": "201",
						"工笔画": "201",
						"敦煌壁画": "201",
						"恐怖": "201",
						"惊悚": "201",
						"诡异": "201",
						"悬疑": "201",
						"玄幻": "201",
						"科幻": "201",
						"魔幻": "201"
					}
					
					hunyuan_style = hunyuan_style_map.get(img_type, "201")
					
					hunyuan_client = HunyuanImageClient(
						secret_id=secret_id,
						secret_key=secret_key
					)
					
					# 腾讯混元支持中文，使用中文风格描述
					# 定义中文风格描述
					style_desc_cn = {
						"写实照片": "高清摄影，写实风格，自然光线，真实质感",
						"日系动漫": "日系动漫风格，精美作画，色彩鲜艳",
						"3D渲染": "3D渲染，高品质建模，精致材质",
						"水彩画": "水彩画风格，色彩柔和，艺术感强",
						"油画": "油画质感，笔触厚重，色彩浓郁",
						"素描": "素描风格，线条流畅，黑白灰调",
						"赛博朋克": "赛博朋克风格，霓虹灯光，未来科技感",
						"蒸汽朋克": "蒸汽朋克风格，机械齿轮，复古科技",
						"像素风": "像素艺术风格，复古游戏美术",
						"中国风": "中国传统绘画风格，水墨意境，古典韵味",
						"国风插画": "国风插画，现代中国美学，线条精美，色彩典雅",
						"古风": "古风，传统服饰，古代建筑，历史氛围，唐宋美学",
						"仙侠": "仙侠奇幻，修仙者，天宫仙境，飘逸长袍，仙气缭绕",
						"武侠": "武侠江湖，武林高手，剑客，竹林，烟雨山水",
						"水墨画": "中国水墨画，笔墨韵味，黑白灰调，禅意美学",
						"工笔画": "工笔重彩，精细笔法，传统颜料，古典构图",
						"敦煌壁画": "敦煌壁画风格，飞天，佛教艺术，唐代色彩",
						"恐怖": "恐怖氛围，阴暗诡异，诡谲光影，惊悚元素",
						"惊悚": "惊悚风格，悬疑紧张，戏剧化光影，神秘阴影",
						"诡异": "诡异风格，超现实，异世界，诡谲氛围",
						"悬疑": "悬疑风格，黑色电影，戏剧阴影，侦探美学",
						"玄幻": "玄幻奇幻，神秘元素，灵兽异兽，磅礴山水",
						"科幻": "科幻未来，高科技，太空场景，先进文明，霓虹",
						"魔幻": "魔幻世界，神话生物，魔法森林，神秘光芒"
					}.get(img_type, f"{img_type}风格")
					
					# 腾讯混元API限制：Prompt最多256个UTF-8字符
					# 优化策略：使用关键词密集型描述，保证信息量
					
					# 简短风格关键词（用于腾讯混元）
					style_keywords_short = {
						"写实照片": "高清摄影",
						"日系动漫": "动漫风",
						"3D渲染": "3D渲染",
						"水彩画": "水彩",
						"油画": "油画质感",
						"素描": "素描",
						"赛博朋克": "赛博朋克",
						"蒸汽朋克": "蒸汽朋克",
						"像素风": "像素艺术",
						"中国风": "中国风",
						"国风插画": "国风插画",
						"古风": "古风",
						"仙侠": "仙侠",
						"武侠": "武侠",
						"水墨画": "水墨",
						"工笔画": "工笔",
						"敦煌壁画": "敦煌壁画",
						"恐怖": "恐怖",
						"惊悚": "惊悚",
						"诡异": "诡异",
						"悬疑": "悬疑",
						"玄幻": "玄幻",
						"科幻": "科幻",
						"魔幻": "魔幻"
					}.get(img_type, img_type)
					
					# 智能处理描述长度
					self._ui(self.status.set, f"⚙️ 优化提示词以适配腾讯混元API...（字符限制256）")
					
					max_base_length = 230  # 为风格关键词留空间
					
					# 使用新变量避免闭包作用域问题
					processed_prompt = prompt_cn
					if len(prompt_cn) > max_base_length:
						# 优先截断，但保留完整的关键信息
						# 尝试在逗号或句号处截断
						truncated = prompt_cn[:max_base_length]
						last_punct = max(truncated.rfind('，'), truncated.rfind('。'), truncated.rfind(','))
						if last_punct > 180:  # 如果能找到合适的断点
							processed_prompt = truncated[:last_punct]
						else:
							processed_prompt = truncated
					
					# 组合风格关键词
					if style_keywords_short:
						enhanced_prompt = f"{processed_prompt}，{style_keywords_short}"
					else:
						enhanced_prompt = processed_prompt
					
					# 最终检查，确保不超过256字符
					if len(enhanced_prompt) > 256:
						# 如果还是超长，优先保证主描述
						enhanced_prompt = enhanced_prompt[:256]
					
					# 腾讯混元的分辨率格式是用冒号分隔，且只支持特定分辨率
					# 将常见分辨率映射到腾讯混元支持的分辨率
					size_mapping = {
						"512x512": "768:768",
						"768x768": "768:768",
						"1024x1024": "1024:1024",
						"1024x1792": "1080:1920",  # 映射到接近的16:9竖版
						"1792x1024": "1920:1080",  # 映射到接近的16:9横版
						"720x1280": "720:1280",
						"1280x720": "1280:720",
						"1080x1920": "1080:1920",
						"1920x1080": "1920:1080"
					}
					current_size = self.img_size.get()
					resolution = size_mapping.get(current_size, "1024:1024")
					
					self._ui(self.status.set, f"🚀 正在调用腾讯混元API生成图片...（分辨率{resolution.replace(':', 'x')}）")
					
					result = hunyuan_client.generate(
						prompt=enhanced_prompt,  # 使用优化后的中文提示词
						resolution=resolution,
						style=hunyuan_style,
						rsp_img_type="base64"
					)
					
					self._ui(self.status.set, f"✅ 处理生成结果...（步骤3/3）")
					# 更新顶部状态栏
					self._header_status("处理结果 (3/3)", "✅")
					
					self.img_last_image = result.image
					self._ui(self._update_img_preview)
					self._ui(self.img_btn_save.configure, state=NORMAL)
					self._ui(self.status.set, f"✨ 【{img_type}】风格图片生成成功！使用腾讯混元模型")
					# 更新顶部状态栏
					self._header_status("图片生成完成", "✅")
					# 自动保存图片到项目
					self._auto_save_image_to_project()
					
					# 生成即梦AI视频提示词
					if hasattr(self, 'video_prompt_text'):
						video_prompt = self._generate_video_prompt()
						self._ui(self.video_prompt_text.config, state=NORMAL)
						self._ui(self.video_prompt_text.delete, "1.0", END)
						self._ui(self.video_prompt_text.insert, "1.0", video_prompt)
						self._ui(self.video_prompt_text.config, state=DISABLED)
				
				else:
					# 使用OpenAI兼容API
					model_name = self.img_model.get().strip() or "dall-e-3"
					img_api_key = self.img_api_key.get().strip()
					img_base_url = self.img_base_url.get().strip() if hasattr(self, 'img_base_url') else None
					
					# 使用OpenAI兼容API生成图片
					
					if not img_api_key:
						self._ui(messagebox.showerror, "错误", "请先配置图片生成API Key")
						return
					
					self._ui(self.status.set, f"🎨 使用OpenAI API生成【{img_type}】风格图片...（模型：{model_name}）")
					# 更新顶部状态栏
					self._header_status("OpenAI生成中 (2/3)", "🎨")
					
					img_client = OpenAIImageClient(
						api_key=img_api_key, 
						model=model_name,
						base_url=img_base_url
					)
					
					# 使用选中的参考人物照片（优先使用第一个）
					ref_image_path = None
					if selected_characters and selected_characters[0].get("photo_path"):
						ref_image_path = selected_characters[0]["photo_path"]
						char_names = [c["name"] for c in selected_characters]
						print(f"📸 使用参考人物：{', '.join(char_names)}")
					elif self.img_ref_path.get().strip():
						ref_image_path = self.img_ref_path.get().strip()
					
					if ref_image_path:
						self._ui(self.status.set, f"📸 使用参考图片生成...（步骤2/3）")
						try:
							results = img_client.generate_with_reference(
								prompt=prompt_en,
								reference_image_path=ref_image_path,
								size=self.img_size.get()
							)
						except Exception as gen_err:
							if not self._is_policy_rejection_error(gen_err):
								raise
							retry_prompt = self._build_safe_retry_prompt(prompt_en)
							if not retry_prompt or retry_prompt == prompt_en:
								raise
							self._ui(self.status.set, "Moderation blocked once; sanitized prompt and retrying...")
							results = img_client.generate_with_reference(
								prompt=retry_prompt,
								reference_image_path=ref_image_path,
								size=self.img_size.get()
							)
							prompt_en = retry_prompt
					else:
						self._ui(self.status.set, f"🚀 正在调用OpenAI API生成图片...（大小：{self.img_size.get()}）")
						try:
							results = img_client.generate(prompt=prompt_en, size=self.img_size.get(), n=1)
						except Exception as gen_err:
							if not self._is_policy_rejection_error(gen_err):
								raise
							retry_prompt = self._build_safe_retry_prompt(prompt_en)
							if not retry_prompt or retry_prompt == prompt_en:
								raise
							self._ui(self.status.set, "Moderation blocked once; sanitized prompt and retrying...")
							results = img_client.generate(prompt=retry_prompt, size=self.img_size.get(), n=1)
							prompt_en = retry_prompt
					
					if not results:
						self._ui(messagebox.showerror, "错误", "生成失败")
						return
					
					self._ui(self.status.set, f"✅ 处理生成结果...（步骤3/3）")
					# 更新顶部状态栏
					self._header_status("处理结果 (3/3)", "✅")
					
				self.img_last_image = results[0].image
				self._ui(self._update_img_preview)
				self._ui(self.img_btn_save.configure, state=NORMAL)
				self._ui(self.status.set, f"✨ 【{img_type}】风格图片生成成功！提示词：{prompt_en[:40]}...")
				# 更新顶部状态栏
				self._header_status("图片生成完成", "✅")
				# 自动保存图片到项目
				self._auto_save_image_to_project()
				
				# 生成即梦AI视频提示词
				if hasattr(self, 'video_prompt_text'):
					video_prompt = self._generate_video_prompt()
					self._ui(self.video_prompt_text.config, state=NORMAL)
					self._ui(self.video_prompt_text.delete, "1.0", END)
					self._ui(self.video_prompt_text.insert, "1.0", video_prompt)
					self._ui(self.video_prompt_text.config, state=DISABLED)
			except Exception as e:
				import traceback
				error_detail = traceback.format_exc()
				print(f"图片生成错误详情：\n{error_detail}")
				err_lower = str(e).lower()
				if "blocked" in err_lower or "safety" in err_lower or "policy" in err_lower:
					msg = "请求被安全策略拦截。请尝试移除未成年、暴力、裸露、仇恨等敏感描述，或改成更中性描述后再试。"
				else:
					msg = f"{str(e)}\n\n详细错误请查看控制台"
				self._ui(messagebox.showerror, "错误", msg)
				self._ui(self.status.set, "❌ 图片生成失败，请检查配置和网络")
				# 更新顶部状态栏
				self._header_status("图片生成失败", "❌")
			finally:
				self._ui(self.img_btn_gen.configure, state=NORMAL)
		
		import threading
		threading.Thread(target=task, daemon=True).start()

	
