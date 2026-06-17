"""GUI-side async client for image-service. See docs/technical_architecture.md.2."""

from __future__ import annotations

from src.shared.domain.schemas import ShotPrompt

from ._run_handle import RunHandle
from ._http import request_json, stream_request
from .events import iter_events_from_response


class ImageClient:
    def __init__(self, *, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token

    # 鈹€鈹€ prompts / shots 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
    async def generate_shot_prompts(self, project_id: str, request: dict) -> RunHandle:
        data = await request_json(
            "POST",
            f"{self.base_url}/v1/projects/{project_id}/image-prompts:generate",
            token=self.token,
            json=request,
        )
        return self._run_handle(data["run_id"])

    async def render_shots_batch(self, project_id: str, options: dict | None = None) -> RunHandle:
        data = await request_json(
            "POST",
            f"{self.base_url}/v1/projects/{project_id}/shots:batch",
            token=self.token,
            json=options or {},
        )
        return self._run_handle(data["run_id"])

    async def list_shots(self, project_id: str) -> list[ShotPrompt]:
        data = await request_json(
            "GET",
            f"{self.base_url}/v1/projects/{project_id}/shots",
            token=self.token,
        )
        rows = data.get("shots", data if isinstance(data, list) else [])
        return [ShotPrompt.model_validate(x) for x in rows]

    # 鈹€鈹€ characters 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
    async def generate_turnaround(self, project_id: str, name: str) -> RunHandle:
        data = await request_json(
            "POST",
            f"{self.base_url}/v1/projects/{project_id}/characters/{name}/turnaround",
            token=self.token,
            json={},
        )
        return self._run_handle(data["run_id"])

    async def generate_character_photo(self, project_id: str, name: str) -> RunHandle:
        data = await request_json(
            "POST",
            f"{self.base_url}/v1/projects/{project_id}/characters/{name}/photo",
            token=self.token,
            json={},
        )
        return self._run_handle(data["run_id"])

    # 鈹€鈹€ single image 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
    async def render_single(self, request: dict) -> dict:
        return await request_json(
            "POST",
            f"{self.base_url}/v1/images:generate",
            token=self.token,
            json=request,
        )

    # 鈹€鈹€ director / publish 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
    async def director_script(self, project_id: str, request: dict) -> RunHandle:
        data = await request_json(
            "POST",
            f"{self.base_url}/v1/projects/{project_id}/director:script",
            token=self.token,
            json=request,
        )
        return self._run_handle(data["run_id"])

    async def publish_zhihu(self, project_id: str, request: dict) -> RunHandle:
        data = await request_json(
            "POST",
            f"{self.base_url}/v1/projects/{project_id}/zhihu:publish",
            token=self.token,
            json=request,
        )
        return self._run_handle(data["run_id"])

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
            await request_json(
                "POST",
                f"{self.base_url}/v1/runs/{run_id}/cancel",
                token=self.token,
            )

        async def wait() -> dict:
            return {"run_id": run_id}

        return RunHandle(run_id=run_id, _events_factory=events_factory, _cancel=cancel, _wait=wait)
