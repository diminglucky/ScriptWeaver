"""Story功能模块"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, messagebox, filedialog, scrolledtext
import tkinter as tk
from tkinter import ttk
import threading
import re
import time
from pathlib import Path
from dotenv import load_dotenv

from src.clients.deepseek_client import DeepSeekClient
# 延迟导入：只在使用时才导入，避免启动时加载 sentence_transformers (3.8秒)
# from src.kb.ingest import KnowledgeBaseIngestor, IngestConfig
# from src.kb.search import KnowledgeBaseSearcher, SearchConfig
from src.utils.text import sanitize as _sanitize


class OutlineGeneratorMixin:
	"""Story outline_generator 功能"""
	
	def on_generate_outline(self) -> None:
		requirement = self._get_prompt_content()
		if not requirement:
			messagebox.showwarning("提示", "请先输入创作需求/主题")
			return
		
		# 获取选中的目录生成API配置
		selected_api = self.outline_gen_api.get() if hasattr(self, 'outline_gen_api') else "DeepSeek"
		if selected_api not in self.api_presets:
			messagebox.showerror("错误", f"未找到API预设: {selected_api}")
			return
		
		api_config = self.api_presets[selected_api]
		api_key = _sanitize(api_config.get("key", ""))
		if not api_key:
			messagebox.showwarning("提示", f"API Key 为空，请在'基础 API 配置'中为 {selected_api} 填写后保存")
			return
		
		if self.model_only.get():
			self._generate_outline_model_only(requirement)
			return
		need_build = False
		index_path = Path(self.index_dir.get()) / "kb.index"
		if not index_path.exists():
			if messagebox.askyesno("提示", "未找到索引，是否现在根据当前数据目录自动构建？"):
				need_build = True
			else:
				return
		def task():
			try:
				# 延迟导入：只在需要时才加载（避免启动时加载 sentence_transformers）
				from src.kb.ingest import KnowledgeBaseIngestor, IngestConfig
				from src.kb.search import KnowledgeBaseSearcher, SearchConfig
				
				self.set_busy(True)
				self.status.set(f"使用 {selected_api} 检索素材并生成目录中...")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("正在生成目录...", "📝")
				
				load_dotenv()
				if need_build:
					if hasattr(self, 'update_header_status'):
						self.update_header_status("正在构建索引...", "⏳")
					cfg = IngestConfig(data_root=Path(self.data_dir.get()), index_dir=Path(self.index_dir.get()))
					KnowledgeBaseIngestor(cfg).build()
				
				if hasattr(self, 'update_header_status'):
					self.update_header_status("检索资料中...", "🔍")
				searcher = KnowledgeBaseSearcher(SearchConfig(index_dir=Path(self.index_dir.get()), top_k=self.top_k.get()))
				results = searcher.search(requirement, self.top_k.get())
				contexts = [c for c, _s, _m in results]
				
				# 使用选中的API配置
				if hasattr(self, 'update_header_status'):
					self.update_header_status("AI生成目录中...", "📝")
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				outline_prompt = self._build_outline_prompt(requirement, contexts, self.category.get())
				self.after(0, lambda: self.output.delete("1.0", END))
				time.sleep(0.05)  # 等待清空完成
				# 不再插入 "生成目录中..." 到正文，只在状态栏显示
				outline_text = client.chat([
					{"role": "system", "content": "你是资深知乎创作者与编辑。请先产出结构化目录，不要写正文。"},
					{"role": "user", "content": outline_prompt},
				], temperature=max(0.4, self.temperature.get() - 0.2))
				self.current_outline = outline_text.strip()
				estimate = self._estimate_chars(self.current_outline)
				
				# 解析章节并更新选择器
				self.parsed_sections = self._parse_outline_sections(self.current_outline)
				self._update_section_selector()
				
				# 只插入目录，不插入字数统计信息（线程安全）
				outline_content = f"{self.current_outline}\n\n"
				self.after(0, lambda content=outline_content: self.output.insert(END, content))
				self.after(0, lambda: self.status.set("目录已生成"))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("目录生成完成", "✅"))
			except Exception as e:
				import traceback
				# 捕获错误信息（线程安全）
				error_msg = "生成目录出错:\n" + traceback.format_exc() + "\n"
				error_str = str(e)
				self.after(0, lambda msg=error_msg: self.output.insert(END, msg))
				self.after(0, lambda err=error_str: messagebox.showerror("错误", err))
				self.after(0, lambda: self.status.set("生成目录失败"))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("生成目录失败", "❌"))
			finally:
				self.after(0, lambda: self.set_busy(False))
		threading.Thread(target=task, daemon=True).start()

	
	def on_generate_section(self) -> None:
		"""生成选中的章节"""
		if not self.parsed_sections:
			messagebox.showwarning("提示", "请先生成目录")
			return
		
		query = self._get_prompt_content()
		if not query:
			messagebox.showwarning("提示", "请先输入创作需求/主题")
			return
		
		if not (_sanitize(self.api_key.get())):
			messagebox.showwarning("提示", "API Key 为空")
			return
		
		# 获取选中的章节索引
		selected_index = self.section_selector.current()
		if selected_index < 0:
			messagebox.showwarning("提示", "请选择要生成的章节")
			return
		
		# 启动生成
		if self.model_only.get():
			self._generate_single_section(query, [], selected_index)
		else:
			# 带知识库检索
			need_build = False
			index_path = Path(self.index_dir.get()) / "kb.index"
			if not index_path.exists():
				if messagebox.askyesno("提示", "未找到索引，是否现在构建？"):
					need_build = True
				else:
					return
			
			def task():
				try:
					# 延迟导入：只在需要时才加载（避免启动时加载 sentence_transformers）
					from src.kb.ingest import KnowledgeBaseIngestor, IngestConfig
					from src.kb.search import KnowledgeBaseSearcher, SearchConfig
					
					self.after(0, lambda: self.set_busy(True))
					load_dotenv()
					if need_build:
						cfg = IngestConfig(data_root=Path(self.data_dir.get()), index_dir=Path(self.index_dir.get()))
						KnowledgeBaseIngestor(cfg).build()
					searcher = KnowledgeBaseSearcher(SearchConfig(index_dir=Path(self.index_dir.get()), top_k=self.top_k.get()))
					results = searcher.search(query, self.top_k.get())
					contexts = [c for c, _s, _m in results]
					self._generate_single_section_with_contexts(query, contexts, selected_index)
				except Exception as e:
					import traceback
					# 捕获错误信息（线程安全）
					error_msg = "\n生成出错:\n" + traceback.format_exc() + "\n"
					error_str = str(e)
					self.after(0, lambda msg=error_msg: self.output.insert(END, msg))
					self.after(0, lambda err=error_str: messagebox.showerror("错误", err))
					self.after(0, lambda: self.status.set("生成失败"))
					# 更新顶部状态栏
					if hasattr(self, 'update_header_status'):
						self.after(0, lambda: self.update_header_status("生成失败", "❌"))
				finally:
					self.after(0, lambda: self.set_busy(False))
			threading.Thread(target=task, daemon=True).start()
	
	
	def on_continue_next_section(self) -> None:
		"""继续生成下一章"""
		current_index = self.section_selector.current()
		if current_index < 0:
			messagebox.showwarning("提示", "请先选择当前章节")
			return
		
		next_index = current_index + 1
		if next_index >= len(self.parsed_sections):
			messagebox.showinfo("提示", "已经是最后一章了！")
			return
		
		# 自动选中下一章
		self.section_selector.current(next_index)
		
		# 直接生成
		self.on_generate_section()
	
	
	def _generate_outline_model_only(self, requirement) -> None:
		def task():
			try:
				self.set_busy(True)
				
				# 获取选中的目录生成API配置
				selected_api = self.outline_gen_api.get() if hasattr(self, 'outline_gen_api') else "DeepSeek"
				if selected_api not in self.api_presets:
					messagebox.showerror("错误", f"未找到API预设: {selected_api}")
					return
				
				api_config = self.api_presets[selected_api]
				api_key = _sanitize(api_config.get("key", ""))
				
				self.status.set(f"使用 {selected_api} 生成目录中...")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("AI生成目录中...", "📝")
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				target_chars = self.target_chars.get()
				# 根据目标字数动态决定章节数
				if target_chars <= 3000:
					suggested_sections = "3-4"
				elif target_chars <= 8000:
					suggested_sections = "4-6"
				elif target_chars <= 15000:
					suggested_sections = "6-8"
				else:
					suggested_sections = "8-10"
				
				prompt = (
					"请产出一个简洁的写作目录（仅目录，不要正文）。\n\n"
					"【核心要求】\n"
					f"- 只输出 {suggested_sections} 个主要章节标题，不要子标题、不要要点列表\n"
					"- 每个章节用数字编号（1. 2. 3. ...）\n"
					"- 章节名简短有力（5-10字），能体现故事发展\n"
					"- 结构要符合：开端 → 发展 → 高潮 → 结局\n"
					"- 不要写\"第一章\"、\"第二章\"，直接写章节内容主题\n\n"
					f"【创作信息】\n"
					f"- 主题/需求：{requirement}\n"
					f"- 种类：{self.category.get()}\n"
					f"- 目标字数：{target_chars}字\n\n"
					"请直接输出章节列表，格式如下：\n"
					"1. 平静的开端\n"
					"2. 意外降临\n"
					"3. 危机爆发\n"
					"4. 绝地反击\n"
					"5. 尘埃落定"
				)
				self.after(0, lambda: self.output.delete("1.0", END))
				time.sleep(0.05)  # 等待清空完成
				# 不再插入 "生成目录中..." 到正文，只在状态栏显示
				outline_text = client.chat([
					{"role": "system", "content": "你是资深知乎创作者与编辑。请先产出结构化目录，不要写正文。"},
					{"role": "user", "content": prompt},
				], temperature=max(0.4, self.temperature.get() - 0.2))
				self.current_outline = outline_text.strip()
				estimate = self._estimate_chars(self.current_outline)
				
				# 解析章节并更新选择器
				self.parsed_sections = self._parse_outline_sections(self.current_outline)
				self._update_section_selector()
				
				# 只插入目录，不插入字数统计信息（线程安全）
				outline_content = f"{self.current_outline}\n\n"
				self.after(0, lambda content=outline_content: self.output.insert(END, content))
				self.after(0, lambda: self.status.set("目录已生成"))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("目录生成完成", "✅"))
			except Exception as e:
				# 捕获错误信息（线程安全）
				error_str = str(e)
				self.after(0, lambda err=error_str: messagebox.showerror("错误", err))
				self.after(0, lambda: self.status.set("生成目录失败"))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("生成目录失败", "❌"))
			finally:
				self.after(0, lambda: self.set_busy(False))
		threading.Thread(target=task, daemon=True).start()

	
	def _generate_in_sections(self, client, requirement, contexts, sections, target_chars) -> None:
		"""分段生成长文本（线程安全版本）- 保持连贯性"""
		from tkinter import END
		
		total_sections = len(sections)
		target_per_section = int(target_chars / total_sections)
		
		total_generated = 0
		previous_content = ""  # 存储前面章节的内容，保持连贯性
		
		for idx, section in enumerate(sections):
			# 在主线程更新状态
			chapter_num = idx + 1
			status_msg = f"生成第 {chapter_num}/{total_sections} 章..."
			self.after(0, lambda msg=status_msg: self.status.set(msg))
			
			# 更新顶部状态栏
			if hasattr(self, 'update_header_status'):
				header_msg = f"生成第 {chapter_num}/{total_sections} 章..."
				self.after(0, lambda msg=header_msg: self.update_header_status(msg, "✍️"))
			
			# 计算本段需要的字数
			remaining_chars = target_chars - total_generated
			remaining_sections = total_sections - idx
			section_target = min(target_per_section + 500, int(remaining_chars / remaining_sections))
			
			# 先输出章节标题（线程安全）
			chapter_title = f"【第 {chapter_num}/{total_sections} 章. {section}】\n\n"
			self.after(0, lambda title=chapter_title: self.output.insert(END, title))
			time.sleep(0.05)  # 等待UI更新
			
			# 构建带上下文的prompt（传入前文内容以保持连贯性）
			section_prompt = self._build_section_prompt(
				requirement, section, contexts, section_target, chapter_num, total_sections, previous_content
			)
			
			# 使用流式输出实现打字机效果
			section_text = ""
			for delta in client.stream([
				{"role": "system", "content": "你是2024年的知乎爆款故事作者，文风现代、口语化、有网感。你精通用细节铺垫、情节反转、情感共鸣抓住读者。你的每一章都节奏紧凑、冲突鲜明、让人停不下来。重要：只输出故事正文，不要任何元信息提示。"},
				{"role": "user", "content": section_prompt},
			], temperature=self.temperature.get()):
				section_text += delta
				# 使用 after() 在主线程更新UI，实现线程安全的打字机效果
				self.after(0, lambda text=delta: self._insert_text_safe(text))
			
			# 过滤掉可能的状态信息
			section_text = re.sub(r'[✓✔☑️⏳🎉]*\s*第\s*\d+\s*章完成[！!].*?字.*?\n', '', section_text)
			section_text = re.sub(r'[✓✔☑️⏳🎉]*\s*准备生成.*?\n', '', section_text)
			section_text = re.sub(r'[✓✔☑️⏳🎉]*\s*全部章节生成完成.*?\n', '', section_text)
			
			# 保存当前章节内容到前文记录（用于下一章保持连贯性）
			previous_content += section_text + "\n\n"
			
			# 章节之间添加空行
			self.after(0, lambda: self.output.insert(END, "\n\n"))
			time.sleep(0.05)  # 等待UI更新
			
			# 统计字数
			section_chars = len(section_text)
			total_generated += section_chars
			
			# 休息一下避免触发限流
			if idx < total_sections - 1:
				# 更新顶部状态栏（线程安全）
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("准备生成下一章...", "⏳"))
				time.sleep(0.5)  # 略微延迟
		
		# 更新完成状态（线程安全）
		final_msg = f"生成完成！总字数：{total_generated} 字"
		if hasattr(self, 'update_header_status'):
			self.after(0, lambda msg=final_msg: self.update_header_status(msg, "🎉"))
		self.after(0, lambda msg=final_msg: self.status.set(msg))
		
		# 自动保存到当前项目（在主线程执行）
		self.after(100, lambda: self._auto_save_to_project())
	
	
	def _insert_text_safe(self, text: str) -> None:
		"""线程安全地插入文本到output，实现打字机效果"""
		try:
			self.output.insert(END, text)
			self.output.see(END)
			self.update_idletasks()
		except Exception as e:
			# 静默处理错误，避免中断生成
			pass
	
	
	def _insert_and_scroll(self, text: str) -> None:
		"""辅助方法：插入文本并滚动到底部"""
		from tkinter import END
		try:
			self.output.insert(END, text)
			self.output.see(END)
			self.update_idletasks()
		except Exception:
			pass
	
	
	def _generate_single_section(self, query, contexts, selected_index) -> None:
		"""不带知识库直接生成单个章节（保持连贯性）"""
		# 在主线程获取已有内容（线程安全）
		try:
			current_content = self.output.get("1.0", END).strip()
		except:
			current_content = ""
		
		def task(previous_content):
			try:
				self.after(0, lambda: self.set_busy(True))
				
				# 获取章节信息
				section_info = self.parsed_sections[selected_index]
				section_title = section_info['title']
				current_num = selected_index + 1
				total_sections = len(self.parsed_sections)
				
				# 获取目标字数
				target_chars = self.target_chars.get()
				section_target = int(target_chars / total_sections)
				
				# 获取选中的章节生成API配置
				selected_api = self.section_gen_api.get() if hasattr(self, 'section_gen_api') else "DeepSeek"
				if selected_api not in self.api_presets:
					api_name = selected_api
					error_msg = f"未找到API预设: {api_name}"
					self.after(0, lambda msg=error_msg: messagebox.showerror("错误", msg))
					return
				
				api_config = self.api_presets[selected_api]
				api_key = _sanitize(api_config.get("key", ""))
				if not api_key:
					api_name = selected_api
					error_msg = f"API Key 为空，请在'基础 API 配置'中为 {api_name} 填写后保存"
					self.after(0, lambda msg=error_msg: messagebox.showerror("错误", msg))
					return
				
				# 捕获变量（线程安全）
				api_name = selected_api
				status_msg = f"使用 {api_name} 生成章节: {section_title}"
				header_msg = f"生成章节: {section_title}"
				self.after(0, lambda msg=status_msg: self.status.set(msg))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda msg=header_msg: self.update_header_status(msg, "✍️"))
				
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				
				# 构建prompt（传入前文内容以保持连贯性）
				prompt = self._build_section_prompt(
					query, section_title, contexts, section_target, 
					current_num, total_sections, previous_content
				)
				
				# 插入章节标题（线程安全）
				chapter_header = f"【第 {current_num}/{total_sections} 章. {section_title}】\n\n"
				self.after(0, lambda h=chapter_header: self.output.insert(END, h))
				time.sleep(0.05)
				
				# 使用流式输出实现打字机效果
				response = ""
				for delta in client.stream([
					{"role": "system", "content": "你是2024年的知乎爆款故事作者，文风现代、口语化、有网感。你精通用细节铺垫、情节反转、情感共鸣抓住读者。你的每一章都节奏紧凑、冲突鲜明、让人停不下来。重要：只输出故事正文，不要任何元信息提示。"},
					{"role": "user", "content": prompt},
				], temperature=self.temperature.get()):
					response += delta
					# 使用 after() 在主线程更新UI，实现线程安全的打字机效果
					self.after(0, lambda text=delta: self._insert_text_safe(text))
				
				# 章节之间添加空行
				self.after(0, lambda: self.output.insert(END, "\n\n"))
				time.sleep(0.05)
				
				# 显示字数统计
				section_chars = len(response)
				final_status = f"章节生成完成！字数: {section_chars}"
				self.after(0, lambda msg=final_status: self.status.set(msg))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda msg=final_status: self.update_header_status(msg, "✅"))
				
				# 自动保存到当前项目（在主线程执行）
				self.after(100, lambda: self._auto_save_to_project())
				
			except Exception as e:
				import traceback
				# 捕获错误信息（线程安全）
				error_msg = f"\n生成章节出错:\n{traceback.format_exc()}\n"
				error_str = str(e)
				self.after(0, lambda msg=error_msg: self.output.insert(END, msg))
				self.after(0, lambda err=error_str: messagebox.showerror("错误", err))
				self.after(0, lambda: self.status.set("生成章节失败"))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("生成章节失败", "❌"))
			finally:
				self.after(0, lambda: self.set_busy(False))
		
		threading.Thread(target=task, args=(current_content,), daemon=True).start()
	
	
	def _generate_single_section_with_contexts(self, query, contexts, selected_index) -> None:
		"""带知识库检索生成单个章节（保持连贯性）"""
		# 在主线程获取已有内容（线程安全）
		try:
			current_content = self.output.get("1.0", END).strip()
		except:
			current_content = ""
		
		def task(previous_content):
			try:
				self.after(0, lambda: self.set_busy(True))
				
				# 获取章节信息
				section_info = self.parsed_sections[selected_index]
				section_title = section_info['title']
				current_num = selected_index + 1
				total_sections = len(self.parsed_sections)
				
				# 获取目标字数
				target_chars = self.target_chars.get()
				section_target = int(target_chars / total_sections)
				
				# 获取选中的章节生成API配置
				selected_api = self.section_gen_api.get() if hasattr(self, 'section_gen_api') else "DeepSeek"
				if selected_api not in self.api_presets:
					api_name = selected_api
					error_msg = f"未找到API预设: {api_name}"
					self.after(0, lambda msg=error_msg: messagebox.showerror("错误", msg))
					return
				
				api_config = self.api_presets[selected_api]
				api_key = _sanitize(api_config.get("key", ""))
				if not api_key:
					api_name = selected_api
					error_msg = f"API Key 为空，请在'基础 API 配置'中为 {api_name} 填写后保存"
					self.after(0, lambda msg=error_msg: messagebox.showerror("错误", msg))
					return
				
				# 捕获变量（线程安全）
				api_name = selected_api
				status_msg = f"使用 {api_name} 生成章节: {section_title}"
				header_msg = f"生成章节: {section_title}"
				self.after(0, lambda msg=status_msg: self.status.set(msg))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda msg=header_msg: self.update_header_status(msg, "✍️"))
				
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				
				# 构建prompt（传入前文内容以保持连贯性）
				prompt = self._build_section_prompt(
					query, section_title, contexts, section_target, 
					current_num, total_sections, previous_content
				)
				
				# 插入章节标题（线程安全）
				chapter_header = f"【第 {current_num}/{total_sections} 章. {section_title}】\n\n"
				self.after(0, lambda h=chapter_header: self.output.insert(END, h))
				time.sleep(0.05)
				
				# 使用流式输出实现打字机效果
				response = ""
				for delta in client.stream([
					{"role": "system", "content": "你是2024年的知乎爆款故事作者，文风现代、口语化、有网感。你精通用细节铺垫、情节反转、情感共鸣抓住读者。你的每一章都节奏紧凑、冲突鲜明、让人停不下来。重要：只输出故事正文，不要任何元信息提示。"},
					{"role": "user", "content": prompt},
				], temperature=self.temperature.get()):
					response += delta
					# 使用 after() 在主线程更新UI，实现线程安全的打字机效果
					self.after(0, lambda text=delta: self._insert_text_safe(text))
				
				# 章节之间添加空行
				self.after(0, lambda: self.output.insert(END, "\n\n"))
				time.sleep(0.05)
				
				# 显示字数统计
				section_chars = len(response)
				final_status = f"章节生成完成！字数: {section_chars}"
				self.after(0, lambda msg=final_status: self.status.set(msg))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda msg=final_status: self.update_header_status(msg, "✅"))
				
				# 自动保存到当前项目（在主线程执行）
				self.after(100, lambda: self._auto_save_to_project())
				
			except Exception as e:
				import traceback
				# 捕获错误信息（线程安全）
				error_msg = f"\n生成章节出错:\n{traceback.format_exc()}\n"
				error_str = str(e)
				self.after(0, lambda msg=error_msg: self.output.insert(END, msg))
				self.after(0, lambda err=error_str: messagebox.showerror("错误", err))
				self.after(0, lambda: self.status.set("生成章节失败"))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("生成章节失败", "❌"))
			finally:
				self.after(0, lambda: self.set_busy(False))
		
		threading.Thread(target=task, args=(current_content,), daemon=True).start()
	
	
	def _build_section_prompt(self, requirement, section_title, contexts, target_chars, current_num, total_num, previous_content="") -> str:
		"""构建章节生成的优化提示词（保持连贯性）"""
		ctx = "\n\n".join(f"【资料{i+1}】\n{c}" for i, c in enumerate(contexts)) if contexts else ""
		
		# 计算字数范围
		min_chars = int(target_chars * 0.85)
		max_chars = int(target_chars * 1.15)
		
		# 准备前文摘要（只取最后1500字，避免token过多）
		previous_summary = ""
		if previous_content and current_num > 1:
			# 只取前文的最后1500字作为上文参考
			prev_text = previous_content.strip()
			if len(prev_text) > 1500:
				prev_text = "..." + prev_text[-1500:]
			previous_summary = f"""
