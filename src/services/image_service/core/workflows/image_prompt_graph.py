"""image_prompt_graph LangGraph. See v2 plan §6.3.

Nodes:
    load_chapter_or_section
    → retrieve_visual_context
    → load_character_anchors
    → extract_shots
    → generate_shot_prompts
    → translate_prompts*
    → review_prompt_safety
    → save_shot_prompts
"""

from __future__ import annotations

from typing import Any

from src.services.story_service.core.workflows.simple_graph import SimpleCompiledGraph
from src.shared.domain.schemas import ShotPrompt


def build_image_prompt_graph(*, registry, prompts, story_client, rag_client) -> Any:
    async def load_chapter_or_section(state: dict[str, Any]) -> dict[str, Any]:
        project_id = str(state.get("project_id") or "")
        story_text = ""
        if story_client is not None and project_id:
            story_text = await story_client.get_story_text(project_id)
        return {"story_text": story_text}

    async def generate_shot_prompts(state: dict[str, Any]) -> dict[str, Any]:
        project_id = str(state.get("project_id") or "project")
        scene = state.get("scene") or state.get("story_text") or "默认场景"
        shot = ShotPrompt(
            shot_id="shot-001",
            scene=str(scene)[:200],
            prompt=str(state.get("prompt") or f"{project_id} cinematic scene: {scene}")[:1000],
        )
        return {"shots": [shot]}

    return SimpleCompiledGraph(steps=[
        ("load_chapter_or_section", load_chapter_or_section),
        ("generate_shot_prompts", generate_shot_prompts),
    ])
