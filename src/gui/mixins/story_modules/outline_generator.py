"""Story功能模块"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, messagebox, filedialog, scrolledtext
import tkinter as tk
from tkinter import ttk
import logging
import threading
import re
import os
from pathlib import Path
try:
	from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
	def load_dotenv(*args, **kwargs):
		return False

from src.clients.deepseek_client import DeepSeekClient
from src.utils.text import sanitize as _sanitize
from src.gui.helpers.story_writing_guardrails import normalize_chapter_title
from src.gui.helpers.story_quality import (
	normalize_memory_entry,
	parse_memory_entry,
	parse_quality_review,
	should_polish,
	strip_duplicate_lines,
)

logger = logging.getLogger(__name__)


def print(*args, **kwargs):  # type: ignore[override]
	logger.info(" ".join(str(a) for a in args))


class OutlineGeneratorMixin:
	"""Story outline_generator 功能"""

	def _is_section_tail_complete(self, text: str) -> bool:
		"""Heuristic check: whether a chapter tail looks complete."""
		tail = (text or "").strip()
		if not tail:
			return False
		# Ends with terminal punctuation (allow trailing closing quotes/brackets)
		if re.search(r"[。！？!?…；;][”’」』】》）)]*\s*$", tail):
			return True
		return False

	def _repair_section_tail_if_needed(self, client, section_title: str, section_content: str) -> str:
		"""
		If section tail looks truncated, ask model for a short natural ending.
		Returns extra text to append (may be empty).
		"""
		if self._is_section_tail_complete(section_content):
			return ""

		tail = (section_content or "").strip()
		if len(tail) < 60:
			return ""
		tail = tail[-450:]
		try:
			temp = float(self.temperature.get())
		except Exception:
			temp = 0.7
		temp = max(0.4, min(0.9, temp))

		prompt = (
			"你是中文小说润色编辑。下面这一章的结尾疑似被截断。\n"
			"请只补写一个自然收束的结尾段（约80-220字），满足：\n"
			"1) 仅续写，不重复已出现原句；\n"
			"2) 不新增章节标题、不总结全文；\n"
			"3) 保持当前叙事语气；\n"
			"4) 最后必须以完整句号/问号/感叹号结束。\n\n"
			f"章节标题：{section_title}\n"
			f"当前结尾片段：\n{tail}\n\n"
			"请直接输出补写内容："
		)
		try:
			extra = client.chat(
				[{"role": "user", "content": prompt}],
				temperature=temp,
			).strip()
		except Exception as e:
			logger.debug("repair section tail failed: %s", e)
			return ""

		if not extra:
			return ""

		# Keep patch small and avoid model adding extra headers.
		extra = re.sub(r"^\s*【?第.*?章[：:】]\s*", "", extra)
		extra = re.sub(r"^\s*(补写|续写|续：)\s*", "", extra)
		extra = extra.strip()
		if not extra:
			return ""
		if len(extra) > 280:
			extra = extra[:280].rstrip()
		if not self._is_section_tail_complete(extra):
			extra = extra.rstrip("，,：:；;、") + "。"
		return extra

	def _is_story_quality_review_enabled(self) -> bool:
		raw = str(os.getenv("STORY_QUALITY_REVIEW", "1") or "1").strip().lower()
		default_enabled = raw in {"1", "true", "yes", "on"}
		val = getattr(self, "story_quality_review_enabled", None)
		if hasattr(val, "get"):
			try:
				return bool(val.get())
			except Exception:
				return default_enabled
		if isinstance(val, bool):
			return val
		return default_enabled

	def _get_story_quality_thresholds(self) -> tuple[float, float]:
		min_avg = 7.4
		min_dim = 6.8
		if hasattr(self, "story_quality_min_avg"):
			try:
				min_avg = float(self.story_quality_min_avg.get())
			except Exception:
				min_avg = 7.4
		else:
			try:
				min_avg = float(os.getenv("STORY_QUALITY_MIN_AVG", "7.4") or "7.4")
			except Exception:
				min_avg = 7.4
		if hasattr(self, "story_quality_min_dim"):
			try:
				min_dim = float(self.story_quality_min_dim.get())
			except Exception:
				min_dim = 6.8
		else:
			try:
				min_dim = float(os.getenv("STORY_QUALITY_MIN_DIM", "6.8") or "6.8")
			except Exception:
				min_dim = 6.8
		min_avg = max(1.0, min(10.0, min_avg))
		min_dim = max(1.0, min(10.0, min_dim))
		return min_avg, min_dim

	def _review_section_quality(self, client, section_title: str, section_content: str, requirement: str, category: str) -> dict:
		if not section_content.strip():
			return {
				"scores": {"realism": 1.0, "detail": 1.0, "coherence": 1.0, "naturalness": 1.0},
				"avg_score": 1.0,
				"strengths": [],
				"issues": ["内容为空"],
				"key_fix": "先生成有效正文。",
			}
		preview = section_content[-1800:]
		prompt = (
			"你是严格的中文小说编辑，请评估以下章节文本质量，并仅返回 JSON。\n"
			"评分维度（1-10）：realism(真实感), detail(细节密度), coherence(逻辑连贯), naturalness(语言自然度)。\n"
			"返回格式：\n"
			"{\"scores\":{\"realism\":0,\"detail\":0,\"coherence\":0,\"naturalness\":0},"
			"\"strengths\":[\"\"],\"issues\":[\"\"],\"key_fix\":\"\"}\n"
			"要求：\n"
			"1) issues 至少给1条且可执行；\n"
			"2) key_fix 20字以内；\n"
			"3) 禁止输出 JSON 以外内容。\n\n"
			f"主题：{requirement}\n"
			f"题材：{category}\n"
			f"章节标题：{section_title}\n"
			f"章节文本：\n{preview}\n"
		)
		try:
			raw = client.chat(
				[{"role": "user", "content": prompt}],
				temperature=0.1,
				max_tokens=600,
			)
		except Exception as e:
			logger.debug("quality review failed: %s", e)
			return {
				"scores": {"realism": 7.0, "detail": 7.0, "coherence": 7.0, "naturalness": 7.0},
				"avg_score": 7.0,
				"strengths": [],
				"issues": ["质量评审不可用，跳过自动改写"],
				"key_fix": "",
			}
		return parse_quality_review(raw)

	def _polish_section_text(
		self,
		client,
		section_title: str,
		section_content: str,
		review: dict,
		target_chars_per_section: int,
	) -> str:
		key_fix = str(review.get("key_fix", "") or "").strip()
		issues = review.get("issues", [])
		if not isinstance(issues, list):
			issues = []
		issue_text = "；".join(str(x) for x in issues[:3] if str(x).strip())
		chars = len(section_content.strip())
		target_low = max(220, int(target_chars_per_section * 0.8))
		target_high = max(target_low, int(target_chars_per_section * 1.15))
		prompt = (
			"你是中文小说精修编辑。请在不改变剧情事实和人物设定的前提下，"
			"对下面章节做一次“真实细腻化”重写。\n"
			"硬性要求：\n"
			"1) 保留原剧情顺序与关键事件，不新增大剧情；\n"
			"2) 优先修复："
			f"{key_fix or issue_text or '语言模板腔和细节不足'}；\n"
			"3) 增加可感知细节（动作/环境/心理），减少空泛评价句；\n"
			"4) 语言自然克制，禁止“首先/其次/最后/总的来说”等模板腔；\n"
			f"5) 字数控制在 {target_low}-{target_high} 字附近（当前约{chars}字）；\n"
			"6) 只输出最终章节正文，不要解释。\n\n"
			f"章节标题：{section_title}\n"
			f"原文：\n{section_content}\n"
		)
		try:
			rewritten = client.chat(
				[{"role": "user", "content": prompt}],
				temperature=0.45,
				max_tokens=max(1200, int(target_chars_per_section * 2.4)),
			).strip()
		except Exception as e:
			logger.debug("section polish failed: %s", e)
			return section_content

		if not rewritten:
			return section_content
		rewritten = re.sub(r"^\s*【?第.*?章[：:】]\s*", "", rewritten)
		rewritten = strip_duplicate_lines(rewritten)
		if len(rewritten) < max(120, int(len(section_content) * 0.55)):
			return section_content
		return rewritten

	def _update_chapter_quality_report(self, section_index: int, section_title: str, review: dict) -> None:
		if not hasattr(self, "chapter_quality_reports") or not isinstance(self.chapter_quality_reports, list):
			self.chapter_quality_reports = []
		while len(self.chapter_quality_reports) <= section_index:
			self.chapter_quality_reports.append({})
		report = {
			"chapter_index": int(section_index),
			"chapter_title": str(section_title or "").strip(),
			"scores": review.get("scores", {}),
			"avg_score": review.get("avg_score", 0.0),
			"issues": review.get("issues", []),
			"key_fix": review.get("key_fix", ""),
		}
		self.chapter_quality_reports[section_index] = report

	def _extract_memory_entry(self, client, section_index: int, section_title: str, section_content: str) -> dict:
		preview = section_content[-2200:]
		prompt = (
			"你是小说连续性编辑。请从以下章节提取“记忆账本”，并仅返回 JSON：\n"
			"{\"summary\":\"\",\"plot_points\":[\"\"],\"relation_changes\":[\"\"],\"unresolved_hooks\":[\"\"],\"state_shift\":\"\"}\n"
			"要求：\n"
			"1) summary 40-120字；\n"
			"2) plot_points 最多4条，聚焦事实事件；\n"
			"3) relation_changes 最多3条，写清人物关系变化；\n"
			"4) unresolved_hooks 最多3条，写未回收问题；\n"
			"5) state_shift 30字以内。\n\n"
			f"章节标题：{section_title}\n"
			f"章节文本：\n{preview}\n"
		)
		try:
			raw = client.chat(
				[{"role": "user", "content": prompt}],
				temperature=0.2,
				max_tokens=700,
			)
			entry = parse_memory_entry(raw)
		except Exception as e:
			logger.debug("memory extraction failed: %s", e)
			entry = {}
		if not entry:
			fallback_summary = section_content.strip().replace("\n", " ")
			entry = {
				"summary": fallback_summary[:120],
				"plot_points": [],
				"relation_changes": [],
				"unresolved_hooks": [],
				"state_shift": "",
			}
		return normalize_memory_entry(entry, chapter_index=section_index, chapter_title=section_title)

	def _update_story_memory_ledger(self, section_index: int, section_title: str, entry: dict) -> None:
		if not hasattr(self, "story_memory_ledger") or not isinstance(self.story_memory_ledger, list):
			self.story_memory_ledger = []
		normalized = normalize_memory_entry(entry, chapter_index=section_index, chapter_title=section_title)
		while len(self.story_memory_ledger) <= section_index:
			self.story_memory_ledger.append({})
		self.story_memory_ledger[section_index] = normalized
	
	def on_generate_outline(self) -> None:
		requirement = self._get_prompt_content()
		if not requirement:
			messagebox.showwarning("提示", "请先输入创作需求/主题")
			return
		try:
			import time
			self._story_creativity_nonce = str(time.time_ns())
		except Exception:
			self._story_creativity_nonce = ""
		
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
				self._ui(self.set_busy, True)
				self._ui(self.status.set, f"使用 {selected_api} 检索素材并生成目录中...")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self._ui(self.update_header_status, "正在生成目录...", "📝")
				from src.kb.ingest import IngestConfig, KnowledgeBaseIngestor
				from src.kb.search import KnowledgeBaseSearcher, SearchConfig
				
				load_dotenv()
				if need_build:
					if hasattr(self, 'update_header_status'):
						self._ui(self.update_header_status, "正在构建索引...", "⏳")
					cfg = IngestConfig(data_root=Path(self._ui_get(self.data_dir.get)), index_dir=Path(self._ui_get(self.index_dir.get)))
					KnowledgeBaseIngestor(cfg).build()
				
					if hasattr(self, 'update_header_status'):
						self._ui(self.update_header_status, "检索资料中...", "🔍")
					searcher = KnowledgeBaseSearcher(SearchConfig(index_dir=Path(self._ui_get(self.index_dir.get)), top_k=self._ui_get(self.top_k.get)))
					results = searcher.search(requirement, self._ui_get(self.top_k.get))
					rag_rows = self._postprocess_rag_results(results) if hasattr(self, "_postprocess_rag_results") else results
					contexts = [c for c, _s, _m in rag_rows]
				
				# 使用选中的API配置
				if hasattr(self, 'update_header_status'):
					self._ui(self.update_header_status, "AI生成目录中...", "📝")
				
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=selected_model,
				)
				outline_prompt = self._build_outline_prompt(requirement, contexts, self._ui_get(self.category.get))
				template = (
					self._get_story_template_profile(
						requirement=requirement,
						category=self._ui_get(self.category.get),
					)
					if hasattr(self, "_get_story_template_profile")
					else {}
				)
				outline_system_prompt = template.get(
					"outline_system_prompt",
					"你是资深中文创作者与编辑。请先产出结构化目录，不要写正文。",
				)
				self._ui(self.output.delete, "1.0", END)
				if hasattr(self, "_build_story_run_banner"):
					banner = self._build_story_run_banner(requirement, self._ui_get(self.category.get), rag_rows)
					if banner:
						self._ui(self.output.insert, END, banner + "\n\n")
				self._ui(self.output.insert, END, "生成目录中...\n\n")
				
				# For chat api, we can't easily stream to tk directly if not implemented
				# The client.chat call is blocking, we do it in background
				outline_text = client.chat([
					{"role": "system", "content": outline_system_prompt},
					{"role": "user", "content": outline_prompt},
				], temperature=max(0.4, self._ui_get(self.temperature.get) - 0.2))
				self.current_outline = outline_text.strip()
				estimate = self._estimate_chars(self.current_outline)
				
				# 解析章节并更新选择器
				self.parsed_sections = self._parse_outline_sections(self.current_outline)
				self.story_memory_ledger = []
				self.chapter_quality_reports = []
				self._ui(self._update_section_selector)
				if hasattr(self, "_update_story_diagnostics_panel"):
					self._ui(self._update_story_diagnostics_panel)
				
				self._ui(self.output.insert, END, f"目录（共{len(self.parsed_sections)}章，预估字数≈{estimate}字）\n\n{self.current_outline}\n\n")
				self._ui(self.status.set, "目录已生成")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self._ui(self.update_header_status, "目录生成完成", "✅")
			except Exception as e:
				import traceback
				self._ui(self.output.insert, END, "生成目录出错:\n" + traceback.format_exc() + "\n")
				self._ui(messagebox.showerror, "错误", str(e))
				self._ui(self.status.set, "生成目录失败")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self._ui(self.update_header_status, "生成目录失败", "❌")
			finally:
				self._ui(self.set_busy, False)
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
		try:
			import time
			self._story_creativity_nonce = str(time.time_ns())
		except Exception:
			self._story_creativity_nonce = ""
		
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
					self._ui(self.set_busy, True)
					from src.kb.ingest import IngestConfig, KnowledgeBaseIngestor
					from src.kb.search import KnowledgeBaseSearcher, SearchConfig
					load_dotenv()
					if need_build:
						cfg = IngestConfig(data_root=Path(self._ui_get(self.data_dir.get)), index_dir=Path(self._ui_get(self.index_dir.get)))
						KnowledgeBaseIngestor(cfg).build()
						searcher = KnowledgeBaseSearcher(SearchConfig(index_dir=Path(self._ui_get(self.index_dir.get)), top_k=self._ui_get(self.top_k.get)))
						results = searcher.search(query, self._ui_get(self.top_k.get))
						rag_rows = self._postprocess_rag_results(results) if hasattr(self, "_postprocess_rag_results") else results
						contexts = [c for c, _s, _m in rag_rows]
						self._generate_single_section_with_contexts(query, contexts, selected_index)
				except Exception as e:
					import traceback
					self._ui(self.output.insert, END, "\n生成出错:\n" + traceback.format_exc() + "\n")
					self._ui(messagebox.showerror, "错误", str(e))
				finally:
					self._ui(self.set_busy, False)
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
				self._ui(self.set_busy, True)
				
				# 目录生成：根据模型路由选择 API
				fallback_provider = None
				if hasattr(self, 'outline_gen_api'):
					fallback_provider = self._ui_get(self.outline_gen_api.get)
				if not fallback_provider and hasattr(self, 'quick_story_api'):
					fallback_provider = self._ui_get(self.quick_story_api.get)
				if not fallback_provider and hasattr(self, 'api_preset'):
					fallback_provider = self._ui_get(self.api_preset.get)
				fallback_model = None
				if hasattr(self, 'story_model_var'):
					fallback_model = self._ui_get(self.story_model_var.get)
				elif hasattr(self, 'model'):
					fallback_model = self._ui_get(self.model.get)
				
				api_config = self._ui_get(lambda: self._resolve_task_api("story_outline", fallback_provider=fallback_provider, fallback_model=fallback_model))
				selected_api = api_config.get("provider", "")
				api_key = _sanitize(api_config.get("key", ""))
				
				self._ui(self.status.set, f"使用 {selected_api} 生成目录中...")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self._ui(self.update_header_status, "AI生成目录中...", "📝")
				
				# 获取用户选择的模型
				selected_model = api_config.get("model", "")
				print(f"🤖 使用模型: {selected_model}")
				
				client = DeepSeekClient(
					api_key=api_key,
					base_url=_sanitize(api_config.get("base_url", "")),
					model=selected_model,
				)
				prompt = self._ui_get(lambda: self._build_outline_prompt(requirement, [], self.category.get()))
				template = (
					self._get_story_template_profile(
						requirement=requirement,
						category=self._ui_get(self.category.get),
					)
					if hasattr(self, "_get_story_template_profile")
					else {}
				)
				outline_system_prompt = template.get(
					"outline_system_prompt",
					"你是资深中文创作者与编辑。请先产出结构化目录，不要写正文。",
				)
				self._ui(self.output.delete, "1.0", END)
				if hasattr(self, "_build_story_run_banner"):
					banner = self._build_story_run_banner(requirement, self._ui_get(self.category.get), [])
					if banner:
						self._ui(self.output.insert, END, banner + "\n\n")
				self._ui(self.output.insert, END, "生成目录中...\n\n")
				
				temperature_val = self._ui_get(self.temperature.get)
				outline_text = client.chat([
					{"role": "system", "content": outline_system_prompt},
					{"role": "user", "content": prompt},
				], temperature=max(0.4, temperature_val - 0.2))
				self.current_outline = outline_text.strip()
				estimate = self._estimate_chars(self.current_outline)
				
				# 解析章节并更新选择器
				self.parsed_sections = self._parse_outline_sections(self.current_outline)
				self.story_memory_ledger = []
				self.chapter_quality_reports = []
				self._ui(self._update_section_selector)
				if hasattr(self, "_update_story_diagnostics_panel"):
					self._ui(self._update_story_diagnostics_panel)
				
				self._ui(self.output.insert, END, f"目录（共{len(self.parsed_sections)}章，预估字数≈{estimate}字）\n\n{self.current_outline}\n\n")
				self._ui(self.status.set, "目录已生成")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self._ui(self.update_header_status, "目录生成完成", "✅")
			except Exception as e:
				self._ui(messagebox.showerror, "错误", str(e))
				self._ui(self.status.set, "生成目录失败")
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self._ui(self.update_header_status, "生成目录失败", "❌")
			finally:
				self._ui(self.set_busy, False)
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
			section_start_pos = self._ui_get(self.output.index, "end-1c") if hasattr(self, "_ui_get") else self.output.index("end-1c")
			# 更新顶部状态栏
			if hasattr(self, 'update_header_status'):
				self._ui(self.update_header_status, f"生成中 ({idx+1}/{total_sections})", "📝")
			
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
			template = (
				self._get_story_template_profile(requirement=requirement, category=category)
				if hasattr(self, "_get_story_template_profile")
				else {}
			)
			story_system_prompt = template.get(
				"story_system_prompt",
				"你是资深中文叙事作者，擅长结合资料写出有观点、有结构的中文故事。",
			)
			
			# 流式生成本段
			section_content = ""
			for delta in client.stream([
				{"role": "system", "content": story_system_prompt},
				{"role": "user", "content": section_prompt},
			], temperature=self.temperature.get(), max_tokens=int(target_per_section*2.5)):
				self._ui(self.output.insert, END, delta)
				self._ui(self.output.see, END)
				section_content += delta

			# 章节末尾补全，避免截断
			tail_patch = self._repair_section_tail_if_needed(client, section.get("title", ""), section_content)
			if tail_patch:
				if not section_content.endswith("\n"):
					section_content += "\n"
					self._ui(self.output.insert, END, "\n")
				section_content += tail_patch
				self._ui(self.output.insert, END, tail_patch)
				self._ui(self.output.see, END)

			# 质量评审 + 自动精修
			review = None
			if self._is_story_quality_review_enabled():
				review = self._review_section_quality(client, section.get("title", ""), section_content, requirement, category)
				self._update_chapter_quality_report(idx, section.get("title", ""), review)
				min_avg, min_dim = self._get_story_quality_thresholds()
				if should_polish(review, min_avg_score=min_avg, min_dimension_score=min_dim):
					polished = self._polish_section_text(
						client,
						section.get("title", ""),
						section_content,
						review,
						target_per_section,
					)
					if polished and polished != section_content:
						self._ui(self.output.delete, section_start_pos, "end-1c")
						self._ui(self.output.insert, END, polished)
						self._ui(self.output.see, END)
						section_content = polished

			# 记忆账本（用于后续章节连贯）
			memory_entry = self._extract_memory_entry(
				client,
				section_index=idx,
				section_title=section.get("title", ""),
				section_content=section_content,
			)
			self._update_story_memory_ledger(idx, section.get("title", ""), memory_entry)
			if hasattr(self, "_update_story_diagnostics_panel"):
				self._ui(self._update_story_diagnostics_panel)
			
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
				self._ui(self.set_busy, True)
				
				# 章节生成：根据模型路由选择 API
				fallback_provider = None
				if hasattr(self, 'story_gen_api'):
					fallback_provider = self._ui_get(self.story_gen_api.get)
				if not fallback_provider and hasattr(self, 'quick_story_api'):
					fallback_provider = self._ui_get(self.quick_story_api.get)
				if not fallback_provider and hasattr(self, 'api_preset'):
					fallback_provider = self._ui_get(self.api_preset.get)
				fallback_model = None
				if hasattr(self, 'story_model_var'):
					fallback_model = self._ui_get(self.story_model_var.get)
				elif hasattr(self, 'model'):
					fallback_model = self._ui_get(self.model.get)
				
				api_config = self._ui_get(lambda: self._resolve_task_api("story_generate", fallback_provider=fallback_provider, fallback_model=fallback_model))
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
				self._ui(self.set_busy, False)
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
		if not self.generated_content and hasattr(self, "_build_story_run_banner"):
			banner = self._build_story_run_banner(query, self.category.get(), contexts)
			if banner:
				self._ui(self.output.insert, END, banner + "\n\n")
		
		# 更新状态
		self._ui(self.status.set, f"生成第 {section_index+1}/{total_sections} 章: {section['title']}")
		# 更新顶部状态栏
		if hasattr(self, 'update_header_status'):
			self._ui(self.update_header_status, f"生成章节 ({section_index+1}/{total_sections})", "📝")
		self._ui(self.output.insert, END, f"\n{'='*50}\n")
		self._ui(self.output.insert, END, f"【第 {section_index+1}/{total_sections} 章：{section['title']}】\n\n")
		self._ui(self.output.see, END)
		section_start_pos = self._ui_get(self.output.index, "end-1c") if hasattr(self, "_ui_get") else self.output.index("end-1c")
		
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
		template = (
			self._get_story_template_profile(requirement=query, category=self.category.get())
			if hasattr(self, "_get_story_template_profile")
			else {}
		)
		story_system_prompt = template.get(
			"story_system_prompt",
			"你是资深中文叙事作者，擅长结合资料写出有观点、有结构的中文故事。",
		)
		
		# 流式生成
		section_content = ""
		max_tokens = max(1200, min(8192, int(target_per_section * 3.2)))
		for delta in client.stream([
			{"role": "system", "content": story_system_prompt},
			{"role": "user", "content": section_prompt},
		], temperature=self.temperature.get(), max_tokens=max_tokens):
			self._ui(self.output.insert, END, delta)
			self._ui(self.output.see, END)
			section_content += delta

		# 如果章节末尾疑似截断，自动补一个收束段，避免上下章衔接断裂
		tail_patch = self._repair_section_tail_if_needed(client, section.get("title", ""), section_content)
		if tail_patch:
			if not section_content.endswith("\n"):
				section_content += "\n"
				self._ui(self.output.insert, END, "\n")
			section_content += tail_patch
			self._ui(self.output.insert, END, tail_patch)
			self._ui(self.output.see, END)

		# 质量评审 + 自动精修
		review = None
		if self._is_story_quality_review_enabled():
			review = self._review_section_quality(
				client,
				section.get("title", ""),
				section_content,
				query,
				self.category.get(),
			)
			self._update_chapter_quality_report(section_index, section.get("title", ""), review)
			min_avg, min_dim = self._get_story_quality_thresholds()
			if should_polish(review, min_avg_score=min_avg, min_dimension_score=min_dim):
				polished = self._polish_section_text(
					client,
					section.get("title", ""),
					section_content,
					review,
					target_per_section,
				)
				if polished and polished != section_content:
					self._ui(self.output.delete, section_start_pos, "end-1c")
					self._ui(self.output.insert, END, polished)
					self._ui(self.output.see, END)
					section_content = polished

		# 记忆账本（用于后续章节连贯）
		memory_entry = self._extract_memory_entry(
			client,
			section_index=section_index,
			section_title=section.get("title", ""),
			section_content=section_content,
		)
		self._update_story_memory_ledger(section_index, section.get("title", ""), memory_entry)
		if hasattr(self, "_update_story_diagnostics_panel"):
			self._ui(self._update_story_diagnostics_panel)
		
		# 累积内容
		self.generated_content += "\n\n" + section_content
		
		# 完成提示
		self._ui(self.output.insert, END, f"\n\n{'='*50}\n")
		self._ui(self.output.insert, END, f"✅ 第 {section_index+1} 章完成！本章字数：{len(section_content)} 字\n")
		self._ui(self.status.set, f"第 {section_index+1} 章完成（{len(section_content)} 字）")
		# 更新顶部状态栏
		if hasattr(self, 'update_header_status'):
			self._ui(self.update_header_status, f"第 {section_index+1} 章完成", "✅")
		
		# 自动保存
		self._auto_save_to_project()
	
	
	def _auto_generate_all_sections(self, query, contexts, start_index=0):
		"""自动生成所有章节（无知识库）"""
		def task():
			try:
				self._ui(self.set_busy, True)
				
				# 自动生成章节：根据模型路由选择 API
				fallback_provider = None
				if hasattr(self, 'story_gen_api'):
					fallback_provider = self._ui_get(self.story_gen_api.get)
				if not fallback_provider and hasattr(self, 'quick_story_api'):
					fallback_provider = self._ui_get(self.quick_story_api.get)
				if not fallback_provider and hasattr(self, 'api_preset'):
					fallback_provider = self._ui_get(self.api_preset.get)
				fallback_model = None
				if hasattr(self, 'story_model_var'):
					fallback_model = self._ui_get(self.story_model_var.get)
				elif hasattr(self, 'model'):
					fallback_model = self._ui_get(self.model.get)
				
				api_config = self._ui_get(lambda: self._resolve_task_api("story_generate", fallback_provider=fallback_provider, fallback_model=fallback_model))
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
					self._ui(self.update_header_status, "全部章节完成", "✅")
				self._ui(messagebox.showinfo, "完成", f"所有章节已生成完成！\n\n共 {total_sections} 章，总字数：{len(self.generated_content)} 字")
			except Exception as e:
				import traceback
				self._ui(self.output.insert, END, "\n自动生成出错:\n" + traceback.format_exc() + "\n")
				self._ui(messagebox.showerror, "错误", str(e))
				# 更新顶部状态栏
				if hasattr(self, 'update_header_status'):
					self._ui(self.update_header_status, "自动生成失败", "❌")
			finally:
				self._ui(self.set_busy, False)
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
		if hasattr(self, "_update_story_diagnostics_panel"):
			try:
				self._update_story_diagnostics_panel()
			except Exception:
				pass
	
	
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
				current_section = normalize_chapter_title(title.strip(), min_len=4, max_len=12)
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


	
