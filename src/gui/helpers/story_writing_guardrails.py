"""Guardrails for story writing quality and title normalization."""

from __future__ import annotations

import re


NON_AI_BANNED_PHRASES = [
    "首先",
    "其次",
    "最后",
    "总的来说",
    "总而言之",
    "不难发现",
    "值得一提的是",
    "在某种程度上",
]


def build_non_ai_writing_guardrails() -> str:
    """Return practical writing constraints to reduce templated AI tone."""
    phrase_block = "、".join(NON_AI_BANNED_PHRASES)
    return (
        "- 禁止模板化论述口吻（如："
        + phrase_block
        + "），避免“先总后分”的说教结构；\n"
        "- 少用抽象判断词，多写可验证细节（时间/地点/动作/后果）；\n"
        "- 段落推进要靠事件和决策，不靠空泛感慨；\n"
        "- 对话符合人物身份与场景，不要全员同一种腔调；\n"
        "- 语气克制专业，避免夸张口号、鸡汤式收束。"
    )


def build_outline_title_guardrails() -> str:
    """Return title-specific constraints for outline generation."""
    return (
        "- 章节标题控制在 4-12 个汉字，避免过长说明句；\n"
        "- 标题优先使用“动作+冲突/结果”结构，避免空泛抽象词；\n"
        "- 禁止营销号措辞（如“震惊”“逆天”“看哭了”“绝了”）。"
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


def normalize_chapter_title(raw: str, *, min_len: int = 4, max_len: int = 12) -> str:
    """Normalize chapter title to short, compact form."""
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


def normalize_article_title(raw: str, *, min_len: int = 12, max_len: int = 20) -> str:
    """Normalize article title for Zhihu: concise and not overlong."""
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

