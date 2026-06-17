"""Director script generation graph."""

from __future__ import annotations

from typing import Any

from src.services.story_service.core.workflows.simple_graph import SimpleCompiledGraph


def build_director_graph(*, registry, prompts, story_client) -> Any:
    async def build_script(state: dict[str, Any]) -> dict[str, Any]:
        project_id = str(state.get("project_id") or "project")
        story_text = ""
        if story_client is not None and project_id:
            story_text = await story_client.get_story_text(project_id)
        return {
            "script": {
                "project_id": project_id,
                "title": state.get("title") or project_id,
                "beats": state.get("beats") or ["opening", "development", "ending"],
                "story_excerpt": story_text[:500],
            }
        }

    return SimpleCompiledGraph(steps=[("build_script", build_script)])
