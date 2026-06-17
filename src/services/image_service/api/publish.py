"""Zhihu publishing endpoints. See docs/technical_architecture.md.6 / 搂7.4."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.services.image_service.api._helpers import project_paths, read_json, start_image_run, write_json
from src.services.image_service.deps import get_event_bus, get_run_registry

router = APIRouter(prefix="/v1/projects", tags=["publish"])


@router.post("/{project_id}/zhihu:publish")
async def publish_zhihu(project_id: str, body: dict, bus=Depends(get_event_bus), runs=Depends(get_run_registry)) -> dict:
    async def work(_: str) -> dict:
        result = {"project_id": project_id, "title": body.get("title") or project_id, "status": "dry_run"}
        write_json(project_paths(project_id).root / "zhihu_last_result.json", result)
        return result

    run_id = await start_image_run(kind="zhihu_publish", project_id=project_id, bus=bus, runs=runs, work=work)
    return {"run_id": run_id, "status": "running"}


@router.get("/{project_id}/zhihu/last-result")
async def last_zhihu_result(project_id: str) -> dict:
    return read_json(project_paths(project_id).root / "zhihu_last_result.json", {})
