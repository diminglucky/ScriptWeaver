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


class PromptOperationsMixin:
	"""Image prompt_ops 功能"""
	
	def _update_after_image_generation(self, img_type: str):
		"""图片生成成功后的更新操作"""
		self._update_img_preview()
		self.img_btn_save.configure(state=NORMAL)
		self.status.set(f"✨ 【{img_type}】风格图片生成成功！")
		
		# 更新顶部状态栏
		if hasattr(self, 'update_header_status'):
			self.update_header_status("图片生成完成", "✅")
		
		# 自动保存图片到项目
		self._auto_save_image_to_project()
		
		# 生成即梦AI视频提示词
		video_prompt = self._generate_video_prompt()
		self.video_prompt_text.config(state=NORMAL)
		self.video_prompt_text.delete("1.0", END)
		self.video_prompt_text.insert("1.0", video_prompt)
		self.video_prompt_text.config(state=DISABLED)

	
	
	def _on_enhance_prompt(self) -> None:
		"""✨ AI补全/优化提示词"""
		current_prompt = self.img_txt_prompt_cn.get("1.0", END).strip()
		
		if not current_prompt:
			messagebox.showwarning("提示", "请先输入一些描述内容，AI将帮您补全和优化")
			return
		
		# 获取API配置
		selected_api = self.outline_gen_api.get() if hasattr(self, 'outline_gen_api') else "DeepSeek"
		if selected_api not in self.api_presets:
			messagebox.showerror("错误", f"未找到API配置: {selected_api}")
			return
		
		api_config = self.api_presets[selected_api]
		api_key = _sanitize(api_config.get("key", ""))
		if not api_key:
			messagebox.showwarning("提示", "请先配置API Key")
			return
		
		# 获取图片类型
		img_type = self.img_type.get() if hasattr(self, 'img_type') else "写实照片"
		
		# 禁用按钮
		self.btn_enhance_prompt.config(state=DISABLED, text="⏳")
		self.status.set("✨ AI正在优化提示词...")
		
		def enhance_thread():
			try:
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				
				instruction = f"""你是专业的AI绘图提示词专家。请将用户的简单描述扩展为详细、丰富的图片描述。

## 要求
1. 保留用户原意，但添加更多视觉细节
2. 补充画面构图、光线、氛围等
3. 补充人物的表情、姿态、服装细节
4. 补充场景的环境、色调、质感
5. 图片类型是【{img_type}】，请匹配该风格
6. 输出中文，200-300字
7. 不要输出任何解释，只输出优化后的描述

## 用户原始描述
{current_prompt}

请直接输出优化后的描述："""
				
				enhanced = client.chat([
					{"role": "user", "content": instruction}
				], temperature=0.7)
				
				# 更新UI
				self.after(0, lambda: self._update_enhanced_prompt(enhanced.strip()))
				self.after(0, lambda: self.status.set("✨ 提示词优化完成"))
				
			except Exception as e:
				self.after(0, lambda: messagebox.showerror("错误", f"优化失败: {str(e)}"))
				self.after(0, lambda: self.status.set("❌ 优化失败"))
			finally:
				self.after(0, lambda: self.btn_enhance_prompt.config(state=NORMAL, text="✨"))
		
		threading.Thread(target=enhance_thread, daemon=True).start()
	
	def _update_enhanced_prompt(self, enhanced_text: str) -> None:
		"""更新优化后的提示词"""
		self.img_txt_prompt_cn.delete("1.0", END)
		self.img_txt_prompt_cn.insert("1.0", enhanced_text)
	
	def _on_preview_prompt(self) -> None:
		"""👁️ 预览完整提示词（生成前确认）"""
		prompt_cn = self.img_txt_prompt_cn.get("1.0", END).strip()
		
		if not prompt_cn:
			messagebox.showwarning("提示", "请先输入或生成图片描述")
			return
		
		# 获取其他参数
		img_type = self.img_type.get() if hasattr(self, 'img_type') else "写实照片"
		scene = self.img_entry_scene.get().strip() if hasattr(self, 'img_entry_scene') else ""
		roles = self.img_txt_roles.get("1.0", END).strip() if hasattr(self, 'img_txt_roles') else ""
		
		# 获取选中的参考人物
		selected_chars = self._get_selected_reference_characters() if hasattr(self, '_get_selected_reference_characters') else []
		char_info = ""
		if selected_chars:
			char_names = [c.get("name", "") for c in selected_chars]
			char_info = f"\n📌 参考人物：{', '.join(char_names)}"
		
		# 获取API类型
		api_type = "腾讯混元" if hasattr(self, 'img_api_type') and self.img_api_type.get() == "hunyuan" else "OpenAI/DALL-E"
		
		# 构建预览内容
		preview_text = f"""═══════════════════════════════════════
        📝 图片生成预览
═══════════════════════════════════════

🎨 图片类型：{img_type}
🖼️ API类型：{api_type}{char_info}

═══════ 中文描述 ═══════

{prompt_cn}

"""
		if scene:
			preview_text += f"\n🏞️ 补充场景：{scene}"
		if roles:
			preview_text += f"\n👤 角色特征：{roles}"
		
		# 估算API调用成本
		if "混元" in api_type:
			cost_hint = "约 ¥0.06/张"
		else:
			cost_hint = "约 $0.04/张 (DALL-E 3)"
		
		preview_text += f"""

═══════════════════════════════════════
💰 预估成本：{cost_hint}
═══════════════════════════════════════

确认无误后，点击「生成图片」按钮开始生成。
"""
		
		# 显示预览对话框
		self._show_preview_dialog(preview_text, prompt_cn)
	
	def _show_preview_dialog(self, preview_text: str, prompt_cn: str) -> None:
		"""显示预览对话框"""
		dialog = tk.Toplevel(self)
		dialog.title("📝 提示词预览")
		dialog.geometry("600x500")
		dialog.transient(self)
		dialog.grab_set()
		
		# 居中显示
		dialog.update_idletasks()
		x = (dialog.winfo_screenwidth() - 600) // 2
		y = (dialog.winfo_screenheight() - 500) // 2
		dialog.geometry(f"+{x}+{y}")
		
		# 主框架
		main_frame = tk.Frame(dialog, bg="#2b2b2b")
		main_frame.pack(fill="both", expand=True, padx=10, pady=10)
		
		# 标题
		title_label = tk.Label(main_frame, text="👁️ 生成前预览", font=("", 14, "bold"), 
							   bg="#2b2b2b", fg="white")
		title_label.pack(pady=(0, 10))
		
		# 预览文本框
		text_frame = tk.Frame(main_frame, bg="#2b2b2b")
		text_frame.pack(fill="both", expand=True)
		
		preview_text_widget = tk.Text(text_frame, font=("", 10), wrap=tk.WORD,
									  bg="#1e1e1e", fg="#e0e0e0", relief=tk.SOLID,
									  borderwidth=1)
		preview_text_widget.pack(fill="both", expand=True)
		preview_text_widget.insert("1.0", preview_text)
		preview_text_widget.config(state=DISABLED)
		
		# 按钮框架
		btn_frame = tk.Frame(main_frame, bg="#2b2b2b")
		btn_frame.pack(fill="x", pady=(10, 0))
		
		# 编辑按钮
		def on_edit():
			dialog.destroy()
			self.img_txt_prompt_cn.focus_set()
		
		btn_edit = ttk.Button(btn_frame, text="✏️ 继续编辑", command=on_edit, width=15)
		btn_edit.pack(side=LEFT, padx=(0, 10))
		
		# 复制按钮
		def on_copy():
			self.clipboard_clear()
			self.clipboard_append(prompt_cn)
			self.status.set("📋 提示词已复制")
		
		btn_copy = ttk.Button(btn_frame, text="📋 复制", command=on_copy, width=10)
		btn_copy.pack(side=LEFT, padx=(0, 10))
		
		# 确认生成按钮
		def on_confirm():
			dialog.destroy()
			self._on_img_generate()
		
		btn_confirm = ttk.Button(btn_frame, text="🎨 确认生成", command=on_confirm, width=15)
		btn_confirm.pack(side=RIGHT)
		
		# 关闭按钮
		btn_close = ttk.Button(btn_frame, text="关闭", command=dialog.destroy, width=10)
		btn_close.pack(side=RIGHT, padx=(0, 10))
	
	def _on_copy_img_prompt(self) -> None:
		text = self.img_txt_prompt_cn.get("1.0", END)
		self.clipboard_clear()
		self.clipboard_append(text)
		self.status.set("图片描述已复制")

	
	
	def _on_clear_img_prompt(self) -> None:
		self.img_txt_prompt_cn.delete("1.0", END)
		self.status.set("图片描述已清空")

	
	
	def _on_img_build_prompt(self) -> None:
		story_text = self.output.get("1.0", END).strip()
		if not story_text:
			messagebox.showwarning("提示", "请先在'故事'页生成或粘贴正文内容，然后再提炼提示词")
			return
		try:
			self.set_busy(True)
			self.status.set("根据故事提炼图片提示词中...")
			scene = self.img_entry_scene.get().strip() if hasattr(self, 'img_entry_scene') else ""
			roles = self.img_txt_roles.get("1.0", END).strip() if hasattr(self, 'img_txt_roles') else ""
			client = DeepSeekClient(
				api_key=_sanitize(self.api_key.get()),
				base_url=_sanitize(self.base_url.get()),
				model=_sanitize(self.model.get()),
			)
			prompt_instruct = (
				"你是资深视觉提示词工程师。请基于提供的故事正文，生成一段用于文本生成图片的英文提示词，"
				"要求与故事的情节、人物外观与气质完全吻合，保持同一人物的一致性（面部、发型、年龄、服饰等）。"
				"如有参考图，将作为身份一致性的最高约束。提示词需包含：场景/构图、主体外观细节、表情动作、光线镜头、风格与质感。"
				"禁止输出任何 Markdown，仅输出单段英文提示词。"
			)
			user_payload = (
				f"故事正文：\n{story_text}\n\n"
				f"补充场景（可选）：{scene or '无'}\n"
				f"人物设定（可选）：{roles or '无'}\n"
				"请输出最终英文提示词。"
			)
			resp = client.chat([
				{"role": "system", "content": prompt_instruct},
				{"role": "user", "content": user_payload},
			], temperature=max(0.4, self.temperature.get() - 0.2))
			self.img_txt_prompt.delete("1.0", END)
			self.img_txt_prompt.insert(END, resp.strip())
			self.status.set("已生成图片提示词（请检查后点击生成图片）")
		except Exception as e:
			messagebox.showerror("错误", str(e))
		finally:
			self.set_busy(False)

	
	
	def _show_style_menu(self) -> None:
		"""显示风格选择菜单"""
		menu = tk.Menu(self, tearoff=0)
		
		# 添加"清空风格"选项
		menu.add_command(label="🗑️ 清空所有风格", command=lambda: self.style.set(""))
		menu.add_separator()
		
		# 添加"手动输入"选项
		menu.add_command(label="✏️ 手动输入风格...", command=self._manual_input_style)
		menu.add_separator()
		
		# 添加预设风格选项（分组显示）
		menu.add_command(label="📚 --- 预设风格（点击追加） ---", state=DISABLED)
		for style_tag in self.preset_styles:
			menu.add_command(
				label=f"  {style_tag}",
				command=lambda s=style_tag: self._add_style_tag(s)
			)
		
		# 在按钮下方显示菜单
		try:
			x = self.btn_add_style.winfo_rootx()
			y = self.btn_add_style.winfo_rooty() + self.btn_add_style.winfo_height()
			menu.post(x, y)
		except Exception:
			menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
	
	
	
	def _add_style_tag(self, tag) -> None:
		"""添加风格标签到风格说明"""
		current = self.style.get().strip()
		if not current:
			self.style.set(tag)
		else:
			# 检查是否已存在
			tags = [t.strip() for t in current.split("/")]
			if tag not in tags:
				self.style.set(current + "/" + tag)
		if hasattr(self, 'status'):
			self.status.set(f"已添加风格: {tag}")
	
	
	
	def _manual_input_style(self) -> None:
		"""手动输入自定义风格"""
		from tkinter import simpledialog
		custom_style = simpledialog.askstring(
			"手动输入风格",
			"请输入自定义风格标签:\n\n（例如：日系清新、赛博朋克、武侠风等）",
			initialvalue=""
		)
		if custom_style and custom_style.strip():
			self._add_style_tag(custom_style.strip())
	
	# ==================== 项目管理回调函数 ====================
	
	# ==================== 人物生成相关函数 ====================
	
	
	
	def _extract_core_features(self, description: str) -> str:
		"""从详细描述中提取核心视觉特征（简洁版）"""
		if not description:
			return ""
		
		# 提取关键信息的关键词
		keywords = {
			"年龄": ["岁", "年轻", "中年", "老年", "青年"],
			"性别": ["男", "女"],
			"发型": ["短发", "长发", "卷发", "直发", "马尾", "光头", "秃"],
			"发色": ["黑发", "白发", "金发", "棕发", "花白"],
			"体型": ["高大", "瘦弱", "健壮", "魁梧", "苗条", "丰满"],
			"肤色": ["白皙", "黝黑", "健康", "苍白"],
			"服装": ["西装", "衬衫", "T恤", "连衣裙", "制服", "工装", "休闲", "正装", "运动"]
		}
		
		core_parts = []
		desc_lower = description
		
		# 提取年龄
		for word in keywords["年龄"]:
			if word in desc_lower:
				# 尝试提取数字+岁
				import re
				age_match = re.search(r'(\d+)岁', desc_lower)
				if age_match:
					core_parts.append(f"{age_match.group(1)}岁")
					break
				elif "年轻" in desc_lower:
					core_parts.append("年轻")
					break
				elif "中年" in desc_lower:
					core_parts.append("中年")
					break
				elif "老年" in desc_lower:
					core_parts.append("老年")
					break
		
		# 提取性别
		if "男" in desc_lower and "女" not in desc_lower:
			core_parts.append("男性")
		elif "女" in desc_lower:
			core_parts.append("女性")
		
		# 提取发型和发色
		for word in keywords["发型"]:
			if word in desc_lower:
				core_parts.append(word)
				break
		for word in keywords["发色"]:
			if word in desc_lower:
				core_parts.append(word)
				break
		
		# 提取服装（只保留最显著的）
		for word in keywords["服装"]:
			if word in desc_lower:
				core_parts.append(word)
				break
		
		# 如果没有提取到任何特征，返回简化的原描述（限制长度）
		if not core_parts:
			return description[:30] + ("..." if len(description) > 30 else "")
		
		return "、".join(core_parts)
	
	
	
	def _generate_sheet_async(self, character_name: str, characters_dir, character_description: str,
							  layout: str, show_labels: bool, show_desc: bool):
		"""异步生成角色设定表"""
		import threading
		from pathlib import Path
		
		self.status.set(f"🎨 正在生成\"{character_name}\"的角色设定表...")
		if hasattr(self, 'update_header_status'):
			self.update_header_status("生成角色设定表...", "🎨")
		
		# 禁用按钮
		if hasattr(self, 'char_btn_generate_sheet'):
			self.char_btn_generate_sheet.config(state=DISABLED)
		
		def generate_thread():
			try:
				# 输出路径
				output_filename = f"{character_name}_角色设定表_{layout}.png"
				output_path = characters_dir / output_filename
				
				# 生成设定表
				result_path = CharacterSheetBuilder.build_character_sheet(
					character_name=character_name,
					photos_dir=characters_dir,
					output_path=output_path,
					layout=layout,
					show_labels=show_labels,
					show_description=show_desc,
					character_description=character_description
				)
				
				if result_path:
					self.after(0, lambda: self.status.set(f"✅ 角色设定表已生成：{output_filename}"))
					self.after(0, lambda: messagebox.showinfo(
						"成功",
						f"角色设定表已生成！\n\n保存位置：\n{result_path}\n\n文件大小：{result_path.stat().st_size / 1024:.1f} KB"
					))
					
					# 自动打开预览
					try:
						import subprocess
						subprocess.run(["open", str(result_path)])
					except Exception:
						pass
				else:
					self.after(0, lambda: self.status.set("❌ 生成角色设定表失败"))
					self.after(0, lambda: messagebox.showerror("失败", "生成角色设定表失败！\n请检查是否有足够的照片。"))
				
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("设定表生成完成", "✅"))
			
			except Exception as e:
				import traceback
				error_detail = traceback.format_exc()
				print(f"\n❌ 生成角色设定表失败：\n{error_detail}")
				self.after(0, lambda: self.status.set("❌ 生成失败"))
				self.after(0, lambda: messagebox.showerror("错误", f"生成角色设定表失败：\n{str(e)}"))
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("生成失败", "❌"))
			
			finally:
				if hasattr(self, 'char_btn_generate_sheet'):
					self.after(0, lambda: self.char_btn_generate_sheet.config(state=NORMAL))
		
		threading.Thread(target=generate_thread, daemon=True).start()
	
	
	
	def _extract_action_keywords(self, text: str) -> str:
		"""
		从文本中提取动作关键词，强化视频动态效果
		"""
		# 动作动词列表
		action_verbs = [
			"走", "跑", "跳", "飞", "转", "摇", "晃", "飘", "落", "升",
			"推", "拉", "开", "关", "举", "放", "拿", "抓", "扔", "接",
			"看", "望", "盯", "瞄", "眨", "笑", "哭", "叫", "喊", "说",
			"吹", "吸", "呼", "吐", "咬", "舔", "吞", "咽", "吃", "喝",
			"站", "坐", "躺", "蹲", "跪", "趴", "靠", "倚", "挂", "吊",
			"打", "踢", "砸", "撞", "碰", "触", "摸", "抚", "拍", "敲",
			"写", "画", "涂", "刻", "印", "盖", "贴", "撕", "剪", "切",
			"流", "滴", "洒", "泼", "溅", "喷", "射", "发", "出", "入",
			"动", "摆", "挥", "舞", "扭", "摇", "震", "颤", "抖", "晃",
			"变", "化", "换", "转", "改", "移", "迁", "搬", "挪", "移动",
			"闪", "现", "消", "散", "聚", "合", "分", "裂", "破", "碎",
			"亮", "暗", "明", "灭", "燃", "烧", "冒", "腾", "升起", "降落",
			"进", "出", "上", "下", "前", "后", "左", "右", "来", "去",
			"推开", "拉开", "打开", "关闭", "抬起", "放下", "睁开", "闭上",
			"转身", "回头", "低头", "抬头", "侧身", "弯腰", "起身", "坐下"
		]
		
		# 查找文本中的动作词
		found_actions = []
		for verb in action_verbs:
			if verb in text:
				# 找到动作词及其上下文
				index = text.find(verb)
				# 提取动作词前后的词语
				start = max(0, index - 3)
				end = min(len(text), index + len(verb) + 5)
				context = text[start:end]
				found_actions.append(context)
		
		# 如果找到动作，强化描述
		if found_actions:
			# 去重并组合
			unique_actions = list(dict.fromkeys(found_actions))
			return "，".join(unique_actions[:3])  # 最多保留3个动作描述
		
		return text
	
	
	