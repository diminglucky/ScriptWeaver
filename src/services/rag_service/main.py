"""FastAPI app for rag-service. See docs/technical_architecture.md.3.

Build-out steps (Phase 2):
    1. wire EmbeddingHub + IndexHub singletons in `deps.py`
    2. implement each router under `api/`
    3. add exception handler that maps CreativeError 鈫?JSON envelope (搂14.1)
"""

from __future__ import annotations


def create_app():
    """Construct the FastAPI app lazily so import is cheap before deps install."""
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    from src.services.rag_service.api import health, kb, memory, reindex, search
    from src.shared.domain.errors import CreativeError

    app = FastAPI(title="ScriptWeaver rag-service", version="2.0.0")

    @app.exception_handler(CreativeError)
    async def creative_error_handler(_request, exc: CreativeError):
        return JSONResponse(status_code=exc.http_status, content=exc.to_payload())

    app.include_router(health.router)
    app.include_router(kb.router)
    app.include_router(search.router)
    app.include_router(memory.router)
    app.include_router(reindex.router)
    return app


# Importing `app` requires FastAPI to be installed; keep it lazy.
def _lazy_app():
    return create_app()
