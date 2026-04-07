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
	
	def on_ingest(self) -> None:
		# Preflight
		if not Path(self.data_dir.get()).exists():
			messagebox.showwarning("提示", "数据目录不存在，请先选择有效的数据目录")
			return
		if (
			not any(Path(self.data_dir.get()).rglob("*.txt"))
			and not any(Path(self.data_dir.get()).rglob("*.md"))
			and not any(Path(self.data_dir.get()).rglob("*.markdown"))
			and not any(Path(self.data_dir.get()).rglob("*.json"))
			and not any(Path(self.data_dir.get()).rglob("*.csv"))
			and not any(Path(self.data_dir.get()).rglob("*.docx"))
			and not any(Path(self.data_dir.get()).rglob("*.pdf"))
		):
			messagebox.showwarning("提示", "数据目录下未发现 .txt/.md/.markdown/.json/.csv/.docx/.pdf 文件")
			return
		def ui_call(func, *args, **kwargs):
			if hasattr(self, '_ui'):
				return self._ui(func, *args, **kwargs)
			return func(*args, **kwargs)
		def task():
			try:
				ui_call(self.set_busy, True)
				ui_call(self.status.set, "构建索引中...")
				from src.kb.ingest import IngestConfig, KnowledgeBaseIngestor
				cfg = IngestConfig(data_root=Path(self.data_dir.get()), index_dir=Path(self.index_dir.get()))
				KnowledgeBaseIngestor(cfg).build()
				ui_call(self.output.insert, END, f"索引已生成: {self.index_dir.get()}\n")
				ui_call(self.status.set, "索引已生成")
			except Exception as e:
				brief = str(e).strip() or e.__class__.__name__
				ui_call(self.output.insert, END, f"❌ 构建索引失败：{brief}\n")
				ui_call(messagebox.showerror, "错误", brief)
				ui_call(self.status.set, "构建索引失败")
			finally:
				ui_call(self.set_busy, False)
		threading.Thread(target=task, daemon=True).start()

	def locate_existing_index(self) -> None:
		"""If current index_dir is a parent, find first child that contains kb.index and switch to it."""
		base = Path(self.index_dir.get())
		if base.is_file():
			base = base.parent
		candidates = list(base.rglob("kb.index"))
		if not candidates:
			messagebox.showinfo("提示", "未在当前索引目录下找到任何 kb.index")
			return
		chosen = candidates[0].parent
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
