"""DI providers for story-service routes. See v2 plan §5."""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def get_model_registry():
    from src.services.story_service.core.ai.models import ModelRegistry

    return ModelRegistry.from_config()


@lru_cache(maxsize=1)
def get_prompt_library():
    from src.services.story_service.core.ai.prompts import PromptLibrary

    return PromptLibrary.from_config()


@lru_cache(maxsize=1)
def get_run_registry():
    from src.services.story_service.core.services.run_registry import RunRegistry

    return RunRegistry()


@lru_cache(maxsize=1)
def get_event_bus():
    from src.services.story_service.core.services.event_bus import EventBus

    return EventBus()


@lru_cache(maxsize=1)
def get_rag_client():
    from src.services.story_service.core.ai.rag_client import RagClient
    from src.shared.config.settings import ServiceSettings

    settings = ServiceSettings()
    return RagClient(
        base_url=settings.rag_base_url,
        token=settings.backend_token,
        service_token=settings.service_token,
    )


@lru_cache(maxsize=1)
def get_workflow_runner():
    from src.services.story_service.core.workflows.runner import WorkflowRunner

    return WorkflowRunner(
        registry=get_model_registry(),
        prompts=get_prompt_library(),
        rag_client=get_rag_client(),
    )


@lru_cache(maxsize=1)
def get_creative_service():
    from src.services.story_service.core.services.creative_service import CreativeService

    return CreativeService(
        registry=get_model_registry(),
        prompts=get_prompt_library(),
        runs=get_run_registry(),
        bus=get_event_bus(),
        runner=get_workflow_runner(),
    )
