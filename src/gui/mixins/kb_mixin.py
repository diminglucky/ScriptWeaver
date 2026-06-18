"""
Kb相关功能模块
"""

import threading
from pathlib import Path
from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, messagebox, filedialog
import tkinter as tk
from tkinter import ttk


class KbMixin:
	"""Kb管理功能"""

	def _rag_ingest_kwargs(self) -> dict:
		def _read_int(name: str, default: int, min_value: int, max_value: int) -> int:
			try:
				var = getattr(self, name)
				value = int(var.get() if hasattr(var, "get") else var)
			except Exception:
				value = default
			return max(min_value, min(max_value, value))

		paragraphs_per_chunk = _read_int("rag_paragraphs_per_chunk", 4, 1, 12)
		overlap_paragraphs = _read_int("rag_overlap_paragraphs", 1, 0, paragraphs_per_chunk - 1)
		return {
			"max_chars": _read_int("rag_long_paragraph_chars", 800, 200, 4000),
			"overlap_paragraphs": overlap_paragraphs,
			"paragraphs_per_chunk": paragraphs_per_chunk,
		}
	
	def on_ingest_incremental(self) -> None:
		self._run_kb_ingest(rebuild=False)

	def on_ingest_rebuild(self) -> None:
		self._run_kb_ingest(rebuild=True)

	def on_ingest(self) -> None:
		self.on_ingest_rebuild()

	def _run_kb_ingest(self, *, rebuild: bool) -> None:
		data_root = Path(self.data_dir.get())
		if not data_root.exists():
			messagebox.showwarning("\u63d0\u793a", "\u6570\u636e\u76ee\u5f55\u4e0d\u5b58\u5728\uff0c\u8bf7\u5148\u9009\u62e9\u6709\u6548\u7684\u6570\u636e\u76ee\u5f55")
			return
		patterns = ("*.txt", "*.md", "*.markdown", "*.json", "*.csv", "*.docx", "*.pdf")
		if not any(any(data_root.rglob(pattern)) for pattern in patterns):
			messagebox.showwarning("\u63d0\u793a", "\u6570\u636e\u76ee\u5f55\u4e0b\u672a\u53d1\u73b0 .txt/.md/.markdown/.json/.csv/.docx/.pdf \u6587\u4ef6")
			return

		def ui_call(func, *args, **kwargs):
			if hasattr(self, '_ui'):
				return self._ui(func, *args, **kwargs)
			return func(*args, **kwargs)

		def task():
			mode = "\u5b8c\u5168\u91cd\u5efa" if rebuild else "\u589e\u91cf\u66f4\u65b0"
			try:
				ui_call(self.set_busy, True)
				ui_call(self.status.set, f"{mode}\u7d22\u5f15\u4e2d...")
				from src.kb.ingest import IngestConfig, KnowledgeBaseIngestor
				cfg = IngestConfig(
					data_root=Path(self.data_dir.get()),
					index_dir=Path(self.index_dir.get()),
					rebuild=rebuild,
					**self._rag_ingest_kwargs(),
				)
				stats = KnowledgeBaseIngestor(cfg).build()
				summary = stats.summary() if hasattr(stats, "summary") else "\u5df2\u5b8c\u6210"
				ui_call(self.output.insert, END, f"{mode}\u5b8c\u6210\uff1a{summary}\n\u7d22\u5f15\u76ee\u5f55: {self.index_dir.get()}\n")
				ui_call(self.status.set, f"{mode}\u5b8c\u6210")
			except Exception as e:
				brief = str(e).strip() or e.__class__.__name__
				ui_call(self.output.insert, END, f"\u274c \u6784\u5efa\u7d22\u5f15\u5931\u8d25\uff1a{brief}\n")
				ui_call(messagebox.showerror, "\u9519\u8bef", brief)
				ui_call(self.status.set, "\u6784\u5efa\u7d22\u5f15\u5931\u8d25")
			finally:
				ui_call(self.set_busy, False)
		threading.Thread(target=task, daemon=True).start()

	def locate_existing_index(self) -> None:
		"""If current index_dir is a parent, find a v2 Chroma RAG index and switch to it."""
		base = Path(self.index_dir.get())
		if base.is_file():
			base = base.parent
		candidates = list(base.rglob("manifest.json")) + list(base.rglob("chroma"))
		if not candidates:
			messagebox.showinfo("提示", "未在当前索引目录下找到任何 Chroma RAG 索引")
			return
		chosen = candidates[0]
		while chosen.name and chosen.name != "v2" and chosen.parent != chosen:
			chosen = chosen.parent
		chosen = chosen.parent if chosen.name == "v2" else candidates[0].parent
		self.index_dir.set(str(chosen))
		self.output.insert(END, f"已定位到索引目录: {chosen}\n")
		self.status.set("已定位到现有索引")

	def choose_data(self) -> None:
		path = filedialog.askdirectory(initialdir=self.data_dir.get())
		if path:
			self.data_dir.set(path)
			self.status.set("已选择数据目录")

	def choose_library_quick(self) -> None:
		path = filedialog.askdirectory(initialdir=self.data_dir.get())
		if not path:
			return
		self.data_dir.set(path)
		base = Path(path).name
		auto_index = Path.cwd() / "index" / base
		auto_index.mkdir(parents=True, exist_ok=True)
		self.index_dir.set(str(auto_index))
		self.output.insert(END, f"已选择资料库: {path}\n已自动设置索引目录: {auto_index}\n")
		self.status.set("已选择资料库并设置索引目录")

	def choose_index(self) -> None:
		path = filedialog.askdirectory(initialdir=self.index_dir.get())
		if path:
			self.index_dir.set(path)
			self.status.set("已选择索引目录")

	def set_busy(self, busy: bool) -> None:
		state = DISABLED if busy else NORMAL
		self.btn_ingest.configure(state=state)
		self.btn_generate.configure(state=state)
		self.btn_outline.configure(state=state)
		if hasattr(self, 'btn_story_overview'):
			self.btn_story_overview.configure(state=state)
		if hasattr(self, 'btn_test_api'):
			self.btn_test_api.configure(state=state)
		if hasattr(self, 'btn_test_img_api'):
			self.btn_test_img_api.configure(state=state)
		if hasattr(self, 'btn_rebuild_index'):
			self.btn_rebuild_index.configure(state=state)
		if hasattr(self, 'btn_clear'):
			self.btn_clear.configure(state=state)
		if hasattr(self, 'btn_copy'):
			self.btn_copy.configure(state=state)
		# 章节生成按钮
		if hasattr(self, 'btn_generate_section'):
			# 只在有章节数据时才启用
			if busy or not self.parsed_sections:
				self.btn_generate_section.configure(state=DISABLED)
				self.btn_continue_next.configure(state=DISABLED)
				if hasattr(self, 'btn_auto_generate'):
					self.btn_auto_generate.configure(state=DISABLED)
			else:
				self.btn_generate_section.configure(state=NORMAL)
				self.btn_continue_next.configure(state=NORMAL)
				if hasattr(self, 'btn_auto_generate'):
					self.btn_auto_generate.configure(state=NORMAL)
		# Image page controls
		for name in (
			'img_btn_build', 'img_btn_gen', 'img_btn_save', 'img_btn_browse',
			'img_btn_extract', 'img_btn_build_from_shots', 'img_btn_copy', 'img_btn_clear',
			'img_btn_copy_shots', 'img_btn_clear_shots'
		):
			if hasattr(self, name):
				getattr(self, name).configure(state=state)
