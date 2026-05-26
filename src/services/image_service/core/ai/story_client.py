"""httpx async client → story-service. Used to fetch StoryBible + chapters."""

from __future__ import annotations

from typing import Any

import httpx

from src.shared.domain.errors import CreativeError
from src.shared.domain.schemas import ChapterDraft, StoryBible


class StoryClient:
    def __init__(self, *, base_url: str, token: str, service_token: str = ""):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.service_token = service_token

    async def get_storybible(self, project_id: str) -> StoryBible | None:
        if not self.base_url:
            return None
        data = await self._request_json("GET", f"/v1/projects/{project_id}/storybible")
        return StoryBible.model_validate(data) if data else None

    async def list_chapters(self, project_id: str) -> list[ChapterDraft]:
        if not self.base_url:
            return []
        data = await self._request_json("GET", f"/v1/projects/{project_id}/chapters")
        rows = data.get("chapters", data if isinstance(data, list) else [])
        return [ChapterDraft.model_validate(x) for x in rows]

    async def get_chapter(self, project_id: str, idx: int) -> ChapterDraft | None:
        if not self.base_url:
            return None
        data = await self._request_json("GET", f"/v1/projects/{project_id}/chapters/{idx}")
        return ChapterDraft.model_validate(data) if data else None

    async def get_story_text(self, project_id: str) -> str:
        if not self.base_url:
            return ""
        data = await self._request_json("GET", f"/v1/projects/{project_id}/story")
        return str(data.get("text", ""))

    async def _request_json(self, method: str, path: str, *, json: dict | None = None) -> dict:
        headers: dict[str, str] = {}
        token = self.service_token or self.token
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.request(method, f"{self.base_url}{path}", json=json, headers=headers)
        except httpx.HTTPError as exc:
            raise CreativeError(str(exc), detail={"service": "story"}) from exc
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = {"status_code": resp.status_code, "text": resp.text}
            raise CreativeError("story-service request failed", detail=detail)
        return resp.json() if resp.content else {}
