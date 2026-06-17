"""Run inspection + SSE + cancel + resume. See docs/technical_architecture.md.2 / 搂7.5 / 搂8.3."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.services.story_service.deps import get_creative_service, get_event_bus
from src.shared.http.sse import sse_event_line

router = APIRouter(prefix="/v1/runs", tags=["runs"])


@router.get("/{run_id}")
async def get_run(run_id: str, service=Depends(get_creative_service)) -> dict:
    return await service.get_status(run_id)


@router.get("/{run_id}/events")
async def stream_run_events(run_id: str, bus=Depends(get_event_bus)):
    async def gen():
        async for ev in bus.subscribe(run_id):
            yield sse_event_line(ev)

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/{run_id}/cancel")
async def cancel_run(run_id: str, service=Depends(get_creative_service)) -> dict:
    ok = await service.cancel(run_id)
    return {"run_id": run_id, "cancelled": ok}


@router.post("/{run_id}/resume")
async def resume_run(run_id: str, body: dict, service=Depends(get_creative_service)) -> dict:
    await service.resume(run_id, body)
    return {"run_id": run_id, "resumed": True}
