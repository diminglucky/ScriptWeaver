"""Story功能模块"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, messagebox, filedialog, scrolledtext
import tkinter as tk
from tkinter import ttk
import logging
import threading
import re
from pathlib import Path
try:
	from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
	def load_dotenv(*args, **kwargs):
		return False

from src.clients.deepseek_client import DeepSeekClient
from src.utils.text import sanitize as _sanitize

logger = logging.getLogger(__name__)


def print(*args, **kwargs):  # type: ignore[override]
	logger.info(" ".join(str(a) for a in args))


class OutlineGeneratorMixin:
	"""Story outline_generator 功能"""
	
	def on_generate_outline(self) -> None:
		requirement = self._get_prompt_content()
		if not requirement:
			messagebox.showwarning("提示", "请先输入创作需求/主题")
			return
		
		# 目录生成：根据模型路由选择 API
		fallback_provider = None
		if hasattr(self, 'outline_gen_api'):
			fallback_provider = self.outline_gen_api.get()
		if not fallback_provider and hasattr(self, 'quick_story_api'):
			fallback_provider = self.quick_story_api.get()
		if not fallback_provider and hasattr(self, 'api_preset'):
			fallback_provider = self.api_preset.get()
		fallback_model = None
		if hasattr(self, 'story_model_var'):
			fallback_model = self.story_model_var.get()
		elif hasattr(self, 'model'):
			fallback_model = self.model.get()
		
		api_config = self._resolve_task_api("story_outline", fallback_provider=fallback_provider, fallback_model=fallback_model)
		selected_api = api_config.get("provider", "")
		api_key = _sanitize(api_config.get("key", ""))
		if not api_key:
			messagebox.showwarning("提示", f"API Key 为空，请在'基础 API 配置'中为 {selected_api} 填写后保存")
			return
		
		# 获取用户选择的模型
		selected_model = api_config.get("model", "")
		print(f"🤖 使用模型: {selected_model}")
		
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
		def task(api_config=api_config, selected_api=selected_api, selected_model=selected_model):
			try:
				self.set_busy(True)
				self._ui(self.status.set, f"使用 {selected_api} 检索素材并生成目录中...")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("正在生成目录...", "📝")
				from src.kb.ingest import IngestConfig, KnowledgeBaseIngestor
				from src.kb.search import KnowledgeBaseSearcher, SearchConfig
				
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
					model=selected_model,
				)
				outline_prompt = self._build_outline_prompt(requirement, contexts, self.category.get())
				self._ui(self.output.delete, "1.0", END)
				self._ui(self.output.insert, END, "生成目录中...\n\n")
				outline_text = client.chat([
					{"role": "system", "content": "你是资深知乎创作者与编辑。请先产出结构化目录，不要写正文。"},
					{"role": "user", "content": outline_prompt},
				], temperature=max(0.4, self.temperature.get() - 0.2))
				self.current_outline = outline_text.strip()
				estimate = self._estimate_chars(self.current_outline)
				
				# 解析章节并更新选择器
				self.parsed_sections = self._parse_outline_sections(self.current_outline)
				self._ui(self._update_section_selector)
				
				self._ui(self.output.insert, END, f"目录（共{len(self.parsed_sections)}章，预估字数≈{estimate}字）\n\n{self.current_outline}\n\n")
				self._ui(self.status.set, "目录已生成")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("目录生成完成", "✅")
			except Exception as e:
				import traceback
				self._ui(self.output.insert, END, "生成目录出错:\n" + traceback.format_exc() + "\n")
				self._ui(messagebox.showerror, "错误", str(e))
				self._ui(self.status.set, "生成目录失败")
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
		
		# 章节生成前置检查：根据模型路由确认 API Key
		fallback_provider = None
		if hasattr(self, 'story_gen_api'):
			fallback_provider = self.story_gen_api.get()
		if not fallback_provider and hasattr(self, 'quick_story_api'):
			fallback_provider = self.quick_story_api.get()
		if not fallback_provider and hasattr(self, 'api_preset'):
			fallback_provider = self.api_preset.get()
		fallback_model = None
		if hasattr(self, 'story_model_var'):
			fallback_model = self.story_model_var.get()
		elif hasattr(self, 'model'):
			fallback_model = self.model.get()
		
		api_config = self._resolve_task_api("story_generate", fallback_provider=fallback_provider, fallback_model=fallback_model)
		if not _sanitize(api_config.get("key", "")):
			messagebox.showwarning("提示", "API Key 为空，请在设置页配置")
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
					self.set_busy(True)
					from src.kb.ingest import IngestConfig, KnowledgeBaseIngestor
					from src.kb.search import KnowledgeBaseSearcher, SearchConfig
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
					self._ui(self.output.insert, END, "\n生成出错:\n" + traceback.format_exc() + "\n")
					self._ui(messagebox.showerror, "错误", str(e))
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
				
				# 目录生成：根据模型路由选择 API
				fallback_provider = None
				if hasattr(self, 'outline_gen_api'):
					fallback_provider = self.outline_gen_api.get()
				if not fallback_provider and hasattr(self, 'quick_story_api'):
					fallback_provider = self.quick_story_api.get()
				if not fallback_provider and hasattr(self, 'api_preset'):
					fallback_provider = self.api_preset.get()
				fallback_model = None
				if hasattr(self, 'story_model_var'):
					fallback_model = self.story_model_var.get()
				elif hasattr(self, 'model'):
					fallback_model = self.model.get()
				
				api_config = self._resolve_task_api("story_outline", fallback_provider=fallback_provider, fallback_model=fallback_model)
				selected_api = api_config.get("provider", "")
				api_key = _sanitize(api_config.get("key", ""))
				
				self._ui(self.status.set, f"使用 {selected_api} 生成目录中...")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("AI生成目录中...", "📝")
				
				# 获取用户选择的模型
				selected_model = api_config.get("model", "")
				print(f"🤖 使用模型: {selected_model}")
				
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=selected_model,
				)
				prompt = self._build_outline_prompt(requirement, [], self.category.get())
				self._ui(self.output.delete, "1.0", END)
				self._ui(self.output.insert, END, "生成目录中...\n\n")
				outline_text = client.chat([
					{"role": "system", "content": "你是资深知乎创作者与编辑。请先产出结构化目录，不要写正文。"},
					{"role": "user", "content": prompt},
				], temperature=max(0.4, self.temperature.get() - 0.2))
				self.current_outline = outline_text.strip()
				estimate = self._estimate_chars(self.current_outline)
				
				# 解析章节并更新选择器
				self.parsed_sections = self._parse_outline_sections(self.current_outline)
				self._ui(self._update_section_selector)
				
				self._ui(self.output.insert, END, f"目录（共{len(self.parsed_sections)}章，预估字数≈{estimate}字）\n\n{self.current_outline}\n\n")
				self._ui(self.status.set, "目录已生成")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("目录生成完成", "✅")
			except Exception as e:
				self._ui(messagebox.showerror, "错误", str(e))
				self._ui(self.status.set, "生成目录失败")
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
		
		self._ui(self.output.insert, END, f"📖 开始分段生成（共{total_sections}段，目标总字数{target_chars}字）\n\n")
		self._ui(self.output.insert, END, "=" * 50 + "\n\n")
		
		accumulated_content = ""
		style_part = self.style.get().strip()
		category = self.category.get()
		
		for idx, section in enumerate(sections):
			# 更新状态
			self._ui(self.status.set, f"生成第 {idx+1}/{total_sections} 段: {section['title']}")
			self._ui(self.output.insert, END, f"【正在生成第 {idx+1}/{total_sections} 段】\n\n")
			self._ui(self.output.see, END)
			# 更新顶部状态栏
			if hasattr(self, 'update_header_status'):
				self.update_header_status(f"生成中 ({idx+1}/{total_sections})", "📝")
			
			# 构建本段提示词
			section_prompt = self._build_section_prompt(
				section=section,
				section_index=idx,
				total_sections=total_sections,
				previous_content=accumulated_content,
				requirement=requirement,
				contexts=contexts,
				category=category,
				style_part=style_part,
				target_chars_per_section=target_per_section
			)
			
			# 流式生成本段
			section_content = ""
			for delta in client.stream([
				{"role": "system", "content": "你是资深知乎创作者，擅长结合资料写出有观点、有结构的中文故事。"},
				{"role": "user", "content": section_prompt},
			], temperature=self.temperature.get(), max_tokens=int(target_per_section*2.5)):
				self._ui(self.output.insert, END, delta)
				self._ui(self.output.see, END)
				section_content += delta
			
			# 累积内容（用于下一段的上下文）
			accumulated_content += section_content
			
			# 段落分隔
			if idx < total_sections - 1:
				self._ui(self.output.insert, END, "\n\n")
				self._ui(self.output.see, END)
		
		# 完成提示
		final_length = len(accumulated_content)
		self._ui(self.output.insert, END, f"\n\n" + "=" * 50 + "\n")
		self._ui(self.output.insert, END, f"✅ 生成完成！总字数：{final_length} 字\n")
		self._ui(self.status.set, f"生成完成（{final_length} 字）")

	
	def _generate_single_section(self, query: str, contexts: list[str], section_index: int) -> None:
		"""生成单个章节（无知识库）"""
		def task():
			try:
				self.set_busy(True)
				
				# 章节生成：根据模型路由选择 API
				fallback_provider = None
				if hasattr(self, 'story_gen_api'):
					fallback_provider = self.story_gen_api.get()
				if not fallback_provider and hasattr(self, 'quick_story_api'):
					fallback_provider = self.quick_story_api.get()
				if not fallback_provider and hasattr(self, 'api_preset'):
					fallback_provider = self.api_preset.get()
				fallback_model = None
				if hasattr(self, 'story_model_var'):
					fallback_model = self.story_model_var.get()
				elif hasattr(self, 'model'):
					fallback_model = self.model.get()
				
				api_config = self._resolve_task_api("story_generate", fallback_provider=fallback_provider, fallback_model=fallback_model)
				selected_api = api_config.get("provider", "")
				api_key = _sanitize(api_config.get("key", ""))
				if not api_key:
					self._ui(messagebox.showwarning, "提示", f"API Key 为空，请在'基础 API 配置'中为 {selected_api} 填写后保存")
					return
				
				# 获取用户选择的模型
				selected_model = api_config.get("model", "")
				print(f"🤖 使用模型: {selected_model}")
				
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=selected_model,
				)
				self._do_generate_section(client, query, contexts, section_index)
			except Exception as e:
				import traceback
				self._ui(self.output.insert, END, "\n生成出错:\n" + traceback.format_exc() + "\n")
				self._ui(messagebox.showerror, "错误", str(e))
			finally:
				self.set_busy(False)
		threading.Thread(target=task, daemon=True).start()
	
	
	def _generate_single_section_with_contexts(self, query: str, contexts: list[str], section_index: int) -> None:
		"""生成单个章节（带知识库）"""
		# 章节生成：根据模型路由选择 API
		fallback_provider = None
		if hasattr(self, 'story_gen_api'):
			fallback_provider = self.story_gen_api.get()
		if not fallback_provider and hasattr(self, 'quick_story_api'):
			fallback_provider = self.quick_story_api.get()
		if not fallback_provider and hasattr(self, 'api_preset'):
			fallback_provider = self.api_preset.get()
		fallback_model = None
		if hasattr(self, 'story_model_var'):
			fallback_model = self.story_model_var.get()
		elif hasattr(self, 'model'):
			fallback_model = self.model.get()
		
		api_config = self._resolve_task_api("story_generate", fallback_provider=fallback_provider, fallback_model=fallback_model)
		selected_api = api_config.get("provider", "")
		api_key = _sanitize(api_config.get("key", ""))
		if not api_key:
			self._ui(messagebox.showwarning, "提示", f"API Key 为空，请在'基础 API 配置'中为 {selected_api} 填写后保存")
			return
		
		# 获取用户选择的模型
		selected_model = api_config.get("model", "")
		print(f"🤖 使用模型: {selected_model}")
		
		client = DeepSeekClient(
			api_key=api_key,
			base_url=_sanitize(api_config.get("base_url", "")),
			model=selected_model,
		)
		self._do_generate_section(client, query, contexts, section_index)
	
	
	def _do_generate_section(self, client, query, contexts, section_index):
		"""实际执行章节生成的核心逻辑"""
		section = self.parsed_sections[section_index]
		total_sections = len(self.parsed_sections)
		
		# 计算本章字数
		target_chars = self.target_chars.get()
		target_per_section = int(target_chars / total_sections)
		
		# 读取当前已有内容作为上下文
		current_output = ""
		try:
			current_output = (self._ui_get(self.output.get, "1.0", END) or "").strip()
		except Exception as e:
			logger.debug("read current output failed, use empty content: %s", e)
			current_output = ""
		# 提取已生成的故事内容（排除目录部分）
		if "目录" in current_output and "\n\n" in current_output:
			parts = current_output.split("\n\n", 2)
			if len(parts) >= 3:
				self.generated_content = parts[2]  # 跳过"生成目录中..."和目录本身
			elif len(parts) == 2:
				self.generated_content = current_output.split(self.current_outline)[-1].strip()
		
		# 更新状态
		self._ui(self.status.set, f"生成第 {section_index+1}/{total_sections} 章: {section['title']}")
		# 更新顶部状态栏
		if hasattr(self, 'update_header_status'):
			self.update_header_status(f"生成章节 ({section_index+1}/{total_sections})", "📝")
		self._ui(self.output.insert, END, f"\n{'='*50}\n")
		self._ui(self.output.insert, END, f"【第 {section_index+1}/{total_sections} 章：{section['title']}】\n\n")
		self._ui(self.output.see, END)
		
		# 构建提示词
		section_prompt = self._build_section_prompt(
			section=section,
			section_index=section_index,
			total_sections=total_sections,
			previous_content=self.generated_content,
			requirement=query,
			contexts=contexts,
			category=self.category.get(),
			style_part=self.style.get().strip(),
			target_chars_per_section=target_per_section
		)
		
		# 流式生成
		section_content = ""
		for delta in client.stream([
			{"role": "system", "content": "你是资深知乎创作者，擅长结合资料写出有观点、有结构的中文故事。"},
			{"role": "user", "content": section_prompt},
		], temperature=self.temperature.get(), max_tokens=int(target_per_section*2.5)):
			self._ui(self.output.insert, END, delta)
			self._ui(self.output.see, END)
			section_content += delta
		
		# 累积内容
		self.generated_content += "\n\n" + section_content
		
		# 完成提示
		self._ui(self.output.insert, END, f"\n\n{'='*50}\n")
		self._ui(self.output.insert, END, f"✅ 第 {section_index+1} 章完成！本章字数：{len(section_content)} 字\n")
		self._ui(self.status.set, f"第 {section_index+1} 章完成（{len(section_content)} 字）")
		# 更新顶部状态栏
		if hasattr(self, 'update_header_status'):
			self.update_header_status(f"第 {section_index+1} 章完成", "✅")
		
		# 自动保存
		self._auto_save_to_project()
	
	
	def _auto_generate_all_sections(self, query, contexts, start_index=0):
		"""自动生成所有章节（无知识库）"""
		def task():
			try:
				self.set_busy(True)
				
				# 自动生成章节：根据模型路由选择 API
				fallback_provider = None
				if hasattr(self, 'story_gen_api'):
					fallback_provider = self.story_gen_api.get()
				if not fallback_provider and hasattr(self, 'quick_story_api'):
					fallback_provider = self.quick_story_api.get()
				if not fallback_provider and hasattr(self, 'api_preset'):
					fallback_provider = self.api_preset.get()
				fallback_model = None
				if hasattr(self, 'story_model_var'):
					fallback_model = self.story_model_var.get()
				elif hasattr(self, 'model'):
					fallback_model = self.model.get()
				
				api_config = self._resolve_task_api("story_generate", fallback_provider=fallback_provider, fallback_model=fallback_model)
				selected_api = api_config.get("provider", "")
				api_key = _sanitize(api_config.get("key", ""))
				
				if not api_key:
					self._ui(messagebox.showwarning, "提示", f"API Key 为空，请在'基础 API 配置'中为 {selected_api} 填写后保存")
					return
				
				# 获取用户选择的模型
				selected_model = api_config.get("model", "")
				print(f"🤖 使用模型: {selected_model}")
				
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=selected_model,
				)
				
				total_sections = len(self.parsed_sections)
				for idx in range(start_index, total_sections):
					# 更新选择器
					self._ui(self.section_selector.current, idx)
					
					# 生成当前章节
					self._do_generate_section(client, query, contexts, idx)
					
					# 如果不是最后一章，添加提示
					if idx < total_sections - 1:
						self._ui(self.output.insert, END, f"\n\n⏳ 准备生成下一章...\n\n")
						self._ui(self.output.see, END)
				
				# 全部完成
				self._ui(self.output.insert, END, f"\n\n{'='*50}\n")
				self._ui(self.output.insert, END, f"🎉 全部章节生成完成！共 {total_sections} 章，总字数：{len(self.generated_content)} 字\n")
				self._ui(self.status.set, f"全部完成（{len(self.generated_content)} 字）")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("全部章节完成", "✅")
				self._ui(messagebox.showinfo, "完成", f"所有章节已生成完成！\n\n共 {total_sections} 章，总字数：{len(self.generated_content)} 字")
			except Exception as e:
				import traceback
				self._ui(self.output.insert, END, "\n自动生成出错:\n" + traceback.format_exc() + "\n")
				self._ui(messagebox.showerror, "错误", str(e))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("自动生成失败", "❌")
			finally:
				self.set_busy(False)
		threading.Thread(target=task, daemon=True).start()
	
	
	def _update_section_selector(self) -> None:
		"""更新章节选择器"""
		if not self.parsed_sections:
			self.section_selector['values'] = ["请先生成目录"]
			self.btn_generate_section.config(state=DISABLED)
			self.btn_continue_next.config(state=DISABLED)
			return
		
		# 构建章节选项列表
		section_options = []
		for idx, section in enumerate(self.parsed_sections):
			title = section['title']
			section_options.append(f"{idx+1}. {title}")
		
		self.section_selector['values'] = section_options
		self.section_selector.current(0)  # 默认选中第一章
		self.btn_generate_section.config(state=NORMAL)
		self.btn_continue_next.config(state=NORMAL)
		
		# 重置生成内容
		self.generated_content = ""
		
		self.status.set(f"已解析 {len(self.parsed_sections)} 个章节，可开始逐章生成")
	
	
	def _parse_outline_sections(self, outline: str) -> list[dict[str, str]]:
		"""解析目录，提取章节信息"""
		if not outline:
			return []
		
		sections = []
		lines = outline.strip().splitlines()
		current_section = None
		current_items = []
		
		for line in lines:
			stripped = line.strip()
			if not stripped:
				continue
			
			# 检测是否为章节标题（数字编号、中文编号、或 -, *, •）
			is_main_section = False
			if re.match(r'^\d+[.、]', stripped) or re.match(r'^[一二三四五六七八九十]+[.、]', stripped):
				is_main_section = True
			elif stripped[:1] in ("-", "•", "*") and not stripped[1:2].isdigit():
				# 一级标题
				is_main_section = True
			
			if is_main_section:
				# 保存上一个章节
				if current_section:
					sections.append({
						"title": current_section,
						"items": current_items.copy()
					})
				# 去掉编号前缀，避免重复显示
				title = stripped
				title = re.sub(r'^\d+[.、]\s*', '', title)
				title = re.sub(r'^[一二三四五六七八九十]+[.、]\s*', '', title)
				title = re.sub(r'^[-•*]\s*', '', title)
				current_section = title.strip()
				current_items = []
			else:
				# 子项
				if current_section:
					current_items.append(stripped)
		
		# 添加最后一个章节
		if current_section:
			sections.append({
				"title": current_section,
				"items": current_items
			})
		
		return sections


	
