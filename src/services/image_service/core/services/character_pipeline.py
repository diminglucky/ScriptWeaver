"""Character art pipelines (turnaround + photo). See v2 plan §6.4."""

from __future__ import annotations

from src.services.image_service.api._helpers import render_payload


class CharacterPipeline:
    async def generate_turnaround(self, project_id: str, character_name: str) -> dict:
        return render_payload(prompt=f"{project_id} character turnaround: {character_name}", aspect_ratio="1:1")

    async def generate_photo(self, project_id: str, character_name: str) -> dict:
        return render_payload(prompt=f"{project_id} character portrait: {character_name}", aspect_ratio="1:1")
