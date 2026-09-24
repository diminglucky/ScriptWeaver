"""Normalize generated story text before it is persisted or published."""

from __future__ import annotations

import json
import re


_RUNTIME_LINE_RE = re.compile(
    r"^(?:🎭|🧭|🔎|📖|⏳|⏹️|❌|🎉|✅\s*(?:生成完成|第\s*\d+\s*章完成)|🧪\s*第\s*\d+\s*章候选版本|生成中\.\.\.|【正在生成第\s*\d+\s*/\s*\d+\s*段】|={20,})"
)
_META_LINE_RE = re.compile(
    r"^(?:好的[，,。！!]?|当然[，,。！!]?|下面是|以下是|我会|我将|让我|创作说明|编辑说明|正文如下)"
)


def _unwrap_json_text(text: str) -> str:
    """Accept providers that accidentally wrap the answer in a JSON object."""
    candidate = text.strip()
    if not candidate.startswith(("{", "[")):
        return text
    try:
        payload = json.loads(candidate)
    except Exception:
        return text
    if isinstance(payload, dict):
        for key in ("content", "story", "text", "正文", "answer"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return text


def clean_story_text(text: str, *, keep_chapter_headers: bool = True) -> str:
    """Remove UI/runtime noise and common model wrappers while preserving prose."""
    raw = _unwrap_json_text(str(text or "").replace("\r\n", "\n").replace("\r", "\n"))
    lines = raw.split("\n")
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            continue
        if not stripped:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue
        if _RUNTIME_LINE_RE.match(stripped):
            continue
        if not keep_chapter_headers and re.match(r"^【第\s*\d+\s*/\s*\d+\s*章：", stripped):
            continue
        # The model occasionally emits a Markdown heading for the title despite the contract.
        if stripped.startswith("#") and len(stripped.lstrip("# ")) >= 2:
            continue
        # Only remove editorial preambles before the first real paragraph.
        if not cleaned and _META_LINE_RE.match(stripped):
            continue
        cleaned.append(line.rstrip())

    while cleaned and cleaned[0] == "":
        cleaned.pop(0)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return "\n".join(cleaned).strip()


def build_story_from_chapters(chapters: list[dict]) -> str:
    """Render chapter bodies as clean, publishable plain text."""
    parts: list[str] = []
    for chapter in chapters:
        body = clean_story_text(str(chapter.get("body", "")), keep_chapter_headers=False)
        if not body:
            continue
        title = str(chapter.get("title", "") or "").strip()
        if title:
            try:
                chapter_no = int(chapter.get("chapter", len(parts) + 1))
            except (TypeError, ValueError):
                chapter_no = len(parts) + 1
            parts.append(f"【第 {chapter_no} 章：{title}】\n\n{body}")
        else:
            parts.append(body)
    return "\n\n".join(parts).strip()
