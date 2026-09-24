"""Wraps zhihu_publisher.publish_to_zhihu_sync as an async service.

See docs/technical_architecture.md.6.
"""

from __future__ import annotations

import asyncio
import os

from src.services.image_service.api._helpers import project_paths, write_json


class PublisherService:
    async def publish_to_zhihu(
        self,
        project_id: str,
        *,
        title: str | None = None,
        content: str = "",
        headless: bool = False,
        neutralize_mentions: bool = True,
    ) -> dict:
        if (os.getenv("WSF_ZHIHU_PUBLISH", "") or "").strip().lower() in {"1", "true", "yes", "on"}:
            return await self._publish_real(
                project_id=project_id,
                title=title,
                content=content,
                headless=headless,
            )
        result = {
            "project_id": project_id,
            "title": title or project_id,
            "status": "dry_run",
            "headless": headless,
            "neutralize_mentions": neutralize_mentions,
        }
        write_json(project_paths(project_id).root / "zhihu_last_result.json", result)
        return result

    async def _publish_real(
        self,
        *,
        project_id: str,
        title: str | None,
        content: str,
        headless: bool,
    ) -> dict:
        from src.gui.services.zhihu_publisher import publish_to_zhihu_sync

        project_root = project_paths(project_id).root
        story_text = content.strip()
        if not story_text:
            story_path = project_root / "story.txt"
            if story_path.exists():
                story_text = story_path.read_text(encoding="utf-8")
        if not story_text.strip():
            raise RuntimeError("no story content available for Zhihu publishing")

        ok, message = await asyncio.to_thread(
            publish_to_zhihu_sync,
            title or project_id,
            story_text,
            headless=headless,
        )
        result = {
            "project_id": project_id,
            "title": title or project_id,
            "status": "succeeded" if ok else "failed",
            "message": message,
            "headless": headless,
        }
        write_json(project_root / "zhihu_last_result.json", result)
        return result
