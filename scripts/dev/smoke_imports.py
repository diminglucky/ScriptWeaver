"""Import-smoke check for v2 scaffold.

Run with the project's recommended interpreter::

    /opt/homebrew/bin/python3.11 scripts/dev/smoke_imports.py

Exits 0 on success, 1 on any failure. Does NOT require fastapi/langgraph to
be installed; verifies the scaffold tree imports cleanly under Python 3.11+.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


MODULES = [
    # shared
    "src.shared",
    "src.shared.domain",
    "src.shared.domain.schemas",
    "src.shared.domain.errors",
    "src.shared.domain.events",
    "src.shared.domain.runs",
    "src.shared.domain.project_paths",
    "src.shared.config",
    "src.shared.config.paths",
    "src.shared.config.keyfile",
    "src.shared.config.routing",
    "src.shared.config.presets",
    "src.shared.config.settings",
    "src.shared.http",
    "src.shared.http.run_headers",
    "src.shared.http.auth",
    "src.shared.http.sse",
    # rag-service
    "src.services.rag_service",
    "src.services.rag_service.deps",
    "src.services.rag_service.core.embedding_hub",
    "src.services.rag_service.core.index_hub",
    "src.services.rag_service.core.metadata",
    "src.services.rag_service.core.citations",
    "src.services.rag_service.core.retrievers",
    "src.services.rag_service.core.loaders",
    "src.services.rag_service.core.splitters",
    "src.services.rag_service.core.sqlite_store",
    # story-service
    "src.services.story_service",
    "src.services.story_service.deps",
    "src.services.story_service.core.ai.routing",
    "src.services.story_service.core.ai.models",
    "src.services.story_service.core.ai.prompts",
    "src.services.story_service.core.ai.structured",
    "src.services.story_service.core.ai.rag_client",
    "src.services.story_service.core.ai.image_client",
    "src.services.story_service.core.workflows.state",
    "src.services.story_service.core.workflows.checkpoint",
    "src.services.story_service.core.workflows.novel_graph",
    "src.services.story_service.core.workflows.character_graph",
    "src.services.story_service.core.workflows.review_graph",
    "src.services.story_service.core.services.run_registry",
    "src.services.story_service.core.services.event_bus",
    "src.services.story_service.core.services.creative_service",
    "src.services.story_service.core.services.project_store",
    # image-service
    "src.services.image_service",
    "src.services.image_service.deps",
    "src.services.image_service.core.ai.models",
    "src.services.image_service.core.ai.prompts",
    "src.services.image_service.core.ai.structured",
    "src.services.image_service.core.ai.story_client",
    "src.services.image_service.core.ai.rag_client",
    "src.services.image_service.core.workflows.state",
    "src.services.image_service.core.workflows.image_prompt_graph",
    "src.services.image_service.core.workflows.director_graph",
    "src.services.image_service.core.services.image_pipeline",
    "src.services.image_service.core.services.character_pipeline",
    "src.services.image_service.core.services.shot_pipeline",
    "src.services.image_service.core.services.publisher_service",
    "src.services.image_service.core.clients.hunyuan",
    "src.services.image_service.core.clients.custom_image",
    # gui backend
    "src.gui.backend",
    "src.gui.backend.ports",
    "src.gui.backend.errors",
    "src.gui.backend.events",
    "src.gui.backend.threading_bridge",
    "src.gui.backend._run_handle",
    "src.gui.backend.story_client",
    "src.gui.backend.rag_client",
    "src.gui.backend.image_client",
    "src.gui.backend.client",
]


def main() -> int:
    ok = fail = 0
    failures: list[str] = []
    for name in MODULES:
        try:
            importlib.import_module(name)
            ok += 1
        except Exception as exc:  # pragma: no cover - dev tool
            fail += 1
            failures.append(f"FAIL {name}: {type(exc).__name__}: {exc}")

    for line in failures:
        print(line)

    print(f"== imports ok={ok} fail={fail} total={len(MODULES)} ==")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
