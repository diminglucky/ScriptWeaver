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
from ...helpers.character_sheet_builder import CharacterSheetBuilder


class CharacterPhotoMixin:
	"""人物 char_photo 功能"""
	
	def _on_generate_character_photo(self) -> None:
		"""生成选中人物的照片"""
		print("🔔 _on_generate_character_photo 被调用")
		
		import threading
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
		character = self.character_list[index]
		character_name = character["name"]
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
		
		# 获取视角、表情和批量生成选项
		view_angle = self.char_view_angle.get() if hasattr(self, 'char_view_angle') else "front"
		expression = self.char_expression.get() if hasattr(self, 'char_expression') else "neutral"
		batch_generate = self.char_batch_generate.get() if hasattr(self, 'char_batch_generate') else False
		batch_expressions = self.char_batch_expressions.get() if hasattr(self, 'char_batch_expressions') else False
		
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
		
		# 表情名称映射
		expression_names = {
			"neutral": "中性",
			"happy": "开心",
			"sad": "悲伤",
			"angry": "愤怒",
			"surprised": "惊讶"
		}
		
		# 确定要生成的视角列表
		if batch_generate:
			angles_to_generate = [("front", "正面"), ("side", "侧面"), ("back", "背面")]
			print(f"📦 批量角度模式：将生成 {len(angles_to_generate)} 个角度")
		else:
			angle_name = angle_names.get(view_angle, "正面")
			angles_to_generate = [(view_angle, angle_name)]
			print(f"📸 单一角度：{angle_name}")
		
		# 确定要生成的表情列表
		if batch_expressions:
			expressions_to_generate = [
				("neutral", "中性"), ("happy", "开心"), ("sad", "悲伤"),
				("angry", "愤怒"), ("surprised", "惊讶")
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
							
							print(f"API Key存在: {bool(api_key)}, Base URL: {base_url}, Model: {model}")
							
							if not api_key:
								print("图片API密钥未配置")
								self.after(0, lambda: messagebox.showerror("错误", "请先在'图片生成-配置'页面设置API密钥"))
								self.after(0, lambda: self.status.set("❌ 未配置API密钥"))
								if hasattr(self, 'update_header_status'):
									self.after(0, lambda: self.update_header_status("未配置API", "❌"))
								return
							
							# 🎯 使用专业的提示词构建器（英文版，使用当前角度、表情、变体和一致性优化）
							composition = "upper_body" if style == "证件照" else "full_body"
							
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
								batch_type=batch_type  # 传递批量类型
							)
							
							# 针对OpenAI优化（DALL-E 3建议1000字符内）
							full_prompt = CharacterPromptBuilder.optimize_for_api(full_prompt, "openai", 1000)
							
							print(f"📝 OpenAI提示词 ({angle_name}+{expr_name}): {full_prompt[:200]}...")
						
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
				except Exception:
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
	
	
	
	