"""invoke_structured: LLM call → pydantic schema with self-repair retry.

See v2 plan §5.7.

The LLM is duck-typed: any object with ``async def ainvoke(prompt) -> Any``
will work. The result is normalised through :func:`_extract_text` (handles
plain str, dict, and LangChain-style ``.content`` messages), parsed as JSON,
then validated against ``schema``. On ``ValidationError`` we rebuild the
prompt with a repair instruction and retry up to ``max_retries`` times.
"""

from __future__ import annotations

import inspect
import json
import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, TypeVar

from pydantic import BaseModel, ValidationError

from src.shared.domain.errors import StructuredOutputError

TModel = TypeVar("TModel", bound=BaseModel)


@dataclass
class AttemptStats:
    attempts: int = 0
    error_paths: list[str] = field(default_factory=list)
    last_error: str = ""


def _extract_text(raw: Any) -> str:
    """Normalise an LLM response object into a plain string."""
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    # LangChain / OpenAI-like message objects.
    content = getattr(raw, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(raw, dict):
        for key in ("content", "text", "message"):
            v = raw.get(key)
            if isinstance(v, str):
                return v
    return str(raw)


_FENCE_RE = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.DOTALL)


def _strip_code_fences(text: str) -> str:
    m = _FENCE_RE.search(text)
    return m.group(1).strip() if m else text.strip()


def _first_error_path(err: ValidationError) -> str:
    errs = err.errors()
    if not errs:
        return ""
    loc = errs[0].get("loc") or ()
    return ".".join(str(p) for p in loc)


def _repair_prompt(original: Any, response: str, error_text: str) -> Any:
    """Build a repair-prompt that asks the model to fix the JSON."""
    instructions = (
        "你上一次的输出无法通过 JSON Schema 校验。"
        f"\n错误信息: {error_text}"
        "\n请只输出修正后的纯 JSON（不要 Markdown 代码块、不要解释）。"
        "\n上一次输出:\n" + response
    )
    if isinstance(original, str):
        return original + "\n\n" + instructions
    if isinstance(original, dict):
        out = dict(original)
        out["repair"] = instructions
        return out
    return [original, instructions]


async def invoke_structured(
    llm: Any,
    prompt: Any,
    schema: type[TModel],
    *,
    max_retries: int = 2,
    repair: bool = True,
    on_attempt: Callable[[int, str], Awaitable[None] | None] | None = None,
) -> tuple[TModel, AttemptStats]:
    """Run ``llm.ainvoke(prompt)`` and validate against ``schema`` with retries."""
    if max_retries < 0:
        raise ValueError("max_retries must be >= 0")

    stats = AttemptStats()
    cur_prompt = prompt
    last_error = ""

    for attempt in range(max_retries + 1):
        stats.attempts = attempt + 1
        if on_attempt is not None:
            res = on_attempt(attempt, last_error)
            if inspect.isawaitable(res):
                await res

        raw = await llm.ainvoke(cur_prompt)
        text = _strip_code_fences(_extract_text(raw))
        try:
            obj = schema.model_validate_json(text)
            return obj, stats
        except ValidationError as e:
            last_error = str(e)
            stats.last_error = last_error
            stats.error_paths.append(_first_error_path(e))
            if not repair or attempt >= max_retries:
                continue
            cur_prompt = _repair_prompt(prompt, text, last_error)
        except (json.JSONDecodeError, ValueError) as e:
            last_error = f"JSONDecodeError: {e}"
            stats.last_error = last_error
            stats.error_paths.append("$")
            if not repair or attempt >= max_retries:
                continue
            cur_prompt = _repair_prompt(prompt, text, last_error)

    raise StructuredOutputError(
        f"structured output validation failed after {stats.attempts} attempt(s): {stats.last_error}",
        detail={"error_paths": stats.error_paths, "attempts": stats.attempts},
    )
