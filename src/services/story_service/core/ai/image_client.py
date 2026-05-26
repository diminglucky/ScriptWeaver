"""httpx async client → image-service.

story-service rarely calls this directly; only certain post-novel nodes
that need image prompts may invoke it.
"""

from __future__ import annotations

import httpx

from src.shared.domain.errors import CreativeError


class ImageClient:
    def __init__(self, *, base_url: str, token: str, service_token: str = ""):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.service_token = service_token

    async def generate_shot_prompts(self, project_id: str, body: dict) -> dict:
        if not self.base_url:
            return {"run_id": "", "status": "disabled"}
        return await self._request_json("POST", f"/v1/projects/{project_id}/image-prompts:generate", json=body)

    async def _request_json(self, method: str, path: str, *, json: dict | None = None) -> dict:
        headers: dict[str, str] = {}
        token = self.service_token or self.token
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.request(method, f"{self.base_url}{path}", json=json, headers=headers)
        except httpx.HTTPError as exc:
            raise CreativeError(str(exc), detail={"service": "image"}) from exc
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = {"status_code": resp.status_code, "text": resp.text}
            raise CreativeError("image-service request failed", detail=detail)
        return resp.json() if resp.content else {}
