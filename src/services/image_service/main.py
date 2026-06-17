"""FastAPI app for image-service. See docs/technical_architecture.md.4."""

from __future__ import annotations


def create_app():
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    from src.services.image_service.api import (
        characters,
        director,
        health,
        images,
        prompts,
        publish,
        runs,
        shots,
    )
    from src.shared.domain.errors import CreativeError

    app = FastAPI(title="ScriptWeaver image-service", version="2.0.0")

    @app.exception_handler(CreativeError)
    async def creative_error_handler(_, exc: CreativeError):
        return JSONResponse(status_code=exc.http_status, content=exc.to_payload())

    app.include_router(health.router)
    app.include_router(prompts.router)
    app.include_router(shots.router)
    app.include_router(characters.router)
    app.include_router(images.router)
    app.include_router(director.router)
    app.include_router(publish.router)
    app.include_router(runs.router)
    return app
