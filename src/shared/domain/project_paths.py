"""Filesystem layout helpers for `projects/<id>/`. See docs/technical_architecture.md.6 / 搂11.

All 3 services must agree on the same paths. story-service is the only
writer; rag-service and image-service must access these paths via HTTP.
"""

from __future__ import annotations

from pathlib import Path


class ProjectPaths:
    """Resolves the v2 paths inside a single project directory."""

    def __init__(self, projects_root: Path, project_id: str):
        self.root = Path(projects_root) / project_id
        self.project_id = project_id

    # 鈹€鈹€ legacy (v1) 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
    @property
    def project_json(self) -> Path:
        return self.root / "project.json"

    @property
    def story_txt(self) -> Path:
        return self.root / "story.txt"

    @property
    def images_dir(self) -> Path:
        return self.root / "images"

    @property
    def characters_dir(self) -> Path:
        return self.root / "characters"

    # 鈹€鈹€ v2 additions 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
    @property
    def storybible_json(self) -> Path:
        return self.root / "storybible.json"

    @property
    def chapters_dir(self) -> Path:
        return self.root / "chapters"

    @property
    def shots_dir(self) -> Path:
        return self.root / "shots"

    @property
    def shots_json(self) -> Path:
        return self.shots_dir / "shots.json"

    @property
    def runs_dir(self) -> Path:
        return self.root / "runs"

    @property
    def checkpoints_sqlite(self) -> Path:
        return self.root / "checkpoints.sqlite"

    @property
    def director_dir(self) -> Path:
        return self.root / "director"

    def chapter_file(self, section_index: int) -> Path:
        return self.chapters_dir / f"{section_index:03d}.json"

    def run_file(self, run_id: str) -> Path:
        return self.runs_dir / f"{run_id}.jsonl"

    def ensure_dirs(self) -> None:
        """Create v2 directories if missing. Safe on existing v1 projects."""
        for path in (
            self.root,
            self.images_dir,
            self.characters_dir,
            self.chapters_dir,
            self.shots_dir,
            self.runs_dir,
            self.director_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
