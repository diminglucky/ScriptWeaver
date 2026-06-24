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
import tkinter.font as tkfont
from tkinter import messagebox, scrolledtext
from typing import Callable, Optional

from src.utils.text import sanitize as _sanitize

logger = logging.getLogger(__name__)


def _font(family: str, size: int, weight: str = "normal") -> tkfont.Font:
    """Use an explicit CJK-capable font so Text line metrics stay readable."""
    return tkfont.Font(family=family, size=size, weight=weight)


def _plain_inline_markdown(text: str) -> str:
    """Remove common inline Markdown markers from generated story plans."""
    clean = str(text or "").strip()
    for marker in ("**", "__", "`"):
        clean = clean.replace(marker, "")
    return clean


def _iter_readable_story_segments(text: str) -> list[tuple[str, str]]:
    """Convert simple Markdown-like story output into readable text segments."""
    segments: list[tuple[str, str]] = []
    for raw_line in str(text or "").strip().splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line in {"---", "——", "***"}:
            segments.append(("separator", ""))
            continue
        if line.startswith("### "):
            segments.append(("h3", _plain_inline_markdown(line[4:])))
            continue
        if line.startswith("## "):
            segments.append(("h2", _plain_inline_markdown(line[3:])))
            continue
        if line.startswith("# "):
            segments.append(("h1", _plain_inline_markdown(line[2:])))
            continue
        if line.startswith(("- ", "* ")):
            segments.append(("list", "• " + _plain_inline_markdown(line[2:])))
            continue

        segments.append(("body", _plain_inline_markdown(line)))
    return segments


def _insert_readable_story_text(widget: tk.Text, text: str) -> None:
    """Insert story overview text with lightweight visual formatting."""
    segments = _iter_readable_story_segments(text)
    for kind, value in segments:
        if kind == "separator":
            widget.insert("end", "─" * 28 + "\n", "md_separator")
        else:
            widget.insert("end", value + "\n", f"md_{kind}")


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
    dialog.configure(bg="#f5f5f5")
    dialog.grid_columnconfigure(0, weight=1)
    dialog.grid_rowconfigure(1, weight=1)

    ui_font = "Microsoft YaHei UI"
    title_font = _font(ui_font, 13, "bold")
    subtitle_font = _font(ui_font, 10)
    body_font = _font(ui_font, 11)
    h1_font = _font(ui_font, 15, "bold")
    h2_font = _font(ui_font, 13, "bold")
    h3_font = _font(ui_font, 12, "bold")
    feedback_font = _font(ui_font, 10)
    label_font = _font(ui_font, 10, "bold")

    # --- header ---
    header = tk.Frame(dialog, bg="#f5f5f5")
    header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))
    tk.Label(
        header,
        text=header_text,
        bg="#f5f5f5",
        fg="#1f2937",
        font=title_font,
        anchor="w",
    ).pack(fill="x")
    tk.Label(
        header,
        text=subtitle_text,
        bg="#f5f5f5",
        fg="#4b5563",
        font=subtitle_font,
        anchor="w",
    ).pack(fill="x", pady=(4, 0))

    # --- editor ---
    editor = scrolledtext.ScrolledText(
        dialog,
        wrap="word",
        height=12,
        font=body_font,
        bg="#ffffff",
        fg="#111827",
        insertbackground="#111827",
        relief=tk.FLAT,
        padx=12,
        pady=10,
        spacing1=4,
        spacing2=2,
        spacing3=8,
    )
    editor.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
    editor.tag_configure("md_h1", font=h1_font, foreground="#111827", spacing1=6, spacing3=3)
    editor.tag_configure("md_h2", font=h2_font, foreground="#1f2937", spacing1=7, spacing3=3)
    editor.tag_configure("md_h3", font=h3_font, foreground="#374151", spacing1=5, spacing3=2)
    editor.tag_configure("md_body", font=body_font, foreground="#111827", spacing1=1, spacing3=3, lmargin1=0, lmargin2=0)
    editor.tag_configure("md_list", font=body_font, foreground="#111827", spacing1=1, spacing3=2, lmargin1=20, lmargin2=20)
    editor.tag_configure("md_separator", foreground="#d1d5db", spacing1=5, spacing3=4)
    _insert_readable_story_text(editor, result["content"])
    if editor_readonly:
        editor.configure(state="disabled")

    footer = tk.Frame(dialog, bg="#f5f5f5")
    footer.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
    footer.grid_columnconfigure(0, weight=1)
    footer_row = 0

    # --- feedback (only shown when regeneration is available) ---
    feedback_box = None
    if regenerate_fn is not None:
        feedback_frame = tk.Frame(footer, bg="#f5f5f5")
        feedback_frame.grid(row=footer_row, column=0, sticky="ew", pady=(0, 6))
        feedback_frame.grid_columnconfigure(0, weight=1)
        tk.Label(
            feedback_frame,
            text="修改意见：",
            bg="#f5f5f5",
            fg="#1f2937",
            font=label_font,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))
        feedback_box = scrolledtext.ScrolledText(
            feedback_frame,
            wrap="word",
            height=3,
            font=feedback_font,
            bg="#ffffff",
            fg="#111827",
            insertbackground="#111827",
            relief=tk.FLAT,
            padx=10,
            pady=8,
            spacing1=2,
            spacing2=1,
            spacing3=5,
        )
        feedback_box.grid(row=1, column=0, sticky="ew")
        footer_row += 1

    # --- status ---
    status_var = tk.StringVar(value=default_status or "可多次重生成，直到满意后再采用。")
    tk.Label(
        footer,
        textvariable=status_var,
        bg="#f5f5f5",
        fg="#4b5563",
        font=subtitle_font,
        anchor="w",
    ).grid(row=footer_row, column=0, sticky="ew", pady=(0, 8))
    footer_row += 1

    # --- buttons ---
    action_row = tk.Frame(footer, bg="#f5f5f5")
    action_row.grid(row=footer_row, column=0, sticky="ew")
    busy = {"flag": False}
    regen_round = {"count": 0}

    def _set_editor_text(text: str) -> None:
        if editor_readonly:
            editor.configure(state="normal")
        editor.delete("1.0", "end")
        _insert_readable_story_text(editor, text)
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
        bg="#dcfce7",
        fg="#166534",
        activebackground="#bbf7d0",
        activeforeground="#14532d",
        disabledforeground="#6b7280",
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
        bg="#f3f4f6",
        fg="#374151",
        activebackground="#e5e7eb",
        activeforeground="#111827",
        disabledforeground="#9ca3af",
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
            bg="#dbeafe",
            fg="#1d4ed8",
            activebackground="#bfdbfe",
            activeforeground="#1e3a8a",
            disabledforeground="#6b7280",
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
