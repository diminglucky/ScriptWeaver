from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# 组合各功能模块
from src.gui.mixins import ProjectMixin, StoryMixin, ImageMixin, KbMixin, ConfigMixin, UiMixin


class App(tk.Tk, ProjectMixin, StoryMixin, ImageMixin, KbMixin, ConfigMixin, UiMixin):
	"""主窗口：组合所有功能模块。
	说明：尽量保持与原 App 接口一致，便于 run_app.py 直接复用。
	"""
	def __init__(self) -> None:
		super().__init__()
		# 基本窗口属性（原来由 gui_app.py 设置）
		self.title("创作知乎故事 - DeepSeek + 知识库")
		self.geometry("1200x800")
		# 由 UiMixin/_build_ui 等方法构建界面
		self._build_ui()
