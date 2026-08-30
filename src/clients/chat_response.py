"""Helpers for extracting text from OpenAI-compatible chat responses."""

from __future__ import annotations

from typing import Any


def _content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, (list, tuple)):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    parts.append(str(text))
            else:
                text = getattr(item, "text", None) or getattr(item, "content", None)
                if text:
                    parts.append(str(text))
        return "".join(parts)
    return str(content)


def is_html_page(value: Any) -> bool:
    """Return whether a text value looks like a web page/error document."""
    return isinstance(value, str) and value.lstrip().lower().startswith(("<!doctype html", "<html"))


def _validate_chat_text(text: str) -> str:
    """Reject an HTML error/login page returned by a misconfigured gateway."""
    if text.lstrip().lower().startswith(("<!doctype html", "<html")):
        raise RuntimeError(
            "AI 返回了 HTML 网页而不是模型内容，请检查 Base URL（兼容网关通常应包含 /v1）"
        )
    return text


def extract_chat_content(response: Any) -> str:
    """Return text from a plain string, mapping, or SDK response object.

    Some OpenAI-compatible gateways return the decoded text directly while
    the official SDK normally returns an object with ``choices``. Keep both
    forms at the client boundary so callers only have to handle text.
    """
    if isinstance(response, str):
        return _validate_chat_text(response)

    if isinstance(response, dict):
        choices = response.get("choices")
    else:
        choices = getattr(response, "choices", None)

    if isinstance(choices, (list, tuple)) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                return _validate_chat_text(_content_to_text(message.get("content")))
            return _validate_chat_text(
                _content_to_text(first.get("content") or first.get("text") or message)
            )

        message = getattr(first, "message", None)
        if message is not None:
            return _validate_chat_text(_content_to_text(getattr(message, "content", None)))
        return _validate_chat_text(
            _content_to_text(getattr(first, "content", None) or getattr(first, "text", None))
        )

    raise RuntimeError(f"AI 返回格式异常: {response!r}")
