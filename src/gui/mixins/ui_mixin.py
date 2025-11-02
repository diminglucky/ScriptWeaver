"""
Ui相关功能模块
"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, messagebox, filedialog
import tkinter as tk
from tkinter import ttk
from ..theme import Theme


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
        
        # 添加导演页面
        if hasattr(self, '_build_director_page'):
            self._build_director_page()
    
    def _clear_prompt_placeholder(self, event=None) -> None:
        """清除占位符（当获得焦点或开始输入时）"""
        if not hasattr(self, 'prompt_text'):
            return
        
        content = self.prompt_text.get("1.0", "end-1c")
        
        # 检查是否是占位符（多种占位符格式）
        is_placeholder = False
        if content:
            # 检查是否有placeholder标签
            tags = self.prompt_text.tag_names("1.0")
            if "placeholder" in tags:
                is_placeholder = True
            # 检查常见占位符文本
            placeholder_texts = [
                "例如：",
                "📝 请详细描述你的故事创意",
                "请详细描述你的故事创意",
                "写一个惊悚短篇"
            ]
            for placeholder in placeholder_texts:
                if placeholder in content and len(content) < 300:  # 占位符通常较短
                    is_placeholder = True
                    break
        
        # 如果是占位符，清除它
        if is_placeholder:
            self.prompt_text.delete("1.0", END)
            self.prompt_text.tag_remove("placeholder", "1.0", "end")
            self.prompt_text.config(fg=Theme.TEXT_PRIMARY)  # 恢复正常文本颜色（使用主题色）
    
    def _on_prompt_key_press(self, event=None) -> None:
        """处理键盘输入事件 - 首次输入时清除占位符"""
        if not hasattr(self, 'prompt_text'):
            return
        
        # 检查是否是占位符
        content = self.prompt_text.get("1.0", "end-1c")
        is_placeholder = False
        
        if content:
            tags = self.prompt_text.tag_names("1.0")
            if "placeholder" in tags:
                is_placeholder = True
            else:
                # 检查常见占位符文本
                placeholder_texts = [
                    "例如：",
                    "📝 请详细描述你的故事创意",
                    "请详细描述你的故事创意",
                    "写一个惊悚短篇"
                ]
                for placeholder in placeholder_texts:
                    if placeholder in content and len(content) < 300:
                        is_placeholder = True
                        break
        
        # 如果是占位符且用户开始输入（可打印字符），清除占位符
        if is_placeholder and event:
            # 检查是否是可打印字符（不是控制键）
            if event.char and len(event.char) > 0 and event.char.isprintable():
                # 清除占位符
                self.prompt_text.delete("1.0", END)
                self.prompt_text.tag_remove("placeholder", "1.0", "end")
                self.prompt_text.config(fg=Theme.TEXT_PRIMARY)  # 恢复正常文本颜色（使用主题色）
                # 插入用户输入的字符（从开头插入，因为已经清空了）
                self.prompt_text.insert("1.0", event.char)
                # 移动光标到插入的字符之后
                self.prompt_text.mark_set("insert", "1.1")
                # 阻止默认处理（避免重复插入）
                return "break"
            # 如果是删除键（Backspace/Delete），也清除占位符
            elif event.keysym in ("BackSpace", "Delete"):
                if is_placeholder:
                    self.prompt_text.delete("1.0", END)
                    self.prompt_text.tag_remove("placeholder", "1.0", "end")
                    self.prompt_text.config(fg=Theme.TEXT_PRIMARY)  # 恢复正常文本颜色（使用主题色）
                    return "break"
    
    def _restore_prompt_placeholder(self, event=None) -> None:
        """恢复占位符（失去焦点且内容为空时）"""
        if not hasattr(self, 'prompt_text'):
            return
        
        content = self.prompt_text.get("1.0", "end-1c").strip()
        if not content:
            placeholder_text = "📝 请详细描述你的故事创意...\n\n💡 提示：你可以输入：\n· 故事主题和关键情节\n· 人物设定和性格特点\n· 故事背景和时代环境\n· 特殊的叙事要求或风格\n\n✨ 越详细的描述，生成的故事越符合你的期望！"
            self.prompt_text.delete("1.0", END)
            self.prompt_text.insert("1.0", placeholder_text)
            self.prompt_text.tag_add("placeholder", "1.0", "end")
            self.prompt_text.config(fg=Theme.TEXT_HINT)  # 使用主题的提示文本颜色
    
    def _get_prompt_content(self) -> str:
        """获取创作需求内容（过滤占位符）"""
        if not hasattr(self, 'prompt_text'):
            return ""
        
        content = self.prompt_text.get("1.0", "end-1c").strip()
        
        # 检查是否是占位符
        is_placeholder = False
        
        # 检查是否有placeholder标签
        tags = self.prompt_text.tag_names("1.0")
        if "placeholder" in tags:
            is_placeholder = True
        else:
            # 检查常见占位符文本
            placeholder_texts = [
                "例如：",
                "📝 请详细描述你的故事创意",
                "请详细描述你的故事创意",
                "写一个惊悚短篇"
            ]
            for placeholder in placeholder_texts:
                if placeholder in content and len(content) < 300:
                    is_placeholder = True
                    break
        
        # 如果是占位符，返回空字符串
        if is_placeholder:
            return ""
        
        return content

    def open_image_window(self) -> None:
        # switch to image page instead of popup
        if hasattr(self, 'notebook') and hasattr(self, 'page_image'):
            self.notebook.select(self.page_image)


