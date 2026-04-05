"""Config-driven profile for story review/polish/memory/emotion prompts."""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_STORY_PIPELINE_PROFILE: dict[str, Any] = {
    "emotion_arc": {
        "story_lines": [
            "主角情绪至少经历三段变化（压抑/犹豫→爆发/决断→余震/代价），每段要有事件触发；",
            "关键情绪通过动作、停顿、对话细节体现，不直接喊口号；",
            "高潮必须体现选择成本，结尾保留情绪余波而非说教总结。",
        ],
        "section_lines": [
            "本节要明确情绪起点与终点，至少发生一次可感知的情绪位移；",
            "用微动作和场景细节承载情绪变化，避免直接解释“他很痛苦/她很感动”；",
            "章节结尾留一个情绪钩子，驱动下一章。",
        ],
    },
    "quality_review": {
        "dimensions": [
            {"key": "realism", "label": "真实感"},
            {"key": "detail", "label": "细节密度"},
            {"key": "coherence", "label": "逻辑连贯"},
            {"key": "continuity", "label": "跨章衔接"},
            {"key": "naturalness", "label": "语言自然度"},
        ],
        "json_schema": (
            "{\"scores\":{\"realism\":0,\"detail\":0,\"coherence\":0,\"continuity\":0,\"naturalness\":0},"
            "\"strengths\":[\"\"],\"issues\":[\"\"],\"key_fix\":\"\"}"
        ),
        "rules": [
            "issues 至少给1条且可执行；",
            "key_fix 20字以内；",
            "禁止输出 JSON 以外内容。",
        ],
    },
    "polish": {
        "fallback_fix": "语言模板腔和细节不足",
        "rules": [
            "保留原剧情顺序与关键事件，不新增大剧情；",
            "优先修复：{fix_goal}；",
            "检查并修复跨章衔接：本章开头应承接上章尾句后的动作/情绪，避免重复叙述；",
            "若提供“连贯性资料”，优先修复与历史设定冲突的称谓/地点/关系，不得自相矛盾；",
            "增加可感知细节（动作/环境/心理），减少空泛评价句；",
            "语言自然克制，禁止模板腔（如：首先/其次/最后/总的来说）；",
            "字数控制在 {target_low}-{target_high} 字附近（当前约{current_chars}字）；",
            "只输出最终章节正文，不要解释。",
        ],
    },
    "transition": {
        "section_lines": [
            "中间章节开头必须承接上一章末尾动作或情绪，不得复制上一章原句；",
            "首段最多1句背景回顾，核心篇幅用于推进新事件；",
            "人物立场、关系变化、已揭示事实必须与记忆账本一致，禁止反向改设定。",
        ],
    },
    "memory_ledger": {
        "json_schema": (
            "{\"summary\":\"\",\"plot_points\":[\"\"],\"relation_changes\":[\"\"],"
            "\"unresolved_hooks\":[\"\"],\"state_shift\":\"\"}"
        ),
        "rules": [
            "summary 40-120字；",
            "plot_points 最多4条，聚焦事实事件；",
            "relation_changes 最多3条，写清人物关系变化；",
            "unresolved_hooks 最多3条，写未回收问题；",
            "state_shift 30字以内；",
            "禁止输出 JSON 以外内容。",
        ],
    },
}


_STORY_PIPELINE_PROFILE_CACHE: dict[str, Any] | None = None
_STORY_PIPELINE_PROFILE_CACHE_KEY: tuple[str, float] | None = None


