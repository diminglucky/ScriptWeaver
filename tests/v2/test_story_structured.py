"""Tests for story_service.core.ai.structured.invoke_structured."""
from __future__ import annotations

import asyncio

import pytest
from pydantic import BaseModel

from src.services.story_service.core.ai.structured import (
    AttemptStats,
    invoke_structured,
)
from src.shared.domain.errors import StructuredOutputError


class Person(BaseModel):
    name: str
    age: int


class _ScriptedLLM:
    """Stub LLM with a queued sequence of responses."""

    def __init__(self, responses: list):
        self._responses = list(responses)
        self.calls: list = []

    async def ainvoke(self, prompt):
        self.calls.append(prompt)
        if not self._responses:
            raise RuntimeError("no more scripted responses")
        return self._responses.pop(0)


def test_first_try_succeeds():
    llm = _ScriptedLLM(['{"name": "Alice", "age": 30}'])
    obj, stats = asyncio.run(invoke_structured(llm, "build", Person))
    assert isinstance(obj, Person) and obj.name == "Alice" and obj.age == 30
    assert stats.attempts == 1
    assert stats.last_error == ""


def test_strips_markdown_fences():
    llm = _ScriptedLLM(['```json\n{"name": "Bob", "age": 5}\n```'])
    obj, _ = asyncio.run(invoke_structured(llm, "build", Person))
    assert obj.name == "Bob"


def test_extracts_content_from_message_like_object():
    class Msg:
        def __init__(self, content):
            self.content = content
    llm = _ScriptedLLM([Msg('{"name": "Carol", "age": 7}')])
    obj, _ = asyncio.run(invoke_structured(llm, "build", Person))
    assert obj.name == "Carol"


def test_retries_after_validation_error_then_succeeds():
    llm = _ScriptedLLM([
        '{"name": "Dave"}',  # missing age → ValidationError
        '{"name": "Dave", "age": 21}',
    ])
    obj, stats = asyncio.run(invoke_structured(llm, "build", Person, max_retries=2))
    assert obj.age == 21
    assert stats.attempts == 2
    assert stats.error_paths and "age" in stats.error_paths[0]


def test_retries_after_invalid_json_then_succeeds():
    llm = _ScriptedLLM([
        "not really json",
        '{"name": "Eve", "age": 9}',
    ])
    obj, stats = asyncio.run(invoke_structured(llm, "build", Person, max_retries=1))
    assert obj.name == "Eve"
    assert stats.attempts == 2


def test_raises_structured_output_error_when_exhausted():
    llm = _ScriptedLLM(['{"name": "no-age"}', "{not json}", '{"oops": 1}'])
    with pytest.raises(StructuredOutputError) as exc_info:
        asyncio.run(invoke_structured(llm, "build", Person, max_retries=2))
    err = exc_info.value
    assert err.detail["attempts"] == 3
    assert err.code == "structured_output"


def test_on_attempt_callback_invoked_per_try():
    llm = _ScriptedLLM([
        '{"name": "X"}',
        '{"name": "X", "age": 1}',
    ])
    seen: list[tuple[int, str]] = []

    def cb(attempt: int, last_err: str):
        seen.append((attempt, last_err))

    asyncio.run(invoke_structured(llm, "p", Person, max_retries=1, on_attempt=cb))
    assert [s[0] for s in seen] == [0, 1]
    assert seen[0][1] == ""  # no error on first attempt
    assert "age" in seen[1][1]


def test_invalid_max_retries_raises():
    llm = _ScriptedLLM([])
    with pytest.raises(ValueError):
        asyncio.run(invoke_structured(llm, "p", Person, max_retries=-1))
