"""uvicorn entry point for image-service."""

from __future__ import annotations

from src.services.image_service.main import create_app

app = create_app()
