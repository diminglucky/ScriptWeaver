"""Run inspection + SSE + cancel for image-service. Same protocol as story-service."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.services.image_service.deps import get_event_bus, get_run_registry
from src.shared.http.sse import sse_event_line

router = APIRouter(prefix="/v1/runs", tags=["runs"])


@router.get("/{run_id}/events")
async def stream_events(run_id: str, bus=Depends(get_event_bus)):
    async def gen():
        async for ev in bus.subscribe(run_id):
            yield sse_event_line(ev)

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/{run_id}/cancel")
async def cancel_run(run_id: str, runs=Depends(get_run_registry)) -> dict:
    ok = await runs.cancel(run_id)
    return {"run_id": run_id, "cancelled": ok}
