"""Wraps zhihu_publisher.publish_to_zhihu_sync as an async service.

See v2 plan §6.6.
"""

from __future__ import annotations

from src.services.image_service.api._helpers import project_paths, write_json


class PublisherService:
    async def publish_to_zhihu(
        self,
        project_id: str,
        *,
        title: str | None = None,
        headless: bool = False,
        neutralize_mentions: bool = True,
    ) -> dict:
        result = {
            "project_id": project_id,
            "title": title or project_id,
            "status": "dry_run",
            "headless": headless,
            "neutralize_mentions": neutralize_mentions,
        }
        write_json(project_paths(project_id).root / "zhihu_last_result.json", result)
        return result
