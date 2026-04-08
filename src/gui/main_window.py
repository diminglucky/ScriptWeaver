from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from pathlib import Path
import os

try:
	from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
	def load_dotenv(*args, **kwargs):
		return False

# 组合各功能模块
from src.gui.mixins import ProjectMixin, StoryMixin, ImageMixin, KbMixin, ConfigMixin, UiMixin, SettingsMixin
from src.project_manager import ProjectManager
from src.gui.helpers.story_templates import DEFAULT_STORY_TEMPLATE_KEY


class App(tk.Tk, ProjectMixin, StoryMixin, ImageMixin, KbMixin, ConfigMixin, UiMixin, SettingsMixin):
	"""主窗口：组合所有功能模块。
	说明：尽量保持与原 App 接口一致，便于 run_app.py 直接复用。
	"""
	def __init__(self) -> None:
		super().__init__()
		# 基本窗口属性
		self.title("创作知乎故事 - DeepSeek + 知识库")
		self.geometry("1200x800")
		
		# 加载环境变量
		load_dotenv()
		
		# 初始化所有必要的变量
		self._init_variables()
		
		# 由 UiMixin/_build_ui 等方法构建界面
		self._build_ui()
		
		# 启动后自动加载配置
		self.after(100, self._auto_load_api_config)
	
	def _init_variables(self) -> None:
		"""初始化所有必要的状态变量，确保 mixin 依赖的属性存在"""
		# Tkinter 变量 - 状态
		self.status = tk.StringVar(value="就绪")
		
		# 路径相关
		self.data_dir = tk.StringVar(value=str(Path("data").absolute()))
		self.index_dir = tk.StringVar(value=str(Path("index").absolute()))
		
		# 故事创作参数
		self.category = tk.StringVar()
		self.requirement = tk.StringVar()
		self.style = tk.StringVar()
		self.target_chars = tk.IntVar(value=1800)
		template_key = (os.getenv("STORY_TEMPLATE_KEY", "") or "").strip() or DEFAULT_STORY_TEMPLATE_KEY
		self.story_template_key = tk.StringVar(value=template_key)
		
		# 模型参数
		self.top_k = tk.IntVar(value=6)
		self.temperature = tk.DoubleVar(value=0.7)
		self.top_p = tk.DoubleVar(value=0.9)
		self.model_only = tk.BooleanVar(value=False)
		
		# 故事生成功能开关（需在 _build_ui 前初始化）
		self.story_global_overview_enabled = tk.BooleanVar(
			value=os.getenv("STORY_GLOBAL_OVERVIEW_ENABLED", "1").strip().lower() in {"1", "true", "yes", "on"}
		)
		self.story_overview_before_generate = tk.BooleanVar(
			value=os.getenv("STORY_OVERVIEW_BEFORE_GENERATE", "1").strip().lower() in {"1", "true", "yes", "on"}
		)
		self.story_preview_before_apply = tk.BooleanVar(
			value=os.getenv("STORY_PREVIEW_BEFORE_APPLY", "1").strip().lower() in {"1", "true", "yes", "on"}
		)
		self.story_quality_review_enabled = tk.BooleanVar(
			value=os.getenv("STORY_QUALITY_REVIEW_ENABLED", "1").strip().lower() in {"1", "true", "yes", "on"}
		)
		
		# API 配置
		self.api_key = tk.StringVar()
		self.base_url = tk.StringVar(value="https://api.deepseek.com/v1")
		self.model_name = tk.StringVar(value="deepseek-chat")
		self.model = tk.StringVar(value="deepseek-chat")
		self.api_preset = tk.StringVar(value="DeepSeek")
		
		# 辅助功能 API 配置
		self.outline_gen_api = tk.StringVar(value="DeepSeek")
		self.story_gen_api = tk.StringVar(value="DeepSeek")
		
		# 章节选择
		self.current_section_index = tk.IntVar(value=0)
		
		# 项目管理相关
		self.project_manager = ProjectManager()
		self.current_project = None
		
		# 故事生成相关
		self.current_outline: str | None = None
		self.parsed_sections: list[dict] = []
		self.generated_content: str = ""
		
		# 图片生成相关
		self.img_last_image = None
	
	# ========== 线程安全的 UI 更新方法 ==========
	
	def safe_update(self, callback, *args, **kwargs) -> None:
		"""线程安全地执行UI更新"""
		self.after(0, lambda: callback(*args, **kwargs))
	
	def safe_insert_text(self, widget, index, text) -> None:
		"""线程安全地插入文本"""
		self.after(0, lambda: widget.insert(index, text))
	
	def safe_delete_text(self, widget, start, end=None) -> None:
		"""线程安全地删除文本"""
		if end:
			self.after(0, lambda: widget.delete(start, end))
		else:
			self.after(0, lambda: widget.delete(start))
	
	def safe_set_status(self, message: str) -> None:
		"""线程安全地设置状态"""
		self.after(0, lambda: self.status.set(message))
	
	def safe_configure(self, widget, **kwargs) -> None:
		"""线程安全地配置组件"""
		self.after(0, lambda: widget.configure(**kwargs))
	
	def safe_see(self, widget, index) -> None:
		"""线程安全地滚动到指定位置"""
		self.after(0, lambda: widget.see(index))
