"""GUI-side async client for story-service.

See v2 plan §10.2.
"""

from __future__ import annotations

from typing import Any

from src.shared.domain.schemas import ChapterDraft, StoryBible

from ._run_handle import RunHandle
from ._http import request_json, stream_request
from .events import iter_events_from_response


class StoryClient:
    def __init__(self, *, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token

    # ── workflows ─────────────────────────────────────────────────────────
    async def generate_novel(self, project_id: str, request: dict) -> RunHandle:
        data = await request_json(
            "POST",
            f"{self.base_url}/v1/projects/{project_id}/novel:run",
            token=self.token,
            json=request,
        )
        return self._run_handle(data["run_id"])

    async def design_characters(self, project_id: str, request: dict) -> RunHandle:
        data = await request_json(
            "POST",
            f"{self.base_url}/v1/projects/{project_id}/characters:design",
            token=self.token,
            json=request,
        )
        return self._run_handle(data["run_id"])

    # ── reads ─────────────────────────────────────────────────────────────
    async def get_storybible(self, project_id: str) -> StoryBible | None:
        data = await request_json(
            "GET",
            f"{self.base_url}/v1/projects/{project_id}/storybible",
            token=self.token,
        )
        if not data:
            return None
        return StoryBible.model_validate(data)

    async def list_chapters(self, project_id: str) -> list[ChapterDraft]:
        data = await request_json(
            "GET",
            f"{self.base_url}/v1/projects/{project_id}/chapters",
            token=self.token,
        )
        rows = data.get("chapters", data if isinstance(data, list) else [])
        return [ChapterDraft.model_validate(x) for x in rows]

    async def get_story_text(self, project_id: str) -> str:
        data = await request_json(
            "GET",
            f"{self.base_url}/v1/projects/{project_id}/story",
            token=self.token,
        )
        return str(data.get("text", ""))

    # ── HITL ──────────────────────────────────────────────────────────────
    async def review(self, run_id: str, decision: dict) -> dict:
        return await request_json(
            "POST",
            f"{self.base_url}/v1/runs/{run_id}/review",
            token=self.token,
            json=decision,
        )

    async def resume(self, run_id: str, patch: dict) -> dict:
        return await request_json(
            "POST",
            f"{self.base_url}/v1/runs/{run_id}/resume",
            token=self.token,
            json=patch,
        )

    async def cancel(self, run_id: str) -> dict:
        return await request_json(
            "POST",
            f"{self.base_url}/v1/runs/{run_id}/cancel",
            token=self.token,
        )

    # ── settings ──────────────────────────────────────────────────────────
    async def get_routing(self) -> dict:
        return await request_json("GET", f"{self.base_url}/v1/routing", token=self.token)

    async def update_routing(self, routing: dict) -> dict:
        return await request_json(
            "PUT",
            f"{self.base_url}/v1/routing",
            token=self.token,
            json=routing,
        )

    async def get_run(self, run_id: str) -> dict:
        return await request_json("GET", f"{self.base_url}/v1/runs/{run_id}", token=self.token)

    def _run_handle(self, run_id: str) -> RunHandle:
        async def events_factory():
            response, client = await stream_request(
                "GET",
                f"{self.base_url}/v1/runs/{run_id}/events",
                token=self.token,
                timeout=None,
            )
            try:
                async for ev in iter_events_from_response(response):
                    yield ev
            finally:
                await response.aclose()
                await client.aclose()

        async def cancel() -> None:
            await self.cancel(run_id)

        async def wait() -> dict:
            return await self.get_run(run_id)

        return RunHandle(run_id=run_id, _events_factory=events_factory, _cancel=cancel, _wait=wait)
