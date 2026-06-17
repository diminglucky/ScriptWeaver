"""Reusable review sub-graph: scores draft + suggests fixes.

Used both for outline review and chapter review. See docs/technical_architecture.md.5.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.services.story_service.core.ai.structured import invoke_structured
from src.services.story_service.core.workflows.novel_graph import _chat_model
from src.services.story_service.core.workflows.simple_graph import SimpleCompiledGraph


class ReviewResult(BaseModel):
    score: float = 1.0
    notes: list[str] = Field(default_factory=list)
    suggested_fixes: list[str] = Field(default_factory=list)


def build_review_graph(*, registry, prompts) -> Any:
    async def review(state: dict[str, Any]) -> dict[str, Any]:
        llm = _chat_model(registry, "review")
        if llm is None:
            result = ReviewResult(score=1.0)
        else:
            prompt = prompts.build_review_prompt(state) if prompts is not None else {"task": "review", "state": state}
            result, _ = await invoke_structured(llm, prompt, ReviewResult)
        return {"review": result}

    return SimpleCompiledGraph(steps=[("review", review)])
