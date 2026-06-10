"""Requirement/category alignment helpers for story prompts."""

from __future__ import annotations

import os
import re

from ...helpers.story_category_signals import (
    get_story_category_signals,
    infer_story_category,
    normalize_story_category_label,
    score_story_category,
)

from ...helpers.story_templates import (
    DEFAULT_STORY_TEMPLATE_STRATEGY,
    normalize_story_template_strategy,
)
from ...helpers.story_writing_guardrails import normalize_chapter_title

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


class StoryPromptAlignmentMixin:
    """Prompt alignment and requirement-anchor helpers."""
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
        return score_story_category(requirement, normalize_story_category_label(category))

    def _infer_category_from_requirement(self, requirement: str) -> tuple[str, int]:
        return infer_story_category(requirement)

    def _resolve_effective_story_category(self, requirement: str, selected_category: str) -> tuple[str, str]:
        selected = normalize_story_category_label(selected_category)
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
            # 优化⑥：合并目录对齐到生成prompt，加强约束
            stage_rule += "\n- 严禁空洞标题：不得使用“第一章：冲突爆发”“第二章：关系升级”等通用模版。"
            stage_rule += "\n- 必须包含具体名词：每章标题必须包含该章节涉及的人物名、核心道具或特定地点。"
            stage_rule += "\n- 强因果链：上一章的悬念必须在下一章有明确交代，且下一章必须产生新的推动力。"
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
        category_keywords = get_story_category_signals(effective_category)
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
            for keyword in get_story_category_signals(effective_category):
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

