from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

GraphStep = Callable[[dict[str, Any]], dict[str, Any] | Awaitable[dict[str, Any] | None] | None]


@dataclass
class SimpleCompiledGraph:
    steps: list[tuple[str, GraphStep]]
    interrupt_before: list[str] = field(default_factory=list)

    async def ainvoke(self, state: dict[str, Any]) -> dict[str, Any]:
        cur = dict(state)
        cur.setdefault("errors", [])
        for name, step in self.steps:
            try:
                out = step(cur)
                if inspect.isawaitable(out):
                    out = await out
                if out:
                    cur.update(out)
            except Exception as exc:
                cur.setdefault("errors", []).append(str(exc))
                cur["last_failed_node"] = name
                raise
        return cur

    def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        return asyncio.run(self.ainvoke(state))

    @property
    def nodes(self) -> list[str]:
        return [name for name, _ in self.steps]
