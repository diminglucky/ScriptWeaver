"""Resolves repo-relative paths: projects/, index/, config/, .runtime/."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class RepoPaths:
    repo_root: Path
    projects_root: Path
    index_root: Path
    config_root: Path
    runtime_root: Path
    logs_root: Path


def _default_repo_root() -> Path:
    # This file lives at src/shared/config/paths.py → 3 parents up = repo root.
    return Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def get_repo_paths() -> RepoPaths:
    root = Path(os.environ.get("WSF_REPO_ROOT") or _default_repo_root()).resolve()
    return RepoPaths(
        repo_root=root,
        projects_root=root / "projects",
        index_root=root / "index",
        config_root=root / "config",
        runtime_root=root / ".runtime",
        logs_root=root / "logs",
    )
