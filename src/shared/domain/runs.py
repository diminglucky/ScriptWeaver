"""Run-id / cancellation protocol. See v2 plan §3.4 / §8.3."""

from __future__ import annotations

import asyncio
from typing import Literal, Protocol, runtime_checkable

RunStatus = Literal[
    "pending",
    "running",
    "interrupted",  # awaiting human input
    "succeeded",
    "failed",
    "cancelled",
]


@runtime_checkable
class RunRegistry(Protocol):
    """Per-process registry. Each service owns one instance."""

    def register(self, run_id: str) -> asyncio.Event: ...

    def cancel(self, run_id: str) -> bool: ...

    def is_cancelled(self, run_id: str) -> bool: ...

    def finish(self, run_id: str) -> None: ...
