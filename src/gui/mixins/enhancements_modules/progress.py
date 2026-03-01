"""Progress dialog helpers extracted from enhancements mixin."""

import logging
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

logger = logging.getLogger(__name__)


class ProgressDialog:
    """Simple modal progress dialog."""

    def __init__(self, parent, title: str = "处理中", message: str = "请稍候..."):
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        width, height = 400, 180
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg="#1e1e1e")

        self.message_var = tk.StringVar(value=message)
        tk.Label(
            self.dialog,
            textvariable=self.message_var,
            bg="#1e1e1e",
            fg="#ffffff",
            font=("", 12),
        ).pack(pady=(30, 15))

        self.progress = ttk.Progressbar(self.dialog, mode="determinate", length=300)
        self.progress.pack(pady=10)

        self.percent_var = tk.StringVar(value="0%")
        tk.Label(
            self.dialog,
            textvariable=self.percent_var,
            bg="#1e1e1e",
            fg="#9CA3AF",
            font=("", 10),
        ).pack(pady=5)

        self.detail_var = tk.StringVar(value="")
        tk.Label(
            self.dialog,
            textvariable=self.detail_var,
            bg="#1e1e1e",
            fg="#6B7280",
            font=("", 9),
        ).pack(pady=5)

        self.dialog.protocol("WM_DELETE_WINDOW", lambda: None)

    def update(self, value: float, message: str = None, detail: str = None):
        self.progress["value"] = value
        self.percent_var.set(f"{int(value)}%")
        if message:
            self.message_var.set(message)
        if detail:
            self.detail_var.set(detail)
        self.dialog.update()

    def set_indeterminate(self, message: str = "处理中..."):
        self.progress.configure(mode="indeterminate")
        self.progress.start(10)
        self.message_var.set(message)
        self.percent_var.set("")
        self.dialog.update()

    def close(self):
        try:
            self.progress.stop()
            self.dialog.destroy()
        except Exception as e:
            logger.debug("close progress dialog failed: %s", e)


class ProgressMixin:
    """Run background tasks with a modal progress indicator."""

    def show_progress(self, title: str = "处理中", message: str = "请稍候...") -> ProgressDialog:
        return ProgressDialog(self, title, message)

    def run_with_progress(
        self,
        func: Callable,
        title: str = "处理中",
        message: str = "请稍候...",
        callback: Callable = None,
    ):
        progress = self.show_progress(title, message)
        progress.set_indeterminate()

        def worker():
            try:
                result = func()
                self.after(0, lambda: self._on_task_complete(progress, result, callback))
            except Exception as e:
                self.after(0, lambda: self._on_task_error(progress, e))

        threading.Thread(target=worker, daemon=True).start()
        return progress

    def _on_task_complete(self, progress: ProgressDialog, result, callback: Callable):
        progress.close()
        if callback:
            callback(result)

    def _on_task_error(self, progress: ProgressDialog, error: Exception):
        progress.close()
        messagebox.showerror("错误", f"操作失败: {error}")
