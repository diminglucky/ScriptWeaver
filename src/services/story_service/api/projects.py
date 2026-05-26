"""Project metadata + storybible + chapters + story.txt endpoints.

See v2 plan §7.2.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from src.services.story_service.core.services.project_store import ProjectStore
from src.shared.config.paths import get_repo_paths
from src.shared.domain.errors import NotFound
from src.shared.domain.schemas import StoryBible

router = APIRouter(prefix="/v1/projects", tags=["projects"])


@router.post("")
async def create_project(body: dict) -> dict:
    project_id = str(body.get("project_id") or body.get("id") or uuid.uuid4().hex)
    store = ProjectStore(project_id)
    store.paths.ensure_dirs()
    if body.get("requirement") is not None:
        bible = StoryBible(
            requirement=str(body.get("requirement") or ""),
            genre=str(body.get("genre") or body.get("category") or ""),
            style=str(body.get("style") or ""),
            target_chars=int(body.get("target_chars") or 0),
        )
        store.save_storybible(bible)
    return {"project_id": project_id, "id": project_id}


@router.get("")
async def list_projects() -> dict:
    root = get_repo_paths().projects_root
    projects: list[dict] = []
    if root.exists():
        for path in sorted(p for p in root.iterdir() if p.is_dir()):
            store = ProjectStore(path.name)
            projects.append(_project_meta(store))
    return {"projects": projects}


@router.get("/{project_id}")
async def get_project(project_id: str) -> dict:
    store = ProjectStore(project_id)
    if not store.paths.root.exists():
        raise NotFound(f"unknown project_id: {project_id}")
    return _project_meta(store)


@router.get("/{project_id}/storybible")
async def get_storybible(project_id: str) -> dict:
    bible = ProjectStore(project_id).load_storybible()
    if bible is None:
        return {}
    return bible.model_dump()


@router.get("/{project_id}/chapters")
async def list_chapters(project_id: str) -> dict:
    chapters = ProjectStore(project_id).list_chapters()
    return {"chapters": [x.model_dump() for x in chapters]}


@router.get("/{project_id}/chapters/{idx}")
async def get_chapter(project_id: str, idx: int) -> dict:
    chapter = ProjectStore(project_id).load_chapter(idx)
    if chapter is None:
        raise NotFound(f"unknown chapter: {project_id}/{idx}")
    return chapter.model_dump()


@router.get("/{project_id}/story")
async def get_story(project_id: str) -> dict:
    return {"text": ProjectStore(project_id).load_final_story()}


def _project_meta(store: ProjectStore) -> dict:
    return {
        "project_id": store.paths.project_id,
        "id": store.paths.project_id,
        "has_storybible": store.paths.storybible_json.exists(),
        "chapter_count": len(store.list_chapters()),
        "has_story": bool(store.load_final_story()),
    }
