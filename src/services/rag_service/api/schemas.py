"""HTTP request / response schemas for rag-service. See docs/technical_architecture.md.3."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.shared.domain.schemas import KbType, RetrievedContext


class DocumentIngest(BaseModel):
    source_id: str
    path: str = ""
    text: str
    tags: list[str] = Field(default_factory=list)
    project_id: str | None = None


class IngestRequest(BaseModel):
    documents: list[DocumentIngest]
    chunk_size: int = 600
    overlap: int = 80
    overlap_paragraphs: int = 1


class IngestResponse(BaseModel):
    ingested: int
    chunks: int
    shard: str


class DeleteResponse(BaseModel):
    removed: int


class SearchRequest(BaseModel):
    query: str
    kb_types: list[KbType] = Field(default_factory=lambda: ["reference"])
    project_id: str | None = None
    top_k: int = 8
    min_score: float = 0.0
    tags: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    results: list[RetrievedContext]


class MemoryEntry(BaseModel):
    source_id: str
    text: str
    tags: list[str] = Field(default_factory=list)


class MemoryWriteRequest(BaseModel):
    entries: list[MemoryEntry]


class MemoryEntryOut(BaseModel):
    chunk_id: str
    source_id: str
    text: str
    tags: list[str] = Field(default_factory=list)


class MemoryListResponse(BaseModel):
    entries: list[MemoryEntryOut]


class ManifestResponse(BaseModel):
    schema_version: int
    embedding_model: str | None
    vector_backend: str = "chroma"
    shards: list[dict]
