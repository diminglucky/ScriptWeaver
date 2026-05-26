"""Shot batch / single render / list. See v2 plan §7.4."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.services.image_service.api._helpers import load_shots, render_payload, start_image_run
from src.services.image_service.deps import get_event_bus, get_run_registry
from src.shared.domain.errors import NotFound

router = APIRouter(prefix="/v1/projects", tags=["shots"])


@router.post("/{project_id}/shots:batch")
async def batch_shots(project_id: str, body: dict, bus=Depends(get_event_bus), runs=Depends(get_run_registry)) -> dict:
    async def work(_: str) -> dict:
        shots = load_shots(project_id)
        rendered = [
            render_payload(prompt=shot.prompt, aspect_ratio=shot.aspect_ratio, model_hint=shot.model_hint)
            for shot in shots
        ]
        return {"rendered": rendered, "count": len(rendered), "options": body}

    run_id = await start_image_run(kind="shots_batch", project_id=project_id, bus=bus, runs=runs, work=work)
    return {"run_id": run_id, "status": "running"}


@router.post("/{project_id}/shots/{shot_id}:render")
async def render_shot(project_id: str, shot_id: str, body: dict) -> dict:
    for shot in load_shots(project_id):
        if shot.shot_id == shot_id:
            return render_payload(prompt=shot.prompt, aspect_ratio=shot.aspect_ratio, model_hint=shot.model_hint)
    raise NotFound(f"unknown shot_id: {shot_id}")


@router.get("/{project_id}/shots")
async def list_shots(project_id: str) -> dict:
    return {"shots": [x.model_dump() for x in load_shots(project_id)]}