def _resolve_profile_file() -> Path:
    raw = (os.getenv("STORY_PIPELINE_PROFILE_FILE", "") or "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.cwd() / "config" / "story_pipeline_profile.json"


def _normalize_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def _normalize_dimensions(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict):
            key = str(item.get("key", "") or "").strip()
            label = str(item.get("label", "") or "").strip()
            if key and label:
                rows.append({"key": key, "label": label})
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            key = str(item[0] or "").strip()
            label = str(item[1] or "").strip()
            if key and label:
                rows.append({"key": key, "label": label})
    return rows


def _ensure_quality_dimensions(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Ensure core quality dimensions are always present, even with custom profile overrides."""
    merged: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        key = str(row.get("key", "") or "").strip()
        label = str(row.get("label", "") or "").strip()
        if not key or not label or key in seen:
            continue
        merged.append({"key": key, "label": label})
        seen.add(key)

    default_dims = _normalize_dimensions(DEFAULT_STORY_PIPELINE_PROFILE["quality_review"]["dimensions"])
    for row in default_dims:
        key = row["key"]
        if key in seen:
            continue
        merged.append({"key": key, "label": row["label"]})
        seen.add(key)
    return merged


def _merge_section_list(cfg: dict[str, Any], payload: dict[str, Any], section: str, key: str) -> None:
    section_payload = payload.get(section, {})
    if not isinstance(section_payload, dict):
        return
    lines = _normalize_text_list(section_payload.get(key))
    if lines:
        cfg[section][key] = lines


def _load_profile() -> dict[str, Any]:
    cfg = deepcopy(DEFAULT_STORY_PIPELINE_PROFILE)
    path = _resolve_profile_file()
    if not path.exists():
        return cfg
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return cfg
    if not isinstance(payload, dict):
        return cfg

    _merge_section_list(cfg, payload, "emotion_arc", "story_lines")
    _merge_section_list(cfg, payload, "emotion_arc", "section_lines")
    _merge_section_list(cfg, payload, "transition", "section_lines")
    _merge_section_list(cfg, payload, "quality_review", "rules")
    _merge_section_list(cfg, payload, "polish", "rules")
    _merge_section_list(cfg, payload, "memory_ledger", "rules")

    quality_raw = payload.get("quality_review", {})
    if isinstance(quality_raw, dict):
        dims = _normalize_dimensions(quality_raw.get("dimensions"))
        if dims:
            cfg["quality_review"]["dimensions"] = dims
        schema = str(quality_raw.get("json_schema", "") or "").strip()
        if schema:
            cfg["quality_review"]["json_schema"] = schema

    polish_raw = payload.get("polish", {})
    if isinstance(polish_raw, dict):
        fallback_fix = str(polish_raw.get("fallback_fix", "") or "").strip()
        if fallback_fix:
            cfg["polish"]["fallback_fix"] = fallback_fix

    memory_raw = payload.get("memory_ledger", {})
    if isinstance(memory_raw, dict):
        schema = str(memory_raw.get("json_schema", "") or "").strip()
        if schema:
            cfg["memory_ledger"]["json_schema"] = schema

    return cfg


def reload_story_pipeline_profile() -> None:
    """Clear cache so next call reloads profile from disk."""
    global _STORY_PIPELINE_PROFILE_CACHE, _STORY_PIPELINE_PROFILE_CACHE_KEY
    _STORY_PIPELINE_PROFILE_CACHE = None
    _STORY_PIPELINE_PROFILE_CACHE_KEY = None


def get_story_pipeline_profile() -> dict[str, Any]:
    """Return merged profile from defaults + optional JSON override."""
    global _STORY_PIPELINE_PROFILE_CACHE, _STORY_PIPELINE_PROFILE_CACHE_KEY
    path = _resolve_profile_file()
    path_key = str(path.resolve())
    mtime = -1.0
    if path.exists():
        try:
            mtime = float(path.stat().st_mtime)
        except Exception:
            mtime = -1.0
    key = (path_key, mtime)
    if _STORY_PIPELINE_PROFILE_CACHE is not None and _STORY_PIPELINE_PROFILE_CACHE_KEY == key:
        return _STORY_PIPELINE_PROFILE_CACHE
    _STORY_PIPELINE_PROFILE_CACHE = _load_profile()
    _STORY_PIPELINE_PROFILE_CACHE_KEY = key
    return _STORY_PIPELINE_PROFILE_CACHE


def _format_lines(lines: list[str], *, numbered: bool = False) -> str:
    out: list[str] = []
    for idx, line in enumerate(lines, start=1):
        text = str(line or "").strip()
        if not text:
            continue
        if numbered:
            out.append(f"{idx}) {text}")
        else:
            if not text.startswith("- "):
                text = "- " + text
            out.append(text)
    return "\n".join(out).strip()


def build_emotion_arc_guidelines(stage: str = "story") -> str:
    cfg = get_story_pipeline_profile()
    emotion_cfg = cfg.get("emotion_arc", {})
    if not isinstance(emotion_cfg, dict):
        emotion_cfg = {}
    key = "section_lines" if stage == "section" else "story_lines"
    lines = _normalize_text_list(emotion_cfg.get(key))
    if not lines:
        lines = _normalize_text_list(DEFAULT_STORY_PIPELINE_PROFILE["emotion_arc"][key])
    return _format_lines(lines, numbered=False)


def build_section_transition_guidelines() -> str:
    cfg = get_story_pipeline_profile()
    transition_cfg = cfg.get("transition", {})
    if not isinstance(transition_cfg, dict):
        transition_cfg = {}
    lines = _normalize_text_list(transition_cfg.get("section_lines"))
    if not lines:
        lines = _normalize_text_list(DEFAULT_STORY_PIPELINE_PROFILE["transition"]["section_lines"])
    return _format_lines(lines, numbered=False)


def build_quality_review_prompt(*, requirement: str, category: str, section_title: str, preview: str) -> str:
    cfg = get_story_pipeline_profile()
    quality_cfg = cfg.get("quality_review", {})
    if not isinstance(quality_cfg, dict):
        quality_cfg = {}

    dimensions = _normalize_dimensions(quality_cfg.get("dimensions"))
    if not dimensions:
        dimensions = _normalize_dimensions(DEFAULT_STORY_PIPELINE_PROFILE["quality_review"]["dimensions"])
    dimensions = _ensure_quality_dimensions(dimensions)
    dims_text = ", ".join(f"{row['key']}({row['label']})" for row in dimensions)

    schema = str(quality_cfg.get("json_schema", "") or "").strip()
    if not schema:
        schema = str(DEFAULT_STORY_PIPELINE_PROFILE["quality_review"]["json_schema"])

    rules = _normalize_text_list(quality_cfg.get("rules"))
    if not rules:
        rules = _normalize_text_list(DEFAULT_STORY_PIPELINE_PROFILE["quality_review"]["rules"])
    rules_text = _format_lines(rules, numbered=True)

    return (
        "你是严格的中文小说编辑，请评估以下章节文本质量，并仅返回 JSON。\n"
        f"评分维度（1-10）：{dims_text}。\n"
        "返回格式：\n"
        f"{schema}\n"
        "要求：\n"
        f"{rules_text}\n\n"
        f"主题：{requirement}\n"
        f"题材：{category}\n"
        f"章节标题：{section_title}\n"
        f"章节文本：\n{preview}\n"
    )


def build_polish_prompt(
    *,
    section_title: str,
    section_content: str,
    fix_goal: str,
    target_low: int,
    target_high: int,
    current_chars: int,
    previous_tail: str = "",
    continuity_context: str = "",
) -> str:
    cfg = get_story_pipeline_profile()
    polish_cfg = cfg.get("polish", {})
    if not isinstance(polish_cfg, dict):
        polish_cfg = {}

    rules = _normalize_text_list(polish_cfg.get("rules"))
    if not rules:
        rules = _normalize_text_list(DEFAULT_STORY_PIPELINE_PROFILE["polish"]["rules"])
    lines: list[str] = []
    for line in rules:
        text = line.replace("{fix_goal}", fix_goal)
        text = text.replace("{target_low}", str(target_low))
        text = text.replace("{target_high}", str(target_high))
        text = text.replace("{current_chars}", str(current_chars))
        lines.append(text)
    rules_text = _format_lines(lines, numbered=True)

    continuity_lines: list[str] = []
    tail = str(previous_tail or "").strip()
    if tail:
        continuity_lines.append(f"- 上章收束句：{tail}")
    continuity = str(continuity_context or "").strip()
    if continuity:
        continuity_lines.append(continuity)
    continuity_block = ""
    if continuity_lines:
        continuity_block = (
            "【连贯性资料（必须遵守）】\n"
            + "\n".join(continuity_lines)
            + "\n\n"
        )

    return (
        "你是中文小说精修编辑。请在不改变剧情事实和人物设定的前提下，"
        "对下面章节做一次“真实细腻化”重写。\n"
        "硬性要求：\n"
        f"{rules_text}\n\n"
        f"{continuity_block}"
        f"章节标题：{section_title}\n"
        f"原文：\n{section_content}\n"
    )


def get_polish_fallback_fix() -> str:
    cfg = get_story_pipeline_profile()
    polish_cfg = cfg.get("polish", {})
    if not isinstance(polish_cfg, dict):
        polish_cfg = {}
    fallback = str(polish_cfg.get("fallback_fix", "") or "").strip()
    if fallback:
        return fallback
    return str(DEFAULT_STORY_PIPELINE_PROFILE["polish"]["fallback_fix"])


def build_memory_ledger_prompt(*, section_title: str, preview: str) -> str:
    cfg = get_story_pipeline_profile()
    memory_cfg = cfg.get("memory_ledger", {})
    if not isinstance(memory_cfg, dict):
        memory_cfg = {}

    schema = str(memory_cfg.get("json_schema", "") or "").strip()
    if not schema:
        schema = str(DEFAULT_STORY_PIPELINE_PROFILE["memory_ledger"]["json_schema"])
    rules = _normalize_text_list(memory_cfg.get("rules"))
    if not rules:
        rules = _normalize_text_list(DEFAULT_STORY_PIPELINE_PROFILE["memory_ledger"]["rules"])
    rules_text = _format_lines(rules, numbered=True)

    return (
        "你是小说连续性编辑。请从以下章节提取“记忆账本”，并仅返回 JSON：\n"
        f"{schema}\n"
        "要求：\n"
        f"{rules_text}\n\n"
        f"章节标题：{section_title}\n"
        f"章节文本：\n{preview}\n"
    )
