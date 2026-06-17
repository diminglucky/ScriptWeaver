"""POST /v1/projects/{id}/characters:design 鈥?character workflow.

See docs/technical_architecture.md.6, 搂7.2.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.services.story_service.deps import get_creative_service

router = APIRouter(prefix="/v1/projects", tags=["characters"])


@router.post("/{project_id}/characters:design")
async def design_characters(
    project_id: str,
    body: dict,
    service=Depends(get_creative_service),
) -> dict:
    run_id = await service.start_characters(project_id, body)
    return {"run_id": run_id, "status": "running"}
