"""
分镜头图片生成器 - 为分镜头自动生成高质量图片
支持API模式和本地SD生成
"""

import tkinter as tk
from typing import List, Dict
import threading
from tkinter import messagebox


class SceneImageGeneratorMixin:
	"""分镜头图片生成功能（已废弃，功能已合并到DirectorMixin）"""
	
	def _legacy_generate_shot_images(self) -> None:
		"""旧版本的生成方法（已不使用）"""
		if not self.current_shots:
			messagebox.showwarning("提示", "请先生成分镜头")
			return
		
		# 获取生成参数
		resolution = self.director_resolution.get() if hasattr(self, 'director_resolution') else "768x512"
		style = self.director_style.get() if hasattr(self, 'director_style') else "photorealistic"
		
		# 启动后台线程生成图片
		def task():
			try:
				self.status.set("🖼️  正在生成分镜头图片...")
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("准备生成图片...", "🖼️"))
				
				total_shots = len(self.current_shots)
				generated_images = []
				
				for i, shot in enumerate(self.current_shots, 1):
					try:
						self.status.set(f"🖼️  正在生成分镜 [{i}/{total_shots}]...")
						if hasattr(self, 'update_header_status'):
							self.after(0, lambda idx=i, tot=total_shots: self.update_header_status(
								f"生成分镜 {idx}/{tot}", "🖼️"
							))
						
						# 为该镜头生成图片
						image_path = self._legacy_generate_single_shot_image(shot, resolution, style, i)
						
						if image_path:
							generated_images.append({
								"shot_number": i,
								"path": image_path,
								"type": shot.get("shot_type", "Unknown")
							})
							print(f"✅ 分镜{i}生成成功: {image_path}")
						
					except Exception as e:
						print(f"❌ 分镜{i}生成失败: {str(e)}")
						continue
				
				# 生成完成
				self.after(0, lambda: messagebox.showinfo(
					"完成",
					f"成功生成 {len(generated_images)}/{total_shots} 张分镜头图片"
				))
				
				# 保存生成的图片列表
				if hasattr(self, 'director_images_list'):
					self.director_images_list = generated_images
				
			except Exception as e:
				self.after(0, lambda: messagebox.showerror("错误", f"生成分镜图片失败: {str(e)}"))
			finally:
				self.status.set("✅ 分镜图片生成完成")
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("完成", "✅"))
		
		threading.Thread(target=task, daemon=True).start()
	
	def _legacy_generate_single_shot_image(self, shot: Dict, resolution: str, style: str, shot_num: int) -> str:
		"""
		生成单个分镜头的图片
		
		Args:
			shot: 分镜头信息
			resolution: 分辨率
			style: 图片风格
			shot_num: 镜头号
			
		Returns:
			生成的图片路径
		"""
		
		try:
			# 构建提示词
			prompt = self._build_shot_image_prompt(shot, style)
			
			print(f"\n【生成分镜{shot_num}】")
			print(f"类型: {shot.get('shot_type', 'Unknown')}")
			print(f"提示词: {prompt[:100]}...")
			
			# 获取当前的图片生成API配置
			if not hasattr(self, 'img_api_key') or not self.img_api_key.get():
				# 如果是本地SD，key可以为空
				provider = getattr(self, 'img_api_provider', tk.StringVar(value='openai')).get()
				if provider != 'sd':
					raise RuntimeError("请先配置图片生成API")
			
			# 解析分辨率
			width, height = map(int, resolution.split('x'))
			
			# 调用图片生成API
			image_data = self._call_image_api(
				prompt=prompt,
				width=width,
				height=height,
				style=style
			)
			
			if image_data:
				# 保存图片
				import os
				output_dir = os.path.join(os.getcwd(), "director_output", "images")
				os.makedirs(output_dir, exist_ok=True)
				
				image_path = os.path.join(output_dir, f"shot_{shot_num:02d}.png")
				
				# 写入图片文件
				if isinstance(image_data, bytes):
					with open(image_path, 'wb') as f:
						f.write(image_data)
				else:
					# 如果是PIL图片对象
					image_data.save(image_path)
				
				return image_path
		
		except Exception as e:
			print(f"❌ 生成分镜{shot_num}失败: {str(e)}")
			raise
		
		return None
	
	def _build_shot_image_prompt(self, shot: Dict, style: str) -> str:
		"""
		为单个镜头构建图片生成提示词
		
		结合一致性约束和镜头信息
		"""
		
		# 获取镜头信息
		description = shot.get("scene_description", "")
		characters = shot.get("characters", [])
		character_details = shot.get("character_details", {})
		action = shot.get("action", "")
		lighting = shot.get("lighting", "")
		atmosphere = shot.get("atmosphere", "")
		
		# 构建提示词
		prompt_parts = []
		
		# 1. 人物描述
		if characters:
			char_desc = []
			for char_name in characters:
				if char_name in character_details:
					char_desc.append(character_details[char_name])
				else:
					char_desc.append(char_name)
			prompt_parts.append("人物: " + ", ".join(char_desc))
		
		# 2. 场景描述
		if description:
			prompt_parts.append("场景: " + description)
		
		# 3. 动作
		if action:
			prompt_parts.append("动作: " + action)
		
		# 4. 光线
		if lighting:
			prompt_parts.append("光线: " + lighting)
		
		# 5. 氛围
		if atmosphere:
			prompt_parts.append("氛围: " + atmosphere)
		
		# 6. 风格和质量关键词
		style_keywords = {
			"photorealistic": "写实照片, 摄影, 专业",
			"cinematic": "电影感, 宽银幕, 专业级",
			"artistic": "艺术风格, 绘画感, 创意"
		}
		style_kw = style_keywords.get(style, "高质量")
		prompt_parts.append(f"风格: {style_kw}, 高质量, 清晰, 8K")
		
		# 合并
		final_prompt = ", ".join(prompt_parts)
		
		# 限制长度
		max_length = 500
		if len(final_prompt) > max_length:
			final_prompt = final_prompt[:max_length].rstrip(",").rstrip()
		
		return final_prompt
	
	def _call_image_api(self, prompt: str, width: int, height: int, style: str) -> bytes:
		"""
		调用图片生成API（支持OpenAI兼容API和本地SD）
		
		Returns:
			图片数据（字节）
		"""
		
		try:
			# 获取当前配置的图片API提供商
			if not hasattr(self, 'img_api_provider'):
				provider = "openai"  # 默认
			else:
				provider = self.img_api_provider.get()
			
			print(f"使用提供商: {provider}")
			
			# 本地Stable Diffusion
			if provider == "sd":
				return self._call_sd_api(prompt, width, height)
			
			# OpenAI兼容API (包括V-API, Hunyuan等)
			else:
				return self._call_openai_api(prompt, width, height)
		
		except Exception as e:
			print(f"API调用失败: {str(e)}")
			raise
	
	def _call_sd_api(self, prompt: str, width: int, height: int) -> bytes:
		"""调用本地Stable Diffusion API"""
		
		try:
			from src.clients.sd_client import StableDiffusionClient
			
			base_url = "http://localhost:7860"
			client = StableDiffusionClient(base_url=base_url)
			
			# 生成图片
			images = client.txt2img(
				prompt=prompt,
				negative_prompt="nsfw, lowres, bad anatomy, bad hands, text, error",
				width=width,
				height=height,
				steps=20,
				cfg_scale=7.0,
				sampler_name="Euler a"
			)
			
			if images:
				return images[0]  # 返回第一张图片的字节
			else:
				raise RuntimeError("SD生成失败")
		
		except Exception as e:
			print(f"本地SD API调用失败: {str(e)}")
			raise
	
	def _call_openai_api(self, prompt: str, width: int, height: int) -> bytes:
		"""调用OpenAI兼容API"""
		
		try:
			import base64
			from src.clients.image_client import OpenAIImageClient
			
			# 获取API配置
			api_key = self.img_api_key.get() if hasattr(self, 'img_api_key') else ""
			base_url = self.img_base_url.get() if hasattr(self, 'img_base_url') else "https://api.openai.com/v1"
			model = self.img_model.get() if hasattr(self, 'img_model') else "dall-e-3"
			
			client = OpenAIImageClient(
				api_key=api_key,
				base_url=base_url,
				model=model
			)
			
			# 生成图片
			image_data = client.generate(
				prompt=prompt,
				size=f"{width}x{height}"
			)
			
			if isinstance(image_data, str):
				# 如果是base64编码
				return base64.b64decode(image_data)
			else:
				return image_data
		
		except Exception as e:
			print(f"OpenAI API调用失败: {str(e)}")
			raise
	
	def display_generated_images(self) -> None:
		"""在图片预览标签页显示生成的图片"""
		
		try:
			if not hasattr(self, 'director_images_scrollable'):
				return
			
			# 清空旧的图片
			for widget in self.director_images_scrollable.winfo_children():
				widget.destroy()
			
			# 显示生成的图片
			if hasattr(self, 'director_images_list'):
				import tkinter as tk
				from PIL import Image, ImageTk
				
				for img_info in self.director_images_list:
					try:
						# 创建图片框
						img_frame = tk.Frame(self.director_images_scrollable, bg="#2b2b2b")
						img_frame.pack(fill="x", padx=10, pady=10)
						
						# 加载并显示图片
						img_path = img_info['path']
						img = Image.open(img_path)
						img.thumbnail((600, 400))
						photo = ImageTk.PhotoImage(img)
						
						img_label = tk.Label(img_frame, image=photo, bg="#2b2b2b")
						img_label.image = photo  # 保持引用
						img_label.pack()
						
						# 显示信息
						info_label = tk.Label(
							img_frame,
							text=f"分镜{img_info['shot_number']}: {img_info['type']}",
							fg="#a78bfa",
							bg="#2b2b2b",
							font=("Consolas", 10)
						)
						info_label.pack()
					
					except Exception as e:
						print(f"显示图片{img_info['shot_number']}失败: {str(e)}")
		
		except Exception as e:
			print(f"显示生成的图片失败: {str(e)}")
