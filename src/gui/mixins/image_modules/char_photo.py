"""人物处理功能"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, VERTICAL, Y, BOTTOM, messagebox, filedialog
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


class CharacterPhotoMixin:
	"""人物 char_photo 功能"""
	
	def _on_generate_character_photo(self) -> None:
		"""生成选中人物的照片"""
		print("🔔 _on_generate_character_photo 被调用")
		
		from src.clients.hunyuan_image_client import HunyuanImageClient
		import base64
		from io import BytesIO
		
		selection = self.char_listbox.curselection()
		print(f"📋 当前选择: {selection}")
		
		if not selection:
			print("⚠️ 没有选择人物")
			messagebox.showwarning("提示", "请先从列表中选择一个人物！")
			return
		
		index = selection[0]
		
		# ✅ 边界检查
		if index < 0 or index >= len(self.character_list):
			messagebox.showerror("错误", "人物索引无效，请重新选择人物")
			print(f"❌ 索引越界: index={index}, list_len={len(self.character_list)}")
			return
		
		character = self.character_list[index]
		character_name = character.get("name", "")
		if not character_name:
			messagebox.showerror("错误", "人物信息不完整")
			return
		
		description = character.get("description", "")
		
		print(f"👤 选中人物: {character_name}")
		print(f"📝 描述长度: {len(description) if description else 0}")
		
		if not description:
			messagebox.showwarning("提示", "请先生成人物特征描述！")
			return
		
		# 检查当前项目
		if not self.current_project:
			messagebox.showwarning("提示", "请先创建或打开一个项目，人物照片需要保存到项目中！")
			return
		
		print(f"📁 当前项目: {self.current_project}")
		
		# 获取图片风格/类型和额外描述
		style = self.char_img_style.get()
		extra_desc = self.char_txt_extra.get("1.0", END).strip()
		
		# 获取生成类型（新UI）
		gen_type = self.char_gen_type.get() if hasattr(self, 'char_gen_type') else "standard"
		
		# 根据生成类型设定批量选项
		if gen_type == "standard":
			# 标准形象：正面+中性
			batch_generate = False
			batch_expressions = False
		elif gen_type == "expressions":
			# 表情库：正面+7种表情
			batch_generate = False
			batch_expressions = True
		elif gen_type == "angles":
			# 角度库：3个角度+中性
			batch_generate = True
			batch_expressions = False
		elif gen_type == "full":
			# 完整套装：3个角度+7种表情
			batch_generate = True
			batch_expressions = True
		else:
			batch_generate = False
			batch_expressions = False
		
		# 获取视角和表情（用于单一生成）
		view_angle = self.char_view_angle.get() if hasattr(self, 'char_view_angle') else "front"
		expression = self.char_expression.get() if hasattr(self, 'char_expression') else "neutral"
		
		# 获取服装/造型变体选项
		variant_mode = self.char_variant_mode.get() if hasattr(self, 'char_variant_mode') else "none"
		variant_preset = self.char_variant_preset.get() if hasattr(self, 'char_variant_preset') else "casual"
		variant_custom = self.char_variant_custom.get() if hasattr(self, 'char_variant_custom') else ""
		
		# 获取一致性级别（用户选择）
		consistency_level = self.char_consistency_level.get() if hasattr(self, 'char_consistency_level') else "high"
		
		# 确定变体值
		if variant_mode == "preset":
			variant_value = variant_preset
		elif variant_mode == "custom":
			variant_value = variant_custom
		else:
			variant_value = ""
		
		print(f"🎨 图片风格/类型: {style}")
		print(f"📝 额外描述: {extra_desc}")
		print(f"👁️ 视角: {view_angle}")
		print(f"😊 表情: {expression}")
		print(f"🎯 批量生成角度: {batch_generate}")
		print(f"😊 批量生成表情: {batch_expressions}")
		print(f"👔 服装变体模式: {variant_mode}")
		if variant_mode != "none":
			print(f"👔 服装变体值: {variant_value}")
		print(f"🎯 一致性级别: {consistency_level}")
		
		# 角度名称映射
		angle_names = {
			"front": "正面",
			"side": "侧面", 
			"back": "背面",
			"three-quarter": "斜侧"
		}
		
		# 表情名称映射（7种）
		expression_names = {
			"neutral": "中性",
			"happy": "开心",
			"sad": "难过",
			"angry": "愤怒",
			"surprised": "惊讶",
			"scared": "害怕",
			"smile": "微笑"
		}
		
		# 确定要生成的视角列表
		if batch_generate:
			angles_to_generate = [("front", "正面"), ("side", "侧面"), ("back", "背面")]
			print(f"📦 批量角度模式：将生成 {len(angles_to_generate)} 个角度")
		else:
			angle_name = angle_names.get(view_angle, "正面")
			angles_to_generate = [(view_angle, angle_name)]
			print(f"📸 单一角度：{angle_name}")
		
		# 确定要生成的表情列表（7种）
		if batch_expressions:
			expressions_to_generate = [
				("neutral", "中性"), ("happy", "开心"), ("sad", "难过"),
				("angry", "愤怒"), ("surprised", "惊讶"), ("scared", "害怕"),
				("smile", "微笑")
			]
			print(f"😊 批量表情模式：将生成 {len(expressions_to_generate)} 种表情")
		else:
			expression_name = expression_names.get(expression, "中性")
			expressions_to_generate = [(expression, expression_name)]
			print(f"😊 单一表情：{expression_name}")
		
		# 计算总数量
		total_count = len(angles_to_generate) * len(expressions_to_generate)
		print(f"📦 总计将生成：{total_count} 张照片 ({len(angles_to_generate)}角度 × {len(expressions_to_generate)}表情)")
		
		# 确定批量生成类型（用于一致性优化）
		batch_type = "none"
		if batch_generate and batch_expressions:
			batch_type = "angle+expression"
		elif batch_generate:
			batch_type = "angle"
		elif batch_expressions:
			batch_type = "expression"
		elif variant_mode != "none":
			batch_type = "variant"
		
		print(f"🎯 批量类型: {batch_type}")
		print(f"🎯 一致性优化: 已启用（medium级别）")
		
		# 禁用按钮
		self.char_btn_gen_photo.config(state=DISABLED)
		self.status.set(f"🎨 正在生成\"{character_name}\"的照片 (共{total_count}张)...")
		if hasattr(self, 'update_header_status'):
			self.update_header_status(f"生成人物照片...", "🎨")
		
		def generate_photo_thread():
			generated_photos = []  # 存储生成的照片信息
			
			try:
				print(f"\n{'='*60}\n开始生成人物照片: {character_name}\n{'='*60}")
				print(f"📦 将生成 {total_count} 张照片")
				
				# 检查是否配置了API
				img_api_type = self.img_api_type.get() if hasattr(self, 'img_api_type') else "openai"
				print(f"图片API类型: {img_api_type}")
				
				# 双重循环生成每个角度和表情的组合
				current_index = 0
				for angle, angle_name in angles_to_generate:
					for expr, expr_name in expressions_to_generate:
						current_index += 1
						print(f"\n{'='*50}")
						print(f"📸 [{current_index}/{total_count}] 正在生成：{angle_name}视图 + {expr_name}表情")
						print(f"{'='*50}\n")
						
						# 更新状态
						self.after(0, lambda i=current_index, a=angle_name, e=expr_name: self.status.set(
							f"🎨 [{i}/{total_count}] 正在生成\"{character_name}\"的{a}照片（{e}）..."
						))
						if hasattr(self, 'update_header_status'):
							self.after(0, lambda i=current_index, a=angle_name, e=expr_name: self.update_header_status(
								f"[{i}/{total_count}] {a}+{e}...", "🎨"
							))
						
						if img_api_type == "hunyuan":
							# 使用腾讯混元
							print(f"使用腾讯混元API - {angle_name}视图 + {expr_name}表情")
							secret_id = self.hunyuan_secret_id.get() if hasattr(self, 'hunyuan_secret_id') else ""
							secret_key = self.hunyuan_secret_key.get() if hasattr(self, 'hunyuan_secret_key') else ""
							
							if not secret_id or not secret_key:
								print("腾讯混元API密钥未配置")
								self.after(0, lambda: messagebox.showerror("错误", "请先在配置页面设置腾讯混元API密钥"))
								self.after(0, lambda: self.status.set("❌ 未配置API密钥"))
								if hasattr(self, 'update_header_status'):
									self.after(0, lambda: self.update_header_status("未配置API", "❌"))
								return
							
							# 🎯 使用专业的提示词构建器（使用当前角度、表情、变体和一致性优化）
							composition = "upper_body" if style == "证件照" else "full_body"
							
							full_prompt = CharacterPromptBuilder.build_character_photo_prompt(
								description=description,
								style=style,
								view_angle=angle,  # 使用当前循环的角度
								expression=expr,   # 使用当前循环的表情
								composition=composition,
								extra_details=extra_desc,
								language="zh",
								default_nationality="chinese",
								variant=variant_value,
								variant_mode=variant_mode,
								consistency_level=consistency_level,  # 使用用户选择的一致性级别
								batch_type=batch_type  # 传递批量类型
							)
							
							# 针对腾讯混元优化（限制256字符）
							full_prompt = CharacterPromptBuilder.optimize_for_api(full_prompt, "hunyuan", 256)
							
							print(f"📝 腾讯混元提示词 ({angle_name}+{expr_name}): {full_prompt}")
						
							self.after(0, lambda a=angle_name, e=expr_name: self.status.set(f"🚀 正在调用腾讯混元API生成{a}+{e}照片..."))
							
							client = HunyuanImageClient(secret_id=secret_id, secret_key=secret_key)
							result = client.generate(
								prompt=full_prompt,
								resolution="1024:1024",
								style="201"
							)
							
							# 解析base64图片
							img_base64 = result["ResultImage"]
							img_data = base64.b64decode(img_base64)
							img = Image.open(BytesIO(img_data))
							
						else:
							# 使用OpenAI DALL-E或兼容API
							print(f"使用OpenAI或兼容API - {angle_name}视图 + {expr_name}表情")
							api_key = self.img_api_key.get()
							base_url = self.img_base_url.get() if hasattr(self, 'img_base_url') and self.img_base_url.get() else None
							model = self.img_model.get() if hasattr(self, 'img_model') else "dall-e-3"
							
							# 检查是否是本地SD
							current_preset = self.img_api_preset.get() if hasattr(self, 'img_api_preset') else ""
							provider = self.img_api_presets.get(current_preset, {}).get("provider", "openai") if hasattr(self, 'img_api_presets') else "openai"
							
							print(f"API Key存在: {bool(api_key)}, Base URL: {base_url}, Model: {model}, Provider: {provider}")
							
							# 本地SD不需要API Key
							if provider != "sd" and not api_key:
								print("图片API密钥未配置")
								self.after(0, lambda: messagebox.showerror("错误", "请先在'图片生成-配置'页面设置API密钥"))
								self.after(0, lambda: self.status.set("❌ 未配置API密钥"))
								if hasattr(self, 'update_header_status'):
									self.after(0, lambda: self.update_header_status("未配置API", "❌"))
								return
							
							# 本地SD处理
							if provider == "sd":
								print(f"使用本地Stable Diffusion - {angle_name}视角 + {expr_name}表情")
								from src.clients.sd_client import StableDiffusionClient
								
								# 🎯 关键：检查是否已有参考图（第一张标准形象）
								reference_image = None
								use_img2img = False
								
								# ✅ 线程安全：检查列表非空且有元素
								if current_index > 1 and generated_photos and len(generated_photos) > 0:
									try:
										# 如果不是第一张，使用第一张作为参考
										reference_image = generated_photos[0].get("image")
										if reference_image:
											use_img2img = True
											print(f"  🔗 使用第一张图片作为参考（强制一致性）")
										else:
											print(f"  ⚠️ 第一张图片数据无效，使用 txt2img")
									except (IndexError, KeyError) as e:
										print(f"  ⚠️ 无法访问参考图: {e}，使用 txt2img")
								
								# 构建SD标签式提示词
								composition = "upper_body" if style == "证件照" else "full_body"
								
								# 如果使用 img2img，简化提示词（只描述变化的部分）
								if use_img2img:
									# 只描述角度和表情，不描述服装和发型
									full_prompt = CharacterPromptBuilder.build_character_photo_prompt(
										description="",  # 不使用原描述，靠参考图保持
										style=style,
										view_angle=angle,
										expression=expr,
										composition=composition,
										extra_details=f"{angle_name} view, {expr_name} expression",
										language="en",
										default_nationality="chinese",
										variant="",  # img2img 时不使用变体
										variant_mode="none",
										consistency_level="high",  # 强制高一致性
										batch_type=batch_type
									)
								else:
									# 第一张：使用完整描述
									full_prompt = CharacterPromptBuilder.build_character_photo_prompt(
										description=description,
										style=style,
										view_angle=angle,
										expression=expr,
										composition=composition,
										extra_details=extra_desc,
										language="en",
										default_nationality="chinese",
										variant=variant_value,
									variant_mode=variant_mode,
									consistency_level=consistency_level,
									batch_type=batch_type,
									api_type="sd"  # ✅ SD使用标签式提示词
								)
								full_prompt = CharacterPromptBuilder.optimize_for_api(full_prompt, "sd", 1000)
								print(f"📝 SD标签式提示词 ({angle_name}+{expr_name}): {full_prompt[:200]}...")
								
								self.after(0, lambda a=angle_name, e=expr_name: self.status.set(f"🚀 正在调用本地SD生成{a}+{e}照片..."))
								
								sd_base_url = base_url or "http://localhost:7860"
								sd_client = StableDiffusionClient(base_url=sd_base_url)
								
								# 使用专业的负面提示词（包含多人物限制）
								negative_prompt = CharacterPromptBuilder.get_negative_prompt_for_character("sd")
								
								# 🎯 如果使用 img2img，添加强力一致性负面词
								if use_img2img:
									consistency_negative = [
										"different clothing", "clothing change", "different outfit", "wardrobe change",
										"different hairstyle", "hair change", "different hair color", "haircut",
										"different accessories", "different style", "style change",
										"different person", "another character", "face swap", "body swap"
									]
									negative_prompt = negative_prompt + ", " + ", ".join(consistency_negative)
									print(f"🔒 强力一致性负面词: {', '.join(consistency_negative[:5])}...")
								
								print(f"🚫 SD完整负面提示词: {negative_prompt[:150]}...")
								
								# 根据是否使用 img2img 调用不同方法
								if use_img2img:
									# 使用 img2img 保持一致性
									print(f"  🎨 使用 img2img 模式（denoising_strength=0.4）")
									
									# 直接传入 PIL Image 对象
									images = sd_client.img2img(
										init_image=reference_image,  # ✅ 第一个参数是 PIL Image
										prompt=full_prompt,
										negative_prompt=negative_prompt,
										denoising_strength=0.4,  # 🎯 关键：低值保持一致性
										width=1024,
										height=1024,
										steps=25,  # img2img 可以用更多步数
										cfg_scale=8.5,  # 更高的 CFG 提高对提示词的遵循
										sampler_name="Euler a"
									)
								else:
									# 第一张使用 txt2img
									print(f"  🎨 使用 txt2img 模式（生成基准图）")
									
									# 计算固定 seed（基于人物名字）
									import hashlib
									seed = int(hashlib.md5(character_name.encode()).hexdigest()[:8], 16)
									print(f"  🎲 固定 seed: {seed}")
									
									images = sd_client.txt2img(
										prompt=full_prompt,
										negative_prompt=negative_prompt,
										width=1024,
										height=1024,
										steps=20,
										cfg_scale=7.5,
										sampler_name="Euler a",
										seed=seed  # 固定 seed 保证可复现
									)
								
								if images:
									img = images[0]
								else:
									raise RuntimeError("SD生成失败")
							
							else:
								# 🎯 使用API自然语言提示词（根据选择的API类型自动调整）
								composition = "upper_body" if style == "证件照" else "full_body"
								
								# 根据provider确定api_type
								if "hunyuan" in provider.lower():
									current_api_type = "hunyuan"
								elif "openai" in provider.lower() or "dalle" in provider.lower():
									current_api_type = "openai"
								else:
									current_api_type = "openai"  # 默认使用OpenAI格式
								
								full_prompt = CharacterPromptBuilder.build_character_photo_prompt(
									description=description,
									style=style,
									view_angle=angle,  # 使用当前循环的角度
									expression=expr,   # 使用当前循环的表情
									composition=composition,
									extra_details=extra_desc,
									language="en",
									default_nationality="chinese",
									variant=variant_value,
									variant_mode=variant_mode,
									consistency_level=consistency_level,  # 使用用户选择的一致性级别
									batch_type=batch_type,  # 传递批量类型
									api_type=current_api_type  # ✅ API使用自然语言提示词
								)
								
								# 针对不同API优化长度
								full_prompt = CharacterPromptBuilder.optimize_for_api(full_prompt, current_api_type, 1000)
								
								print(f"📝 {current_api_type.upper()}自然语言提示词 ({angle_name}+{expr_name}): {full_prompt[:200]}...")
							
								self.after(0, lambda a=angle_name, e=expr_name: self.status.set(f"🚀 正在调用图片API生成{a}+{e}照片..."))
								
								print(f"创建OpenAIImageClient...")
								client = OpenAIImageClient(api_key=api_key, base_url=base_url, model=model)
								print(f"调用generate方法...")
								results = client.generate(full_prompt, size="1024x1024")
								print(f"收到结果: {len(results) if results else 0} 张图片")
								
								# 获取第一张图片
								if results:
									img = results[0].image
								else:
									raise RuntimeError("API未返回任何图片")
						
						# 保存图片到内存（最后一张用于预览）
						self.character_last_image = img
						
						# 保存当前角度和表情的照片
						print(f"✅ [{current_index}/{total_count}] {angle_name}+{expr_name}照片生成成功")
					
						# 构建文件名（包含角度、表情和变体）
						filename_parts = [character_name]
						
						# 添加角度信息（如果有多个角度或不是正面）
						if batch_generate or angle != "front":
							filename_parts.append(angle_name)
						
						# 添加表情信息（如果有多种表情或不是中性表情）
						if batch_expressions or expr != "neutral":
							filename_parts.append(expr_name)
						
						# 添加变体信息（如果使用了变体）
						if variant_mode == "preset" and variant_value:
							# 变体名称映射
							variant_name_map = {
								"formal": "正装",
								"casual": "休闲",
								"sport": "运动",
								"traditional": "古装",
								"artistic": "艺术",
								"professional": "职业"
							}
							variant_name = variant_name_map.get(variant_value, variant_value)
							filename_parts.append(variant_name)
						elif variant_mode == "custom" and variant_value and not variant_value.startswith("例如"):
							# 自定义变体，取前10个字符作为标识
							variant_short = variant_value[:10].replace(" ", "_")
							filename_parts.append(variant_short)
						
						filename = "_".join(filename_parts) + ".png"
						
						# 保存照片
						saved_path = self._auto_save_character_photo_with_name(img, character_name, filename)
						
						if saved_path:
							print(f"💾 已保存: {saved_path}")
							generated_photos.append({
								"angle": angle,
								"angle_name": angle_name,
								"expression": expr,
								"expression_name": expr_name,
								"path": saved_path,
								"image": img
							})
					
				# 所有角度生成完毕后，在主线程中更新UI
				def update_ui_and_save():
					# 更新预览（显示最后一张）
					if generated_photos:
						last_photo = generated_photos[-1]
						self._update_character_photo_preview(last_photo["image"])
						
						# 获取项目名称
						if self.current_project:
							project_name = self.current_project.metadata.get("name", "未命名项目")
						else:
							project_name = "未知项目"
						
					# 根据生成数量显示不同的消息
					if len(generated_photos) > 1:
						# 构建照片列表描述
						photo_desc_list = []
						for p in generated_photos:
							desc_parts = []
							if p["angle_name"]:
								desc_parts.append(p["angle_name"])
							if p.get("expression_name") and p["expression_name"] != "中性":
								desc_parts.append(p["expression_name"])
							photo_desc_list.append("+".join(desc_parts) if desc_parts else "照片")
						
						photo_list_str = "、".join(photo_desc_list)
						self.status.set(f"✅ 成功生成{len(generated_photos)}张照片（{photo_list_str}）并保存到项目 [{project_name}]")
						
						# 构建详细消息
						detail_list = "\n".join([f"• {desc}" for desc in photo_desc_list])
						messagebox.showinfo("成功", f"已成功生成并保存 {len(generated_photos)} 张照片！\n\n{detail_list}\n\n保存位置：项目/characters/{character_name}_xxx.png")
					else:
						photo = generated_photos[0]
						desc_parts = [photo["angle_name"]]
						if photo.get("expression_name") and photo["expression_name"] != "中性":
							desc_parts.append(photo["expression_name"])
						desc = "+".join(desc_parts)
						self.status.set(f"✅ 成功生成并保存\"{character_name}\"的{desc}照片到项目 [{project_name}]")
					
					if not generated_photos:
						self.status.set(f"❌ 照片生成失败或未保存")
					# 启用保存按钮
					self.char_btn_save_photo.config(state=NORMAL)
					# 更新参考人物列表
					self._update_reference_character_list()
					# 更新顶部状态
					if hasattr(self, 'update_header_status'):
						self.update_header_status("照片生成完成", "✅")
				
				self.after(0, update_ui_and_save)
				
			except Exception as e:
				import traceback
				error_detail = traceback.format_exc()
				error_msg = f"生成照片失败: {str(e)}"
				print(f"\n{'='*60}\n生成人物照片时发生错误：\n{error_detail}\n{'='*60}\n")
				
				# 显示更详细的错误信息
				if "401" in str(e) or "authentication" in str(e).lower():
					error_msg = "API密钥无效或已过期，请检查配置"
				elif "timeout" in str(e).lower():
					error_msg = "API请求超时，请检查网络连接"
				elif "rate" in str(e).lower() or "quota" in str(e).lower():
					error_msg = "API配额用尽或请求频率过高"
				
				self.after(0, lambda msg=error_msg: messagebox.showerror("生成失败", msg))
				self.after(0, lambda: self.status.set("❌ 生成照片失败"))
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("生成失败", "❌"))
			finally:
				self.after(0, lambda: self.char_btn_gen_photo.config(state=NORMAL))
		
		threading.Thread(target=generate_photo_thread, daemon=True).start()
	
	
	
	
	def _update_character_photo_preview(self, img: Image.Image) -> None:
		"""更新人物照片预览"""
		canvas_width = self.char_canvas.winfo_width()
		canvas_height = self.char_canvas.winfo_height()
		
		# 如果Canvas还没有初始化大小，使用默认值
		if canvas_width <= 1:
			canvas_width = 400
		if canvas_height <= 1:
			canvas_height = 400
		
		img_width, img_height = img.size
		
		# 计算缩放比例
		width_ratio = canvas_width / img_width
		height_ratio = canvas_height / img_height
		scale_ratio = min(width_ratio, height_ratio, 1.0)
		
		new_w = int(img_width * scale_ratio)
		new_h = int(img_height * scale_ratio)
		
		# 缩放图片
		resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
		
		# 转换为PhotoImage
		self.character_preview_photo = ImageTk.PhotoImage(resized_img)
		
		# 更新Label
		self.char_preview.configure(image=self.character_preview_photo, text="")
		
		# 更新Canvas的滚动区域 - 确保图片可以完全滚动查看
		# 如果图片比Canvas大，设置滚动区域为图片尺寸
		# 如果图片比Canvas小，设置滚动区域为Canvas尺寸
		scroll_width = max(new_w, canvas_width)
		scroll_height = max(new_h, canvas_height)
		self.char_canvas.configure(scrollregion=(0, 0, scroll_width, scroll_height))
		
		# 居中显示
		if new_w < canvas_width:
			x_offset = (canvas_width - new_w) // 2
		else:
			x_offset = 0
		
		if new_h < canvas_height:
			y_offset = (canvas_height - new_h) // 2
		else:
			y_offset = 0
		
		self.char_canvas.coords(self.char_canvas_window, x_offset, y_offset)
	
	
	
	
	def _auto_save_character_photo(self, index: int, img: Image.Image, character_name: str) -> str:
		"""自动保存人物照片到当前项目的characters文件夹，并保存描述信息"""
		try:
			import re
			import json
			from pathlib import Path
			
			# 检查是否有当前项目
			if not self.current_project:
				messagebox.showwarning("提示", "请先创建或打开一个项目，人物照片将保存到项目目录中")
				return ""
			
			# 确定保存目录：项目目录/characters/
			self.character_photos_dir = self.current_project.project_dir / "characters"
			
			# 确保文件夹存在
			if not self.character_photos_dir.exists():
				print(f"📁 创建人物照片文件夹：{self.character_photos_dir}")
			self.character_photos_dir.mkdir(parents=True, exist_ok=True)
			
			# 验证文件夹创建成功
			if not self.character_photos_dir.exists():
				print(f"❌ 文件夹创建失败：{self.character_photos_dir}")
				return ""
			
			# 生成文件名（只使用人物名称，不加时间戳，这样同一人物会覆盖旧照片）
			clean_name = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', character_name)
			filename = f"{clean_name}.png"
			
			save_path = self.character_photos_dir / filename
			print(f"💾 准备保存到：{save_path}")
			
			img.save(str(save_path))
			
			# 验证文件保存成功
			if not save_path.exists():
				print(f"❌ 文件保存失败：{save_path}")
				return ""
			
			# 更新人物列表中的照片路径
			self.character_list[index]["photo_path"] = str(save_path)
			
			# 保存人物描述到 JSON 文件
			characters_info_path = self.character_photos_dir / "characters_info.json"
			
			# 读取现有的描述信息（如果存在）
			characters_info = {}
			if characters_info_path.exists():
				try:
					with open(characters_info_path, 'r', encoding='utf-8') as f:
						characters_info = json.load(f)
				except:
					pass
			
			# 更新当前人物的描述
			characters_info[character_name] = {
				"description": self.character_list[index].get("description", ""),
				"photo_path": str(save_path)
			}
			
			# 保存到文件
			with open(characters_info_path, 'w', encoding='utf-8') as f:
				json.dump(characters_info, f, ensure_ascii=False, indent=2)
			
			print(f"✅ 人物照片已自动保存到项目：{save_path}")
			print(f"📊 文件大小：{save_path.stat().st_size / 1024:.2f} KB")
			print(f"💾 人物描述已保存到：{characters_info_path}")
			return str(save_path)
			
		except Exception as e:
			print(f"❌ 自动保存失败：{str(e)}")
			import traceback
			traceback.print_exc()
			return ""
	
	
	
	
	def _auto_save_character_photo_with_name(self, img: Image.Image, character_name: str, filename: str) -> str:
		"""自动保存人物照片（支持自定义文件名，用于多角度生成）"""
		try:
			from pathlib import Path
			
			# 检查是否有当前项目
			if not self.current_project:
				return ""
			
			# 确定保存目录：项目目录/characters/
			self.character_photos_dir = self.current_project.project_dir / "characters"
			self.character_photos_dir.mkdir(parents=True, exist_ok=True)
			
			# 使用提供的文件名
			save_path = self.character_photos_dir / filename
			print(f"💾 保存照片到：{save_path}")
			
			img.save(str(save_path))
			
			if save_path.exists():
				print(f"✅ 照片已保存：{save_path} ({save_path.stat().st_size / 1024:.2f} KB)")
				return str(save_path)
			else:
				print(f"❌ 文件保存失败：{save_path}")
				return ""
			
		except Exception as e:
			print(f"❌ 保存失败：{str(e)}")
			import traceback
			traceback.print_exc()
			return ""
	
	
	
	
	def _on_view_character_gallery(self) -> None:
		"""查看人物图片库"""
		print(f"\n{'='*60}")
		print(f"📸 打开图片库")
		print(f"{'='*60}")
		
		selection = self.char_listbox.curselection()
		if not selection:
			messagebox.showwarning("提示", "请先从列表中选择一个人物！")
			return
		
		index = selection[0]
		character = self.character_list[index]
		character_name = character["name"]
		print(f"✅ 选中人物: {character_name}")
		
		# 检查当前项目
		if not self.current_project:
			messagebox.showwarning("提示", "请先创建或打开一个项目！")
			return
		
		# 获取人物图片目录
		char_dir = self.current_project.project_dir / "characters"
		print(f"📁 图片目录: {char_dir}")
		print(f"📁 目录存在: {char_dir.exists()}")
		
		if not char_dir.exists():
			messagebox.showinfo("提示", f"还没有生成\"{character_name}\"的照片")
			return
		
		# 查找该人物的所有图片
		import re
		clean_name = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', character_name)
		print(f"🔍 搜索模式: {clean_name}*.png")
		
		char_images = list(char_dir.glob(f"{clean_name}*.png"))
		print(f"📷 找到图片数量: {len(char_images)}")
		
		if char_images:
			print(f"📋 图片列表:")
			for img in char_images:
				print(f"  - {img.name} (存在: {img.exists()}, 大小: {img.stat().st_size if img.exists() else 'N/A'} bytes)")
		
		if not char_images:
			messagebox.showinfo("提示", f"还没有生成\"{character_name}\"的照片")
			return
		
		# 创建图片库窗口
		gallery_window = tk.Toplevel(self)
		gallery_window.title(f"{character_name} - 图片库")
		gallery_window.geometry("900x700")
		
		# 标题
		title_frame = ttk.Frame(gallery_window)
		title_frame.pack(fill="x", padx=20, pady=15)
		
		ttk.Label(title_frame, text=f"🎨 {character_name} 的图片库", 
				 font=("", 14, "bold")).pack(side=LEFT)
		ttk.Label(title_frame, text=f"共 {len(char_images)} 张图片", 
				 font=("", 11)).pack(side=RIGHT)
		
		# 创建可滚动区域
		canvas = tk.Canvas(gallery_window, bg="#2b2b2b")
		scrollbar = ttk.Scrollbar(gallery_window, orient=VERTICAL, command=canvas.yview)
		scrollable_frame = ttk.Frame(canvas)
		
		scrollable_frame.bind(
			"<Configure>",
			lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
		)
		
		canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
		canvas.configure(yscrollcommand=scrollbar.set)
		
		# 存储所有卡片引用，用于删除后刷新
		card_refs = []
		col_count = 3  # 定义列数（移到外部作用域）
		
		def refresh_gallery():
			"""刷新图片库显示"""
			# 重新扫描图片
			updated_images = list(char_dir.glob(f"{clean_name}*.png"))
			
			# 更新标题中的图片数量
			for widget in title_frame.winfo_children():
				if isinstance(widget, ttk.Label) and "共" in widget.cget("text"):
					widget.config(text=f"共 {len(updated_images)} 张图片")
			
			# 清空现有卡片
			for widget in scrollable_frame.winfo_children():
				widget.destroy()
			card_refs.clear()
			
			# 如果没有图片了，显示提示
			if not updated_images:
				ttk.Label(scrollable_frame, text="📭 该人物已无照片", 
						 font=("", 14)).grid(row=0, column=0, columnspan=3, pady=50)
				return
			
			# 重新加载图片
			load_images(updated_images)
		
		def load_images(images_list):
			"""加载并显示图片"""
			print(f"📸 开始加载 {len(images_list)} 张图片...")
			
			for idx, img_path in enumerate(sorted(images_list)):
				row = idx // col_count
				col = idx % col_count
				
				print(f"  [{idx+1}/{len(images_list)}] 加载: {img_path}")
				
				# 创建图片卡片
				card = ttk.Frame(scrollable_frame, relief="solid", borderwidth=1)
				card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
				card_refs.append(card)
				
				try:
					# 验证文件存在
					if not img_path.exists():
						print(f"  ❌ 文件不存在: {img_path}")
						ttk.Label(card, text=f"文件不存在:\n{img_path.name}", 
								 foreground="red").pack(pady=20)
						continue
					
					print(f"  ✅ 文件存在，尝试加载图片...")
					# 加载图片
					img = Image.open(img_path)
					print(f"  ✅ 图片已打开，尺寸: {img.size}")
					
					# 缩略图
					img.thumbnail((250, 250), Image.Resampling.LANCZOS)
					print(f"  ✅ 缩略图已生成，尺寸: {img.size}")
					
					photo = ImageTk.PhotoImage(img)
					print(f"  ✅ PhotoImage 已创建")
					
					# 图片标签
					img_label = tk.Label(card, image=photo, bg="#1e1e1e", cursor="hand2")
					img_label.image = photo  # 保持引用
					img_label.pack(padx=5, pady=5)
					
					# 添加点击放大功能
					def create_zoom_handler(path):
						def on_click(event):
							self._show_image_fullsize(path)
						return on_click
					
					img_label.bind("<Button-1>", create_zoom_handler(img_path))
					
					# 添加悬停提示
					def on_enter(event):
						img_label.config(bg="#3a3a3a")
					def on_leave(event):
						img_label.config(bg="#1e1e1e")
					
					img_label.bind("<Enter>", on_enter)
					img_label.bind("<Leave>", on_leave)
					
					# 文件名标签
					filename = img_path.stem
					ttk.Label(card, text=filename, font=("", 9)).pack(pady=(0, 5))
					
					# 删除按钮
					def create_delete_handler(path):
						def on_delete():
							# 确认删除
							result = messagebox.askyesno(
								"确认删除",
								f"确定要删除这张照片吗？\n\n{path.name}\n\n本地文件也会被永久删除！",
								icon="warning"
							)
							if result:
								try:
									# 删除文件
									path.unlink()
									print(f"✅ 已删除图片: {path}")
									
									# 刷新图片库
									refresh_gallery()
									
									# 更新状态
									self.status.set(f"✅ 已删除照片: {path.name}")
									
								except Exception as e:
									messagebox.showerror("删除失败", f"无法删除文件：\n{str(e)}")
									print(f"❌ 删除失败: {e}")
						return on_delete
					
					delete_btn = ttk.Button(
						card, 
						text="🗑️ 删除", 
						command=create_delete_handler(img_path),
						width=10
					)
					delete_btn.pack(pady=(0, 5))
					
				except Exception as e:
					error_msg = f"加载失败:\n{img_path.name}\n{str(e)}"
					print(f"  ❌ 加载图片失败: {e}")
					import traceback
					traceback.print_exc()
					ttk.Label(card, text=error_msg, foreground="red", 
							 font=("", 8)).pack(pady=20)
		
		# 初始加载
		load_images(char_images)
		
		# 配置列权重
		for i in range(col_count):
			scrollable_frame.columnconfigure(i, weight=1)
		
		canvas.pack(side=LEFT, fill=BOTH, expand=True, padx=(20, 0), pady=(0, 20))
		scrollbar.pack(side=RIGHT, fill=Y, padx=(0, 20), pady=(0, 20))
		
		# 鼠标滚轮支持
		def _on_mousewheel(event):
			canvas.yview_scroll(int(-1*(event.delta/120)), "units")
		
		# ✅ 只绑定到当前 canvas，不影响其他窗口
		mousewheel_binding = canvas.bind("<MouseWheel>", _on_mousewheel)
		
		# 关闭时清理资源
		def on_close():
			# ✅ 只解绑当前 canvas
			try:
				canvas.unbind("<MouseWheel>", mousewheel_binding)
			except:
				pass
			
			# ✅ 清理图片引用，释放内存
			for widget in scrollable_frame.winfo_children():
				try:
					for child in widget.winfo_children():
						if hasattr(child, 'image'):
							child.image = None
				except:
					pass
			
			gallery_window.destroy()
		
		gallery_window.protocol("WM_DELETE_WINDOW", on_close)
	
	
	def _show_image_fullsize(self, img_path) -> None:
		"""显示图片的全尺寸查看窗口"""
		# 创建全屏查看窗口
		viewer = tk.Toplevel(self)
		viewer.title(f"查看图片 - {img_path.name}")
		viewer.geometry("1200x900")
		viewer.configure(bg="#000000")
		
		# 居中显示
		viewer.update_idletasks()
		x = (viewer.winfo_screenwidth() - 1200) // 2
		y = (viewer.winfo_screenheight() - 900) // 2
		viewer.geometry(f"1200x900+{x}+{y}")
		
		# 顶部工具栏
		toolbar = ttk.Frame(viewer)
		toolbar.pack(fill="x", padx=10, pady=10)
		
		ttk.Label(toolbar, text=img_path.name, font=("", 12, "bold")).pack(side=LEFT, padx=10)
		
		# 缩放控制
		zoom_frame = ttk.Frame(toolbar)
		zoom_frame.pack(side=RIGHT, padx=10)
		
		zoom_label = ttk.Label(zoom_frame, text="100%", font=("", 10))
		zoom_label.pack(side=RIGHT, padx=5)
		
		# 关闭按钮
		ttk.Button(toolbar, text="✕ 关闭", command=viewer.destroy).pack(side=RIGHT, padx=5)
		
		# 创建画布用于显示图片
		canvas = tk.Canvas(viewer, bg="#000000", highlightthickness=0)
		canvas.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))
		
		# 加载原始图片
		try:
			original_img = Image.open(img_path)
			img_width, img_height = original_img.size
			
			# 计算适合窗口的初始缩放
			canvas_width = 1180
			canvas_height = 800
			
			scale_w = canvas_width / img_width
			scale_h = canvas_height / img_height
			scale = min(scale_w, scale_h, 1.0)  # 不放大，最多显示原始大小
			
			current_scale = [scale]  # 使用列表以便在闭包中修改
			
			def update_image(new_scale=None):
				"""更新图片显示"""
				if new_scale is not None:
					current_scale[0] = new_scale
				
				scale_val = current_scale[0]
				new_width = int(img_width * scale_val)
				new_height = int(img_height * scale_val)
				
				# 调整图片大小
				resized_img = original_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
				photo = ImageTk.PhotoImage(resized_img)
				
				# 清除画布
				canvas.delete("all")
				
				# 居中显示
				x = (canvas_width - new_width) // 2
				y = (canvas_height - new_height) // 2
				canvas.create_image(x, y, image=photo, anchor="nw")
				canvas.image = photo  # 保持引用
				
				# 更新缩放比例显示
				zoom_label.config(text=f"{int(scale_val * 100)}%")
			
			# 初始显示
			update_image()
			
			# 缩放按钮
			def zoom_in():
				new_scale = min(current_scale[0] * 1.2, 3.0)  # 最大300%
				update_image(new_scale)
			
			def zoom_out():
				new_scale = max(current_scale[0] / 1.2, 0.1)  # 最小10%
				update_image(new_scale)
			
			def zoom_reset():
				# 重置到适合窗口大小
				scale_w = canvas_width / img_width
				scale_h = canvas_height / img_height
				new_scale = min(scale_w, scale_h, 1.0)
				update_image(new_scale)
			
			def zoom_actual():
				# 显示实际大小（100%）
				update_image(1.0)
			
			# 添加缩放按钮
			ttk.Button(zoom_frame, text="🔍+", command=zoom_in, width=5).pack(side=LEFT, padx=2)
			ttk.Button(zoom_frame, text="🔍-", command=zoom_out, width=5).pack(side=LEFT, padx=2)
			ttk.Button(zoom_frame, text="适合", command=zoom_reset, width=5).pack(side=LEFT, padx=2)
			ttk.Button(zoom_frame, text="100%", command=zoom_actual, width=5).pack(side=LEFT, padx=2)
			
			# 鼠标滚轮缩放
			def on_mousewheel(event):
				if event.delta > 0:
					zoom_in()
				else:
					zoom_out()
			
			canvas.bind_all("<MouseWheel>", on_mousewheel)
			
			# 点击画布关闭（可选）
			def on_canvas_click(event):
				pass  # 可以添加其他交互
			
			canvas.bind("<Button-1>", on_canvas_click)
			
			# 快捷键
			def on_key(event):
				if event.keysym == "Escape":
					viewer.destroy()
				elif event.keysym == "plus" or event.keysym == "equal":
					zoom_in()
				elif event.keysym == "minus":
					zoom_out()
				elif event.keysym == "0":
					zoom_reset()
			
			viewer.bind("<Key>", on_key)
			
			# 关闭时解绑
			def on_close():
				canvas.unbind_all("<MouseWheel>")
				viewer.destroy()
			
			viewer.protocol("WM_DELETE_WINDOW", on_close)
			
			# 显示图片信息
			info_text = f"尺寸: {img_width} × {img_height} | 文件: {img_path.name}"
			info_label = ttk.Label(viewer, text=info_text, font=("", 9), foreground="#888")
			info_label.pack(side=BOTTOM, pady=5)
			
		except Exception as e:
			messagebox.showerror("加载失败", f"无法加载图片：\n{str(e)}")
			viewer.destroy()
	
	def _on_save_character_photo(self) -> None:
		"""额外保存人物照片副本（可选）"""
		if not self.character_last_image:
			messagebox.showwarning("提示", "没有可保存的照片")
			return
		
		selection = self.char_listbox.curselection()
		if not selection:
			return
		
		index = selection[0]
		character = self.character_list[index]
		character_name = character["name"]
		
		# 弹出保存对话框，允许用户保存副本到其他位置
		file_path = filedialog.asksaveasfilename(
			defaultextension=".png",
			filetypes=[("PNG图片", "*.png"), ("JPEG图片", "*.jpg"), ("所有文件", "*.*")],
			initialfile=f"{character_name}_photo.png"
		)
		
		if file_path:
			try:
				self.character_last_image.save(file_path)
				self.status.set(f"✅ 照片副本已保存：{file_path}")
				messagebox.showinfo("成功", f"照片副本已保存到：\n{file_path}")
			except Exception as e:
				messagebox.showerror("错误", f"保存失败：{str(e)}")
	
	
	
	