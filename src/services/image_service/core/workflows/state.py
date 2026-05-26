"""LangGraph state for image prompt + director workflows."""

from __future__ import annotations

from typing import TypedDict

from src.shared.domain.schemas import (
    CharacterProfile,
    RetrievedContext,
    ShotPrompt,
)


class ImagePromptState(TypedDict, total=False):
    project_id: str
    run_id: str
    section_index: int
    chapter_text: str
    retrieved_contexts: list[RetrievedContext]
    character_anchors: list[CharacterProfile]
    shots: list[ShotPrompt]
    errors: list[str]
    last_failed_node: str


class DirectorState(TypedDict, total=False):
    project_id: str
    run_id: str
    chapter_count: int
    director_script: dict
    errors: list[str]
    last_failed_node: str
