"""DI providers for image-service. See v2 plan §6."""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def get_run_registry():
    # image-service uses the same RunRegistry implementation as story-service.
    from src.services.story_service.core.services.run_registry import RunRegistry

    return RunRegistry()


@lru_cache(maxsize=1)
def get_event_bus():
    from src.services.story_service.core.services.event_bus import EventBus

    return EventBus()


@lru_cache(maxsize=1)
def get_image_pipeline():
    from src.services.image_service.core.services.image_pipeline import ImagePipeline

    return ImagePipeline()


@lru_cache(maxsize=1)
def get_character_pipeline():
    from src.services.image_service.core.services.character_pipeline import CharacterPipeline

    return CharacterPipeline()


@lru_cache(maxsize=1)
def get_shot_pipeline():
    from src.services.image_service.core.services.shot_pipeline import ShotPipeline

    return ShotPipeline()


@lru_cache(maxsize=1)
def get_publisher_service():
    from src.services.image_service.core.services.publisher_service import PublisherService

    return PublisherService()
