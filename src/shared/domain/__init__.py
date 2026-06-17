"""Shared domain models. See docs/technical_architecture.md."""

from .schemas import (
    CharacterProfile,
    ChapterDraft,
    ContextBudget,
    KbType,
    OutlineSection,
    RetrievedContext,
    ShotPrompt,
    SourceRef,
    StoryBible,
)
from .events import CreativeEvent, EventType, deserialize_event, serialize_event
from .errors import (
    AuthError,
    CreativeError,
    DependencyMissing,
    ModelProviderError,
    NotFound,
    ProjectSaveError,
    RetrievalError,
    StructuredOutputError,
    WorkflowCancelled,
    WorkflowInterrupted,
)
from .runs import RunRegistry, RunStatus

__all__ = [
    "CharacterProfile",
    "ChapterDraft",
    "ContextBudget",
    "KbType",
    "OutlineSection",
    "RetrievedContext",
    "ShotPrompt",
    "SourceRef",
    "StoryBible",
    "CreativeEvent",
    "EventType",
    "serialize_event",
    "deserialize_event",
    "AuthError",
    "CreativeError",
    "DependencyMissing",
    "ModelProviderError",
    "NotFound",
    "ProjectSaveError",
    "RetrievalError",
    "StructuredOutputError",
    "WorkflowCancelled",
    "WorkflowInterrupted",
    "RunRegistry",
    "RunStatus",
]
