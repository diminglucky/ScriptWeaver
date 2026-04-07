"""Base UI helpers for settings page layout."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk

from ...theme import Theme

logger = logging.getLogger(__name__)


class SettingsPageLayoutBaseMixin:
    """Shared low-level layout helpers for settings tabs."""
    def _fix_entry_colors(self, entry_widget):
        """
        修复Entry组件的颜色问题，防止焦点时变成白底白字
        使用短时守护重试，避免长期高频轮询带来的性能负担
        """
        def _apply_dark_colors():
            try:
                entry_widget.config(
                    bg=Theme.BG_TERTIARY, 
                    fg=Theme.TEXT_PRIMARY,
                    insertbackground=Theme.TEXT_PRIMARY,
                    selectbackground=Theme.PRIMARY,
                    selectforeground=Theme.TEXT_PRIMARY,
                    disabledbackground=Theme.BG_TERTIARY,
                    disabledforeground=Theme.TEXT_DISABLED,
                    readonlybackground=Theme.BG_TERTIARY
                )
            except Exception:
                pass  # UI config may fail during widget teardown

        def _cancel_guard(_event=None):
            job = getattr(entry_widget, "_dark_guard_job", None)
            try:
                if job:
                    entry_widget.after_cancel(job)
            except Exception:
                pass  # timer may already be cancelled
            entry_widget._dark_guard_job = None

        def _schedule_guard(retries: int = 10):
            _cancel_guard()
            if retries <= 0:
                return

            def _tick(left: int):
                try:
                    if not entry_widget.winfo_exists():
                        entry_widget._dark_guard_job = None
                        return
                    current_bg = str(entry_widget.cget("bg"))
                    if current_bg != Theme.BG_TERTIARY:
                        _apply_dark_colors()
                    if left > 1:
                        entry_widget._dark_guard_job = entry_widget.after(200, lambda: _tick(left - 1))
                    else:
                        entry_widget._dark_guard_job = None
                except Exception:
                    entry_widget._dark_guard_job = None

            _tick(retries)

        def force_dark_colors(event=None):
            _apply_dark_colors()
            # 在焦点/输入等关键阶段做短时守护，避免长期循环
            _schedule_guard(retries=10)

        # 绑定多个事件，确保颜色在关键交互时恢复
        entry_widget.bind("<FocusIn>", force_dark_colors, add="+")
        entry_widget.bind("<FocusOut>", force_dark_colors, add="+")
        entry_widget.bind("<Button-1>", force_dark_colors, add="+")
        entry_widget.bind("<KeyPress>", force_dark_colors, add="+")
        entry_widget.bind("<KeyRelease>", force_dark_colors, add="+")
        entry_widget.bind("<ButtonRelease-1>", force_dark_colors, add="+")
        entry_widget.bind("<Map>", force_dark_colors, add="+")
        entry_widget.bind("<Destroy>", _cancel_guard, add="+")

        # 初始设置
        force_dark_colors()

    def _make_scroll_tab(self, settings_notebook: ttk.Notebook, title: str):
        """创建带滚动容器的设置页子页，返回内部可放控件的 frame。"""
        tab = tk.Frame(settings_notebook, bg=Theme.BG_SECONDARY)
        settings_notebook.add(tab, text=title)

        canvas = tk.Canvas(tab, bg=Theme.BG_SECONDARY, highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=Theme.BG_SECONDARY)

        inner.bind(
            "<Configure>",
            lambda _e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            if event.delta:
                canvas.yview_scroll(int(-1 * event.delta), "units")
            elif event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

        def _bind_mousewheel_recursive(widget):
            widget.bind("<MouseWheel>", _on_mousewheel)
            widget.bind("<Button-4>", _on_mousewheel)
            widget.bind("<Button-5>", _on_mousewheel)
            for child in widget.winfo_children():
                _bind_mousewheel_recursive(child)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 仅在当前设置页面容器内绑定滚轮，避免污染全局事件绑定。
        _bind_mousewheel_recursive(tab)

        return inner

