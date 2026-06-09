"""Quality review and memory helpers for long-form story generation."""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from typing import Any


QUALITY_DIM_KEYS = (
    "realism",
    "detail",
    "coherence",
    "continuity",
    "escalation",
    "hook_density",
    "naturalness",
)


def _clip_score(value: Any, default: float = 7.0) -> float:
    try:
        score = float(value)
    except Exception:
        score = float(default)
    return max(1.0, min(10.0, score))


def _ensure_str_list(value: Any, max_items: int = 3) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            out.append(text)
        if len(out) >= max_items:
            break
    return out


def _extract_json_obj(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        pass

    # Try first balanced object.
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        fragment = text[start : end + 1]
        try:
            payload = json.loads(fragment)
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}
    return {}


def parse_quality_review(raw: str) -> dict[str, Any]:
    """Parse model review output into stable structured scores."""
    payload = _extract_json_obj(raw)
    scores_raw = payload.get("scores", {}) if isinstance(payload, dict) else {}
    if not isinstance(scores_raw, dict):
        scores_raw = {}

    scores = {
        "realism": _clip_score(scores_raw.get("realism", payload.get("realism", 7.0))),
        "detail": _clip_score(scores_raw.get("detail", payload.get("detail", 7.0))),
        "coherence": _clip_score(scores_raw.get("coherence", payload.get("coherence", 7.0))),
        "continuity": _clip_score(scores_raw.get("continuity", payload.get("continuity", 7.0))),
        "escalation": _clip_score(scores_raw.get("escalation", payload.get("escalation", 7.0))),
        "hook_density": _clip_score(scores_raw.get("hook_density", payload.get("hook_density", 7.0))),
        "naturalness": _clip_score(scores_raw.get("naturalness", payload.get("naturalness", 7.0))),
    }
    avg_score = round(sum(scores.values()) / float(len(scores)), 2)

    strengths = _ensure_str_list(payload.get("strengths"), max_items=3)
    issues = _ensure_str_list(payload.get("issues"), max_items=3)
    key_fix = str(payload.get("key_fix", "") or "").strip()

    return {
        "scores": scores,
        "avg_score": avg_score,
        "strengths": strengths,
        "issues": issues,
        "key_fix": key_fix,
    }


def should_polish(
    review: dict[str, Any],
    *,
    min_avg_score: float = 7.4,
    min_dimension_score: float = 6.8,
) -> bool:
    if not isinstance(review, dict):
        return True
    try:
        avg = float(review.get("avg_score", 0.0))
    except Exception:
        avg = 0.0
    scores = review.get("scores", {})
    if not isinstance(scores, dict):
        scores = {}

    if avg < min_avg_score:
        return True
    for key in QUALITY_DIM_KEYS:
        try:
            dim = float(scores.get(key, 0.0))
        except Exception:
            dim = 0.0
        if dim < min_dimension_score:
            return True
    return False


def parse_memory_entry(raw: str) -> dict[str, Any]:
    """Parse memory extraction output and normalize list fields."""
    payload = _extract_json_obj(raw)
    if not payload:
        return {}

    summary = str(payload.get("summary", "") or "").strip()
    plot_points = _ensure_str_list(payload.get("plot_points"), max_items=4)
    relation_changes = _ensure_str_list(payload.get("relation_changes"), max_items=3)
    unresolved_hooks = _ensure_str_list(payload.get("unresolved_hooks"), max_items=3)
    state_shift = str(payload.get("state_shift", "") or "").strip()
    character_states = _ensure_str_list(payload.get("character_states"), max_items=5)
    timeline_events = _ensure_str_list(payload.get("timeline_events"), max_items=5)
    open_threads = _ensure_str_list(payload.get("open_threads"), max_items=5)

    return {
        "summary": summary,
        "plot_points": plot_points,
        "relation_changes": relation_changes,
        "unresolved_hooks": unresolved_hooks,
        "state_shift": state_shift,
        "character_states": character_states,
        "timeline_events": timeline_events,
        "open_threads": open_threads,
    }


def normalize_memory_entry(entry: dict[str, Any], *, chapter_index: int, chapter_title: str) -> dict[str, Any]:
    """Ensure memory row has stable schema for persistence and prompt use."""
    if not isinstance(entry, dict):
        entry = {}
    summary = str(entry.get("summary", "") or "").strip()
    plot_points = _ensure_str_list(entry.get("plot_points"), max_items=4)
    relation_changes = _ensure_str_list(entry.get("relation_changes"), max_items=3)
    unresolved_hooks = _ensure_str_list(entry.get("unresolved_hooks"), max_items=3)
    state_shift = str(entry.get("state_shift", "") or "").strip()
    character_states = _ensure_str_list(entry.get("character_states"), max_items=5)
    timeline_events = _ensure_str_list(entry.get("timeline_events"), max_items=5)
    open_threads = _ensure_str_list(entry.get("open_threads"), max_items=5)

    return {
        "chapter_index": max(0, int(chapter_index)),
        "chapter_title": str(chapter_title or "").strip(),
        "summary": summary,
        "plot_points": plot_points,
        "relation_changes": relation_changes,
        "unresolved_hooks": unresolved_hooks,
        "state_shift": state_shift,
        "character_states": character_states,
        "timeline_events": timeline_events,
        "open_threads": open_threads,
    }


