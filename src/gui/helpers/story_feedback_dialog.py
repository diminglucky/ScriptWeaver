"""Reusable modal feedback dialog for story generation workflows.

Consolidates the shared UI pattern from:
- _show_story_global_overview_dialog  (~190 lines)
- _show_section_overview_dialog       (~190 lines)
- _show_story_section_preview_dialog  (~210 lines)

All three use identical structure:
  header + editor + feedback_box + status_label + 3 buttons + regenerate worker
"""

from __future__ import annotations

import logging
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext
from typing import Callable, Optional

from src.utils.text import sanitize as _sanitize

logger = logging.getLogger(__name__)


def show_story_feedback_dialog(
    parent,
    *,
    title: str,
    header_text: str,
    subtitle_text: str,
    initial_content: str,
    default_status: str = "",
    geometry: str = "960x720",
    min_size: tuple = (760, 560),
    accept_label: str = "✅ 采用",
    discard_label: str = "❌ 取消",
    regen_label: Optional[str] = "🔄 重生成（可多次）",
    editor_readonly: bool = False,
    regenerate_fn: Optional[Callable[[str, str], str]] = None,
) -> tuple[str, str]:
    """Show a modal feedback dialog with editor, feedback box, and regenerate support.

    Args:
        parent: Tk parent widget.
        title: Window title.
        header_text: Bold header line.
        subtitle_text: Smaller subtitle.
        initial_content: Text to pre-fill in the editor.
        default_status: Initial status bar message.
        geometry: Window geometry string.
        min_size: (width, height) minimum size.
        accept_label: Text for the accept button.
        discard_label: Text for the discard button.
        regen_label: Text for the regenerate button.
        editor_readonly: If True, editor is read-only (preview mode).
        regenerate_fn: Callable(current_text, feedback) -> new_text.
            Called in a background thread. If None, regen button is hidden.

    Returns:
        (action, content) where action is 'accept' or 'discard'.
    """
    result = {"action": "discard", "content": str(initial_content or "").strip()}

    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.geometry(geometry)
    dialog.minsize(*min_size)

    # --- header ---
    header = tk.Frame(dialog, bg="#f5f5f5")
    header.pack(fill="x", padx=12, pady=(12, 8))
    tk.Label(
        header,
        text=header_text,
        bg="#f5f5f5",
        fg="#1f2937",
        font=("", 13, "bold"),
        anchor="w",
    ).pack(fill="x")
    tk.Label(
        header,
        text=subtitle_text,
        bg="#f5f5f5",
        fg="#4b5563",
        anchor="w",
    ).pack(fill="x", pady=(4, 0))

    # --- editor ---
    editor = scrolledtext.ScrolledText(
        dialog,
        wrap="word",
        font=("", 12),
        bg="#ffffff",
        fg="#111827",
        insertbackground="#111827",
        relief=tk.FLAT,
    )
    editor.pack(fill="both", expand=True, padx=12, pady=(0, 8))
    editor.insert("1.0", result["content"])
    if editor_readonly:
        editor.configure(state="disabled")

    # --- feedback (only shown when regeneration is available) ---
    feedback_box = None
    if regenerate_fn is not None:
        feedback_frame = tk.Frame(dialog, bg="#f5f5f5")
        feedback_frame.pack(fill="x", padx=12, pady=(0, 6))
        tk.Label(
            feedback_frame,
            text="修改意见：",
            bg="#f5f5f5",
            fg="#1f2937",
            font=("", 10, "bold"),
            anchor="w",
        ).pack(anchor="w", pady=(0, 4))
        feedback_box = scrolledtext.ScrolledText(
            feedback_frame,
            wrap="word",
            height=4,
            font=("", 11),
            bg="#ffffff",
            fg="#111827",
            insertbackground="#111827",
            relief=tk.FLAT,
        )
        feedback_box.pack(fill="x")

    # --- status ---
    status_var = tk.StringVar(value=default_status or "可多次重生成，直到满意后再采用。")
    tk.Label(
        dialog,
        textvariable=status_var,
        bg="#f5f5f5",
        fg="#4b5563",
        anchor="w",
    ).pack(fill="x", padx=12, pady=(0, 8))

    # --- buttons ---
    action_row = tk.Frame(dialog, bg="#f5f5f5")
    action_row.pack(fill="x", padx=12, pady=(0, 12))
    busy = {"flag": False}
    regen_round = {"count": 0}

    def _set_editor_text(text: str) -> None:
        if editor_readonly:
            editor.configure(state="normal")
        editor.delete("1.0", "end")
        editor.insert("1.0", text)
        if editor_readonly:
            editor.configure(state="disabled")

    def _set_busy(flag: bool, message: str = "") -> None:
        busy["flag"] = flag
        state = tk.DISABLED if flag else tk.NORMAL
        btn_apply.configure(state=state)
        btn_discard.configure(state=state)
        if btn_regen is not None:
            btn_regen.configure(state=state)
        if message:
            status_var.set(message)

    def _accept():
        if busy["flag"]:
            return
        if editor_readonly:
            merged = result["content"]
        else:
            merged = str(editor.get("1.0", "end-1c") or "").strip()
        if not merged:
            messagebox.showwarning("提示", "内容为空，请先生成或补充后再采用。")
            return
        result["action"] = "accept"
        result["content"] = merged
        dialog.destroy()

    def _discard():
        if busy["flag"]:
            return
        result["action"] = "discard"
        dialog.destroy()

    def _regenerate():
        if busy["flag"] or regenerate_fn is None:
            return
        if editor_readonly:
            current_text = str(result.get("content", "") or "").strip()
        else:
            current_text = str(editor.get("1.0", "end-1c") or "").strip()
        if not current_text:
            messagebox.showwarning("提示", "当前内容为空，无法重生成。")
            return
        feedback = str(feedback_box.get("1.0", "end-1c") or "").strip()
        _set_busy(
            True,
            "正在根据你的意见重生成..." if feedback else "正在重生成一个新版本...",
        )

        def _worker():
            err = ""
            new_text = current_text
            try:
                new_text = regenerate_fn(current_text, feedback)
            except Exception as exc:
                err = _sanitize(str(exc)) or exc.__class__.__name__

            def _finish():
                _set_busy(False)
                if err:
                    status_var.set(f"重生成失败：{err}")
                    messagebox.showerror("重生成失败", err)
                    return
                merged = str(new_text or "").strip()
                if not merged:
                    status_var.set("重生成结果为空，已保留原内容。")
                    return
                regen_round["count"] += 1
                result["content"] = merged
                _set_editor_text(merged)
                status_var.set(f"已生成第 {regen_round['count']} 个新版本，可继续调整或直接采用。")

            dialog.after(0, _finish)

        threading.Thread(target=_worker, daemon=True).start()

    btn_apply = tk.Button(
        action_row,
        text=accept_label,
        command=_accept,
        bg="#16a34a",
        fg="#ffffff",
        relief=tk.FLAT,
        padx=16,
        pady=8,
        cursor="hand2",
    )
    btn_apply.pack(side="right")
    btn_discard = tk.Button(
        action_row,
        text=discard_label,
        command=_discard,
        bg="#6b7280",
        fg="#ffffff",
        relief=tk.FLAT,
        padx=16,
        pady=8,
        cursor="hand2",
    )
    btn_discard.pack(side="right", padx=(0, 10))

    btn_regen = None
    if regenerate_fn is not None:
        btn_regen = tk.Button(
            action_row,
            text=regen_label,
            command=_regenerate,
            bg="#2563eb",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=16,
            pady=8,
            cursor="hand2",
        )
        btn_regen.pack(side="right", padx=(0, 10))

    dialog.protocol("WM_DELETE_WINDOW", _discard)
    dialog.transient(parent)
    dialog.grab_set()
    parent.wait_window(dialog)
    return str(result.get("action", "discard")), str(result.get("content", "") or "").strip()
