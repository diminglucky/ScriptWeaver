"""High-level orchestration: build graph 鈫?run 鈫?emit events.

See docs/technical_architecture.md.2 / 搂5.10 / 搂8.4.

Workflows themselves are not built here; a *runner* callable is injected at
construction time so this layer is fully testable without LangGraph. The
runner signature is::

    async def runner(*, kind: str, project_id: str, run_id: str,
                     request: dict, ctx: RunContext) -> None

It can publish progress events through ``ctx.bus`` and must respect
``ctx.cancel_event``.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from src.shared.domain.errors import CreativeError, NotFound
from src.shared.domain.events import CreativeEvent

Runner = Callable[..., Awaitable[None]]


@dataclass
class RunContext:
    kind: str
    project_id: str
    run_id: str
    request: dict
    bus: Any
    cancel_event: asyncio.Event
    resume_signals: dict[str, asyncio.Event] = field(default_factory=dict)
    resume_payload: dict[str, Any] = field(default_factory=dict)

    def cancelled(self) -> bool:
        return self.cancel_event.is_set()

    def signal_resume(self, key: str, payload: Any | None = None) -> None:
        ev = self.resume_signals.setdefault(key, asyncio.Event())
        if payload is not None:
            self.resume_payload[key] = payload
        ev.set()

    async def wait_resume(self, key: str) -> Any:
        ev = self.resume_signals.setdefault(key, asyncio.Event())
        await ev.wait()
        return self.resume_payload.get(key)


@dataclass
class _RunHandle:
    run_id: str
    kind: str
    project_id: str
    status: str
    started_at: float
    ctx: RunContext
    task: asyncio.Task
    finished_at: float | None = None
    error: str | None = None


class CreativeService:
    """Owns the lifecycle of a single workflow run."""

    def __init__(self, *, registry: Any, prompts: Any, runs: Any, bus: Any, runner: Runner | None = None):
        self.registry = registry
        self.prompts = prompts
        self.runs = runs
        self.bus = bus
        self.runner = runner
        self._handles: dict[str, _RunHandle] = {}

    # ------------------------------------------------------------------
    # Public API

    async def start_novel(self, project_id: str, request: dict) -> str:
        return await self._start("novel", project_id, request)

    async def start_characters(self, project_id: str, request: dict) -> str:
        return await self._start("characters", project_id, request)

    async def resume(self, run_id: str, patch: dict) -> None:
        handle = self._handles.get(run_id)
        if handle is None:
            raise NotFound(f"unknown run_id: {run_id}")
        key = str(patch.get("decision") or patch.get("key") or "resume")
        handle.ctx.signal_resume(key, patch)

    async def cancel(self, run_id: str) -> bool:
        ok = await self.runs.cancel(run_id)
        handle = self._handles.get(run_id)
        if handle is not None and not handle.task.done():
            handle.task.cancel()
        return ok

    async def get_status(self, run_id: str) -> dict:
        handle = self._handles.get(run_id)
        if handle is None:
            raise NotFound(f"unknown run_id: {run_id}")
        return {
            "run_id": run_id,
            "kind": handle.kind,
            "project_id": handle.project_id,
            "status": handle.status,
            "started_at": handle.started_at,
            "finished_at": handle.finished_at,
            "error": handle.error,
        }

    # ------------------------------------------------------------------
    # Internals

    async def _start(self, kind: str, project_id: str, request: dict) -> str:
        if self.runner is None:
            raise CreativeError("no workflow runner configured", detail={"kind": kind})
        run_id = uuid.uuid4().hex
        cancel_ev = self.runs.register(run_id)
        ctx = RunContext(
            kind=kind,
            project_id=project_id,
            run_id=run_id,
            request=request,
            bus=self.bus,
            cancel_event=cancel_ev,
        )
        task = asyncio.create_task(self._drive(ctx))
        self._handles[run_id] = _RunHandle(
            run_id=run_id,
            kind=kind,
            project_id=project_id,
            status="running",
            started_at=time.time(),
            ctx=ctx,
            task=task,
        )
        return run_id

    async def _drive(self, ctx: RunContext) -> None:
        handle: _RunHandle | None = None
        # Allow _start to install the handle before we mutate it.
        await asyncio.sleep(0)
        handle = self._handles.get(ctx.run_id)
        self.bus.publish(CreativeEvent(
            type="run_started",
            run_id=ctx.run_id,
            payload={"kind": ctx.kind, "project_id": ctx.project_id},
        ))
        try:
            await self.runner(
                kind=ctx.kind,
                project_id=ctx.project_id,
                run_id=ctx.run_id,
                request=ctx.request,
                ctx=ctx,
            )
            if handle is not None:
                handle.status = "succeeded"
                handle.finished_at = time.time()
            self.bus.publish(CreativeEvent(type="succeeded", run_id=ctx.run_id))
        except asyncio.CancelledError:
            if handle is not None:
                handle.status = "cancelled"
                handle.finished_at = time.time()
            self.bus.publish(CreativeEvent(type="cancelled", run_id=ctx.run_id))
            raise
        except CreativeError as e:
            if handle is not None:
                handle.status = "failed"
                handle.finished_at = time.time()
                handle.error = e.message
            self.bus.publish(CreativeEvent(
                type="failed", run_id=ctx.run_id, payload=e.to_payload(),
            ))
        except Exception as e:  # noqa: BLE001 鈥?surface as failed event
            if handle is not None:
                handle.status = "failed"
                handle.finished_at = time.time()
                handle.error = str(e)
            self.bus.publish(CreativeEvent(
                type="failed",
                run_id=ctx.run_id,
                payload={"code": "creative_error", "message": str(e)},
            ))
        finally:
            self.runs.finish(ctx.run_id)
