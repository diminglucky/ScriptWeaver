"""Guardrails for story writing quality and title normalization.

This module is configuration-driven:
- Defaults are defined in code for resilience.
- Optional runtime override can be loaded from JSON file.
- No code edits are needed when tuning writing constraints.
"""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import re
from typing import Any


DEFAULT_STORY_GUARDRAILS: dict[str, Any] = {
    "non_ai": {
        "banned_phrases": [
            "首先",
            "其次",
            "最后",
            "总的来说",
            "总而言之",
            "不难发现",
            "值得一提的是",
            "在某种程度上",
        ],
        "guardrail_lines": [
            "禁止模板化论述口吻（如：{banned_phrases}），避免“先总后分”的说教结构；",
            "少用抽象判断词，多写可验证细节（时间/地点/动作/后果）；",
            "段落推进要靠事件和决策，不靠空泛感慨；",
            "对话符合人物身份与场景，不要全员同一种腔调；",
            "语气克制专业，避免夸张口号、鸡汤式收束。",
        ],
    },
    "outline_title": {
        "chapter_title_min_len": 4,
        "chapter_title_max_len": 12,
        "guardrail_lines": [
            "章节标题控制在 {chapter_title_min_len}-{chapter_title_max_len} 个汉字，避免过长说明句；",
            "标题优先使用“动作+冲突/结果”结构，避免空泛抽象词；",
            "禁止营销号措辞（如“震惊”“逆天”“看哭了”“绝了”）。",
        ],
    },
    "article_title": {
        "min_len": 12,
        "max_len": 20,
    },
}


_STORY_GUARDRAILS_CACHE: dict[str, Any] | None = None
_STORY_GUARDRAILS_CACHE_KEY: tuple[str, float] | None = None


