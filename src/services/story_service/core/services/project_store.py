"""Sole writer for `projects/<id>/` (StoryBible, ChapterDraft, story.txt).

See v2 plan §5.9 / §11.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from src.shared.config.paths import get_repo_paths
from src.shared.domain.project_paths import ProjectPaths
from src.shared.domain.schemas import ChapterDraft, StoryBible


class ProjectStore:
    def __init__(self, project_id: str, *, projects_root: Path | None = None):
        root = projects_root or get_repo_paths().projects_root
        self.paths = ProjectPaths(root, project_id)

    # ── StoryBible ────────────────────────────────────────────────────────
    def save_storybible(self, bible: StoryBible) -> None:
        self.paths.ensure_dirs()
        tmp = self.paths.storybible_json.with_suffix(".json.tmp")
        tmp.write_text(bible.model_dump_json(indent=2), encoding="utf-8")
        os.replace(tmp, self.paths.storybible_json)

    def load_storybible(self) -> StoryBible | None:
        fp = self.paths.storybible_json
        if not fp.exists():
            return None
        return StoryBible.model_validate_json(fp.read_text(encoding="utf-8"))

    # ── Chapters ──────────────────────────────────────────────────────────
    def save_chapter(self, draft: ChapterDraft) -> None:
        self.paths.ensure_dirs()
        target = self.paths.chapter_file(draft.section_index)
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(draft.model_dump_json(indent=2), encoding="utf-8")
        os.replace(tmp, target)

    def load_chapter(self, idx: int) -> ChapterDraft | None:
        fp = self.paths.chapter_file(idx)
        if not fp.exists():
            return None
        return ChapterDraft.model_validate_json(fp.read_text(encoding="utf-8"))

    def list_chapters(self) -> list[ChapterDraft]:
        d = self.paths.chapters_dir
        if not d.exists():
            return []
        out: list[ChapterDraft] = []
        for fp in sorted(d.glob("*.json")):
            try:
                out.append(ChapterDraft.model_validate_json(fp.read_text(encoding="utf-8")))
            except Exception:
                continue
        return out

    # ── Final story.txt ───────────────────────────────────────────────────
    def save_final_story(self, text: str) -> None:
        self.paths.ensure_dirs()
        target = self.paths.story_txt
        tmp = target.with_suffix(".txt.tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, target)

    def load_final_story(self) -> str:
        fp = self.paths.story_txt
        return fp.read_text(encoding="utf-8") if fp.exists() else ""

    # ── Migration ─────────────────────────────────────────────────────────
    @classmethod
    def migrate_legacy(cls, project_id: str) -> StoryBible:
        """Build a minimal StoryBible from legacy project.json fields. See §11.6."""
        return cls.migrate_legacy_with_root(project_id)

    @classmethod
    def migrate_legacy_with_root(
        cls,
        project_id: str,
        *,
        projects_root: Path | None = None,
    ) -> StoryBible:
        """Same as `migrate_legacy` but with explicit projects_root (test-friendly)."""
        store = cls(project_id, projects_root=projects_root)
        existing = store.load_storybible()
        if existing is not None:
            return existing
        legacy_fp = store.paths.project_json
        legacy: dict = {}
        if legacy_fp.exists():
            try:
                legacy = json.loads(legacy_fp.read_text(encoding="utf-8"))
            except Exception:
                legacy = {}
        bible = StoryBible(
            requirement=legacy.get("requirement", ""),
            genre=legacy.get("category", ""),
            style=legacy.get("style", ""),
            target_chars=int(legacy.get("target_chars") or 0),
        )
        store.save_storybible(bible)
        return bible