def format_memory_context(entries: list[dict[str, Any]], max_entries: int = 3) -> str:
    if not isinstance(entries, list):
        return ""
    rows = [x for x in entries if isinstance(x, dict)]
    if not rows:
        return ""
    rows = rows[-max(1, int(max_entries)) :]

    lines: list[str] = []
    for row in rows:
        idx = int(row.get("chapter_index", 0)) + 1
        title = str(row.get("chapter_title", "") or "").strip() or f"第{idx}章"
        summary = str(row.get("summary", "") or "").strip()
        if summary:
            lines.append(f"- 第{idx}章《{title}》摘要：{summary}")
        relation_changes = row.get("relation_changes", [])
        if isinstance(relation_changes, list) and relation_changes:
            lines.append(f"  关系变化：{'；'.join(str(x) for x in relation_changes[:2])}")
        unresolved = row.get("unresolved_hooks", [])
        if isinstance(unresolved, list) and unresolved:
            lines.append(f"  未回收伏笔：{'；'.join(str(x) for x in unresolved[:2])}")
        character_states = row.get("character_states", [])
        if isinstance(character_states, list) and character_states:
            lines.append(f"  人物状态：{'；'.join(str(x) for x in character_states[:2])}")
        timeline_events = row.get("timeline_events", [])
        if isinstance(timeline_events, list) and timeline_events:
            lines.append(f"  时间线：{'；'.join(str(x) for x in timeline_events[:2])}")
        open_threads = row.get("open_threads", [])
        if isinstance(open_threads, list) and open_threads:
            lines.append(f"  待处理线索：{'；'.join(str(x) for x in open_threads[:2])}")
    return "\n".join(lines).strip()


def strip_duplicate_lines(text: str) -> str:
    """Small dedupe pass for rewritten sections."""
    lines = str(text or "").splitlines()
    cleaned: list[str] = []
    seen: set[str] = set()
    for line in lines:
        sig = re.sub(r"\s+", " ", line.strip()).lower()
        if not sig:
            cleaned.append(line.rstrip())
            continue
        if sig in seen:
            continue
        seen.add(sig)
        cleaned.append(line.rstrip())
    result = "\n".join(cleaned).strip()
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result


def normalize_sentence_signature(text: str) -> str:
    """Normalize sentence for fuzzy duplicate checks."""
    value = str(text or "").strip().lower()
    if not value:
        return ""
    value = re.sub(r"[“”\"'`‘’]", "", value)
    value = re.sub(r"[，。！？!?；;：:、\-—…（）()\[\]{}<>《》【】\s]+", "", value)
    return value


def extract_last_sentence(text: str, *, max_chars: int = 220) -> str:
    """Extract last complete sentence from text tail."""
    raw = str(text or "").strip()
    if not raw:
        return ""
    tail = raw[-max(80, int(max_chars)) :]
    parts = re.findall(r"[^。！？!?…\n]+[。！？!?…]?", tail)
    parts = [p.strip() for p in parts if p and p.strip()]
    if not parts:
        return tail.strip()
    for item in reversed(parts):
        cleaned = item.strip()
        if len(cleaned) >= 8:
            return cleaned
    return parts[-1]


def extract_first_sentence(text: str, *, max_chars: int = 220) -> str:
    """Extract first complete sentence from text head."""
    raw = str(text or "").strip()
    if not raw:
        return ""
    head = raw[: max(80, int(max_chars))]
    parts = re.findall(r"[^。！？!?…\n]+[。！？!?…]?", head)
    parts = [p.strip() for p in parts if p and p.strip()]
    if not parts:
        return head.strip()
    for item in parts:
        cleaned = item.strip()
        if len(cleaned) >= 8:
            return cleaned
    return parts[0]


def is_redundant_transition_head(previous_tail: str, current_head: str, *, min_shared: int = 12) -> bool:
    """Detect whether current opening is too similar to previous chapter tail."""
    prev_sig = normalize_sentence_signature(previous_tail)
    head_sig = normalize_sentence_signature(current_head)
    if not prev_sig or not head_sig:
        return False

    shared = min(len(prev_sig), len(head_sig))
    if shared >= min_shared and (prev_sig in head_sig or head_sig in prev_sig):
        return True

    ratio = SequenceMatcher(None, prev_sig[:220], head_sig[:220]).ratio()
    return ratio >= 0.84
