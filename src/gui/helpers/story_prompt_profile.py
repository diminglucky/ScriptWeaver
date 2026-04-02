"""Config-driven prompt skeleton for outline/story/section generation."""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_STORY_PROMPT_PROFILE: dict[str, Any] = {
    "outline": {
        "intro": "基于资料产出一个可执行的写作目录（仅目录，不要正文）。",
        "core_requirements": [
            "只输出 {suggested_sections} 个主要章节标题，不要子标题、不要要点列表",
            "每个章节用数字编号（1. 2. 3. ...）",
            "章节名简短有力（{chapter_title_min_len}-{chapter_title_max_len}字），能体现故事发展",
            "结构要符合：开端 → 发展 → 高潮 → 结局",
            "不要写\"第一章\"、\"第二章\"，直接写章节内容主题",
        ],
        "output_intro": "请直接输出章节列表，格式如下：",
        "output_example_lines": [
            "1. 平静的开端",
            "2. 意外降临",
            "3. 危机爆发",
            "4. 绝地反击",
            "5. 尘埃落定",
        ],
    },
    "story": {
        "intro": "请基于以下资料，创作一篇长篇中文故事。",
        "writing_spec_lines": [
            "语言自然口语化，逻辑清晰，富有生活气息；",
            "不要写标题，直接进入正文；段落衔接自然，避免列表化与生硬小标题；",
            "开头要抓人，中段有冲突与反转，结尾有观点或反思；",
            "开篇前150字必须抛出异常信息、冲突或悬念，不要先铺陈背景；",
            "每3-5段必须推进一次情节（冲突升级/关键决策/关系反转），禁止流水账；",
            "关键场景需同时写到动作、心理、环境细节，避免空泛叙述；",
            "结尾必须回扣开头悬念，并给出可传播的观点或情绪余味；",
            "输出为纯文本，不使用任何 Markdown 标记（不要 #、*、-、**、``` 等）；",
            "即使参考目录，也不要显式输出分节标题；将要点融合到连续正文中；",
            "可以适当分段，但段落之间要自然过渡。",
        ],
        "reminder_template": "请一定要写到至少 {min_chars} 字，不要因为觉得写完了就停止。如果还没达到字数，请继续展开细节、增加情节、深化描写。",
    },
    "section": {
        "intro_template": "请继续创作故事的第 {section_no}/{total_sections} 部分。",
        "writing_spec_lines": [
            "语言自然口语化，逻辑清晰，富有生活气息",
            "**不要写章节标题**，直接进入正文内容",
            "与前文保持人物、情节、语气的连贯性",
            "本节至少设计一个新的冲突点或信息反转，推动故事前进",
            "本节结尾要留下下一节的悬念钩子，避免平铺直叙收尾",
            "段落衔接自然，避免列表化",
            "输出为纯文本，不使用任何 Markdown 标记",
            "如果前文已有内容，本节要自然承接，不要重复前文情节",
        ],
        "reminder_template": "请写够 {min_chars} 字以上，展开细节描写和情节发展。",
    },
}


_STORY_PROMPT_PROFILE_CACHE: dict[str, Any] | None = None
_STORY_PROMPT_PROFILE_CACHE_KEY: tuple[str, float] | None = None


