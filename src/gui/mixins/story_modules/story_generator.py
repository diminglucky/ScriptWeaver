"""Story功能模块"""

from __future__ import annotations

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, messagebox, filedialog, scrolledtext
import tkinter as tk
from tkinter import ttk
import logging
import threading
import re
from pathlib import Path
try:
	from dotenv import load_dotenv
except Exception:  # pragma: no cover - fallback for minimal environments
	def load_dotenv(*args, **kwargs):
		return False

from src.clients.deepseek_client import DeepSeekClient
from src.utils.text import sanitize as _sanitize

logger = logging.getLogger(__name__)


def print(*args, **kwargs):  # type: ignore[override]
	logger.info(" ".join(str(a) for a in args))


class StoryGeneratorMixin:
	"""Story story_generator 功能"""

	def _persist_target_chars_preference(self) -> None:
		"""Persist current target chars to .env so it survives restart."""
		try:
			from pathlib import Path
			from dotenv import find_dotenv, set_key

			chars_value = int(self.target_chars.get())
			chars_value = max(500, min(30000, chars_value))
			env_path_str = find_dotenv(usecwd=True)
			env_path = Path(env_path_str) if env_path_str else Path.cwd() / ".env"
			env_path.touch(exist_ok=True)
			set_key(str(env_path), "TARGET_CHARS", str(chars_value))
		except Exception as e:
			logger.debug("persist target chars failed: %s", e)

	def _stream_story_with_retry(
		self,
		client,
		prompt: str,
		target_chars: int,
		min_ratio: float = 0.95,
		max_rounds: int | None = None,
		*,
		requirement: str = "",
		category: str = "",
	) -> str:
		"""Stream story text and auto-continue if output is shorter than expected."""
		min_chars = max(1, int(target_chars * min_ratio))
		if max_rounds is None:
			# Larger targets need more continuation rounds on providers with short per-response limits.
			max_rounds = max(2, min(8, (target_chars // 1500) + 2))

		template = (
			self._get_story_template_profile(requirement=requirement, category=category)
			if hasattr(self, "_get_story_template_profile")
			else {}
		)
		base_system_prompt = template.get(
			"story_system_prompt",
			"你是资深中文叙事作者，擅长写出冲突清晰、节奏稳定的故事。",
		)
		system_prompt = (
			f"{base_system_prompt}\n"
			"写作必须具备强戏剧性：开头迅速抛冲突，中段持续升级并制造反转，结尾回扣并留余味。"
			"禁止流水账、空话、重复总结。"
			"语言要自然克制，避免“首先/其次/最后/总的来说/不难发现/值得一提的是”等模板腔。"
			"用具体行动、细节和代价推进，不要口号化表达。"
		)
		accumulated = ""
		current_prompt = prompt

		for round_idx in range(max_rounds):
			remaining = max(0, min_chars - len(accumulated.strip()))
			current_target = target_chars if round_idx == 0 else max(300, int(remaining * 1.2))
			before_len = len(accumulated.strip())

			for delta in client.stream([
				{"role": "system", "content": system_prompt},
				{"role": "user", "content": current_prompt},
			], temperature=self.temperature.get(), max_tokens=int(current_target * 2.5)):
				self._ui(self.output.insert, END, delta)
				self._ui(self.output.see, END)
				accumulated += delta

			after_len = len(accumulated.strip())
			if after_len >= min_chars:
				break

			remaining = max(0, min_chars - after_len)
			produced_this_round = max(0, after_len - before_len)
			# If backend no longer returns enough useful continuation, avoid infinite retries.
			if produced_this_round < 120 and round_idx > 0:
				break

			if round_idx < max_rounds - 1 and remaining > 0:
				if hasattr(self, "status"):
					self._ui(self.status.set, f"内容偏短，自动续写中（还需约{remaining}字）")
				current_prompt = (
					"请在不重复前文的前提下继续正文，重点补强紧张感与戏剧性：\n"
					"1) 立刻推进情节，不要复述；\n"
					"2) 增加人物决策与代价；\n"
					"3) 至少加入一次误导或反转；\n"
					f"4) 继续补足约 {remaining} 字。\n\n"
					"以下为前文末尾（用于衔接）：\n"
					f"{accumulated[-1400:]}"
				)

		return accumulated
	
	def on_generate(self) -> None:
		query = self._get_prompt_content()
		if not query:
			messagebox.showwarning("提示", "请先输入创作需求/主题")
			return
		try:
			import time
			self._story_creativity_nonce = str(time.time_ns())
		except Exception:
			self._story_creativity_nonce = ""
		self._persist_target_chars_preference()
		
		# 故事生成：根据模型路由选择 API
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
			messagebox.showwarning("提示", f"API Key 为空，请在'基础 API 配置'中为 {selected_api} 填写后保存")
			return
		
		# 获取用户选择的模型
		selected_model = api_config.get("model", "")
		print(f"🤖 使用模型: {selected_model}")
		
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
		target_chars_val = self.target_chars.get()
		category_val = self.category.get()
		data_dir_val = self.data_dir.get()
		index_dir_val = self.index_dir.get()
		top_k_val = self.top_k.get()
		current_outline_val = self.current_outline

		def task():
			try:
				self._ui(self.set_busy, True)
				self._ui(self.status.set, f"使用 {selected_api} 检索素材并生成正文中...")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self._ui(self.update_header_status, "准备生成故事...", "📝")
				
				load_dotenv()
				contexts = []
				rag_rows = []
				if need_build:
					if hasattr(self, 'update_header_status'):
						self._ui(self.update_header_status, "正在构建索引...", "⏳")
					from src.kb.ingest import IngestConfig, KnowledgeBaseIngestor
					cfg = IngestConfig(data_root=Path(data_dir_val), index_dir=Path(index_dir_val))
					KnowledgeBaseIngestor(cfg).build()
				
				if hasattr(self, 'update_header_status'):
					self._ui(self.update_header_status, "检索资料中...", "🔍")
				from src.kb.search import KnowledgeBaseSearcher, SearchConfig
				searcher = KnowledgeBaseSearcher(SearchConfig(index_dir=Path(index_dir_val), top_k=top_k_val))
				results = searcher.search(query, top_k_val)
				rag_rows = self._postprocess_rag_results(results) if hasattr(self, "_postprocess_rag_results") else results
				contexts = [c for c, _s, _m in rag_rows]
				
				# 使用选中的API配置
				if hasattr(self, 'update_header_status'):
					self._ui(self.update_header_status, "AI创作故事中...", "📝")
				
				# 获取用户选择的模型
				selected_model = api_config.get("model", "")
				print(f"🤖 使用模型: {selected_model}")
				
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=selected_model,
				)
				self._ui(self.output.delete, "1.0", END)
				if hasattr(self, "_build_story_run_banner"):
					banner = self._build_story_run_banner(query, category_val, rag_rows)
					if banner:
						self._ui(self.output.insert, END, banner + "\n\n")
				
				# 检查是否需要分段生成
				sections = self._parse_outline_sections(current_outline_val) if current_outline_val else []
				
				# 如果字数 > 8000 且有目录，则分段生成
				if target_chars_val > 8000 and sections:
					self._generate_in_sections(client, query, contexts, sections, target_chars_val)
				else:
					# 一次性生成（原逻辑）
					self._ui(self.output.insert, END, "生成中...\n\n")
					prompt = self._build_prompt(query, contexts, category_val, current_outline_val)
					self._stream_story_with_retry(
						client,
						prompt,
						target_chars_val,
						requirement=query,
						category=category_val,
					)
				
				self._ui(self.status.set, "生成完成")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self._ui(self.update_header_status, "故事生成完成", "✅")
				# 自动保存到当前项目
				self._ui(self._auto_save_to_project)
			except Exception as e:
				logger.exception("story generation with rag failed")
				brief = _sanitize(str(e)) or e.__class__.__name__
				self._ui(self.output.insert, END, f"❌ 生成故事失败：{brief}\n")
				self._ui(messagebox.showerror, "错误", brief)
				self._ui(self.status.set, "生成失败")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self._ui(self.update_header_status, "生成故事失败", "❌")
			finally:
				self._ui(self.set_busy, False)
		threading.Thread(target=task, daemon=True).start()


	
	def on_auto_generate_all(self) -> None:
		"""自动连续生成所有章节"""
		if not self.parsed_sections:
			messagebox.showwarning("提示", "请先生成目录")
			return
		self._persist_target_chars_preference()
		
		query = self._get_prompt_content()
		if not query:
			messagebox.showwarning("提示", "请先输入创作需求/主题")
			return
		try:
			import time
			self._story_creativity_nonce = str(time.time_ns())
		except Exception:
			self._story_creativity_nonce = ""
		
		# 故事生成：根据模型路由选择 API
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
			messagebox.showwarning("提示", f"API Key 为空，请在'基础 API 配置'中为 {selected_api} 填写后保存")
			return
		
		# 获取用户选择的模型
		selected_model = api_config.get("model", "")
		print(f"🤖 使用模型: {selected_model}")
		
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
			
			data_dir_val = self.data_dir.get()
			index_dir_val = self.index_dir.get()
			top_k_val = self.top_k.get()
			def task():
				try:
					self._ui(self.set_busy, True)
					load_dotenv()
					contexts = []
					if need_build:
						from src.kb.ingest import IngestConfig, KnowledgeBaseIngestor
						cfg = IngestConfig(data_root=Path(data_dir_val), index_dir=Path(index_dir_val))
						KnowledgeBaseIngestor(cfg).build()
					from src.kb.search import KnowledgeBaseSearcher, SearchConfig
					searcher = KnowledgeBaseSearcher(SearchConfig(index_dir=Path(index_dir_val), top_k=top_k_val))
					results = searcher.search(query, top_k_val)
					rag_rows = self._postprocess_rag_results(results) if hasattr(self, "_postprocess_rag_results") else results
					contexts = [c for c, _s, _m in rag_rows]
					# 修复：调用 _auto_generate_all_sections 而非未定义的方法
					self._auto_generate_all_sections(query, contexts, start_index)
				except Exception as e:
					logger.exception("auto generate all with rag failed")
					brief = _sanitize(str(e)) or e.__class__.__name__
					self._ui(self.output.insert, END, f"\n❌ 自动生成失败：{brief}\n")
					self._ui(messagebox.showerror, "错误", brief)
				finally:
					self._ui(self.set_busy, False)
			threading.Thread(target=task, daemon=True).start()
	
	
	def _generate_model_only(self, query) -> None:
		target_chars_val = self.target_chars.get()
		category_val = self.category.get()
		current_outline_val = self.current_outline

		# 预先获取所有的GUI组件值
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
		
		# _resolve_task_api可能会访问GUI或修改，我们在主线程调用比较好
		# 但原作者在task里调用可能需要阻塞，这也没问题
		api_config = self._resolve_task_api("story_generate", fallback_provider=fallback_provider, fallback_model=fallback_model)
		selected_api = api_config.get("provider", "")
		api_key = _sanitize(api_config.get("key", ""))
		selected_model = api_config.get("model", "")

		def task():
			try:
				self._ui(self.set_busy, True)
				
				self._ui(self.status.set, f"使用 {selected_api} 准备生成...")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self._ui(self.update_header_status, "AI创作故事中...", "📝")
				
				# 获取用户选择的模型
				print(f"🤖 使用模型: {selected_model}")
				
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=selected_model,
				)
				self._ui(self.output.delete, "1.0", END)
				if hasattr(self, "_build_story_run_banner"):
					banner = self._build_story_run_banner(query, category_val, [])
					if banner:
						self._ui(self.output.insert, END, banner + "\n\n")
				
				# 检查是否需要分段生成
				sections = self._parse_outline_sections(current_outline_val) if current_outline_val else []
				
				# 如果字数 > 8000 且有目录，则分段生成
				if target_chars_val > 8000 and sections:
					self._generate_in_sections(client, query, [], sections, target_chars_val)
				else:
					# 一次性生成（原逻辑）
					self._ui(self.output.insert, END, "生成中...\n\n")
					prompt = self._build_prompt(query, [], category_val, current_outline_val)
					self._stream_story_with_retry(
						client,
						prompt,
						target_chars_val,
						requirement=query,
						category=category_val,
					)
				
				self._ui(self.status.set, "生成完成")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self._ui(self.update_header_status, "故事生成完成", "✅")
				# 自动保存到当前项目
				self._ui(self._auto_save_to_project)
			except Exception as e:
				logger.exception("story generation model-only failed")
				brief = _sanitize(str(e)) or e.__class__.__name__
				self._ui(self.output.insert, END, f"\n❌ 生成故事失败：{brief}\n")
				self._ui(messagebox.showerror, "错误", brief)
				self._ui(self.status.set, "生成失败")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self._ui(self.update_header_status, "生成故事失败", "❌")
			finally:
				self._ui(self.set_busy, False)
		threading.Thread(target=task, daemon=True).start()
	
	
