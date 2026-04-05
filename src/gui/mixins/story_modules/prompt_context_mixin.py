"""Story template/creativity/memory/RAG context helpers."""

from __future__ import annotations

import re
from pathlib import Path

from ...helpers.story_creativity import (
    DEFAULT_STORY_CREATIVITY_MODE,
    normalize_story_creativity_mode,
)
from ...helpers.story_quality import extract_last_sentence, format_memory_context
from ...helpers.story_templates import (
    get_story_template,
    list_story_template_strategies,
    resolve_story_template,
)


class StoryPromptContextMixin:
    """Context and diagnostic helpers used by story prompt builders."""
    def _get_story_template_profile(self, requirement: str = "", category: str = ""):
        key = ""
        if hasattr(self, "story_template_key"):
            try:
                key = (self.story_template_key.get() or "").strip()
            except Exception:
                key = ""
        strategy = self._get_story_template_strategy()
        return resolve_story_template(
            key,
            strategy,
            nonce=self._get_story_creativity_nonce(),
            requirement=requirement,
            category=category,
        )

    def _get_story_creativity_mode(self) -> str:
        mode = DEFAULT_STORY_CREATIVITY_MODE
        if hasattr(self, "story_creativity_mode"):
            try:
                mode = self.story_creativity_mode.get()
            except Exception:
                mode = DEFAULT_STORY_CREATIVITY_MODE
        return normalize_story_creativity_mode(mode)

    def _get_story_creativity_nonce(self) -> str:
        return str(getattr(self, "_story_creativity_nonce", "") or "").strip()

    def _get_story_memory_ledger(self) -> list[dict]:
        rows = getattr(self, "story_memory_ledger", [])
        if not isinstance(rows, list):
            return []
        return [x for x in rows if isinstance(x, dict)]

    def _build_story_memory_context(self, section_index: int, max_items: int = 3) -> str:
        try:
            idx = int(section_index)
        except Exception:
            idx = 0
        rows = [x for x in self._get_story_memory_ledger() if int(x.get("chapter_index", -1)) < idx]
        if not rows:
            return ""
        return format_memory_context(rows, max_entries=max_items)

    def _build_section_transition_context(self, section_index: int, previous_content: str) -> str:
        """Build compact cross-chapter continuity brief for current section."""
        try:
            idx = int(section_index)
        except Exception:
            idx = 0
        if idx <= 0:
            return ""

        lines: list[str] = []
        tail_sentence = extract_last_sentence(previous_content or "", max_chars=260)
        if tail_sentence:
            lines.append(f"- 上章收束句：{tail_sentence}")

        prev_rows = [x for x in self._get_story_memory_ledger() if int(x.get("chapter_index", -1)) < idx]
        if prev_rows:
            last = prev_rows[-1]
            summary = str(last.get("summary", "") or "").strip()
            if summary:
                lines.append(f"- 上章事件摘要：{summary[:90]}")
            relation = last.get("relation_changes", [])
            if isinstance(relation, list) and relation:
                relation_text = "；".join(str(x).strip() for x in relation[:2] if str(x).strip())
                if relation_text:
                    lines.append(f"- 当前关系状态：{relation_text}")
            hooks = last.get("unresolved_hooks", [])
            if isinstance(hooks, list) and hooks:
                hooks_text = "；".join(str(x).strip() for x in hooks[:2] if str(x).strip())
                if hooks_text:
                    lines.append(f"- 待延续伏笔：{hooks_text}")

        if lines:
            lines.append("- 首段必须承接上章结尾后的即时动作/情绪，不得复述原句。")
        return "\n".join(lines).strip()

    def _update_story_diagnostics_panel(self) -> None:
        if not hasattr(self, "story_quality_summary_var") or not hasattr(self, "story_memory_summary_var"):
            return

        quality_enabled = True
        if hasattr(self, "story_quality_review_enabled"):
            try:
                quality_enabled = bool(self.story_quality_review_enabled.get())
            except Exception:
                quality_enabled = True

        if not quality_enabled:
            self.story_quality_summary_var.set("质量评审：已关闭（仅生成，不自动精修）")
        else:
            reports = getattr(self, "chapter_quality_reports", [])
            last_report = None
            if isinstance(reports, list):
                for row in reversed(reports):
                    if isinstance(row, dict) and row:
                        last_report = row
                        break
            if last_report:
                avg = float(last_report.get("avg_score", 0.0) or 0.0)
                scores = last_report.get("scores", {}) if isinstance(last_report.get("scores", {}), dict) else {}
                realism = float(scores.get("realism", 0.0) or 0.0)
                detail = float(scores.get("detail", 0.0) or 0.0)
                issue = ""
                issues = last_report.get("issues", [])
                if isinstance(issues, list) and issues:
                    issue = str(issues[0] or "").strip()
                key_fix = str(last_report.get("key_fix", "") or "").strip()
                title = str(last_report.get("chapter_title", "") or "").strip()
                self.story_quality_summary_var.set(
                    f"质量评审：{title or '最近章节'} | 平均{avg:.1f} | 真实{realism:.1f} 细节{detail:.1f}"
                    f"{' | 修复: ' + (key_fix or issue) if (key_fix or issue) else ''}"
                )
            else:
                self.story_quality_summary_var.set("质量评审：等待章节生成后自动打分")

        ledger = self._get_story_memory_ledger()
        if ledger:
            last = ledger[-1]
            try:
                chapter_no = int(last.get("chapter_index", len(ledger) - 1)) + 1
            except Exception:
                chapter_no = len(ledger)
            chapter_title = str(last.get("chapter_title", "") or "").strip()
            summary = str(last.get("summary", "") or "").strip()
            hooks = last.get("unresolved_hooks", [])
            hook_text = ""
            if isinstance(hooks, list) and hooks:
                hook_text = str(hooks[0] or "").strip()
            desc = summary[:36] + ("..." if len(summary) > 36 else "") if summary else "已记录"
            self.story_memory_summary_var.set(
                f"记忆账本：第{chapter_no}章《{chapter_title or '未命名'}》 | {desc}"
                f"{' | 伏笔: ' + hook_text if hook_text else ''}"
            )
        else:
            self.story_memory_summary_var.set("记忆账本：暂无章节记忆")

    def _format_story_rules(self, rules):
        items = []
        for rule in (rules or []):
            text = str(rule).strip()
            if text:
                items.append(text)
        if not items:
            return "- 无"
        return "\n".join(f"- {item}" for item in items)

    def _get_rag_min_score(self) -> float:
        raw = 0.12
        if hasattr(self, "rag_min_score"):
            try:
                raw = float(self.rag_min_score.get())
            except Exception:
                raw = 0.12
        return max(0.0, min(1.0, raw))

    def _postprocess_rag_results(self, results):
        rows = list(results or [])
        if not rows:
            return []

        min_score = self._get_rag_min_score()
        accepted = []
        seen = set()

        for chunk, score, meta in rows:
            text = str(chunk or "").strip()
            if not text:
                continue
            try:
                score_value = float(score)
            except Exception:
                score_value = 0.0
            if score_value < min_score:
                continue
            signature = re.sub(r"\s+", " ", text[:260]).strip().lower()
            if not signature or signature in seen:
                continue
            seen.add(signature)
            accepted.append((text, score_value, meta))

        if not accepted:
            for chunk, score, meta in rows:
                text = str(chunk or "").strip()
                if not text:
                    continue
                signature = re.sub(r"\s+", " ", text[:260]).strip().lower()
                if not signature or signature in seen:
                    continue
                seen.add(signature)
                try:
                    score_value = float(score)
                except Exception:
                    score_value = 0.0
                accepted.append((text, score_value, meta))
                if len(accepted) >= 2:
                    break

        top_k = 6
        if hasattr(self, "top_k"):
            try:
                top_k = int(self.top_k.get())
            except Exception:
                top_k = 6
        return accepted[: max(1, top_k)]

    def _build_story_run_banner(self, requirement: str, category: str, rag_rows=None) -> str:
        effective_category, category_note = self._resolve_effective_story_category(requirement, category)
        template = self._get_story_template_profile(requirement=requirement, category=effective_category)
        base_key = str(template.get("base_key", template.get("key", "")) or "").strip()
        resolved_key = str(template.get("resolved_key", template.get("key", "")) or "").strip()
        strategy_key = str(template.get("strategy", self._get_story_template_strategy()) or "").strip()
        strategy_label = strategy_key
        for row in list_story_template_strategies():
            if row.get("key") == strategy_key:
                strategy_label = row.get("label", strategy_key)
                break

        base_label = get_story_template(base_key).get("label", base_key) if base_key else "默认模版"
        resolved_label = template.get("label", resolved_key or "默认模版")

        lines = []
        if base_key and resolved_key and base_key != resolved_key:
            lines.append(f"🎭 本次模版：{resolved_label}（策略：{strategy_label}，基准：{base_label}）")
        else:
            lines.append(f"🎭 本次模版：{resolved_label}（策略：{strategy_label}）")
        if category_note:
            lines.append(f"🧭 题材纠偏：{category_note}")

        rag_items = list(rag_rows or [])
        if rag_items:
            lines.append(f"🔎 RAG检索：命中 {len(rag_items)} 条（阈值≥{self._get_rag_min_score():.2f}）")
            for idx, (_chunk, score, meta) in enumerate(rag_items[:4], start=1):
                source = "未知来源"
                if isinstance(meta, (list, tuple)) and meta:
                    try:
                        source = Path(str(meta[0])).name or str(meta[0])
                    except Exception:
                        source = str(meta[0])
                lines.append(f"  {idx}. {source}（score={float(score):.3f}）")
        return "\n".join(lines)
