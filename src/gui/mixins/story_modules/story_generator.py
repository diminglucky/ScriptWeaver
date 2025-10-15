"""Story功能模块"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, messagebox, filedialog, scrolledtext
import tkinter as tk
from tkinter import ttk
import threading
import re
from pathlib import Path
from dotenv import load_dotenv

from src.clients.deepseek_client import DeepSeekClient
from src.kb.ingest import KnowledgeBaseIngestor, IngestConfig
from src.kb.search import KnowledgeBaseSearcher, SearchConfig
from src.utils.text import sanitize as _sanitize


class StoryGeneratorMixin:
	"""Story story_generator 功能"""
	
	def on_generate(self) -> None:
		query = self._get_prompt_content()
		if not query:
			messagebox.showwarning("提示", "请先输入创作需求/主题")
			return
		
		# 获取选中的故事生成API配置
		selected_api = self.story_gen_api.get() if hasattr(self, 'story_gen_api') else "DeepSeek"
		if selected_api not in self.api_presets:
			messagebox.showerror("错误", f"未找到API预设: {selected_api}")
			return
		
		api_config = self.api_presets[selected_api]
		api_key = _sanitize(api_config.get("key", ""))
		if not api_key:
			messagebox.showwarning("提示", f"API Key 为空，请在'基础 API 配置'中为 {selected_api} 填写后保存")
			return
		
		if self.model_only.get():
			self._generate_model_only(query)
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
				self.set_busy(True)
				self.status.set(f"使用 {selected_api} 检索素材并生成正文中...")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("准备生成故事...", "📝")
				
				load_dotenv()
				if need_build:
					if hasattr(self, 'update_header_status'):
						self.update_header_status("正在构建索引...", "⏳")
					cfg = IngestConfig(data_root=Path(self.data_dir.get()), index_dir=Path(self.index_dir.get()))
					KnowledgeBaseIngestor(cfg).build()
				
				if hasattr(self, 'update_header_status'):
					self.update_header_status("检索资料中...", "🔍")
				searcher = KnowledgeBaseSearcher(SearchConfig(index_dir=Path(self.index_dir.get()), top_k=self.top_k.get()))
				results = searcher.search(query, self.top_k.get())
				contexts = [c for c, _s, _m in results]
				
				# 使用选中的API配置
				if hasattr(self, 'update_header_status'):
					self.update_header_status("AI创作故事中...", "📝")
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				self.output.delete("1.0", END)
				
				# 检查是否需要分段生成
				target_chars = self.target_chars.get()
				sections = self._parse_outline_sections(self.current_outline) if self.current_outline else []
				
				# 如果字数 > 8000 且有目录，则分段生成
				if target_chars > 8000 and sections:
					self._generate_in_sections(client, query, contexts, sections, target_chars)
				else:
					# 一次性生成（原逻辑）
					self.output.insert(END, "生成中...\n\n")
					prompt = self._build_prompt(query, contexts, self.category.get(), self.current_outline)
					for delta in client.stream([
						{"role": "system", "content": "你是资深知乎创作者，擅长结合资料写出有观点、有结构的中文故事。"},
						{"role": "user", "content": prompt},
					], temperature=self.temperature.get(), max_tokens=int(target_chars*2.5)):
						self.output.insert(END, delta)
						self.output.see(END)
				
				self.status.set("生成完成")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("故事生成完成", "✅")
				# 自动保存到当前项目
				self._auto_save_to_project()
			except Exception as e:
				import traceback
				self.output.insert(END, "生成出错:\n" + traceback.format_exc() + "\n")
				messagebox.showerror("错误", str(e))
				self.status.set("生成失败")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("生成故事失败", "❌")
			finally:
				self.set_busy(False)
		threading.Thread(target=task, daemon=True).start()

	
	def on_auto_generate_all(self) -> None:
		"""自动连续生成所有章节"""
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
		
		# 确认开始
		total_chapters = len(self.parsed_sections)
		current_index = self.section_selector.current()
		start_index = max(0, current_index)
		
		confirm = messagebox.askyesno(
			"确认自动生成",
			f"将从第 {start_index + 1} 章开始，自动连续生成到第 {total_chapters} 章。\n\n"
			f"共需生成 {total_chapters - start_index} 章，可能需要较长时间。\n\n"
			f"期间请勿关闭窗口，是否继续？"
		)
		
		if not confirm:
			return
		
		# 启动自动生成
		if self.model_only.get():
			self._auto_generate_all_sections(query, [], start_index)
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
					load_dotenv()
					if need_build:
						cfg = IngestConfig(data_root=Path(self.data_dir.get()), index_dir=Path(self.index_dir.get()))
						KnowledgeBaseIngestor(cfg).build()
					searcher = KnowledgeBaseSearcher(SearchConfig(index_dir=Path(self.index_dir.get()), top_k=self.top_k.get()))
					results = searcher.search(query, self.top_k.get())
					contexts = [c for c, _s, _m in results]
					self._auto_generate_all_sections_with_contexts(query, contexts, start_index)
				except Exception as e:
					import traceback
					self.output.insert(END, "\n自动生成出错:\n" + traceback.format_exc() + "\n")
					messagebox.showerror("错误", str(e))
				finally:
					self.set_busy(False)
			threading.Thread(target=task, daemon=True).start()
	
	
	def _generate_model_only(self, query) -> None:
		def task():
			try:
				self.set_busy(True)
				
				# 获取选中的故事生成API配置
				selected_api = self.story_gen_api.get() if hasattr(self, 'story_gen_api') else "DeepSeek"
				if selected_api not in self.api_presets:
					messagebox.showerror("错误", f"未找到API预设: {selected_api}")
					return
				
				api_config = self.api_presets[selected_api]
				api_key = _sanitize(api_config.get("key", ""))
				
				self.status.set(f"使用 {selected_api} 准备生成...")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("AI创作故事中...", "📝")
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=_sanitize(api_config.get("model", "")),
				)
				self.output.delete("1.0", END)
				
				# 检查是否需要分段生成
				target_chars = self.target_chars.get()
				sections = self._parse_outline_sections(self.current_outline) if self.current_outline else []
				
				# 如果字数 > 8000 且有目录，则分段生成
				if target_chars > 8000 and sections:
					self._generate_in_sections(client, query, [], sections, target_chars)
				else:
					# 一次性生成（原逻辑）
					self.output.insert(END, "生成中...\n\n")
					prompt = self._build_prompt(query, [], self.category.get(), self.current_outline)
					for delta in client.stream([
						{"role": "system", "content": "你是资深知乎创作者，擅长结合资料写出有观点、有结构的中文故事。"},
						{"role": "user", "content": prompt},
					], temperature=self.temperature.get(), max_tokens=int(target_chars*2.5)):
						self.output.insert(END, delta)
						self.output.see(END)
				
				self.status.set("生成完成")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("故事生成完成", "✅")
				# 自动保存到当前项目
				self._auto_save_to_project()
			except Exception as e:
				import traceback
				self.output.insert(END, "\n\n生成出错:\n" + traceback.format_exc() + "\n")
				messagebox.showerror("错误", str(e))
				self.status.set("生成失败")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self.update_header_status("生成故事失败", "❌")
			finally:
				self.set_busy(False)
		threading.Thread(target=task, daemon=True).start()
	
	