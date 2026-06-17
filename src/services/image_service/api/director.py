"""Director script generation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.services.image_service.api._helpers import project_paths, read_json, start_image_run, write_json
from src.services.image_service.deps import get_event_bus, get_run_registry

router = APIRouter(prefix="/v1/projects", tags=["director"])


@router.post("/{project_id}/director:script")
async def generate_script(project_id: str, body: dict, bus=Depends(get_event_bus), runs=Depends(get_run_registry)) -> dict:
    async def work(_: str) -> dict:
        script = {
            "project_id": project_id,
            "title": body.get("title") or project_id,
            "beats": body.get("beats") or ["opening", "development", "ending"],
        }
        write_json(project_paths(project_id).director_dir / "script.json", script)
        return script

    run_id = await start_image_run(kind="director_script", project_id=project_id, bus=bus, runs=runs, work=work)
    return {"run_id": run_id, "status": "running"}


@router.get("/{project_id}/director/script")
async def get_script(project_id: str) -> dict:
    return read_json(project_paths(project_id).director_dir / "script.json", {})
