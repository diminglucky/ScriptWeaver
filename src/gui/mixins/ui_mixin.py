"""
Ui-related mixin helpers.
"""

import threading
from typing import Optional
import tkinter as tk
from tkinter import BOTH, END, ttk

from ..theme import Theme


class UiMixin:
    """UI helpers and page bootstrap."""

    def _is_output_widget_call(self, func, method_name: str) -> bool:
        widget = getattr(func, "__self__", None)
        if widget is None or widget is not getattr(self, "output", None):
            return False
        return getattr(func, "__name__", "") == method_name

    def _is_output_at_bottom(self) -> bool:
        output = getattr(self, "output", None)
        if output is None or not hasattr(output, "yview"):
            return True
        try:
            return float(output.yview()[1]) >= 0.995
        except Exception:
            return True

    def _output_see_end_if_following(self) -> None:
        output = getattr(self, "output", None)
        if output is None or not hasattr(output, "see"):
            return
        should_follow = bool(getattr(self, "_output_follow_after_insert", False))
        self._output_follow_after_insert = False
        if should_follow or self._is_output_at_bottom():
            output.see(END)

    def _output_insert_preserving_scroll(self, index, text) -> None:
        self._output_follow_after_insert = self._is_output_at_bottom()
        self.output.insert(index, text)

    def _call_with_output_scroll_guard(self, func, *args, **kwargs):
        if self._is_output_widget_call(func, "insert"):
            self._output_follow_after_insert = self._is_output_at_bottom()
            return func(*args, **kwargs)
        if self._is_output_widget_call(func, "see") and args and str(args[0]).lower() == "end":
            self._output_see_end_if_following()
            return None
        return func(*args, **kwargs)

    def _ui(self, func, *args, **kwargs):
        """Run callable on Tk main thread, returning the result."""
        if threading.current_thread() is threading.main_thread():
            return self._call_with_output_scroll_guard(func, *args, **kwargs)

        done = threading.Event()
        state = {"result": None, "error": None}

        def runner():
            try:
                state["result"] = self._call_with_output_scroll_guard(func, *args, **kwargs)
            except Exception as e:  # pragma: no cover - UI callback surface
                state["error"] = e
            finally:
                done.set()

        self.after(0, runner)
        if not done.wait(timeout=30):
            raise TimeoutError("UI thread execution timed out")
        if state["error"] is not None:
            raise state["error"]
        return state["result"]

    def _ui_get(self, func, *args, **kwargs):
        """Read UI state safely from worker threads."""
        return self._ui(func, *args, **kwargs)

    def _ui_modal(self, func, *args, **kwargs):
        """Run long-lived modal UI call on Tk main thread without 30s timeout."""
        if threading.current_thread() is threading.main_thread():
            return func(*args, **kwargs)

        done = threading.Event()
        state = {"result": None, "error": None}

        def runner():
            try:
                state["result"] = func(*args, **kwargs)
            except Exception as e:  # pragma: no cover - UI callback surface
                state["error"] = e
            finally:
                done.set()

        self.after(0, runner)
        done.wait()
        if state["error"] is not None:
            raise state["error"]
        return state["result"]

    def _header_status(self, text: str, icon: str = "🔄", color: Optional[str] = None):
        """Thread-safe wrapper for top header status updates."""
        if not hasattr(self, "update_header_status"):
            return
        if color is None:
            self._ui(self.update_header_status, text, icon)
            return
        self._ui(self.update_header_status, text, icon, color)

    def _build_ui(self) -> None:
        # Pages container with styled notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=BOTH, expand=True, padx=10, pady=(10, 8))

        self.page_project = tk.Frame(self.notebook, bg=Theme.BG_SECONDARY)
        self.page_story = tk.Frame(self.notebook, bg=Theme.BG_SECONDARY)
        self.page_image = tk.Frame(self.notebook, bg=Theme.BG_SECONDARY)
        self.page_director = tk.Frame(self.notebook, bg=Theme.BG_SECONDARY)
        self.page_settings = tk.Frame(self.notebook, bg=Theme.BG_SECONDARY)

        self.notebook.add(self.page_project, text="  📁 项目管理  ")
        self.notebook.add(self.page_story, text="  📝 故事生成  ")
        self.notebook.add(self.page_image, text="  🎨 图片生成  ")
        self.notebook.add(self.page_director, text="  🎞️ 导演  ")
        self.notebook.add(self.page_settings, text="  ⚙️ 设置  ")

        # Build pages
        self._build_project_page()
        self._build_story_page()
        self._build_image_page()
        if hasattr(self, "_build_director_page"):
            self._build_director_page()
        self._build_settings_page()

    def _clear_prompt_placeholder(self, event=None) -> None:
        content = self.prompt_text.get("1.0", "end-1c")
        if "例如：" in content:
            self.prompt_text.delete("1.0", END)
            self.prompt_text.tag_remove("placeholder", "1.0", "end")

    def _restore_prompt_placeholder(self, event=None) -> None:
        content = self.prompt_text.get("1.0", "end-1c").strip()
        if not content:
            self.prompt_text.insert("1.0", "例如：写一个惊悚短篇，要求特别惊奇感人，跌宕起伏...")
            self.prompt_text.tag_add("placeholder", "1.0", "end")

    def _get_prompt_content(self) -> str:
        content = self.prompt_text.get("1.0", "end-1c").strip()
        if "例如：" in content and "placeholder" in str(self.prompt_text.tag_names("1.0")):
            return ""
        return content

    def open_image_window(self) -> None:
        # switch to image page instead of popup
        if hasattr(self, "notebook") and hasattr(self, "page_image"):
            self.notebook.select(self.page_image)