【前文内容摘要】（请仔细阅读，保持连贯！）
{prev_text}

⚠️ **连贯性要求**：
✓ 人物性格、说话方式必须与前文一致
✓ 情节发展要自然承接前文，不能突兀
✓ 已经铺垫的线索要记得呼应
✓ 语气、叙事风格要统一
✓ 如果前文有未解的悬念，本章可以推进或揭露
❌ 不要出现前文没有的新人物（除非合理引入）
❌ 不要与前文的设定、情节矛盾
"""
		
		# 根据位置定制提示
		position_hint = ""
		if current_num == 1:
			position_hint = """
【开篇要求】（极其重要！）
✓ 必须用一个吸引人的场景或冲突开场，不要平淡引入
✓ 前100字就要制造悬念或冲突，抓住读者
✓ 用具体的细节和画面感，而非笼统描述
✓ 设置一个让人好奇的"钩子"：反常的事、未解的谜、强烈的对比
❌ 绝对不要："那天天气不错"、"我叫XXX"这种平淡开场
✅ 应该是："手机响的时候，我正盯着窗外那个已经站了三小时的陌生人"
"""
		elif current_num == total_num:
			position_hint = """
【收尾要求】
✓ 情节要有结局，不要留太多悬念（除非是系列故事）
✓ 情感要升华，给读者回味
✓ 可以呼应开头，形成首尾照应
✓ 最后留一个余韵：金句、反思、或意外的微笑
❌ 避免草草收场或强行说教
"""
		else:
			position_hint = f"""
