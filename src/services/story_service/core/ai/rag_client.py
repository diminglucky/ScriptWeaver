"""httpx async client → rag-service. See v2 plan §5.5 retrieval nodes."""

from __future__ import annotations

from typing import Any

import httpx

from src.shared.domain.errors import RetrievalError
from src.shared.domain.schemas import RetrievedContext


class RagClient:
    def __init__(self, *, base_url: str, token: str, service_token: str = ""):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.service_token = service_token

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
        if not self.base_url:
            return []
        payload: dict[str, Any] = {
            "query": query,
            "project_id": project_id,
            "top_k": top_k,
            "min_score": min_score,
            "kb_types": [kb_type],
        }
        if budget:
            payload["budget"] = budget
        data = await self._request_json("POST", f"/v1/kb/{kb_type}/search", json=payload)
        return [RetrievedContext.model_validate(x) for x in data.get("results", [])]

    async def write_memory(self, project_id: str, payload: dict | list[dict]) -> dict:
        if not self.base_url:
            return {"entries": []}
        body = {"entries": payload} if isinstance(payload, list) else payload
        return await self._request_json("POST", f"/v1/projects/{project_id}/memory", json=body)

    async def _request_json(self, method: str, path: str, *, json: dict) -> dict:
        headers: dict[str, str] = {}
        token = self.service_token or self.token
        if token:
            headers["Authorization"] = f"Bearer {token}"
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.request(method, url, json=json, headers=headers)
        except httpx.HTTPError as exc:
            raise RetrievalError(str(exc), detail={"url": url}) from exc
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = {"status_code": resp.status_code, "text": resp.text}
            raise RetrievalError("rag-service request failed", detail=detail)
        return resp.json() if resp.content else {}
