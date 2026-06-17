"""LangGraph state dicts. See docs/technical_architecture.md.4.

Note: events are NOT stored in state. EventBus distributes them externally.
"""

from __future__ import annotations

from typing import TypedDict

from src.shared.domain.schemas import (
    ChapterDraft,
    CharacterProfile,
    RetrievedContext,
    StoryBible,
)


class NovelWorkflowState(TypedDict, total=False):
    project_id: str
    run_id: str

    # inputs
    requirement: str
    genre: str
    style: str
    target_chars: int
    use_rag: bool
    chapter_count: int

    # stage outputs
    retrieved_contexts: list[RetrievedContext]
    story_bible: StoryBible
    chapters: list[ChapterDraft]
    current_section_index: int

    # rolling memory ledger (last N items only)
    rolling_memory: list[dict]

    # final
    final_text: str

    # failures
    errors: list[str]
    last_failed_node: str


class CharacterWorkflowState(TypedDict, total=False):
    project_id: str
    run_id: str
    story_context: str
    retrieved_contexts: list[RetrievedContext]
    characters: list[CharacterProfile]
    errors: list[str]
    last_failed_node: str
