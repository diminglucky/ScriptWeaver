"""POST /v1/runs/{run_id}/review — human review decision. See v2 plan §8.4."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.services.story_service.deps import get_creative_service

router = APIRouter(prefix="/v1/runs", tags=["reviews"])


@router.post("/{run_id}/review")
async def submit_review(run_id: str, body: dict, service=Depends(get_creative_service)) -> dict:
    patch = dict(body)
    patch.setdefault("decision", "review")
    await service.resume(run_id, patch)
    return {"run_id": run_id, "reviewed": True, "decision": patch["decision"]}
