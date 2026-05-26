from __future__ import annotations

from typing import Any

from src.services.story_service.core.workflows.character_graph import build_character_graph
from src.services.story_service.core.workflows.novel_graph import build_novel_graph
from src.shared.domain.events import CreativeEvent
from src.shared.domain.errors import CreativeError


class WorkflowRunner:
    def __init__(self, *, registry: Any, prompts: Any, rag_client: Any):
        self.registry = registry
        self.prompts = prompts
        self.rag_client = rag_client

    async def __call__(self, *, kind: str, project_id: str, run_id: str, request: dict, ctx: Any) -> None:
        if kind == "novel":
            graph = build_novel_graph(
                registry=self.registry,
                prompts=self.prompts,
                rag_client=self.rag_client,
                project_id=project_id,
            )
        elif kind == "characters":
            graph = build_character_graph(
                registry=self.registry,
                prompts=self.prompts,
                rag_client=self.rag_client,
                project_id=project_id,
            )
        else:
            raise CreativeError(f"unknown workflow kind: {kind}", detail={"kind": kind})

        for node in graph.nodes:
            ctx.bus.publish(CreativeEvent(type="node_started", run_id=run_id, node=node))
        state = await graph.ainvoke({"request": request, "project_id": project_id, "run_id": run_id})
        ctx.bus.publish(CreativeEvent(
            type="node_finished",
            run_id=run_id,
            node="workflow",
            payload={"keys": sorted(state.keys())},
        ))
