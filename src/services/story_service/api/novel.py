"""POST /v1/projects/{id}/novel:run — kick off the novel workflow.

See v2 plan §5.5, §7.2.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.services.story_service.deps import get_creative_service

router = APIRouter(prefix="/v1/projects", tags=["novel"])


@router.post("/{project_id}/novel:run")
async def run_novel(
    project_id: str,
    body: dict,
    service=Depends(get_creative_service),
) -> dict:
    run_id = await service.start_novel(project_id, body)
    return {"run_id": run_id, "status": "running"}
