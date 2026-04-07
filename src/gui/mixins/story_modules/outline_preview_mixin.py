"""Section preview dialog before applying generated content.

Extracted from outline_section_generate_mixin.py to reduce file size.
"""

from tkinter import END, messagebox, scrolledtext
import logging, os, re, threading
import tkinter as tk

from src.utils.text import sanitize as _sanitize
from src.gui.helpers.story_quality import extract_last_sentence, strip_duplicate_lines

logger = logging.getLogger(__name__)

class OutlinePreviewMixin:
    """Preview generated section content before final apply."""

    def _is_story_preview_before_apply_enabled(self) -> bool:
        """Whether to preview chapter content before final apply/save."""
        val = getattr(self, "story_preview_before_apply", None)
        if hasattr(val, "get"):
            try:
                return bool(val.get())
            except Exception:
                pass
        raw = str(os.getenv("STORY_PREVIEW_BEFORE_APPLY", "1") or "1").strip().lower()
        return raw in {"1", "true", "yes", "on"}

    def _preview_generated_section_before_apply(
        self,
        *,
        client,
        section_index: int,
        total_sections: int,
        section_title: str,
        section_content: str,
        requirement: str,
        category: str,
        previous_content: str,
    ) -> tuple[str, str]:
        """Show modal preview and return (`accept|discard`, effective content)."""
        if not self._is_story_preview_before_apply_enabled():
            return "accept", str(section_content or "").strip()
        return self._run_modal_ui_call(
            self._show_story_section_preview_dialog,
            client=client,
            section_index=section_index,
            total_sections=total_sections,
            section_title=section_title,
            section_content=section_content,
            requirement=requirement,
            category=category,
            previous_content=previous_content,
        )

    def _regenerate_section_preview_with_feedback(
        self,
        *,
        client,
        section_index: int,
        section_title: str,
        current_content: str,
        feedback: str,
        requirement: str,
        category: str,
        previous_content: str,
    ) -> str:
        """Regenerate chapter preview text from user feedback while keeping continuity."""
        current = str(current_content or "").strip()
        user_feedback = str(feedback or "").strip()
        if not current:
            return current

        try:
            temperature = float(self.temperature.get())
        except Exception:
            temperature = 0.65
        temperature = max(0.35, min(0.9, temperature))

        prev_tail = ""
        transition_context = ""
        memory_context = ""
        try:
            idx = int(section_index)
        except Exception:
            idx = 0
        if idx > 0:
            prev_tail = extract_last_sentence(previous_content or "", max_chars=260)
            if hasattr(self, "_build_section_transition_context"):
                try:
                    transition_context = str(
                        self._build_section_transition_context(section_index, previous_content) or ""
                    ).strip()
                except Exception:
                    transition_context = ""
            if hasattr(self, "_build_story_memory_context"):
                try:
                    memory_context = str(
                        self._build_story_memory_context(section_index, max_items=3) or ""
                    ).strip()
                except Exception:
                    memory_context = ""

        continuity_lines: list[str] = []
        if prev_tail:
            continuity_lines.append(f"- 上章收束句：{prev_tail}")
        if transition_context:
            continuity_lines.append(f"【跨章衔接线索】\n{transition_context}")
        if memory_context:
            continuity_lines.append(
                "【记忆账本】\n"
                f"{memory_context}\n"
                "- 人物关系、事实设定、未回收伏笔必须保持一致。"
            )
        continuity_block = ("\n\n".join(continuity_lines)).strip() if continuity_lines else "无"

        prompt = (
            "你是中文小说编辑。请根据“用户修改意见”重写当前章节预览。\n"
            "要求：\n"
            "1) 必须落实用户意见，允许调整表达与细节；\n"
            "2) 不改变章节主线事件，不新增章节标题；\n"
            "3) 与前文保持连续，不要与既有设定冲突；\n"
            "4) 仅输出重写后的章节正文。\n\n"
            f"章节标题：{section_title}\n"
            f"主题需求：{requirement}\n"
            f"题材：{category}\n"
            "用户修改意见："
            f"{user_feedback if user_feedback else '（未填写意见）请在保持主线和设定一致前提下，换一种节奏与措辞，生成一个明显不同但同质量的新版本。'}\n\n"
            f"连贯性资料：\n{continuity_block}\n\n"
            f"当前预览正文：\n{current}\n"
        )
        max_tokens = max(1200, min(8192, int(len(current) * 2.8)))
        rewritten = client.chat(
            [{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        ).strip()
        if not rewritten:
            return current
        rewritten = re.sub(r"^\s*【?第.*?章[：:】]\s*", "", rewritten).strip()
        rewritten = strip_duplicate_lines(rewritten)
        if len(rewritten) < max(40, int(len(current) * 0.45)):
            return current
        return rewritten

    def _show_story_section_preview_dialog(
        self,
        *,
        client,
        section_index: int,
        total_sections: int,
        section_title: str,
        section_content: str,
        requirement: str,
        category: str,
        previous_content: str,
    ) -> tuple[str, str]:
        """Modal preview dialog that supports feedback-based regeneration."""
        result = {"action": "discard", "content": str(section_content or "").strip()}
        dialog = tk.Toplevel(self)
        dialog.title(f"章节预览 - 第 {section_index + 1}/{total_sections} 章")
        dialog.geometry("1020x780")
        dialog.minsize(760, 560)

        header = tk.Frame(dialog, bg="#f5f5f5")
        header.pack(fill="x", padx=12, pady=(12, 8))
        tk.Label(
            header,
            text=f"《{section_title or '未命名章节'}》预览",
            bg="#f5f5f5",
            fg="#1f2937",
            font=("", 13, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            header,
            text=f"字数：{len((section_content or '').strip())} 字 | 确认后才会入稿保存",
            bg="#f5f5f5",
            fg="#4b5563",
            anchor="w",
        ).pack(fill="x", pady=(4, 0))

        tips = tk.Frame(dialog, bg="#f5f5f5")
        tips.pack(fill="x", padx=12, pady=(0, 8))
        tk.Label(
            tips,
            text="不满意可反复点“重生成预览”（可不填意见）；填意见会按你的要求改写。确认后后续章节按该版本衔接。",
            bg="#f5f5f5",
            fg="#6b7280",
            anchor="w",
        ).pack(fill="x")

        editor = scrolledtext.ScrolledText(
            dialog,
            wrap="word",
            font=("", 12),
            bg="#ffffff",
            fg="#111827",
            insertbackground="#111827",
            relief=tk.FLAT,
        )
        editor.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        editor.insert("1.0", result["content"])
        editor.configure(state="disabled")

        feedback_frame = tk.Frame(dialog, bg="#f5f5f5")
        feedback_frame.pack(fill="x", padx=12, pady=(0, 8))
        tk.Label(
            feedback_frame,
            text="修改意见：",
            bg="#f5f5f5",
            fg="#1f2937",
            anchor="w",
            font=("", 10, "bold"),
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

        status_var = tk.StringVar(value="可多次重生成预览，直到满意后再采用。")
        tk.Label(
            dialog,
            textvariable=status_var,
            bg="#f5f5f5",
            fg="#4b5563",
            anchor="w",
        ).pack(fill="x", padx=12, pady=(0, 8))

        action_row = tk.Frame(dialog, bg="#f5f5f5")
        action_row.pack(fill="x", padx=12, pady=(0, 12))
        busy = {"flag": False}
        regen_round = {"count": 0}

        def _set_preview_text(text: str) -> None:
            editor.configure(state="normal")
            editor.delete("1.0", "end")
            editor.insert("1.0", text)
            editor.configure(state="disabled")

        def _set_busy(flag: bool, message: str = "") -> None:
            busy["flag"] = flag
            state = tk.DISABLED if flag else tk.NORMAL
            btn_apply.configure(state=state)
            btn_discard.configure(state=state)
            btn_regen.configure(state=state)
            if message:
                status_var.set(message)

        def _apply():
            if busy["flag"]:
                return
            result["action"] = "accept"
            result["content"] = str(result.get("content", "") or "").strip()
            dialog.destroy()

        def _discard():
            if busy["flag"]:
                return
            result["action"] = "discard"
            dialog.destroy()

        def _regenerate():
            if busy["flag"]:
                return
            feedback = str(feedback_box.get("1.0", "end-1c") or "").strip()
            current_preview = str(result.get("content", "") or "").strip()
            if not current_preview:
                messagebox.showwarning("提示", "当前预览为空，无法重生成。")
                return

            _set_busy(
                True,
                "正在根据你的意见重生成预览..."
                if feedback
                else "正在重生成一个新版本预览...",
            )

            def _worker():
                err = ""
                new_text = current_preview
                try:
                    new_text = self._regenerate_section_preview_with_feedback(
                        client=client,
                        section_index=section_index,
                        section_title=section_title,
                        current_content=current_preview,
                        feedback=feedback,
                        requirement=requirement,
                        category=category,
                        previous_content=previous_content,
                    )
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
                        status_var.set("重生成结果为空，已保留原预览。")
                        return
                    regen_round["count"] += 1
                    result["content"] = merged
                    _set_preview_text(merged)
                    status_var.set(f"已生成第 {regen_round['count']} 个新预览版本，可继续重生成或直接采用。")

                dialog.after(0, _finish)

            threading.Thread(target=_worker, daemon=True).start()

        btn_apply = tk.Button(
            action_row,
            text="✅ 采用当前预览并入稿",
            command=_apply,
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
            text="❌ 丢弃本次生成",
            command=_discard,
            bg="#6b7280",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=16,
            pady=8,
            cursor="hand2",
        )
        btn_discard.pack(side="right", padx=(0, 10))
        btn_regen = tk.Button(
            action_row,
            text="🔄 重生成预览（可多次）",
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
        dialog.transient(self)
        dialog.grab_set()
        self.wait_window(dialog)
        return str(result.get("action", "discard")), str(result.get("content", "") or "").strip()


