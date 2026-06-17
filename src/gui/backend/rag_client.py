"""GUI-side async client for rag-service. See docs/technical_architecture.md.2."""

from __future__ import annotations

from typing import Any

from src.shared.domain.schemas import RetrievedContext

from ._http import request_json


class RagClient:
    def __init__(self, *, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token

    async def ingest(self, kb_type: str, payload: dict) -> dict:
        return await request_json(
            "POST",
            f"{self.base_url}/v1/kb/{kb_type}/documents",
            token=self.token,
            json=payload,
        )

    async def search(
        self,
        kb_type: str,
        query: str,
        *,
        project_id: str | None = None,
        top_k: int = 8,
        min_score: float = 0.0,
        budget: dict[str, Any] | None = None,
    ) -> list[RetrievedContext]:
        payload = {
            "query": query,
            "kb_types": [kb_type],
            "project_id": project_id,
            "top_k": top_k,
            "min_score": min_score,
        }
        if budget is not None:
            payload["budget"] = budget
        data = await request_json(
            "POST",
            f"{self.base_url}/v1/kb/{kb_type}/search",
            token=self.token,
            json=payload,
        )
        return [RetrievedContext.model_validate(x) for x in data.get("results", [])]

    async def list_memory(self, project_id: str) -> dict:
        return await request_json(
            "GET",
            f"{self.base_url}/v1/projects/{project_id}/memory",
            token=self.token,
        )

    async def write_memory(self, project_id: str, entries: list[dict]) -> dict:
        return await request_json(
            "POST",
            f"{self.base_url}/v1/projects/{project_id}/memory",
            token=self.token,
            json={"entries": entries},
        )

    async def clear_memory(self, project_id: str) -> dict:
        return await request_json(
            "DELETE",
            f"{self.base_url}/v1/projects/{project_id}/memory",
            token=self.token,
        )

    async def rebuild_manifest(self) -> dict:
        return await request_json(
            "POST",
            f"{self.base_url}/v1/admin/manifest:rebuild",
            token=self.token,
        )

    async def reindex(self) -> dict:
        return await self.rebuild_manifest()

    async def manifest(self) -> dict:
        return await request_json(
            "GET",
            f"{self.base_url}/v1/admin/manifest",
            token=self.token,
        )
