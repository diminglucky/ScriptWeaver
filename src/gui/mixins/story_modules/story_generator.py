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

	def _preview_story_text_before_finalize(
		self,
		*,
		client,
		query: str,
		category: str,
		story_text: str,
	) -> tuple[str, str]:
		"""Preview full-story output and allow iterative re-generation before final apply."""
		story = str(story_text or "").strip()
		if not story:
			return "discard", ""
		if not hasattr(self, "_preview_generated_section_before_apply"):
			return "accept", story
		try:
			action, content = self._preview_generated_section_before_apply(
				client=client,
				section_index=0,
				total_sections=1,
				section_title="整篇故事",
				section_content=story,
				requirement=query,
				category=category,
				previous_content="",
			)
			final_story = str(content or "").strip() or story
			return str(action or "discard"), final_story
		except Exception as e:
			logger.debug("full-story preview fallback failed: %s", e)
			return "accept", story

	def _render_story_output(self, banner_text: str, story_text: str) -> None:
		"""Render final story text (banner + body) to output area."""
		self._ui(self.output.delete, "1.0", END)
		text = str(story_text or "").strip()
		if banner_text:
			self._ui(self.output.insert, END, banner_text + "\n\n")
		if text:
			self._ui(self.output.insert, END, text)
		self._ui(self.output.see, END)
	
	def _resolve_story_api_config(self) -> dict:
		"""Resolve API config for story generation from model routing and fallbacks."""
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
		return self._resolve_task_api("story_generate", fallback_provider=fallback_provider, fallback_model=fallback_model)

	def _run_story_generation(
		self,
		*,
		query: str,
		contexts: list,
		rag_rows: list,
		api_config: dict,
		target_chars_val: int,
		category_val: str,
		current_outline_val,
		log_label: str = "story generation",
	) -> None:
		"""Core generation logic shared by RAG and model-only paths."""
		selected_api = api_config.get("provider", "")
		api_key = _sanitize(api_config.get("key", ""))
		selected_model = api_config.get("model", "")

		self._ui(self.status.set, f"使用 {selected_api} 准备生成...")
		self._header_status("AI创作故事中...", "📝")
		print(f"🤖 使用模型: {selected_model}")

		client = DeepSeekClient(
			api_key=api_key,
			base_url=_sanitize(api_config.get("base_url", "")),
			model=selected_model,
		)
		if hasattr(self, "_ensure_story_global_overview_before_generation"):
			overview_action, _overview_text = self._ensure_story_global_overview_before_generation(
				client=client,
				requirement=query,
				category=category_val,
				contexts=contexts,
				outline_text=(current_outline_val or ""),
				force_review=False,
			)
			if overview_action == "discard":
				self._ui(self.status.set, "已取消（全书总览未采用）")
				self._header_status("生成已取消", "↩️")
				return
		self._ui(self.output.delete, "1.0", END)
		banner_text = ""
		if hasattr(self, "_build_story_run_banner"):
			banner = self._build_story_run_banner(query, category_val, rag_rows)
			if banner:
				banner_text = str(banner).strip()
				self._ui(self.output.insert, END, banner + "\n\n")

		sections = self._parse_outline_sections(current_outline_val) if current_outline_val else []

		if target_chars_val > 8000 and sections:
			completed = self._generate_in_sections(client, query, contexts, sections, target_chars_val)
			if not completed:
				self._ui(self.status.set, "已停止（预览取消）")
				self._header_status("生成已停止", "⏹️")
				self._ui(self._auto_save_to_project)
				return
		else:
			self._ui(self.output.insert, END, "生成中...\n\n")
			prompt = self._build_prompt(query, contexts, category_val, current_outline_val)
			generated_story = self._stream_story_with_retry(
				client,
				prompt,
				target_chars_val,
				requirement=query,
				category=category_val,
			)
			preview_action, final_story = self._preview_story_text_before_finalize(
				client=client,
				query=query,
				category=category_val,
				story_text=generated_story,
			)
			if preview_action == "discard":
				self._ui(self.status.set, "已取消（预览未采用）")
				self._header_status("生成已取消", "↩️")
				return
			self._render_story_output(banner_text, final_story)

		self._ui(self.status.set, "生成完成")
		self._header_status("故事生成完成", "✅")
		self._ui(self._auto_save_to_project)

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

		api_config = self._resolve_story_api_config()
		selected_api = api_config.get("provider", "")
		api_key = _sanitize(api_config.get("key", ""))
		if not api_key:
			messagebox.showwarning("提示", f"API Key 为空，请在'基础 API 配置'中为 {selected_api} 填写后保存")
			return

		print(f"🤖 使用模型: {api_config.get('model', '')}")

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
				self._header_status("准备生成故事...", "📝")

				load_dotenv()
				contexts = []
				rag_rows = []
				if need_build:
					self._header_status("正在构建索引...", "⏳")
					from src.kb.ingest import IngestConfig, KnowledgeBaseIngestor
					cfg = IngestConfig(data_root=Path(data_dir_val), index_dir=Path(index_dir_val))
					KnowledgeBaseIngestor(cfg).build()

				self._header_status("检索资料中...", "🔍")
				from src.kb.search import KnowledgeBaseSearcher, SearchConfig
				searcher = KnowledgeBaseSearcher(SearchConfig(index_dir=Path(index_dir_val), top_k=top_k_val))
				results = searcher.search(query, top_k_val)
				rag_rows = self._postprocess_rag_results(results) if hasattr(self, "_postprocess_rag_results") else results
				contexts = [c for c, _s, _m in rag_rows]

				self._run_story_generation(
					query=query,
					contexts=contexts,
					rag_rows=rag_rows,
					api_config=api_config,
					target_chars_val=target_chars_val,
					category_val=category_val,
					current_outline_val=current_outline_val,
					log_label="story generation with rag",
				)
			except Exception as e:
				logger.exception("story generation with rag failed")
				brief = _sanitize(str(e)) or e.__class__.__name__
				self._ui(self.output.insert, END, f"❌ 生成故事失败：{brief}\n")
				self._ui(messagebox.showerror, "错误", brief)
				self._ui(self.status.set, "生成失败")
				self._header_status("生成故事失败", "❌")
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
		
		api_config = self._resolve_story_api_config()
		selected_api = api_config.get("provider", "")
		api_key = _sanitize(api_config.get("key", ""))
		if not api_key:
			messagebox.showwarning("提示", f"API Key 为空，请在'基础 API 配置'中为 {selected_api} 填写后保存")
			return
		print(f"🤖 使用模型: {api_config.get('model', '')}")
		
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
		api_config = self._resolve_story_api_config()

		def task():
			try:
				self._ui(self.set_busy, True)
				self._run_story_generation(
					query=query,
					contexts=[],
					rag_rows=[],
					api_config=api_config,
					target_chars_val=target_chars_val,
					category_val=category_val,
					current_outline_val=current_outline_val,
					log_label="story generation model-only",
				)
			except Exception as e:
				logger.exception("story generation model-only failed")
				brief = _sanitize(str(e)) or e.__class__.__name__
				self._ui(self.output.insert, END, f"\n❌ 生成故事失败：{brief}\n")
				self._ui(messagebox.showerror, "错误", brief)
				self._ui(self.status.set, "生成失败")
				self._header_status("生成故事失败", "❌")
			finally:
				self._ui(self.set_busy, False)
		threading.Thread(target=task, daemon=True).start()

