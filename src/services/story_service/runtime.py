"""uvicorn entry point for story-service.

Run with::

    uvicorn src.services.story_service.runtime:app --port 0 --host 127.0.0.1
"""

from __future__ import annotations

from src.services.story_service.main import create_app

app = create_app()
