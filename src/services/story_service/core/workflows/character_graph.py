"""Character-design LangGraph. See v2 plan §5.6."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.services.story_service.core.ai.structured import invoke_structured
from src.services.story_service.core.workflows.novel_graph import _chat_model, _search
from src.services.story_service.core.workflows.simple_graph import SimpleCompiledGraph
from src.shared.domain.schemas import CharacterProfile


class CharacterPlan(BaseModel):
    characters: list[CharacterProfile] = Field(default_factory=list)


def build_character_graph(*, registry, prompts, rag_client, project_id: str) -> Any:
    async def load_context(state: dict[str, Any]) -> dict[str, Any]:
        request = state.get("request") or {}
        story_context = state.get("story_context") or request.get("story_context") or request.get("requirement") or ""
        refs = await _search(rag_client, "reference", story_context, project_id=None)
        memory = await _search(rag_client, "project_memory", story_context, project_id=project_id)
        return {
            "project_id": project_id,
            "story_context": story_context,
            "retrieved_contexts": refs + memory,
        }

    async def design_characters(state: dict[str, Any]) -> dict[str, Any]:
        llm = _chat_model(registry, "character_design")
        if llm is None:
            chars = [CharacterProfile(name="主角", role="protagonist", motivation=state.get("story_context", ""))]
        else:
            prompt = prompts.build_character_prompt(state) if prompts is not None else {"task": "character_design", "state": state}
            plan, _ = await invoke_structured(llm, prompt, CharacterPlan)
            chars = plan.characters
        if not chars:
            chars = [CharacterProfile(name="主角", role="protagonist")]
        return {"characters": chars}

    return SimpleCompiledGraph(steps=[
        ("load_context", load_context),
        ("design_characters", design_characters),
    ])
