"""POST /v1/projects/{id}/image-prompts:generate. See v2 plan §6.3."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.services.image_service.api._helpers import make_shots, save_shots, start_image_run
from src.services.image_service.deps import get_event_bus, get_run_registry

router = APIRouter(prefix="/v1/projects", tags=["prompts"])


@router.post("/{project_id}/image-prompts:generate")
async def generate_prompts(
    project_id: str,
    body: dict,
    bus=Depends(get_event_bus),
    runs=Depends(get_run_registry),
) -> dict:
    async def work(_: str) -> dict:
        shots = make_shots(project_id, body)
        save_shots(project_id, shots)
        return {"shots": [x.model_dump() for x in shots]}

    run_id = await start_image_run(kind="image_prompts", project_id=project_id, bus=bus, runs=runs, work=work)
    return {"run_id": run_id, "status": "running"}
