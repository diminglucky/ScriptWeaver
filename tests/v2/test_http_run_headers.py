"""X-Run-Id contextvar propagation. See docs/technical_architecture.md.2."""

from __future__ import annotations

import asyncio

from src.shared.http.run_headers import RUN_ID_HEADER, current_run_id, with_run_id


def test_run_id_default_is_empty():
    assert current_run_id() == ""


def test_run_id_header_constant():
    assert RUN_ID_HEADER == "X-Run-Id"


def test_with_run_id_sets_and_resets():
    assert current_run_id() == ""
    with with_run_id("abc"):
        assert current_run_id() == "abc"
    assert current_run_id() == ""


def test_with_run_id_nested():
    with with_run_id("outer"):
        assert current_run_id() == "outer"
        with with_run_id("inner"):
            assert current_run_id() == "inner"
        assert current_run_id() == "outer"
    assert current_run_id() == ""


def test_run_id_isolated_per_async_task():
    async def setter(label: str) -> str:
        with with_run_id(label):
            await asyncio.sleep(0)
            return current_run_id()

    async def main():
        # contextvars are copied per task 鈫?no cross-talk.
        results = await asyncio.gather(setter("A"), setter("B"), setter("C"))
        return results

    out = asyncio.run(main())
    assert sorted(out) == ["A", "B", "C"]
