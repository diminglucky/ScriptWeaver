"""Task → provider/model resolution. See v2 plan §5.3.

Thin wrapper over `src.shared.config.routing.RoutingConfig` that exposes
helpers specific to story-service tasks (e.g. fallbacks).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.shared.config.routing import RouteEntry, RoutingConfig


_DEFAULT_FALLBACK: dict[str, str] = {
    "requirement_parse": "story_outline",
    "character_extract": "story_outline",
    "character_description": "story_outline",
}


def resolve(routing: "RoutingConfig", task: str) -> "RouteEntry":
    fallback = _DEFAULT_FALLBACK.get(task)
    return routing.resolve(task, fallback=fallback)
