"""GET /v1/models, GET/PUT /v1/routing. See v2 plan §7.2 / §12.3."""

from __future__ import annotations

import json
import os

from fastapi import APIRouter, Depends

from src.services.story_service.deps import get_model_registry
from src.shared.config.paths import get_repo_paths
from src.shared.config.routing import RouteEntry

router = APIRouter(prefix="/v1", tags=["models"])


@router.get("/models")
async def list_models(registry=Depends(get_model_registry)) -> dict:
    routes = _routes_payload(registry.routing.by_task)
    providers = sorted({entry["provider"] for entry in routes.values() if entry.get("provider")})
    return {"providers": providers, "routes": routes}


@router.get("/routing")
async def get_routing(registry=Depends(get_model_registry)) -> dict:
    return {"routes": _routes_payload(registry.routing.by_task)}


@router.put("/routing")
async def update_routing(body: dict) -> dict:
    routes = body.get("routes") if isinstance(body.get("routes"), dict) else body
    clean: dict[str, dict] = {}
    for task, cfg in routes.items():
        if not isinstance(cfg, dict):
            continue
        entry = {
            "provider": str(cfg.get("provider") or ""),
            "model": str(cfg.get("model") or ""),
        }
        if cfg.get("temperature") is not None:
            entry["temperature"] = cfg["temperature"]
        for key, value in cfg.items():
            if key not in {"provider", "model", "temperature"}:
                entry[key] = value
        clean[str(task)] = entry

    target = get_repo_paths().repo_root / "custom_model_routing.json"
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"version": 1, "routes": clean}, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, target)
    _clear_story_deps_cache()
    return {"routes": clean}


def _routes_payload(routes: dict[str, RouteEntry]) -> dict:
    return {
        task: {
            "provider": entry.provider,
            "model": entry.model,
            **({"temperature": entry.temperature} if entry.temperature is not None else {}),
            **entry.extras,
        }
        for task, entry in sorted(routes.items())
    }


def _clear_story_deps_cache() -> None:
    from src.services.story_service import deps

    for name in ("get_model_registry", "get_workflow_runner", "get_creative_service"):
        fn = getattr(deps, name, None)
        if hasattr(fn, "cache_clear"):
            fn.cache_clear()
