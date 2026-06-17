"""uvicorn entry point for rag-service.

Run with::

    uvicorn src.services.rag_service.runtime:app --port 0 --host 127.0.0.1

See docs/technical_architecture.md.2 / 搂9.4.
"""

from __future__ import annotations

from src.services.rag_service.main import create_app

app = create_app()
