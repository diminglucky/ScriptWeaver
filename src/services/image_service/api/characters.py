"""Character turnaround / photo endpoints. See v2 plan §6.4 / §7.4."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.services.image_service.api._helpers import render_payload, start_image_run
from src.services.image_service.deps import get_event_bus, get_run_registry

router = APIRouter(prefix="/v1/projects", tags=["characters"])


@router.post("/{project_id}/characters/{name}/turnaround")
async def generate_turnaround(project_id: str, name: str, body: dict, bus=Depends(get_event_bus), runs=Depends(get_run_registry)) -> dict:
    async def work(_: str) -> dict:
        return render_payload(prompt=f"{project_id} character turnaround: {name}", aspect_ratio="1:1")

    run_id = await start_image_run(kind="character_turnaround", project_id=project_id, bus=bus, runs=runs, work=work)
    return {"run_id": run_id, "status": "running"}


@router.post("/{project_id}/characters/{name}/photo")
async def generate_photo(project_id: str, name: str, body: dict, bus=Depends(get_event_bus), runs=Depends(get_run_registry)) -> dict:
    async def work(_: str) -> dict:
        return render_payload(prompt=f"{project_id} character portrait: {name}", aspect_ratio="1:1")

    run_id = await start_image_run(kind="character_photo", project_id=project_id, bus=bus, runs=runs, work=work)
    return {"run_id": run_id, "status": "running"}
