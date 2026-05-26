from __future__ import annotations

import asyncio
import json
import os
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from src.services.story_service.core.services.event_bus import EventBus
from src.services.story_service.core.services.run_registry import RunRegistry
from src.shared.config.paths import get_repo_paths
from src.shared.domain.events import CreativeEvent
from src.shared.domain.project_paths import ProjectPaths
from src.shared.domain.schemas import ShotPrompt


async def start_image_run(
    *,
    kind: str,
    project_id: str,
    bus: EventBus,
    runs: RunRegistry,
    work: Callable[[str], Awaitable[dict]],
) -> str:
    run_id = uuid.uuid4().hex
    runs.register(run_id)
    asyncio.create_task(_drive_run(run_id=run_id, kind=kind, project_id=project_id, bus=bus, runs=runs, work=work))
    return run_id


async def _drive_run(
    *,
    run_id: str,
    kind: str,
    project_id: str,
    bus: EventBus,
    runs: RunRegistry,
    work: Callable[[str], Awaitable[dict]],
) -> None:
    bus.publish(CreativeEvent(type="run_started", run_id=run_id, payload={"kind": kind, "project_id": project_id}))
    bus.publish(CreativeEvent(type="node_started", run_id=run_id, node=kind))
    try:
        payload = await work(run_id)
        bus.publish(CreativeEvent(type="node_finished", run_id=run_id, node=kind, payload=payload))
        bus.publish(CreativeEvent(type="succeeded", run_id=run_id))
    except asyncio.CancelledError:
        bus.publish(CreativeEvent(type="cancelled", run_id=run_id))
        raise
    except Exception as exc:
        bus.publish(CreativeEvent(type="failed", run_id=run_id, payload={"code": "creative_error", "message": str(exc)}))
    finally:
        runs.finish(run_id)


def project_paths(project_id: str) -> ProjectPaths:
    paths = ProjectPaths(get_repo_paths().projects_root, project_id)
    paths.ensure_dirs()
    return paths


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def load_shots(project_id: str) -> list[ShotPrompt]:
    raw = read_json(project_paths(project_id).shots_json, {"shots": []})
    rows = raw.get("shots", raw if isinstance(raw, list) else []) if isinstance(raw, (dict, list)) else []
    return [x if isinstance(x, ShotPrompt) else ShotPrompt.model_validate(x) for x in rows]


def save_shots(project_id: str, shots: list[ShotPrompt]) -> None:
    write_json(project_paths(project_id).shots_json, {"shots": [x.model_dump() for x in shots]})


def make_shots(project_id: str, body: dict) -> list[ShotPrompt]:
    rows = body.get("shots") if isinstance(body.get("shots"), list) else []
    if rows:
        return [ShotPrompt.model_validate(x) for x in rows]
    scene = str(body.get("scene") or body.get("summary") or "默认场景")
    prompt = str(body.get("prompt") or f"{project_id} cinematic scene: {scene}")
    return [ShotPrompt(shot_id="shot-001", scene=scene, prompt=prompt, aspect_ratio=str(body.get("aspect_ratio") or "16:9"))]


def render_payload(*, prompt: str, aspect_ratio: str = "16:9", model_hint: str = "") -> dict:
    image_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{prompt}|{aspect_ratio}|{model_hint}").hex
    return {
        "image_id": image_id,
        "url": f"generated://image/{image_id}",
        "path": f"generated://image/{image_id}.png",
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "model_hint": model_hint,
        "status": "succeeded",
    }