【中段要求】（第 {current_num}/{total_num} 部分）
✓ 本节必须有新的冲突或转折，推进情节
✓ 与前文自然衔接，不要突兀
✓ 本节结尾要埋下伏笔，吸引读者继续
✓ 保持节奏：有紧张也有舒缓
❌ 避免写成过渡性内容或填充字数
"""
		
		return (
			f"你是2024年知乎爆款故事作者，正在创作第 {current_num}/{total_num} 章，文风现代、节奏紧凑、情节波澜。\n\n"
			f"{previous_summary}\n"
			f"【本章要求】\n"
			f"1. **字数**：必须写足 {min_chars}-{max_chars} 字，目标 {target_chars} 字\n"
			f"2. **章节主题**：{section_title}\n"
			f"3. **整体主题**：{requirement}\n\n"
			f"{position_hint}\n"
			
			f"【2024现代文风格】\n"
			f"✓ **语言现代化**：口语化、接地气、有网感，像2024年的人在说话\n"
			f"✓ **节奏紧凑**：不拖沓、每句话有信息量、让人停不下来\n"
			f"✓ **冲突频繁**：每200-300字一个小冲突或意外，起伏不断\n"
			f"✓ **铺垫扎实**：重要转折前必须有铺垫，让反转合理又精彩\n"
			f"✓ **细节生动**：用具体细节代替抽象概括\n"
			f"❌ **避免老土**：不要\"那天天气很好\"\"我陷入沉思\"这种90年代风格\n\n"
			
			f"【本章核心任务】\n"
			f"1. **制造冲突转折**\n"
			f"   ✓ 本章至少2-3个小冲突或意外\n"
			f"   ✓ 人物计划被打乱、遇到阻碍\n"
			f"   ✓ 新信息揭露、改变局势\n"
			f"   ✓ 人物关系微妙变化、产生矛盾\n"
			f"   ✓ 情绪起伏：紧张→舒缓→更紧张\n"
			f"   ❌ 绝不平铺直叙、一帆风顺\n\n"
			
			f"2. **扎实铺垫与反转**\n"
			f"   ✓ 如果有重要转折，前面必须有细节铺垫\n"
			f"   ✓ 不经意提到的小细节，后面成为关键\n"
			f"   ✓ 先压抑再爆发，先平静再震撼\n"
			f"   ✓ 让反转既意外又合理\n"
			f"   ❌ 不要突然蹦出没铺垫的转折\n\n"
			
			f"3. **细节生动有画面感**\n"
			f"   ✓ 环境：光线、声音、气味、温度、氛围\n"
			f"   ✓ 人物：神态、微表情、小动作、语气\n"
			f"   ✓ 心理：矛盾、挣扎、情绪波动、内心活动\n"
			f"   ✓ 对话：有情绪、有潜台词、有冲突、口语化\n"
			f"   ✓ 好例子：\"他握杯子的手在颤抖，咖啡洒了一桌\"\n"
			f"   ❌ 差例子：\"他很紧张\" \"气氛尴尬\"\n\n"
			
			f"4. **节奏控制**\n"
			f"   ✓ 紧张时：短句、快节奏、多动作\n"
			f"   ✓ 舒缓时：长句、细腻描写、情感深度\n"
			f"   ✓ 重要情节前：铺垫、酝酿、制造期待\n"
			f"   ✓ 本章结尾：留钩子，让人想看下一章\n\n"
			
			f"【写作规范（必须遵守）】\n"
			f"✓ **语言现代化**：像2024年的人说话，不是90年代老土风格\n"
			f"✓ **不写标题**：不要写章节标题，直接进入正文\n"
			f"✓ **Show不Tell**：不说\"他紧张\"，写\"手心全是汗\"\n"
			f"✓ **纯文本**：不用Markdown标记（#、*、-、**、```）\n"
			f"✓ **保持连贯**：与前文人物、情节、语气一致\n"
			f"✓ **持续推进**：每段都推情节或深化人物\n"
			f"✓ **埋钩子**：段落结尾留悬念\n\n"
			
			f"【90/00年代老土风格（别这么写！）】\n"
			f"❌ \"后来我去了公司，天气很好，心情不错。到了公司做了一些工作，和同事聊了几句，然后下班回家了。一切都很平常。\"\n"
			f"→ 流水账、无冲突、无画面感、拖沓无聊、像老头子写的\n\n"
			
			f"【2024现代风格（就这么写！）】\n"
			f"✅ \"推开办公室门的瞬间，我愣了。老板的位置上坐着个陌生人，正翻我的项目文件。他抬头，冲我诡异地笑：'来得正好。'我心一沉，因为昨天老板还说今天要给我升职加薪。\"\n"
			f"→ 有冲突、有悬念、有画面感、节奏紧凑、有铺垫反转\n\n"
			
			f"{f'【参考资料】\n{ctx}\n' if ctx else ''}"
			f"\n【特别强调】\n"
			f"✓ 必须写足 {min_chars}-{max_chars} 字，不要提前结束\n"
			f"✓ 如果字数不够，请：\n"
			f"   • 增加冲突转折（每300字一个小意外）\n"
			f"   • 加强铺垫（重要情节前必须铺垫）\n"
			f"   • 丰富细节（环境、人物、心理、对话）\n"
			f"   • 深化情感（情绪起伏变化）\n\n"
			f"✓ 记住：你是2024年知乎作者，写现代文，不是90年代老古董！\n"
			f"✓ 节奏紧凑、情节波澜、铺垫扎实、反转精彩！\n\n"
			
			f"【严格禁止】\n"
			f"❌ 绝对不要输出：\"第X章完成\"、\"✓\"、\"本章字数\"、\"准备生成\"等任何元信息\n"
			f"❌ 绝对不要输出任何完成提示、字数统计、状态标记\n"
			f"❌ 只输出故事正文，不要任何标记、符号、完成信息\n"
			f"✅ 写完后直接结束，不要任何总结或提示\n\n"
			f"现在开始创作！直接进入正文，每300字一个冲突，重要转折前有铺垫："
		)
	
	
	def _estimate_chars(self, outline) -> int:
		"""根据目录估算总字数"""
		sections = self._parse_outline_sections(outline)
		return len(sections) * 1200  # 假设每章平均1200字
	
	
	def _parse_outline_sections(self, outline):
		"""解析目录文本，提取章节"""
		sections = []
		lines = outline.strip().split('\n')
		
		for line in lines:
			line = line.strip()
			# 匹配数字开头的章节
			if re.match(r'^\d+[\.\、\s]', line):
				# 提取章节标题
				title = re.sub(r'^\d+[\.\、\s]+', '', line).strip()
				if title:
					sections.append({
						'title': title,
						'line': line
					})
		
		return sections
	
	
	def _update_section_selector(self):
		"""更新章节选择器"""
		if not hasattr(self, 'section_selector'):
			return
		
		# 清空现有选项
		self.section_selector['values'] = []
		
		if self.parsed_sections:
			# 设置新选项
			options = [f"{i+1}. {s['title']}" for i, s in enumerate(self.parsed_sections)]
			self.section_selector['values'] = options
			# 默认选中第一个
			if options:
				self.section_selector.current(0)
		else:
			self.section_selector.set("请先生成目录")
	
	
	def on_generate_all_sections(self) -> None:
		"""一键生成所有章节"""
		if not self.parsed_sections:
			messagebox.showwarning("提示", "请先生成目录")
			return
		
		query = self._get_prompt_content()
		if not query:
			messagebox.showwarning("提示", "请先输入创作需求/主题")
			return
		
		# 获取选中的章节生成API配置
		selected_api = self.section_gen_api.get() if hasattr(self, 'section_gen_api') else "DeepSeek"
		if selected_api not in self.api_presets:
			messagebox.showerror("错误", f"未找到API预设: {selected_api}")
			return
		
		api_config = self.api_presets[selected_api]
		api_key = _sanitize(api_config.get("key", ""))
		if not api_key:
			messagebox.showwarning("提示", f"API Key 为空，请在'基础 API 配置'中为 {selected_api} 填写后保存")
			return
		
		if self.model_only.get():
			self._generate_all_sections_model_only(query)
		else:
			# 带知识库的生成
			need_build = False
			index_path = Path(self.index_dir.get()) / "kb.index"
			if not index_path.exists():
				if messagebox.askyesno("提示", "未找到索引，是否现在构建？"):
					need_build = True
				else:
					return
			
			def task():
				try:
					# 延迟导入
					from src.kb.ingest import KnowledgeBaseIngestor, IngestConfig
					from src.kb.search import KnowledgeBaseSearcher, SearchConfig
					
					self.after(0, lambda: self.set_busy(True))
					load_dotenv()
					
					if need_build:
						cfg = IngestConfig(data_root=Path(self.data_dir.get()), index_dir=Path(self.index_dir.get()))
						KnowledgeBaseIngestor(cfg).build()
					
					searcher = KnowledgeBaseSearcher(SearchConfig(index_dir=Path(self.index_dir.get()), top_k=self.top_k.get()))
					results = searcher.search(query, self.top_k.get())
					contexts = [c for c, _s, _m in results]
					
					# 使用选中的API
					client = DeepSeekClient(
						api_key=api_key,
						base_url=_sanitize(api_config.get("base_url", "")),
						model=_sanitize(api_config.get("model", "")),
					)
					
					# 清空输出区（线程安全）
					self.after(0, lambda: self.output.delete("1.0", END))
					time.sleep(0.05)
					# 先显示目录（线程安全）
					outline_content = f"{self.current_outline}\n\n"
					self.after(0, lambda content=outline_content: self.output.insert(END, content))
					time.sleep(0.05)
					
					# 逐章生成
					sections = [s['title'] for s in self.parsed_sections]
					self._generate_in_sections(client, query, contexts, sections, self.target_chars.get())
					
					# 完成后显示总字数（注意：在子线程不能直接get，但_generate_in_sections已经处理了状态更新）
					# 不再插入到正文，只在状态栏显示（已在_generate_in_sections中处理）
					
				except Exception as e:
					import traceback
					# 捕获错误信息（线程安全）
					error_msg = f"\n生成出错:\n{traceback.format_exc()}\n"
					error_str = str(e)
					self.after(0, lambda msg=error_msg: self.output.insert(END, msg))
					self.after(0, lambda err=error_str: messagebox.showerror("错误", err))
					# 更新顶部状态栏
					if hasattr(self, 'update_header_status'):
						self.after(0, lambda: self.update_header_status("生成失败", "❌"))
				finally:
					self.after(0, lambda: self.set_busy(False))
			
			threading.Thread(target=task, daemon=True).start()
	
	
	def _generate_all_sections_model_only(self, query) -> None:
		"""不使用知识库，直接生成所有章节"""
		def task():
			try:
				self.after(0, lambda: self.set_busy(True))
				
				# 获取选中的章节生成API配置
				selected_api = self.section_gen_api.get() if hasattr(self, 'section_gen_api') else "DeepSeek"
				api_config = self.api_presets[selected_api]
				
				client = DeepSeekClient(
					api_key=_sanitize(api_config.get("key", "")),
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				
				# 清空输出区（线程安全）
				self.after(0, lambda: self.output.delete("1.0", END))
				time.sleep(0.05)
				# 先显示目录（线程安全）
				outline_content = f"{self.current_outline}\n\n"
				self.after(0, lambda content=outline_content: self.output.insert(END, content))
				time.sleep(0.05)
				
				# 逐章生成
				sections = [s['title'] for s in self.parsed_sections]
				self._generate_in_sections(client, query, [], sections, self.target_chars.get())
				
				# 完成后显示总字数（注意：在子线程不能直接get，但_generate_in_sections已经处理了状态更新）
				# 不再插入到正文，只在状态栏显示（已在_generate_in_sections中处理）
				
			except Exception as e:
				import traceback
				# 捕获错误信息（线程安全）
				error_msg = f"\n生成出错:\n{traceback.format_exc()}\n"
				error_str = str(e)
				self.after(0, lambda msg=error_msg: self.output.insert(END, msg))
				self.after(0, lambda err=error_str: messagebox.showerror("错误", err))
				self.after(0, lambda: self.status.set("生成失败"))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("生成失败", "❌"))
			finally:
				self.after(0, lambda: self.set_busy(False))
		
		threading.Thread(target=task, daemon=True).start()