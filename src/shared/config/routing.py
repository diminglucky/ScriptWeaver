"""Loads `model_routing.json` + `custom_model_routing.json`.

See v2 plan §5.3 / §12.4.

TaskName values must align with `model_routing.json` keys; full table in
the v2 design doc.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .paths import get_repo_paths

TaskName = Literal[
    "story_outline",
    "story_generate",
    "character_extract",
    "character_description",
    "image_prompt_translate",
    "image_prompt_enhance",
    "image_prompt_from_story",
    "image_prompt_from_shots",
    "image_shot_extract",
    "image_shot_to_desc",
    "director_script_generate",
    # NOTE: `requirement_parse` may need to be added per §12.4; falls back
    # to `story_outline` until the routing file is updated.
]


@dataclass
class RouteEntry:
    provider: str
    model: str
    temperature: float | None = None
    extras: dict = field(default_factory=dict)


@dataclass
class RoutingConfig:
    """In-memory view of the merged routing files."""

    by_task: dict[str, RouteEntry] = field(default_factory=dict)

    def resolve(self, task: str, fallback: str | None = None) -> RouteEntry:
        if task in self.by_task:
            return self.by_task[task]
        if fallback and fallback in self.by_task:
            return self.by_task[fallback]
        raise KeyError(f"No routing for task={task!r} and no fallback resolved.")


def load_routing(
    *,
    routing_path: Path | None = None,
    custom_routing_path: Path | None = None,
) -> RoutingConfig:
    """Read and merge routing files. Missing files are tolerated."""
    paths = get_repo_paths()
    routing_path = routing_path or (paths.repo_root / "model_routing.json")
    custom_routing_path = custom_routing_path or (
        paths.repo_root / "custom_model_routing.json"
    )

    merged: dict[str, RouteEntry] = {}

    for fp in (routing_path, custom_routing_path):
        if not fp.exists():
            continue
        raw = json.loads(fp.read_text(encoding="utf-8"))
        items = raw.get("routes") if isinstance(raw, dict) and isinstance(raw.get("routes"), dict) else raw
        if not isinstance(items, dict):
            continue
        for task, cfg in items.items():
            if not isinstance(cfg, dict):
                continue
            merged[task] = RouteEntry(
                provider=cfg.get("provider", ""),
                model=cfg.get("model", ""),
                temperature=cfg.get("temperature"),
                extras={k: v for k, v in cfg.items() if k not in {"provider", "model", "temperature"}},
            )

    return RoutingConfig(by_task=merged)