def _resolve_profile_file() -> Path:
    raw = (os.getenv("STORY_PROMPT_PROFILE_FILE", "") or "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.cwd() / "config" / "story_prompt_profile.json"


def _normalize_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def _merge_section_text(cfg: dict[str, Any], payload: dict[str, Any], section: str, key: str) -> None:
    section_payload = payload.get(section, {})
    if not isinstance(section_payload, dict):
        return
    text = str(section_payload.get(key, "") or "").strip()
    if text:
        cfg[section][key] = text


def _merge_section_list(cfg: dict[str, Any], payload: dict[str, Any], section: str, key: str) -> None:
    section_payload = payload.get(section, {})
    if not isinstance(section_payload, dict):
        return
    rows = _normalize_text_list(section_payload.get(key))
    if rows:
        cfg[section][key] = rows


def _load_profile() -> dict[str, Any]:
    cfg = deepcopy(DEFAULT_STORY_PROMPT_PROFILE)
    path = _resolve_profile_file()
    if not path.exists():
        return cfg
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return cfg
    if not isinstance(payload, dict):
        return cfg

    _merge_section_text(cfg, payload, "outline", "intro")
    _merge_section_list(cfg, payload, "outline", "core_requirements")
    _merge_section_text(cfg, payload, "outline", "output_intro")
    _merge_section_list(cfg, payload, "outline", "output_example_lines")

    _merge_section_text(cfg, payload, "story", "intro")
    _merge_section_list(cfg, payload, "story", "writing_spec_lines")
    _merge_section_text(cfg, payload, "story", "reminder_template")

    _merge_section_text(cfg, payload, "section", "intro_template")
    _merge_section_list(cfg, payload, "section", "writing_spec_lines")
    _merge_section_text(cfg, payload, "section", "reminder_template")
    return cfg


def reload_story_prompt_profile() -> None:
    """Clear cache so next call reloads prompt profile from disk."""
    global _STORY_PROMPT_PROFILE_CACHE, _STORY_PROMPT_PROFILE_CACHE_KEY
    _STORY_PROMPT_PROFILE_CACHE = None
    _STORY_PROMPT_PROFILE_CACHE_KEY = None


def get_story_prompt_profile() -> dict[str, Any]:
    """Return merged prompt profile from defaults + optional JSON override."""
    global _STORY_PROMPT_PROFILE_CACHE, _STORY_PROMPT_PROFILE_CACHE_KEY
    path = _resolve_profile_file()
    path_key = str(path.resolve())
    mtime = -1.0
    if path.exists():
        try:
            mtime = float(path.stat().st_mtime)
        except Exception:
            mtime = -1.0
    key = (path_key, mtime)
    if _STORY_PROMPT_PROFILE_CACHE is not None and _STORY_PROMPT_PROFILE_CACHE_KEY == key:
        return _STORY_PROMPT_PROFILE_CACHE
    _STORY_PROMPT_PROFILE_CACHE = _load_profile()
    _STORY_PROMPT_PROFILE_CACHE_KEY = key
    return _STORY_PROMPT_PROFILE_CACHE


def _render_lines(lines: list[str], *, prefix: str = "- ", replacements: dict[str, str] | None = None) -> str:
    repl = replacements or {}
    out: list[str] = []
    for line in lines:
        text = str(line or "").strip()
        if not text:
            continue
        for k, v in repl.items():
            text = text.replace("{" + k + "}", v)
        if prefix and not text.startswith(prefix):
            text = prefix + text
        out.append(text)
    return "\n".join(out).strip()


def get_outline_intro_text() -> str:
    cfg = get_story_prompt_profile()
    return str(cfg.get("outline", {}).get("intro", "") or "").strip() or str(
        DEFAULT_STORY_PROMPT_PROFILE["outline"]["intro"]
    )


def get_outline_core_requirements_text(*, suggested_sections: str, chapter_title_min_len: int, chapter_title_max_len: int) -> str:
    cfg = get_story_prompt_profile()
    lines = _normalize_text_list(cfg.get("outline", {}).get("core_requirements"))
    if not lines:
        lines = _normalize_text_list(DEFAULT_STORY_PROMPT_PROFILE["outline"]["core_requirements"])
    return _render_lines(
        lines,
        prefix="- ",
        replacements={
            "suggested_sections": str(suggested_sections),
            "chapter_title_min_len": str(chapter_title_min_len),
            "chapter_title_max_len": str(chapter_title_max_len),
        },
    )


def get_outline_output_example_text() -> str:
    cfg = get_story_prompt_profile()
    intro = str(cfg.get("outline", {}).get("output_intro", "") or "").strip() or str(
        DEFAULT_STORY_PROMPT_PROFILE["outline"]["output_intro"]
    )
    lines = _normalize_text_list(cfg.get("outline", {}).get("output_example_lines"))
    if not lines:
        lines = _normalize_text_list(DEFAULT_STORY_PROMPT_PROFILE["outline"]["output_example_lines"])
    examples = _render_lines(lines, prefix="", replacements=None)
    return f"{intro}\n{examples}".strip()


def get_story_intro_text() -> str:
    cfg = get_story_prompt_profile()
    return str(cfg.get("story", {}).get("intro", "") or "").strip() or str(
        DEFAULT_STORY_PROMPT_PROFILE["story"]["intro"]
    )


def get_story_writing_spec_text() -> str:
    cfg = get_story_prompt_profile()
    lines = _normalize_text_list(cfg.get("story", {}).get("writing_spec_lines"))
    if not lines:
        lines = _normalize_text_list(DEFAULT_STORY_PROMPT_PROFILE["story"]["writing_spec_lines"])
    return _render_lines(lines, prefix="- ", replacements=None)


def get_story_reminder_text(*, min_chars: int) -> str:
    cfg = get_story_prompt_profile()
    tpl = str(cfg.get("story", {}).get("reminder_template", "") or "").strip() or str(
        DEFAULT_STORY_PROMPT_PROFILE["story"]["reminder_template"]
    )
    return tpl.replace("{min_chars}", str(int(min_chars)))


def get_section_intro_text(*, section_no: int, total_sections: int) -> str:
    cfg = get_story_prompt_profile()
    tpl = str(cfg.get("section", {}).get("intro_template", "") or "").strip() or str(
        DEFAULT_STORY_PROMPT_PROFILE["section"]["intro_template"]
    )
    return (
        tpl.replace("{section_no}", str(int(section_no)))
        .replace("{total_sections}", str(int(total_sections)))
        .strip()
    )


def get_section_writing_spec_text() -> str:
    cfg = get_story_prompt_profile()
    lines = _normalize_text_list(cfg.get("section", {}).get("writing_spec_lines"))
    if not lines:
        lines = _normalize_text_list(DEFAULT_STORY_PROMPT_PROFILE["section"]["writing_spec_lines"])
    return _render_lines(lines, prefix="- ", replacements=None)


def get_section_reminder_text(*, min_chars: int) -> str:
    cfg = get_story_prompt_profile()
    tpl = str(cfg.get("section", {}).get("reminder_template", "") or "").strip() or str(
        DEFAULT_STORY_PROMPT_PROFILE["section"]["reminder_template"]
    )
    return tpl.replace("{min_chars}", str(int(min_chars)))

