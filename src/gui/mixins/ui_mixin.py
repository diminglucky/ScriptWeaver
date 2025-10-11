"""
Ui相关功能模块
"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, messagebox, filedialog
import tkinter as tk
from tkinter import ttk


class UiMixin:
    """Ui管理功能"""
    
    def _build_ui(self) -> None:
        # Pages container with styled notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=BOTH, expand=True, padx=10, pady=(10, 8))
        
        self.page_project = tk.Frame(self.notebook, bg="#2b2b2b")
        self.page_story = tk.Frame(self.notebook, bg="#2b2b2b")
        self.page_image = tk.Frame(self.notebook, bg="#2b2b2b")
        self.notebook.add(self.page_project, text="  📁 项目管理  ")
        self.notebook.add(self.page_story, text="  📝 故事生成  ")
        self.notebook.add(self.page_image, text="  🎨 图片生成  ")
        
        # Build pages
        self._build_project_page()
        self._build_story_page()
        self._build_image_page()
    
    def _clear_prompt_placeholder(self, event=None) -> None:
        """清除占位符"""
        content = self.prompt_text.get("1.0", "end-1c")
        if "例如：" in content:
            self.prompt_text.delete("1.0", END)
            self.prompt_text.tag_remove("placeholder", "1.0", "end")
    
    def _restore_prompt_placeholder(self, event=None) -> None:
        """恢复占位符"""
        content = self.prompt_text.get("1.0", "end-1c").strip()
        if not content:
            self.prompt_text.insert("1.0", "例如：写一个惊悚短篇，要求特别惊奇感人，跌宕起伏...")
            self.prompt_text.tag_add("placeholder", "1.0", "end")
    
    def _get_prompt_content(self) -> str:
        """获取创作需求内容（过滤占位符）"""
        content = self.prompt_text.get("1.0", "end-1c").strip()
        if "例如：" in content and "placeholder" in str(self.prompt_text.tag_names("1.0")):
            return ""
        return content

    def open_image_window(self) -> None:
        # switch to image page instead of popup
        if hasattr(self, 'notebook') and hasattr(self, 'page_image'):
            self.notebook.select(self.page_image)


