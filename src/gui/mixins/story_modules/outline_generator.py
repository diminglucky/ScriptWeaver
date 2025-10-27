"""Story功能模块"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, messagebox, filedialog, scrolledtext
import tkinter as tk
from tkinter import ttk
import threading
import re
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
				self.output.delete("1.0", END)
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
				
				# 只插入目录，不插入字数统计信息
				self.output.insert(END, f"{self.current_outline}\n\n")
				self.status.set("目录已生成")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("目录生成完成", "✅")
			except Exception as e:
				import traceback
				self.output.insert(END, "生成目录出错:\n" + traceback.format_exc() + "\n")
				messagebox.showerror("错误", str(e))
				self.status.set("生成目录失败")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("生成目录失败", "❌")
			finally:
				self.set_busy(False)
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
					
					self.set_busy(True)
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
					self.output.insert(END, "\n生成出错:\n" + traceback.format_exc() + "\n")
					messagebox.showerror("错误", str(e))
				finally:
					self.set_busy(False)
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
				self.output.delete("1.0", END)
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
				
				# 只插入目录，不插入字数统计信息
				self.output.insert(END, f"{self.current_outline}\n\n")
				self.status.set("目录已生成")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("目录生成完成", "✅")
			except Exception as e:
				messagebox.showerror("错误", str(e))
				self.status.set("生成目录失败")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("生成目录失败", "❌")
			finally:
				self.set_busy(False)
		threading.Thread(target=task, daemon=True).start()

	
	def _generate_in_sections(self, client, requirement, contexts, sections, target_chars) -> None:
		"""分段生成长文本"""
		total_sections = len(sections)
		target_per_section = int(target_chars / total_sections)
		
		# 不再插入分段生成提示到正文，只在状态栏显示
		# self.output.insert(END, f"📖 开始分段生成（共{total_sections}段，目标总字数{target_chars}字）\n\n")
		
		total_generated = 0
		for idx, section in enumerate(sections):
			# 不再插入章节生成状态到正文，只在状态栏显示
			# self.output.insert(END, f"【正在生成第 {idx + 1}/{total_sections} 段】\n")
			self.status.set(f"生成第 {idx + 1}/{total_sections} 章...")
			# 更新顶部状态栏
			if hasattr(self, 'update_header_status'):
				self.update_header_status(f"生成第 {idx + 1}/{total_sections} 章...", "✍️")
			
			# 计算本段需要的字数
			remaining_chars = target_chars - total_generated
			remaining_sections = total_sections - idx
			section_target = min(target_per_section + 500, int(remaining_chars / remaining_sections))
			
			# 先输出章节标题
			self.output.insert(END, f"【第 {idx + 1}/{total_sections} 章. {section}】\n\n")
			
			# 构建带上下文的prompt
			section_prompt = self._build_section_prompt(
				requirement, section, contexts, section_target, idx + 1, total_sections
			)
			
			section_text = client.chat([
				{"role": "system", "content": "你是资深知乎故事创作者，善于把控节奏和情感。重要：只输出故事正文，绝对不要输出\"第X章完成\"、\"本章字数\"等任何元信息或状态提示。"},
				{"role": "user", "content": section_prompt},
			], temperature=self.temperature.get())
			
			# 过滤掉可能的状态信息
			import re
			section_text = re.sub(r'[✓✔☑️⏳🎉]*\s*第\s*\d+\s*章完成[！!].*?字.*?\n', '', section_text)
			section_text = re.sub(r'[✓✔☑️⏳🎉]*\s*准备生成.*?\n', '', section_text)
			section_text = re.sub(r'[✓✔☑️⏳🎉]*\s*全部章节生成完成.*?\n', '', section_text)
			
			# 输出生成的内容
			self.output.insert(END, section_text.strip() + "\n\n")
			self.output.see(END)
			self.update()
			
			# 统计字数
			section_chars = len(section_text)
			total_generated += section_chars
			# 只在状态栏显示字数统计，不插入到正文
			# self.output.insert(END, f"✓ 第 {idx + 1} 章完成！本章字数：{section_chars} 字\n")
			
			# 休息一下避免触发限流
			if idx < total_sections - 1:
				# self.output.insert(END, "⏳ 准备生成下一章...\n\n")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("准备生成下一章...", "⏳")
				import time
				time.sleep(0.5)  # 略微延迟
		
		# 不再插入总字数到正文，只在状态栏显示
		# self.output.insert(END, f"\n✅ 生成完成！总字数：{total_generated} 字\n")
		# 更新顶部状态栏
		if hasattr(self, 'update_header_status'):
			self.update_header_status(f"生成完成！总字数：{total_generated} 字", "🎉")
		self.status.set(f"生成完成！总字数：{total_generated} 字")
	
	
	def _generate_single_section(self, query, contexts, selected_index) -> None:
		"""不带知识库直接生成单个章节"""
		def task():
			try:
				self.set_busy(True)
				
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
					messagebox.showerror("错误", f"未找到API预设: {selected_api}")
					return
				
				api_config = self.api_presets[selected_api]
				api_key = _sanitize(api_config.get("key", ""))
				if not api_key:
					messagebox.showerror("错误", f"API Key 为空，请在'基础 API 配置'中为 {selected_api} 填写后保存")
					return
				
				self.status.set(f"使用 {selected_api} 生成章节: {section_title}")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status(f"生成章节: {section_title}", "✍️")
				
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				
				# 获取已生成内容（用于保持连贯性）
				current_content = self.output.get("1.0", END).strip()
				
				# 构建prompt
				prompt = self._build_section_prompt(
					query, section_title, contexts, section_target, 
					current_num, total_sections
				)
				
				# 调用AI生成
				response = client.chat([
					{"role": "system", "content": "你是资深知乎故事创作者，善于把控节奏和情感。重要：只输出故事正文，绝对不要输出\"第X章完成\"、\"本章字数\"等任何元信息或状态提示。"},
					{"role": "user", "content": prompt},
				], temperature=self.temperature.get())
				
				# 过滤掉可能的状态信息
				import re
				response = re.sub(r'[✓✔☑️⏳🎉]*\s*第\s*\d+\s*章完成[！!].*?字.*?\n', '', response)
				response = re.sub(r'[✓✔☑️⏳🎉]*\s*准备生成.*?\n', '', response)
				response = re.sub(r'[✓✔☑️⏳🎉]*\s*全部章节生成完成.*?\n', '', response)
				
				# 清空并显示新内容
				if self.clear_before_section.get():
					self.output.delete("1.0", END)
					# 先显示目录
					self.output.insert(END, f"{self.current_outline}\n\n")
				
				# 插入章节标题和内容
				self.output.insert(END, f"【第 {current_num}/{total_sections} 章. {section_title}】\n\n")
				self.output.insert(END, response.strip() + "\n\n")
				
				# 显示字数统计
				section_chars = len(response)
				# 只在状态栏显示，不插入到正文
				# self.output.insert(END, f"✓ 生成完成！本章字数：{section_chars} 字\n")
				self.output.see(END)
				
				self.status.set(f"章节生成完成！字数: {section_chars}")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status(f"章节生成完成！字数: {section_chars}", "✅")
				
			except Exception as e:
				import traceback
				self.output.insert(END, f"\n生成章节出错:\n{traceback.format_exc()}\n")
				messagebox.showerror("错误", str(e))
				self.status.set("生成章节失败")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("生成章节失败", "❌")
			finally:
				self.set_busy(False)
		
		threading.Thread(target=task, daemon=True).start()
	
	
	def _generate_single_section_with_contexts(self, query, contexts, selected_index) -> None:
		"""带知识库检索生成单个章节"""
		def task():
			try:
				self.set_busy(True)
				
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
					messagebox.showerror("错误", f"未找到API预设: {selected_api}")
					return
				
				api_config = self.api_presets[selected_api]
				api_key = _sanitize(api_config.get("key", ""))
				if not api_key:
					messagebox.showerror("错误", f"API Key 为空，请在'基础 API 配置'中为 {selected_api} 填写后保存")
					return
				
				self.status.set(f"使用 {selected_api} 生成章节: {section_title}")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status(f"生成章节: {section_title}", "✍️")
				
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				
				# 获取已生成内容（用于保持连贯性）
				current_content = self.output.get("1.0", END).strip()
				
				# 构建prompt
				prompt = self._build_section_prompt(
					query, section_title, contexts, section_target, 
					current_num, total_sections
				)
				
				# 调用AI生成
				response = client.chat([
					{"role": "system", "content": "你是资深知乎故事创作者，善于把控节奏和情感。重要：只输出故事正文，绝对不要输出\"第X章完成\"、\"本章字数\"等任何元信息或状态提示。"},
					{"role": "user", "content": prompt},
				], temperature=self.temperature.get())
				
				# 过滤掉可能的状态信息
				import re
				response = re.sub(r'[✓✔☑️⏳🎉]*\s*第\s*\d+\s*章完成[！!].*?字.*?\n', '', response)
				response = re.sub(r'[✓✔☑️⏳🎉]*\s*准备生成.*?\n', '', response)
				response = re.sub(r'[✓✔☑️⏳🎉]*\s*全部章节生成完成.*?\n', '', response)
				
				# 清空并显示新内容
				if self.clear_before_section.get():
					self.output.delete("1.0", END)
					# 先显示目录
					self.output.insert(END, f"{self.current_outline}\n\n")
				
				# 插入章节标题和内容
				self.output.insert(END, f"【第 {current_num}/{total_sections} 章. {section_title}】\n\n")
				self.output.insert(END, response.strip() + "\n\n")
				
				# 显示字数统计
				section_chars = len(response)
				# 只在状态栏显示，不插入到正文
				# self.output.insert(END, f"✓ 生成完成！本章字数：{section_chars} 字\n")
				self.output.see(END)
				
				self.status.set(f"章节生成完成！字数: {section_chars}")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status(f"章节生成完成！字数: {section_chars}", "✅")
				
			except Exception as e:
				import traceback
				self.output.insert(END, f"\n生成章节出错:\n{traceback.format_exc()}\n")
				messagebox.showerror("错误", str(e))
				self.status.set("生成章节失败")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("生成章节失败", "❌")
			finally:
				self.set_busy(False)
		
		threading.Thread(target=task, daemon=True).start()
	
	
	def _build_outline_prompt(self, requirement, contexts, category) -> str:
		prompt = f"请为一篇{category}文章生成详细目录。\n\n"
		prompt += f"【写作主题】{requirement}\n\n"
		if contexts:
			prompt += "【参考素材】\n"
			for i, ctx in enumerate(contexts[:3]):
				prompt += f"{i+1}. {ctx[:200]}...\n"
			prompt += "\n"
		prompt += "【要求】\n"
		prompt += "- 根据主题和素材，设计3-6个章节\n"
		prompt += "- 每个章节标题简洁有力（5-10字）\n"
		prompt += "- 结构完整：开端→发展→高潮→结局\n"
		prompt += "- 不要子标题，只要主章节\n"
		prompt += "- 直接输出章节列表，如：\n"
		prompt += "  1. 初遇\n"
		prompt += "  2. 误会\n"
		prompt += "  3. 真相大白\n"
		return prompt
	
	
	def _build_section_prompt(self, requirement, section_title, contexts, target_chars, current_num, total_num) -> str:
		prompt = f"请写作第 {current_num}/{total_num} 章内容。\n\n"
		prompt += f"【写作主题】{requirement}\n"
		prompt += f"【当前章节】{section_title}\n"
		prompt += f"【目标字数】{target_chars}字左右\n\n"
		
		if contexts:
			prompt += "【参考素材】\n"
			for i, ctx in enumerate(contexts[:2]):
				prompt += f"- {ctx[:150]}...\n"
			prompt += "\n"
		
		prompt += "【写作要求】\n"
		prompt += "1. 紧扣章节主题展开\n"
		prompt += "2. 注意与整体故事的连贯性\n"
		
		if current_num == 1:
			prompt += "3. 开篇要吸引人，快速进入主题\n"
		elif current_num == total_num:
			prompt += "3. 收尾要完整，情感到位\n"
		else:
			prompt += "3. 承上启下，推进剧情发展\n"
		
		prompt += "4. 多用细节描写，增强画面感\n"
		prompt += "5. 控制好节奏，张弛有度\n"
		prompt += f"6. 字数控制在{target_chars}字左右\n\n"
		prompt += "\n【严格禁止】\n"
		prompt += "❌ 绝对不要输出：\"第X章完成\"、\"✓\"、\"本章字数\"、\"准备生成\"等任何元信息\n"
		prompt += "❌ 绝对不要输出任何完成提示、字数统计、状态标记\n"
		prompt += "❌ 只输出故事正文，不要任何标记、符号、完成信息\n"
		prompt += "✅ 写完后直接结束，不要任何总结或提示\n\n"
		prompt += "立即开始写故事正文："
		
		return prompt
	
	
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
					
					self.set_busy(True)
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
					
					# 清空输出区
					self.output.delete("1.0", END)
					# 先显示目录
					self.output.insert(END, f"{self.current_outline}\n\n")
					
					# 逐章生成
					sections = [s['title'] for s in self.parsed_sections]
					self._generate_in_sections(client, query, contexts, sections, self.target_chars.get())
					
					# 完成后显示总字数
					all_content = self.output.get("1.0", END)
					total_chars = len(all_content) - len(self.current_outline) - 2
					# 不再插入到正文，只在状态栏显示
					# self.output.insert(END, f"\n🎉 全部章节生成完成！共 {len(sections)} 章，总字数：{total_chars} 字\n")
					self.status.set(f"全部生成完成！共 {len(sections)} 章，总字数：{total_chars} 字")
					# 更新顶部状态栏
					if hasattr(self, 'update_header_status'):
						self.update_header_status(f"全部生成完成！共 {len(sections)} 章，总字数：{total_chars} 字", "🎉")
					
				except Exception as e:
					import traceback
					self.output.insert(END, f"\n生成出错:\n{traceback.format_exc()}\n")
					messagebox.showerror("错误", str(e))
					# 更新顶部状态栏
					if hasattr(self, 'update_header_status'):
						self.update_header_status("生成失败", "❌")
				finally:
					self.set_busy(False)
			
			threading.Thread(target=task, daemon=True).start()
	
	
	def _generate_all_sections_model_only(self, query) -> None:
		"""不使用知识库，直接生成所有章节"""
		def task():
			try:
				self.set_busy(True)
				
				# 获取选中的章节生成API配置
				selected_api = self.section_gen_api.get() if hasattr(self, 'section_gen_api') else "DeepSeek"
				api_config = self.api_presets[selected_api]
				
				client = DeepSeekClient(
					api_key=_sanitize(api_config.get("key", "")),
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				
				# 清空输出区
				self.output.delete("1.0", END)
				# 先显示目录
				self.output.insert(END, f"{self.current_outline}\n\n")
				
				# 逐章生成
				sections = [s['title'] for s in self.parsed_sections]
				self._generate_in_sections(client, query, [], sections, self.target_chars.get())
				
				# 完成后显示总字数
				all_content = self.output.get("1.0", END)
				total_chars = len(all_content) - len(self.current_outline) - 2
				# 不再插入到正文，只在状态栏显示
				# self.output.insert(END, f"\n🎉 全部章节生成完成！共 {len(sections)} 章，总字数：{total_chars} 字\n")
				self.status.set(f"全部生成完成！共 {len(sections)} 章，总字数：{total_chars} 字")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status(f"全部生成完成！共 {len(sections)} 章，总字数：{total_chars} 字", "🎉")
				
			except Exception as e:
				import traceback
				self.output.insert(END, f"\n生成出错:\n{traceback.format_exc()}\n")
				messagebox.showerror("错误", str(e))
				self.status.set("生成失败")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("生成失败", "❌")
			finally:
				self.set_busy(False)
		
		threading.Thread(target=task, daemon=True).start()