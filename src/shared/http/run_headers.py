"""X-Run-Id propagation. See docs/technical_architecture.md.2."""

from __future__ import annotations

import contextvars
from contextlib import contextmanager
from typing import Iterator

RUN_ID_HEADER = "X-Run-Id"

_run_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("wsf_run_id", default="")


def current_run_id() -> str:
    return _run_id_var.get()


@contextmanager
def with_run_id(run_id: str) -> Iterator[None]:
    token = _run_id_var.set(run_id)
    try:
        yield
    finally:
        _run_id_var.reset(token)
