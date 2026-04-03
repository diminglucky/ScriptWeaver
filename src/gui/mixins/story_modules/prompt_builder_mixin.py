"""Prompt/alignment/model-loading helpers for story UI builder."""

from __future__ import annotations

import logging
import os
import re
import threading
from pathlib import Path

from ...helpers.story_creativity import (
    DEFAULT_STORY_CREATIVITY_MODE,
    build_story_creativity_block,
    normalize_story_creativity_mode,
)
from ...helpers.story_pipeline_profile import build_emotion_arc_guidelines
from ...helpers.story_prompt_profile import (
    get_outline_core_requirements_text,
    get_outline_intro_text,
    get_outline_output_example_text,
    get_section_intro_text,
    get_section_reminder_text,
    get_section_writing_spec_text,
    get_story_intro_text,
    get_story_reminder_text,
    get_story_writing_spec_text,
)
from ...helpers.story_quality import format_memory_context
from ...helpers.story_templates import (
    DEFAULT_STORY_TEMPLATE_STRATEGY,
    get_story_template,
    list_story_template_strategies,
    normalize_story_template_strategy,
    resolve_story_template,
)
from ...helpers.story_writing_guardrails import (
    build_non_ai_writing_guardrails,
    build_outline_title_guardrails,
    get_chapter_title_limits,
    normalize_chapter_title,
)

logger = logging.getLogger(__name__)

_STORY_CATEGORY_HINT_KEYWORDS = {
    "校园": ("校园", "学生", "班级", "宿舍", "老师", "考试", "大学", "高中", "中学", "校门", "社团"),
    "职场": ("职场", "公司", "同事", "上司", "老板", "办公室", "项目", "KPI", "升职", "裁员", "开会"),
    "悬疑": ("悬疑", "谜", "命案", "线索", "侦探", "凶手", "疑点", "真相", "反转"),
    "科幻": ("科幻", "未来", "AI", "人工智能", "机器人", "太空", "时空", "实验室"),
    "爱情": ("爱情", "恋爱", "告白", "前任", "暗恋", "分手", "心动"),
    "成长": ("成长", "蜕变", "自我", "逆袭", "成熟", "和解"),
    "亲情": ("亲情", "父亲", "母亲", "家人", "兄妹", "家庭"),
    "社会观察": ("社会", "现实", "阶层", "制度", "舆论", "公共"),
    "历史": ("历史", "朝代", "古代", "王朝", "战国", "明朝", "清朝"),
    "奇幻": ("奇幻", "魔法", "精灵", "异界", "龙", "神话"),
}

_STORY_REQUIREMENT_ANCHOR_STOPWORDS = {
    "写一个",
    "写一篇",
    "写个",
    "故事",
    "文章",
    "题材",
    "要求",
    "不要",
    "希望",
    "可以",
    "必须",
    "以及",
    "并且",
    "然后",
    "这种",
    "那个",
}


