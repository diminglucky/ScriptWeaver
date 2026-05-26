"""Shot batch pipeline: read shots.json → render each → persist."""

from __future__ import annotations

from src.services.image_service.api._helpers import load_shots, render_payload
from src.shared.domain.errors import NotFound


class ShotPipeline:
    async def render_batch(self, project_id: str, *, options: dict | None = None) -> dict:
        shots = load_shots(project_id)
        rendered = [
            render_payload(prompt=shot.prompt, aspect_ratio=shot.aspect_ratio, model_hint=shot.model_hint)
            for shot in shots
        ]
        return {"rendered": rendered, "count": len(rendered), "options": options or {}}

    async def render_one(self, project_id: str, shot_id: str) -> dict:
        for shot in load_shots(project_id):
            if shot.shot_id == shot_id:
                return render_payload(prompt=shot.prompt, aspect_ratio=shot.aspect_ratio, model_hint=shot.model_hint)
        raise NotFound(f"unknown shot_id: {shot_id}")
