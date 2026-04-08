"""Section preview dialog before applying generated content.

Extracted from outline_section_generate_mixin.py to reduce file size.
"""

from tkinter import END, messagebox, scrolledtext
import logging, os, re, threading
import tkinter as tk

from src.utils.text import sanitize as _sanitize
from src.gui.helpers.story_quality import extract_last_sentence, strip_duplicate_lines
from src.gui.helpers.story_feedback_dialog import show_story_feedback_dialog

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

    def _should_auto_accept_by_quality(self, section_index: int) -> bool:
        """质量评审分数达标时自动通过，跳过手动预览弹窗。"""
        if not hasattr(self, "chapter_quality_reports"):
            return False
        reports = getattr(self, "chapter_quality_reports", [])
        if not isinstance(reports, list) or section_index >= len(reports):
            return False
        report = reports[section_index]
        if not isinstance(report, dict) or not report:
            return False
        avg = float(report.get("avg_score", 0.0) or 0.0)
        # 平均分 >= 7.5 自动通过
        auto_threshold = 7.5
        try:
            auto_threshold = float(os.getenv("STORY_AUTO_ACCEPT_THRESHOLD", "7.5") or "7.5")
        except Exception:
            auto_threshold = 7.5
        return avg >= auto_threshold

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
        skip_dialog: bool = False,
    ) -> tuple[str, str]:
        """Show modal preview and return (`accept|discard`, effective content).

        skip_dialog=True 时跳过弹窗自动采用（用于自动批量生成）。
        质量评审达标时也自动通过，无需手动确认。
        """
        if skip_dialog or not self._is_story_preview_before_apply_enabled():
            return "accept", str(section_content or "").strip()
        if self._should_auto_accept_by_quality(section_index):
            logger.info("chapter %d auto-accepted by quality score", section_index + 1)
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
        def _regen(current_text: str, feedback: str) -> str:
            return self._regenerate_section_preview_with_feedback(
                client=client,
                section_index=section_index,
                section_title=section_title,
                current_content=current_text,
                feedback=feedback,
                requirement=requirement,
                category=category,
                previous_content=previous_content,
            )

        return show_story_feedback_dialog(
            self,
            title=f"章节预览 - 第 {section_index + 1}/{total_sections} 章",
            header_text=f"《{section_title or '未命名章节'}》预览",
            subtitle_text=f"字数：{len((section_content or '').strip())} 字 | 确认后才会入稿保存",
            initial_content=section_content,
            default_status="可多次重生成预览，直到满意后再采用。",
            geometry="1020x780",
            accept_label="✅ 采用当前预览并入稿",
            discard_label="❌ 丢弃本次生成",
            regen_label="🔄 重生成预览（可多次）",
            editor_readonly=True,
            regenerate_fn=_regen,
        )


