"""FastAPI app for story-service. See v2 plan §5, §7.2.

Build-out order (Phase 3):
    1. ModelRegistry singleton in `deps.py`
    2. prompts + structured output helpers
    3. novel_graph wired up with fake LLM
    4. SSE event bus + RunRegistry
    5. cancel/resume + interrupt_before
    6. ProjectStore + migrations
"""

from __future__ import annotations


def create_app():
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    from src.services.story_service.api import (
        characters,
        health,
        models,
        novel,
        projects,
        reviews,
        runs,
    )
    from src.shared.domain.errors import CreativeError

    app = FastAPI(title="ScriptWeaver story-service", version="2.0.0")

    @app.exception_handler(CreativeError)
    async def creative_error_handler(_request, exc: CreativeError):
        return JSONResponse(status_code=exc.http_status, content=exc.to_payload())

    app.include_router(health.router)
    app.include_router(models.router)
    app.include_router(projects.router)
    app.include_router(novel.router)
    app.include_router(characters.router)
    app.include_router(runs.router)
    app.include_router(reviews.router)
    return app