def _resolve_guardrails_file() -> Path:
    raw = (os.getenv("STORY_GUARDRAILS_FILE", "") or "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.cwd() / "config" / "story_guardrails.json"


def _safe_int(value: Any, default: int, *, min_value: int, max_value: int) -> int:
    try:
        parsed = int(float(value))
    except Exception:
        parsed = int(default)
    return max(min_value, min(max_value, parsed))


def _normalize_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def _load_story_guardrails() -> dict[str, Any]:
    cfg = deepcopy(DEFAULT_STORY_GUARDRAILS)
    path = _resolve_guardrails_file()
    if not path.exists():
        return cfg

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return cfg
    if not isinstance(payload, dict):
        return cfg

    non_ai_raw = payload.get("non_ai", {})
    if isinstance(non_ai_raw, dict):
        banned = _normalize_text_list(non_ai_raw.get("banned_phrases"))
        if banned:
            cfg["non_ai"]["banned_phrases"] = banned
        lines = _normalize_text_list(non_ai_raw.get("guardrail_lines"))
        if lines:
            cfg["non_ai"]["guardrail_lines"] = lines

    outline_raw = payload.get("outline_title", {})
    if isinstance(outline_raw, dict):
        cfg["outline_title"]["chapter_title_min_len"] = _safe_int(
            outline_raw.get("chapter_title_min_len", cfg["outline_title"]["chapter_title_min_len"]),
            cfg["outline_title"]["chapter_title_min_len"],
            min_value=1,
            max_value=40,
        )
        cfg["outline_title"]["chapter_title_max_len"] = _safe_int(
            outline_raw.get("chapter_title_max_len", cfg["outline_title"]["chapter_title_max_len"]),
            cfg["outline_title"]["chapter_title_max_len"],
            min_value=2,
            max_value=80,
        )
        if cfg["outline_title"]["chapter_title_max_len"] < cfg["outline_title"]["chapter_title_min_len"]:
            cfg["outline_title"]["chapter_title_max_len"] = cfg["outline_title"]["chapter_title_min_len"]
        lines = _normalize_text_list(outline_raw.get("guardrail_lines"))
        if lines:
            cfg["outline_title"]["guardrail_lines"] = lines

    article_raw = payload.get("article_title", {})
    if isinstance(article_raw, dict):
        cfg["article_title"]["min_len"] = _safe_int(
            article_raw.get("min_len", cfg["article_title"]["min_len"]),
            cfg["article_title"]["min_len"],
            min_value=1,
            max_value=60,
        )
        cfg["article_title"]["max_len"] = _safe_int(
            article_raw.get("max_len", cfg["article_title"]["max_len"]),
            cfg["article_title"]["max_len"],
            min_value=2,
            max_value=100,
        )
        if cfg["article_title"]["max_len"] < cfg["article_title"]["min_len"]:
            cfg["article_title"]["max_len"] = cfg["article_title"]["min_len"]

    return cfg


def reload_story_guardrails() -> None:
    """Clear cache so next call reloads guardrails from file."""
    global _STORY_GUARDRAILS_CACHE, _STORY_GUARDRAILS_CACHE_KEY
    _STORY_GUARDRAILS_CACHE = None
    _STORY_GUARDRAILS_CACHE_KEY = None


def get_story_guardrails() -> dict[str, Any]:
    """Return merged guardrails config from defaults + optional JSON override."""
    global _STORY_GUARDRAILS_CACHE, _STORY_GUARDRAILS_CACHE_KEY
    path = _resolve_guardrails_file()
    path_key = str(path.resolve())
    mtime = -1.0
    if path.exists():
        try:
            mtime = float(path.stat().st_mtime)
        except Exception:
            mtime = -1.0
    key = (path_key, mtime)
    if _STORY_GUARDRAILS_CACHE is not None and _STORY_GUARDRAILS_CACHE_KEY == key:
        return _STORY_GUARDRAILS_CACHE

    _STORY_GUARDRAILS_CACHE = _load_story_guardrails()
    _STORY_GUARDRAILS_CACHE_KEY = key
    return _STORY_GUARDRAILS_CACHE


def get_non_ai_banned_phrases() -> list[str]:
    cfg = get_story_guardrails()
    phrases = cfg.get("non_ai", {}).get("banned_phrases", [])
    return _normalize_text_list(phrases)


def get_chapter_title_limits() -> tuple[int, int]:
    cfg = get_story_guardrails()
    outline_cfg = cfg.get("outline_title", {})
    min_len = _safe_int(outline_cfg.get("chapter_title_min_len", 4), 4, min_value=1, max_value=40)
    max_len = _safe_int(outline_cfg.get("chapter_title_max_len", 12), 12, min_value=2, max_value=80)
    if max_len < min_len:
        max_len = min_len
    return min_len, max_len


def get_article_title_limits() -> tuple[int, int]:
    cfg = get_story_guardrails()
    article_cfg = cfg.get("article_title", {})
    min_len = _safe_int(article_cfg.get("min_len", 12), 12, min_value=1, max_value=60)
    max_len = _safe_int(article_cfg.get("max_len", 20), 20, min_value=2, max_value=100)
    if max_len < min_len:
        max_len = min_len
    return min_len, max_len


def _render_guardrail_lines(lines: list[str], replacements: dict[str, str]) -> str:
    rendered: list[str] = []
    for line in lines:
        text = str(line or "").strip()
        if not text:
            continue
        for k, v in replacements.items():
            text = text.replace("{" + k + "}", v)
        if not text.startswith("- "):
            text = "- " + text
        rendered.append(text)
    return "\n".join(rendered).strip()


def build_non_ai_writing_guardrails() -> str:
    """Return practical writing constraints to reduce templated AI tone."""
    cfg = get_story_guardrails()
    lines = _normalize_text_list(cfg.get("non_ai", {}).get("guardrail_lines"))
    if not lines:
        lines = _normalize_text_list(DEFAULT_STORY_GUARDRAILS["non_ai"]["guardrail_lines"])
    banned = get_non_ai_banned_phrases()
    return _render_guardrail_lines(lines, {"banned_phrases": "、".join(banned)})


def build_outline_title_guardrails() -> str:
    """Return title-specific constraints for outline generation."""
    cfg = get_story_guardrails()
    lines = _normalize_text_list(cfg.get("outline_title", {}).get("guardrail_lines"))
    if not lines:
        lines = _normalize_text_list(DEFAULT_STORY_GUARDRAILS["outline_title"]["guardrail_lines"])
    chapter_min, chapter_max = get_chapter_title_limits()
    return _render_guardrail_lines(
        lines,
        {
            "chapter_title_min_len": str(chapter_min),
            "chapter_title_max_len": str(chapter_max),
        },
    )


def _clean_title_prefix(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    text = text.splitlines()[0].strip()
    text = re.sub(r"^\s*(标题|建议标题|知乎标题)\s*[：:]\s*", "", text)
    text = re.sub(r"^\s*\d+\s*[.、:：\-—]\s*", "", text)
    text = re.sub(r"^\s*第\s*[一二三四五六七八九十百千\d]+\s*[章节篇回]\s*[：:、.\-— ]*", "", text)
    text = text.strip().strip("\"'“”‘’「」『』《》【】[]()（）")
    text = re.sub(r"\s+", "", text)
    return text


def normalize_chapter_title(raw: str, *, min_len: int | None = None, max_len: int | None = None) -> str:
    """Normalize chapter title to short, compact form."""
    cfg_min, cfg_max = get_chapter_title_limits()
    min_len = cfg_min if min_len is None else _safe_int(min_len, cfg_min, min_value=1, max_value=40)
    max_len = cfg_max if max_len is None else _safe_int(max_len, cfg_max, min_value=2, max_value=80)
    if max_len < min_len:
        max_len = min_len

    text = _clean_title_prefix(raw)
    text = text.strip("，,。！？!?；;：:、-—· ")
    if not text:
        return "章节推进"

    if len(text) > max_len:
        parts = [p.strip() for p in re.split(r"[，,。！？!?；;：:、\-—|/]", text) if p.strip()]
        for part in parts:
            if min_len <= len(part) <= max_len:
                return part
        text = text[:max_len].rstrip("，,。！？!?；;：:、-—· ")

    if not text:
        return "章节推进"
    return text


def normalize_article_title(raw: str, *, min_len: int | None = None, max_len: int | None = None) -> str:
    """Normalize article title for Zhihu: concise and not overlong."""
    cfg_min, cfg_max = get_article_title_limits()
    min_len = cfg_min if min_len is None else _safe_int(min_len, cfg_min, min_value=1, max_value=60)
    max_len = cfg_max if max_len is None else _safe_int(max_len, cfg_max, min_value=2, max_value=100)
    if max_len < min_len:
        max_len = min_len

    text = _clean_title_prefix(raw)
    text = text.strip("，,。！？!?；;：:、-—· ")
    if not text:
        return ""

    if len(text) > max_len:
        parts = [p.strip() for p in re.split(r"[。！？!?；;|/]", text) if p.strip()]
        for part in parts:
            if min_len <= len(part) <= max_len:
                return part
        text = text[:max_len].rstrip("，,。！？!?；;：:、-—· ")

    # Keep very short titles untouched to avoid inventing content.
    return text
