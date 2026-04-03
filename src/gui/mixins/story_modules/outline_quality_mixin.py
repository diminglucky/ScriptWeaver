"""Outline quality/alignment helpers extracted from outline generator."""

from __future__ import annotations

import logging
import os
import re
from tkinter import END

from src.gui.helpers.story_pipeline_profile import (
    build_memory_ledger_prompt,
    build_polish_prompt,
    build_quality_review_prompt,
    get_polish_fallback_fix,
)
from src.gui.helpers.story_quality import (
    normalize_memory_entry,
    parse_memory_entry,
    parse_quality_review,
    should_polish,
    strip_duplicate_lines,
)

logger = logging.getLogger(__name__)


class OutlineQualityMixin:
    """Quality review, polishing, and alignment repair helpers."""

    def _is_section_tail_complete(self, text: str) -> bool:
        tail = (text or "").strip()
        if not tail:
            return False
        if re.search(r"[。！？!?…；;][”’」』】》）)]*\s*$", tail):
            return True
        return False

    def _repair_section_tail_if_needed(self, client, section_title: str, section_content: str) -> str:
        if self._is_section_tail_complete(section_content):
            return ""

        tail = (section_content or "").strip()
        if len(tail) < 60:
            return ""
        tail = tail[-450:]
        try:
            temp = float(self.temperature.get())
        except Exception:
            temp = 0.7
        temp = max(0.4, min(0.9, temp))

        prompt = (
            "你是中文小说润色编辑。下面这一章的结尾疑似被截断。\n"
            "请只补写一个自然收束的结尾段（约80-220字），满足：\n"
            "1) 仅续写，不重复已出现原句；\n"
            "2) 不新增章节标题、不总结全文；\n"
            "3) 保持当前叙事语气；\n"
            "4) 最后必须以完整句号/问号/感叹号结束。\n\n"
            f"章节标题：{section_title}\n"
            f"当前结尾片段：\n{tail}\n\n"
            "请直接输出补写内容："
        )
        try:
            extra = client.chat(
                [{"role": "user", "content": prompt}],
                temperature=temp,
            ).strip()
        except Exception as exc:
            logger.debug("repair section tail failed: %s", exc)
            return ""

        if not extra:
            return ""

        extra = re.sub(r"^\s*【?第.*?章[：:】]\s*", "", extra)
        extra = re.sub(r"^\s*(补写|续写|续：)\s*", "", extra)
        extra = extra.strip()
        if not extra:
            return ""
        if len(extra) > 280:
            extra = extra[:280].rstrip()
        if not self._is_section_tail_complete(extra):
            extra = extra.rstrip("，,：:；;、") + "。"
        return extra

    def _is_story_quality_review_enabled(self) -> bool:
        raw = str(os.getenv("STORY_QUALITY_REVIEW", "1") or "1").strip().lower()
        default_enabled = raw in {"1", "true", "yes", "on"}
        val = getattr(self, "story_quality_review_enabled", None)
        if hasattr(val, "get"):
            try:
                return bool(val.get())
            except Exception:
                return default_enabled
        if isinstance(val, bool):
            return val
        return default_enabled

    def _get_story_quality_thresholds(self) -> tuple[float, float]:
        min_avg = 7.4
        min_dim = 6.8
        if hasattr(self, "story_quality_min_avg"):
            try:
                min_avg = float(self.story_quality_min_avg.get())
            except Exception:
                min_avg = 7.4
        else:
            try:
                min_avg = float(os.getenv("STORY_QUALITY_MIN_AVG", "7.4") or "7.4")
            except Exception:
                min_avg = 7.4
        if hasattr(self, "story_quality_min_dim"):
            try:
                min_dim = float(self.story_quality_min_dim.get())
            except Exception:
                min_dim = 6.8
        else:
            try:
                min_dim = float(os.getenv("STORY_QUALITY_MIN_DIM", "6.8") or "6.8")
            except Exception:
                min_dim = 6.8
        min_avg = max(1.0, min(10.0, min_avg))
        min_dim = max(1.0, min(10.0, min_dim))
        return min_avg, min_dim

    def _review_section_quality(self, client, section_title: str, section_content: str, requirement: str, category: str) -> dict:
        if not section_content.strip():
            return {
                "scores": {"realism": 1.0, "detail": 1.0, "coherence": 1.0, "naturalness": 1.0},
                "avg_score": 1.0,
                "strengths": [],
                "issues": ["内容为空"],
                "key_fix": "先生成有效正文。",
            }
        preview = section_content[-1800:]
        prompt = build_quality_review_prompt(
            requirement=requirement,
            category=category,
            section_title=section_title,
            preview=preview,
        )
        try:
            raw = client.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=600,
            )
        except Exception as exc:
            logger.debug("quality review failed: %s", exc)
            return {
                "scores": {"realism": 7.0, "detail": 7.0, "coherence": 7.0, "naturalness": 7.0},
                "avg_score": 7.0,
                "strengths": [],
                "issues": ["质量评审不可用，跳过自动改写"],
                "key_fix": "",
            }
        return parse_quality_review(raw)

    def _polish_section_text(
        self,
        client,
        section_title: str,
        section_content: str,
        review: dict,
        target_chars_per_section: int,
    ) -> str:
        key_fix = str(review.get("key_fix", "") or "").strip()
        issues = review.get("issues", [])
        if not isinstance(issues, list):
            issues = []
        issue_text = "；".join(str(x) for x in issues[:3] if str(x).strip())
        chars = len(section_content.strip())
        target_low = max(220, int(target_chars_per_section * 0.8))
        target_high = max(target_low, int(target_chars_per_section * 1.15))
        prompt = build_polish_prompt(
            section_title=section_title,
            section_content=section_content,
            fix_goal=key_fix or issue_text or get_polish_fallback_fix(),
            target_low=target_low,
            target_high=target_high,
            current_chars=chars,
        )
        try:
            rewritten = client.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.45,
                max_tokens=max(1200, int(target_chars_per_section * 2.4)),
            ).strip()
        except Exception as exc:
            logger.debug("section polish failed: %s", exc)
            return section_content

        if not rewritten:
            return section_content
        rewritten = re.sub(r"^\s*【?第.*?章[：:】]\s*", "", rewritten)
        rewritten = strip_duplicate_lines(rewritten)
        if len(rewritten) < max(120, int(len(section_content) * 0.55)):
            return section_content
        return rewritten

    def _update_chapter_quality_report(self, section_index: int, section_title: str, review: dict) -> None:
        if not hasattr(self, "chapter_quality_reports") or not isinstance(self.chapter_quality_reports, list):
            self.chapter_quality_reports = []
        while len(self.chapter_quality_reports) <= section_index:
            self.chapter_quality_reports.append({})
        report = {
            "chapter_index": int(section_index),
            "chapter_title": str(section_title or "").strip(),
            "scores": review.get("scores", {}),
            "avg_score": review.get("avg_score", 0.0),
            "issues": review.get("issues", []),
            "key_fix": review.get("key_fix", ""),
        }
        self.chapter_quality_reports[section_index] = report

    def _extract_memory_entry(self, client, section_index: int, section_title: str, section_content: str) -> dict:
        preview = section_content[-2200:]
        prompt = build_memory_ledger_prompt(
            section_title=section_title,
            preview=preview,
        )
        try:
            raw = client.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=700,
            )
            entry = parse_memory_entry(raw)
        except Exception as exc:
            logger.debug("memory extraction failed: %s", exc)
            entry = {}
        if not entry:
            fallback_summary = section_content.strip().replace("\n", " ")
            entry = {
                "summary": fallback_summary[:120],
                "plot_points": [],
                "relation_changes": [],
                "unresolved_hooks": [],
                "state_shift": "",
            }
        return normalize_memory_entry(entry, chapter_index=section_index, chapter_title=section_title)

    def _update_story_memory_ledger(self, section_index: int, section_title: str, entry: dict) -> None:
        if not hasattr(self, "story_memory_ledger") or not isinstance(self.story_memory_ledger, list):
            self.story_memory_ledger = []
        normalized = normalize_memory_entry(entry, chapter_index=section_index, chapter_title=section_title)
        while len(self.story_memory_ledger) <= section_index:
            self.story_memory_ledger.append({})
        self.story_memory_ledger[section_index] = normalized

    def _evaluate_outline_alignment_safe(self, requirement: str, category: str, outline_text: str) -> dict | None:
        if not hasattr(self, "_evaluate_outline_alignment"):
            return None
        try:
            return self._ui_get(
                lambda: self._evaluate_outline_alignment(
                    requirement,
                    category,
                    outline_text,
                )
            )
        except Exception as exc:
            logger.debug("outline alignment evaluate failed: %s", exc)
            return None

    def _refine_outline_with_alignment(
        self,
        client,
        requirement: str,
        contexts: list[str],
        category: str,
        outline_text: str,
        outline_system_prompt: str,
        base_temperature: float,
        stage_tag: str = "",
    ) -> tuple[str, dict | None]:
        alignment_report = self._evaluate_outline_alignment_safe(requirement, category, outline_text)
        if alignment_report is None:
            return outline_text, None
        strict_enabled = False
        if hasattr(self, "_is_outline_alignment_strict_enabled"):
            try:
                strict_enabled = bool(self._ui_get(self._is_outline_alignment_strict_enabled))
            except Exception:
                strict_enabled = False
        max_attempts = 2
        if hasattr(self, "_get_outline_alignment_max_attempts"):
            try:
                max_attempts = int(self._ui_get(self._get_outline_alignment_max_attempts))
            except Exception:
                max_attempts = 2
        max_attempts = max(1, min(4, max_attempts))
        if strict_enabled and max_attempts < 2:
            max_attempts = 2

        log_suffix = f" ({stage_tag})" if stage_tag else ""
        attempt = 1
        while (
            alignment_report is not None
            and not bool(alignment_report.get("passed"))
            and attempt < max_attempts
        ):
            prev_score = float(alignment_report.get("score", 0.0))
            reason = str(alignment_report.get("reason", "") or "目录与需求不够一致")
            can_retry = bool(alignment_report.get("should_retry")) or strict_enabled
            improved = False

            if can_retry and hasattr(self, "_build_outline_realign_prompt"):
                try:
                    self._ui(self.status.set, f"目录对齐不足（{prev_score:.2f}），自动纠偏重试({attempt}/{max_attempts - 1})...")
                    self._ui(
                        self.output.insert,
                        END,
                        f"检测到目录偏题（{reason}），正在自动纠偏重试（第{attempt}次）...\n\n",
                    )
                    retry_prompt = self._ui_get(
                        lambda: self._build_outline_realign_prompt(
                            requirement,
                            contexts,
                            category,
                            outline_text,
                            alignment_report,
                        )
                    )
                    if strict_enabled:
                        missing_tokens = alignment_report.get("missing_tokens", [])
                        if not isinstance(missing_tokens, list):
                            missing_tokens = []
                        missing_text = "、".join(str(x) for x in missing_tokens[:4] if str(x).strip()) or "需求关键词"
                        retry_prompt = (
                            f"{retry_prompt}\n"
                            "【强约束输出（必须满足）】\n"
                            f"- 目录必须明显出现：{missing_text}\n"
                            "- 至少 2 章标题直接体现题材与核心冲突。\n"
                            "- 不得输出解释，只输出目录条目。\n"
                        )
                    retry_outline = client.chat(
                        [
                            {"role": "system", "content": outline_system_prompt},
                            {"role": "user", "content": retry_prompt},
                        ],
                        temperature=max(0.3, base_temperature - 0.25 - (attempt - 1) * 0.05),
                    )
                    retry_report = self._evaluate_outline_alignment_safe(requirement, category, retry_outline)
                    retry_score = float(retry_report.get("score", 0.0)) if isinstance(retry_report, dict) else 0.0
                    if isinstance(retry_report, dict) and (
                        retry_score >= prev_score or bool(retry_report.get("passed"))
                    ):
                        outline_text = retry_outline
                        alignment_report = retry_report
                        improved = True
                except Exception as exc:
                    logger.debug("outline auto realign failed%s: %s", log_suffix, exc)

            if (
                alignment_report
                and (not bool(alignment_report.get("passed")))
                and hasattr(self, "_repair_outline_for_alignment")
            ):
                try:
                    repaired_outline = self._ui_get(
                        lambda: self._repair_outline_for_alignment(
                            requirement,
                            category,
                            outline_text,
                            alignment_report,
                        )
                    )
                    repaired_text = str(repaired_outline or "").strip()
                    if repaired_text and repaired_text != str(outline_text).strip():
                        repaired_report = self._evaluate_outline_alignment_safe(requirement, category, repaired_text)
                        old_score = float(alignment_report.get("score", 0.0))
                        new_score = float(repaired_report.get("score", 0.0)) if isinstance(repaired_report, dict) else 0.0
                        if isinstance(repaired_report, dict) and (
                            new_score >= old_score or bool(repaired_report.get("passed"))
                        ):
                            outline_text = repaired_text
                            alignment_report = repaired_report
                            improved = True
                            self._ui(self.output.insert, END, "检测到目录偏题，已应用关键词对齐修复。\n\n")
                except Exception as exc:
                    logger.debug("outline local alignment repair failed%s: %s", log_suffix, exc)

            if alignment_report and bool(alignment_report.get("passed")):
                break
            if not strict_enabled and not improved:
                break
            attempt += 1

        return outline_text, alignment_report

    @staticmethod
    def _should_polish_review(review: dict, min_avg: float, min_dim: float) -> bool:
        return should_polish(review, min_avg=min_avg, min_dim=min_dim)
