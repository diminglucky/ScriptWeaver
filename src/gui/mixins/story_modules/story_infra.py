"""Shared infrastructure for story generation modules.

Eliminates duplication of:
- _resolve_deepseek_client_cls (was defined 3 times)
- logger-based print override (was defined 3 times)
- API config resolution with fallback pattern (was copy-pasted 8+ times)
- Client creation boilerplate (was duplicated 6+ times)
"""

from __future__ import annotations

import logging
from src.clients.deepseek_client import DeepSeekClient
from src.utils.text import sanitize as _sanitize

logger = logging.getLogger(__name__)


def resolve_deepseek_client_cls():
    """Use aggregator module symbol so tests can monkey-patch one stable path."""
    try:
        from . import outline_generator as outline_generator_module

        patched = getattr(outline_generator_module, "DeepSeekClient", None)
        if patched is not None:
            return patched
    except Exception:
        pass
    return DeepSeekClient


def log_print(*args, **kwargs):  # type: ignore[override]
    """Logger-based print replacement for story modules."""
    logger.info(" ".join(str(a) for a in args))


class StoryInfraMixin:
    """Shared API resolution and client creation for all story generation mixins.

    Replaces the 8+ copy-pasted fallback_provider / fallback_model resolution
    blocks with a single reusable method.
    """

    def _resolve_generation_api_config(self, task_name: str = "story_generate") -> dict:
        """Resolve API config for any generation task with standard fallback chain.

        Supports task_name: 'story_generate', 'story_outline', etc.
        """
        fallback_provider = None
        # Task-specific API vars
        task_api_map = {
            "story_outline": "outline_gen_api",
            "story_generate": "story_gen_api",
        }
        primary_attr = task_api_map.get(task_name, "story_gen_api")
        if hasattr(self, primary_attr):
            fallback_provider = getattr(self, primary_attr).get()
        if not fallback_provider and hasattr(self, "quick_story_api"):
            fallback_provider = self.quick_story_api.get()
        if not fallback_provider and hasattr(self, "api_preset"):
            fallback_provider = self.api_preset.get()

        fallback_model = None
        if hasattr(self, "story_model_var"):
            fallback_model = self.story_model_var.get()
        elif hasattr(self, "model"):
            fallback_model = self.model.get()

        return self._resolve_task_api(
            task_name,
            fallback_provider=fallback_provider,
            fallback_model=fallback_model,
        )

    def _resolve_generation_api_config_safe(self, task_name: str = "story_generate") -> dict:
        """Thread-safe version using _ui_get for background threads."""
        fallback_provider = None
        task_api_map = {
            "story_outline": "outline_gen_api",
            "story_generate": "story_gen_api",
        }
        primary_attr = task_api_map.get(task_name, "story_gen_api")
        if hasattr(self, primary_attr):
            fallback_provider = self._ui_get(getattr(self, primary_attr).get)
        if not fallback_provider and hasattr(self, "quick_story_api"):
            fallback_provider = self._ui_get(self.quick_story_api.get)
        if not fallback_provider and hasattr(self, "api_preset"):
            fallback_provider = self._ui_get(self.api_preset.get)

        fallback_model = None
        if hasattr(self, "story_model_var"):
            fallback_model = self._ui_get(self.story_model_var.get)
        elif hasattr(self, "model"):
            fallback_model = self._ui_get(self.model.get)

        return self._ui_get(
            lambda: self._resolve_task_api(
                task_name,
                fallback_provider=fallback_provider,
                fallback_model=fallback_model,
            )
        )

    def _create_generation_client(self, api_config: dict):
        """Create a DeepSeekClient from resolved API config."""
        cls = resolve_deepseek_client_cls()
        return cls(
            api_key=_sanitize(api_config.get("key", "")),
            base_url=_sanitize(api_config.get("base_url", "")),
            model=api_config.get("model", ""),
        )
