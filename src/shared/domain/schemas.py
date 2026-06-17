"""Pydantic v2 schemas shared by services, HTTP contracts, and persistence.

Source of truth for the current architecture Any change here must remain
backwards compatible with `projects/<id>/storybible.json`,
`projects/<id>/chapters/*.json`, and `projects/<id>/shots/shots.json`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

KbType = Literal["reference", "project_memory", "style_corpus"]


class SourceRef(BaseModel):
    """Reference to a chunk inside one of the RAG shards."""

    source_id: str
    path: str
    chunk_id: str
    score: float = 0.0
    kb_type: KbType = "reference"
    project_id: str | None = None  # only set for project_memory entries


class RetrievedContext(BaseModel):
    """A single retrieved chunk + provenance + retrieval rationale."""

    text: str
    source: SourceRef
    reason: str = ""
    truncated: bool = False


class CharacterProfile(BaseModel):
    """Character profile produced by the character workflow."""

    name: str
    # Free-form to tolerate Chinese / mixed responses; prompt enforces semantics.
    role: str = "supporting"
    motivation: str = ""
    fear: str = ""
    secret: str = ""
    arc: str = ""
    relationship_notes: list[str] = Field(default_factory=list)
    visual_anchor: list[str] = Field(default_factory=list)
    negative_visuals: list[str] = Field(default_factory=list)
    image_prompt_base: str = ""


class OutlineSection(BaseModel):
    """One section of the outline (typically one chapter)."""

    index: int
    title: str
    purpose: str = ""
    conflict: str = ""
    required_beats: list[str] = Field(default_factory=list)
    expected_chars: int = 1800


class StoryBible(BaseModel):
    """Full story bible persisted as `projects/<id>/storybible.json`.

    `continuity_memory` lives in rag-service's `project_memory` shard, not here.
    """

    requirement: str
    genre: str = ""
    style: str = ""
    theme: str = ""
    premise: str = ""
    core_conflict: str = ""
    target_chars: int = 0
    rules: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    characters: list[CharacterProfile] = Field(default_factory=list)
    outline: list[OutlineSection] = Field(default_factory=list)
    foreshadowing: list[str] = Field(default_factory=list)


class ChapterDraft(BaseModel):
    """Single chapter persisted as `projects/<id>/chapters/<NNN>.json`."""

    section_index: int
    title: str
    content: str
    summary: str = ""
    continuity_updates: list[str] = Field(default_factory=list)
    citations: list[SourceRef] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)
    char_count: int = 0
    token_usage: dict[str, int] = Field(default_factory=dict)


class ShotPrompt(BaseModel):
    """A single image-generation shot prompt."""

    shot_id: str
    section_index: int | None = None
    characters: list[str] = Field(default_factory=list)
    scene: str
    camera: str = ""
    mood: str = ""
    aspect_ratio: str = "16:9"
    style_tags: list[str] = Field(default_factory=list)
    model_hint: str = ""
    prompt: str
    prompt_translated: str = ""
    negative_prompt: str = ""


class ContextBudget(BaseModel):
    """Optional token budget for RAG context returned to the caller."""

    max_total_tokens: int = 1500
    max_per_chunk_tokens: int = 400
    reserve_for_response: int = 0  # advisory only, not used for truncation