class StoryPromptBuilderMixin:
    """Prompt construction and outline-alignment helpers."""

    def _get_story_template_strategy(self) -> str:
        strategy = DEFAULT_STORY_TEMPLATE_STRATEGY
        if hasattr(self, "story_template_strategy"):
            try:
                strategy = self.story_template_strategy.get()
            except Exception:
                strategy = DEFAULT_STORY_TEMPLATE_STRATEGY
        return normalize_story_template_strategy(strategy)

    def _is_outline_alignment_strict_enabled(self) -> bool:
        default_enabled = str(os.getenv("STORY_OUTLINE_ALIGNMENT_STRICT", "1") or "1").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if hasattr(self, "story_outline_alignment_strict"):
            try:
                return bool(self.story_outline_alignment_strict.get())
            except Exception:
                return default_enabled
        return default_enabled

    def _get_outline_alignment_max_attempts(self) -> int:
        default_attempts = 2
        raw = (os.getenv("STORY_OUTLINE_ALIGNMENT_MAX_ATTEMPTS", str(default_attempts)) or str(default_attempts)).strip()
        try:
            attempts = int(raw)
        except Exception:
            attempts = default_attempts
        if hasattr(self, "story_outline_alignment_max_attempts"):
            try:
                attempts = int(self.story_outline_alignment_max_attempts.get())
            except Exception:
                pass
        return max(1, min(4, attempts))

    def _score_requirement_for_category(self, requirement: str, category: str) -> int:
        text = str(requirement or "").strip()
        if not text:
            return 0
        keywords = _STORY_CATEGORY_HINT_KEYWORDS.get(str(category or "").strip(), ())
        score = 0
        for keyword in keywords:
            if keyword and keyword in text:
                score += 2 if len(keyword) >= 2 else 1
        return score

    def _infer_category_from_requirement(self, requirement: str) -> tuple[str, int]:
        text = str(requirement or "").strip()
        if not text:
            return "", 0
        best_category = ""
        best_score = 0
        for category, keywords in _STORY_CATEGORY_HINT_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword and keyword in text:
                    score += 2 if len(keyword) >= 2 else 1
                if score > best_score:
                    best_score = score
                    best_category = category
        if best_score <= 0:
            return "", 0
        return best_category, best_score

    def _resolve_effective_story_category(self, requirement: str, selected_category: str) -> tuple[str, str]:
        selected = str(selected_category or "").strip()
        detected, detected_score = self._infer_category_from_requirement(requirement)
        selected_score = self._score_requirement_for_category(requirement, selected) if selected else 0
        if detected and selected and detected != selected:
            should_override = False
            if selected_score <= 0 and detected_score >= 2:
                should_override = True
            elif detected_score >= (selected_score + 3):
                should_override = True
            if should_override:
                return detected, f"检测到需求更偏“{detected}”（信号 {detected_score}>{selected_score}），已覆盖界面选择“{selected}”"
            return selected, f"需求含“{detected}”线索（信号 {detected_score}），但保留界面选择“{selected}”"
        if detected and not selected:
            return detected, ""
        return selected, ""

    def _extract_requirement_anchors(self, requirement: str, max_items: int = 6) -> list[str]:
        text = str(requirement or "").strip()
        if not text:
            return []
        raw_tokens = re.findall(r"[\u4e00-\u9fff]{2,10}|[A-Za-z][A-Za-z0-9_-]{2,20}", text)
        anchors: list[str] = []
        seen: set[str] = set()
        for token in raw_tokens:
            cleaned = str(token).strip("，。！？：；、“”\"'（）() ")
            if not cleaned:
                continue
            if cleaned in _STORY_REQUIREMENT_ANCHOR_STOPWORDS:
                continue
            if cleaned.endswith("故事") and len(cleaned) <= 4:
                continue
            if cleaned in seen:
                continue
            seen.add(cleaned)
            anchors.append(cleaned)
            if len(anchors) >= max_items:
                break
        detected_category, _detected_score = self._infer_category_from_requirement(text)
        if detected_category and detected_category not in seen:
            anchors.insert(0, detected_category)
        return anchors[:max_items]

    def _build_requirement_alignment_block(self, requirement: str, selected_category: str, *, stage: str) -> tuple[str, str, str]:
        effective_category, category_note = self._resolve_effective_story_category(requirement, selected_category)
        anchors = self._extract_requirement_anchors(requirement)
        anchor_lines = "\n".join(f"- {item}" for item in anchors) if anchors else "- 以用户需求原文为唯一锚点"
        if stage == "outline":
            stage_rule = "目录每一章都必须命中至少一个锚点，首章必须直接进入主冲突，不得偏题。"
        elif stage == "section":
            stage_rule = "本节必须围绕锚点推进，至少兑现一个冲突或关系变化，不能偏离主线。"
        else:
            stage_rule = "正文段落必须持续围绕锚点展开，不得被模版风格带偏主题。"
        note_line = f"- 系统纠偏：{category_note}\n" if category_note else ""
        block = (
            "【需求对齐锚点（最高优先级）】\n"
            f"- 用户原始需求：{requirement}\n"
            f"- 关键锚点：\n{anchor_lines}\n"
            f"- {stage_rule}\n"
            "- 若界面“种类”与需求冲突，以需求锚点为准。\n"
            f"{note_line}"
        )
        return block, effective_category or str(selected_category or "").strip(), category_note

    def _collect_outline_titles(self, outline_text: str) -> list[str]:
        lines = str(outline_text or "").splitlines()
        titles: list[str] = []
        for raw in lines:
            line = str(raw or "").strip()
            if not line:
                continue
            match = re.match(r'^\s*(\d+|[一二三四五六七八九十]+)[.、]\s*(.+?)\s*$', line)
            if not match:
                continue
            title = normalize_chapter_title(match.group(2).strip())
            if title:
                titles.append(title)
        return titles

    def _is_generic_outline_title(self, title: str) -> bool:
        text = str(title or "").strip()
        if not text:
            return True
        generic_exact = {
            "平静的开端",
            "意外降临",
            "危机爆发",
            "绝地反击",
            "尘埃落定",
            "故事开端",
            "冲突升级",
            "迎来结局",
        }
        if text in generic_exact:
            return True
        if re.match(r"^(开端|发展|高潮|结局|尾声|序章)$", text):
            return True
        return False

    def _evaluate_outline_alignment(self, requirement: str, selected_category: str, outline_text: str) -> dict:
        anchors = self._extract_requirement_anchors(requirement, max_items=8)
        must_tokens = self._derive_outline_must_tokens(requirement, selected_category, max_items=4)
        effective_category, _note = self._resolve_effective_story_category(requirement, selected_category)
        titles = self._collect_outline_titles(outline_text)
        joined = "\n".join(titles)

        anchor_hits = [a for a in anchors if a and a in joined]
        missing_anchors = [a for a in anchors if a and a not in joined]
        must_hits = [a for a in must_tokens if a and a in joined]
        missing_tokens = [a for a in must_tokens if a and a not in joined]
        category_keywords = _STORY_CATEGORY_HINT_KEYWORDS.get(effective_category, ())
        category_hits = [k for k in category_keywords if k and len(k) >= 2 and k in joined]
        generic_count = sum(1 for t in titles if self._is_generic_outline_title(t))
        generic_ratio = (generic_count / len(titles)) if titles else 1.0

        usable_tokens = must_tokens or anchors
        token_hits = must_hits if must_tokens else anchor_hits
        target_anchor_hits = 1 if len(usable_tokens) <= 2 else 2
        actual_anchor_hits = max(len(anchor_hits), len(token_hits))
        anchor_score = min(1.0, actual_anchor_hits / max(1, target_anchor_hits))
        category_score = 1.0 if category_hits else 0.0
        generic_score = max(0.0, 1.0 - generic_ratio)
        score = round(anchor_score * 0.6 + category_score * 0.25 + generic_score * 0.15, 4)

        fail_reasons: list[str] = []
        if actual_anchor_hits < target_anchor_hits:
            reason = f"关键锚点命中不足（{actual_anchor_hits}/{target_anchor_hits}）"
            if missing_tokens:
                reason += f"，建议补齐：{'、'.join(missing_tokens[:3])}"
            fail_reasons.append(reason)
        if effective_category and not category_hits:
            fail_reasons.append(f"缺少“{effective_category}”题材信号")
        if generic_ratio >= 0.5:
            fail_reasons.append("章节标题过于通用")
        if len(titles) < 3:
            fail_reasons.append("章节数量过少")

        passed = (score >= 0.55) and not fail_reasons
        reason = "对齐通过" if passed else "；".join(fail_reasons)
        critical_fail = False
        if actual_anchor_hits == 0:
            critical_fail = True
        if effective_category and not category_hits and score < 0.5:
            critical_fail = True
        if len(titles) < 3:
            critical_fail = True
        should_retry = (not passed) and (critical_fail or score < 0.45)
        return {
            "passed": passed,
            "should_retry": should_retry,
            "score": score,
            "reason": reason,
            "effective_category": effective_category,
            "titles": titles,
            "anchor_hits": anchor_hits,
            "missing_anchors": missing_anchors,
            "must_tokens": must_tokens,
            "must_hits": must_hits,
            "missing_tokens": missing_tokens,
            "category_hits": category_hits,
            "generic_ratio": generic_ratio,
        }

    def _build_outline_realign_prompt(
        self,
        requirement: str,
        contexts: list[str],
        selected_category: str,
        previous_outline: str,
        assessment: dict,
    ) -> str:
        base_prompt = self._build_outline_prompt(requirement, contexts, selected_category)
        missing_tokens = assessment.get("missing_tokens", [])
        if not isinstance(missing_tokens, list):
            missing_tokens = []
        missing = "、".join(missing_tokens[:6]) or "无"
        effective_category = str(assessment.get("effective_category", selected_category) or selected_category).strip()
        reason = str(assessment.get("reason", "") or "目录与需求不够一致").strip()
        return (
            f"{base_prompt}\n\n"
            "【自动纠偏（二次生成）】\n"
            f"- 上一版对齐评分：{float(assessment.get('score', 0.0)):.2f}\n"
            f"- 问题：{reason}\n"
            f"- 必须命中锚点：{missing}\n"
            f"- 必须体现题材：{effective_category}\n"
            "- 请重新输出完整目录，禁止解释说明，禁止复用示例词汇。\n"
            "- 若上一版标题偏泛，改成具体场景/冲突导向标题。\n\n"
            "【上一版目录（仅供纠偏参考，不可照抄）】\n"
            f"{previous_outline.strip()}\n"
        )

    def _derive_outline_must_tokens(self, requirement: str, selected_category: str, max_items: int = 3) -> list[str]:
        effective_category, _note = self._resolve_effective_story_category(requirement, selected_category)
        anchors = self._extract_requirement_anchors(requirement, max_items=8)
        tokens: list[str] = []

        def _add_token(token: str) -> None:
            clean = str(token or "").strip("，。！？：；、“”\"'（）() ")
            if len(clean) < 2:
                return
            if clean in _STORY_REQUIREMENT_ANCHOR_STOPWORDS:
                return
            if clean in tokens:
                return
            tokens.append(clean)

        if effective_category:
            _add_token(effective_category)
        for anchor in anchors:
            if len(tokens) >= max_items:
                break
            anchor_text = str(anchor or "").strip()
            if not anchor_text:
                continue
            if len(anchor_text) <= 4:
                _add_token(anchor_text)
            if effective_category and anchor_text.startswith(effective_category) and len(anchor_text) > len(effective_category):
                tail = anchor_text[len(effective_category):].strip()
                if 1 < len(tail) <= 4:
                    _add_token(tail)

        if effective_category and len(tokens) < max_items:
            for keyword in _STORY_CATEGORY_HINT_KEYWORDS.get(effective_category, ()):
                if len(tokens) >= max_items:
                    break
                if keyword == effective_category:
                    continue
                if 1 < len(str(keyword).strip()) <= 4:
                    _add_token(str(keyword))

        return tokens[:max_items]

    def _repair_outline_for_alignment(
        self,
        requirement: str,
        selected_category: str,
        outline_text: str,
        assessment: dict | None = None,
    ) -> str:
        _ = assessment
        titles = self._collect_outline_titles(outline_text)
        if not titles:
            return str(outline_text or "").strip()
        must_tokens = self._derive_outline_must_tokens(requirement, selected_category, max_items=3)
        if not must_tokens:
            effective_category, _note = self._resolve_effective_story_category(requirement, selected_category)
            if effective_category:
                must_tokens = [effective_category]
        if not must_tokens:
            return str(outline_text or "").strip()

        changed = False
        repaired_titles: list[str] = []
        for idx, title in enumerate(titles):
            raw_title = normalize_chapter_title(str(title or "").strip())
            if not raw_title:
                continue
            if any(token in raw_title for token in must_tokens):
                repaired_titles.append(raw_title)
                continue
            token = must_tokens[idx % len(must_tokens)]
            if len(token) <= 2:
                candidate = f"{token}{raw_title}"
            else:
                candidate = f"{token}·{raw_title}"
            candidate = normalize_chapter_title(candidate)
            if candidate != raw_title:
                changed = True
            repaired_titles.append(candidate or raw_title)

        if not changed:
            return str(outline_text or "").strip()
        return "\n".join(f"{i + 1}. {title}" for i, title in enumerate(repaired_titles)).strip()

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

    def _build_outline_prompt(self, requirement, contexts, category):
        ctx = "\n\n".join(f"【资料{i+1}】\n{c}" for i, c in enumerate(contexts))
        target_chars = self.target_chars.get()
        style_part = ""
        if hasattr(self, "style"):
            try:
                style_part = self.style.get().strip()
            except Exception:
                style_part = ""
        alignment_block, effective_category, _category_note = self._build_requirement_alignment_block(
            requirement,
            category,
            stage="outline",
        )
        template = self._get_story_template_profile(requirement=requirement, category=effective_category)
        template_label = template.get("label", "默认模版")
        outline_focus = template.get("outline_focus", "围绕主题构建起承转合")
        outline_rules = self._format_story_rules(template.get("outline_rules", []))
        outline_guardrails = build_outline_title_guardrails()
        creativity_mode = self._get_story_creativity_mode()
        creativity_rules = build_story_creativity_block(
            creativity_mode,
            requirement=requirement,
            category=effective_category,
            style_hint=style_part,
            stage="outline",
            nonce=self._get_story_creativity_nonce(),
            primary_template_key=template.get("key", ""),
        )
        creativity_part = (
            f"【创新引擎（{creativity_mode}）】\n{creativity_rules}\n\n"
            if creativity_rules
            else ""
        )
        if target_chars <= 3000:
            suggested_sections = "3-4"
        elif target_chars <= 8000:
            suggested_sections = "4-6"
        elif target_chars <= 15000:
            suggested_sections = "6-8"
        else:
            suggested_sections = "8-10"
        chapter_title_min_len, chapter_title_max_len = get_chapter_title_limits()
        outline_intro = get_outline_intro_text()
        outline_core_requirements = get_outline_core_requirements_text(
            suggested_sections=suggested_sections,
            chapter_title_min_len=chapter_title_min_len,
            chapter_title_max_len=chapter_title_max_len,
        )
        outline_output_example = get_outline_output_example_text()

        return (
            f"{outline_intro}\n\n"
            "【核心要求】\n"
            f"{outline_core_requirements}\n\n"
            f"{alignment_block}\n"
            "【模版要求】\n"
            f"- 当前模版：{template_label}\n"
            f"- 模版导向：{outline_focus}\n"
            f"{outline_rules}\n\n"
            "【标题质量约束】\n"
            f"{outline_guardrails}\n\n"
            f"{creativity_part}"
            f"【创作信息】\n"
            f"- 主题/需求：{requirement}\n"
            f"- 种类（最终）：{effective_category}\n"
            f"- 种类（界面）：{category}\n"
            f"- 目标字数：{target_chars}字\n\n"
            f"【参考资料】\n{ctx if ctx else '无特定资料'}\n\n"
            f"{outline_output_example}"
        )

    def _build_prompt(self, requirement, contexts, category, outline=""):
        ctx = "\n\n".join(f"【资料{i+1}】\n{c}" for i, c in enumerate(contexts))
        outline_part = ("\n\n请严格参照下述目录完成写作：\n" + outline.strip()) if outline else ""
        style_part = self.style.get().strip()
        target = self.target_chars.get()
        alignment_block, effective_category, _category_note = self._build_requirement_alignment_block(
            requirement,
            category,
            stage="story",
        )
        template = self._get_story_template_profile(requirement=requirement, category=effective_category)
        template_label = template.get("label", "默认模版")
        story_focus = template.get("story_focus", "叙事连贯，冲突清晰，结尾有回扣")
        story_rules = self._format_story_rules(template.get("story_rules", []))
        writing_guardrails = build_non_ai_writing_guardrails()
        emotion_guardrails = build_emotion_arc_guidelines(stage="story")
        creativity_mode = self._get_story_creativity_mode()
        creativity_rules = build_story_creativity_block(
            creativity_mode,
            requirement=requirement,
            category=effective_category,
            style_hint=style_part,
            stage="story",
            nonce=self._get_story_creativity_nonce(),
            primary_template_key=template.get("key", ""),
        )
        creativity_part = (
            f"【创新引擎（{creativity_mode}）】\n{creativity_rules}\n\n"
            if creativity_rules
            else ""
        )
        style_value = style_part if style_part else "自动匹配模版风格"
        min_chars = int(target * 0.9)
        max_chars = int(target * 1.1)
        story_intro = get_story_intro_text()
        story_writing_spec = get_story_writing_spec_text()
        story_reminder = get_story_reminder_text(min_chars=min_chars)
        return (
            f"{story_intro}\n\n"
            "【核心要求】\n"
            f"1. **字数要求（强制）**：必须写足 {min_chars}-{max_chars} 字之间，目标 {target} 字。请务必写够长度，不要过早结束。\n"
            f"2. **模版**：{template_label}\n"
            f"3. **模版导向**：{story_focus}\n"
            f"4. **种类（最终）**：{effective_category}\n"
            f"5. **种类（界面）**：{category}\n"
            f"{alignment_block}\n"
            f"6. **风格倾向**：{style_value}\n"
            f"7. **创作主题/需求**：{requirement}\n\n"
            "【模版规则】\n"
            f"{story_rules}\n\n"
            f"{creativity_part}"
            "【写作规范】\n"
            f"{story_writing_spec}\n\n"
            "【去模板腔与专业度】\n"
            f"{writing_guardrails}\n\n"
            "【情感弧线与真人感】\n"
            f"{emotion_guardrails}\n\n"
            "【特别提醒】\n"
            f"{story_reminder}\n"
            f"{outline_part}\n\n"
            f"【参考资料】\n{ctx if ctx else '无特定资料，请根据主题自由创作。'}"
        )

    def _build_section_prompt(
        self,
        section,
        section_index,
        total_sections,
        previous_content,
        requirement,
        contexts,
        category,
        style_part,
        target_chars_per_section,
    ):
        ctx = "\n\n".join(f"【资料{i+1}】\n{c}" for i, c in enumerate(contexts)) if contexts else ""
        alignment_block, effective_category, _category_note = self._build_requirement_alignment_block(
            requirement,
            category,
            stage="section",
        )
        template = self._get_story_template_profile(requirement=requirement, category=effective_category)
        template_label = template.get("label", "默认模版")
        section_rules = self._format_story_rules(template.get("section_rules", []))
        writing_guardrails = build_non_ai_writing_guardrails()
        emotion_guardrails = build_emotion_arc_guidelines(stage="section")
        creativity_mode = self._get_story_creativity_mode()
        creativity_rules = build_story_creativity_block(
            creativity_mode,
            requirement=requirement,
            category=effective_category,
            style_hint=style_part,
            stage="section",
            nonce=self._get_story_creativity_nonce(),
            primary_template_key=template.get("key", ""),
        )
        creativity_part = (
            f"【创新引擎（{creativity_mode}）】\n{creativity_rules}\n\n"
            if creativity_rules
            else ""
        )
        style_value = style_part if style_part else "自动匹配模版风格"
        min_chars = int(target_chars_per_section * 0.85)
        max_chars = int(target_chars_per_section * 1.15)
        section_title = section["title"]
        section_items = "\n".join(f"  - {item}" for item in section["items"]) if section["items"] else ""
        context_hint = ""
        if section_index == 0:
            context_hint = "这是故事的开篇部分，需要引人入胜，设置场景和主要人物。"
        elif section_index == total_sections - 1:
            context_hint = f"这是故事的最后部分，需要收尾总结，呼应前文。\n\n前文概要：\n{previous_content[-500:] if previous_content else '无'}"
        else:
            context_hint = f"这是故事的第 {section_index + 1} 部分，需要承上启下，保持情节连贯。\n\n前文最后部分：\n{previous_content[-500:] if previous_content else '无'}"
        memory_context = self._build_story_memory_context(section_index, max_items=3)
        if memory_context:
            context_hint += (
                "\n\n【记忆账本（最近章节）】\n"
                f"{memory_context}\n"
                "- 必须保持人物状态、关系变化、未回收伏笔的一致性。"
            )
        section_intro = get_section_intro_text(section_no=section_index + 1, total_sections=total_sections)
        section_writing_spec = get_section_writing_spec_text()
        section_reminder = get_section_reminder_text(min_chars=min_chars)
        return (
            f"{section_intro}\n\n"
            f"【本节要求】\n"
            f"1. **字数**：必须写足 {min_chars}-{max_chars} 字，目标 {target_chars_per_section} 字\n"
            f"2. **章节主题**：{section_title}\n"
            f"3. **要点**：\n{section_items if section_items else '  根据标题自由发挥'}\n"
            f"4. **模版**：{template_label}\n"
            f"5. **种类（最终）**：{effective_category}\n"
            f"6. **种类（界面）**：{category}\n"
            f"{alignment_block}\n"
            f"7. **风格**：{style_value}\n\n"
            f"【模版规则】\n{section_rules}\n\n"
            f"{creativity_part}"
            f"【上下文】\n{context_hint}\n\n"
            "【写作规范】\n"
            f"{section_writing_spec}\n\n"
            f"【去模板腔与专业度】\n{writing_guardrails}\n\n"
            f"【情感弧线与真人感】\n{emotion_guardrails}\n\n"
            "【特别提醒】\n"
            f"{section_reminder}\n"
            f"主题/需求：{requirement}\n\n"
            + (f"【参考资料】\n{ctx}\n" if ctx else "")
            + "请直接开始写正文，不要任何前缀或标题："
        )

    def _canonical_story_preset_name(self, raw_name: str, cfg: dict) -> str:
        name = str(raw_name or "").strip()
        if not name:
            return "Custom"
        canonical = {
            "DeepSeek",
            "OpenAI",
            "Azure OpenAI",
            "Moonshot (Kimi)",
            "Zhipu AI (GLM)",
            "Baidu ERNIE",
            "Alibaba Qwen",
            "Custom",
        }
        if name in canonical:
            return name

        legacy_alias = {
            "Moonshot (鏈堜箣鏆楅潰)": "Moonshot (Kimi)",
            "Moonshot (月之暗面)": "Moonshot (Kimi)",
            "鏅鸿氨AI (GLM)": "Zhipu AI (GLM)",
            "智谱AI (GLM)": "Zhipu AI (GLM)",
            "鐧惧害鏂囧績": "Baidu ERNIE",
            "百度文心": "Baidu ERNIE",
            "闃块噷閫氫箟": "Alibaba Qwen",
            "阿里通义": "Alibaba Qwen",
            "鑷畾涔?": "Custom",
            "自定义": "Custom",
        }
        if name in legacy_alias:
            return legacy_alias[name]
        return name

    def _normalize_story_preset_names(self):
        presets = getattr(self, "api_presets", None)
        if not isinstance(presets, dict):
            return
        normalized = {}
        for raw_name, cfg in presets.items():
            if not isinstance(cfg, dict):
                continue
            name = self._canonical_story_preset_name(raw_name, cfg)
            if name not in normalized:
                normalized[name] = cfg
            else:
                existing = normalized[name]
                for key in ("key", "base_url", "model"):
                    if not existing.get(key) and cfg.get(key):
                        existing[key] = cfg[key]
        self.api_presets = normalized

    def _resolve_model_fetch_api_config(self):
        presets = getattr(self, "api_presets", None)
        if not isinstance(presets, dict) or not presets:
            return None, "", ""

        selected = ""
        if hasattr(self, "api_preset"):
            try:
                if hasattr(self, "_ui_get"):
                    selected = (self._ui_get(self.api_preset.get) or "").strip()
                else:
                    selected = (self.api_preset.get() or "").strip()
            except Exception as exc:
                logger.debug("Failed to read current api_preset: %s", exc)

        if selected and isinstance(presets.get(selected), dict):
            cfg = presets[selected]
            return selected, cfg.get("key", ""), cfg.get("base_url", "")

        for alias in ("Custom",):
            cfg = presets.get(alias)
            if isinstance(cfg, dict):
                return alias, cfg.get("key", ""), cfg.get("base_url", "")

        for name, cfg in presets.items():
            if isinstance(cfg, dict) and (cfg.get("key") or cfg.get("base_url")):
                return name, cfg.get("key", ""), cfg.get("base_url", "")

        return None, "", ""

    def _load_available_models(self):
        def task():
            try:
                import requests

                preset_name, api_key, base_url = self._resolve_model_fetch_api_config()
                if not api_key or not base_url:
                    logger.warning("Model fetch skipped: incomplete API config (preset=%s)", preset_name)
                    self._set_default_models()
                    return

                base_url = base_url.rstrip("/")
                candidates = [f"{base_url}/models"] if base_url.endswith("/v1") else [f"{base_url}/v1/models", f"{base_url}/models"]
                headers = {"Authorization": f"Bearer {api_key}", "User-Agent": "Mozilla/5.0"}
                last_status = None
                result = None
                for url in candidates:
                    try:
                        response = requests.get(url, headers=headers, timeout=10)
                        last_status = response.status_code
                        if response.status_code == 200:
                            result = response.json()
                            break
                    except Exception as exc:
                        logger.debug("Model list probe failed for %s: %s", url, exc)
                        continue

                if result is not None:
                    models = []
                    if isinstance(result, dict):
                        if isinstance(result.get("data"), list):
                            models = [m.get("id") or m.get("name") for m in result["data"] if isinstance(m, dict)]
                        elif isinstance(result.get("models"), list):
                            models = [m.get("id") or m.get("name") for m in result["models"] if isinstance(m, dict)]
                    elif isinstance(result, list):
                        models = [m.get("id") or m.get("name") for m in result if isinstance(m, dict)]

                    models = [m for m in models if m]
                    if models:
                        if hasattr(self, "combo_story_model"):
                            self._ui(self.combo_story_model.__setitem__, "values", models)
                            current = self._ui_get(self.story_model_var.get) if hasattr(self, "_ui_get") else self.story_model_var.get()
                            if current not in models:
                                self._ui(self.story_model_var.set, models[0])

                        if hasattr(self, "combo_char_model"):
                            self._ui(self.combo_char_model.__setitem__, "values", models)
                            current = self._ui_get(self.char_model_var.get) if hasattr(self, "_ui_get") else self.char_model_var.get()
                            if current not in models:
                                self._ui(self.char_model_var.set, models[0])

                        logger.info("Loaded %d models for story/character tabs (preset=%s)", len(models), preset_name)
                    else:
                        logger.warning("Model fetch returned no model entries; using defaults")
                        self._set_default_models()
                else:
                    logger.warning("Model fetch failed with status=%s; using defaults", last_status)
                    self._set_default_models()

            except Exception as exc:
                logger.warning("Failed to load available model list: %s", exc)
                self._set_default_models()

        threading.Thread(target=task, daemon=True).start()

    def _set_default_models(self):
        def _ui_call(func, *args):
            if hasattr(self, "_ui"):
                return self._ui(func, *args)
            return func(*args)

        default_models = [
            "claude-sonnet-4-5",
            "claude-sonnet-4-5-20250929",
            "claude-sonnet-4",
            "gemini-3-pro-preview",
            "gemini-3-flash-preview",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gpt-4o",
            "gpt-4o-mini",
        ]

        if hasattr(self, "combo_story_model"):
            _ui_call(self.combo_story_model.__setitem__, "values", default_models)
            current = self._ui_get(self.story_model_var.get) if hasattr(self, "_ui_get") else self.story_model_var.get()
            if current not in default_models:
                _ui_call(self.story_model_var.set, default_models[0])

        if hasattr(self, "combo_char_model"):
            _ui_call(self.combo_char_model.__setitem__, "values", default_models)
            current = self._ui_get(self.char_model_var.get) if hasattr(self, "_ui_get") else self.char_model_var.get()
            if current not in default_models:
                _ui_call(self.char_model_var.set, default_models[0])

        logger.info("Using default model list (%d entries)", len(default_models))
