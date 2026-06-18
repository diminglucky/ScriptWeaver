"""HTTP request / response schemas for rag-service. See docs/technical_architecture.md.3."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.shared.domain.schemas import KbType, RetrievedContext


class DocumentIngest(BaseModel):
    source_id: str
    path: str = ""
    text: str
    tags: list[str] = Field(default_factory=list)
    project_id: str | None = None


class IngestRequest(BaseModel):
    documents: list[DocumentIngest]
    chunk_size: int = Field(default=600, ge=1, le=4000)
    overlap: int = Field(default=80, ge=0, le=3999)
    overlap_paragraphs: int = Field(default=1, ge=0)
    paragraphs_per_chunk: int = Field(default=4, ge=1, le=12)

    @field_validator("documents")
    @classmethod
    def _documents_must_not_be_empty(cls, value: list[DocumentIngest]) -> list[DocumentIngest]:
        if not value:
            raise ValueError("documents must not be empty")
        source_ids = [doc.source_id for doc in value]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("documents source_id values must be unique")
        return value

    @model_validator(mode="after")
    def _validate_chunk_window(self) -> "IngestRequest":
        if self.overlap >= self.chunk_size:
            raise ValueError("overlap must be less than chunk_size")
        if self.overlap_paragraphs >= self.paragraphs_per_chunk:
            raise ValueError("overlap_paragraphs must be less than paragraphs_per_chunk")
        return self


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
    top_k: int = Field(default=8, ge=1, le=50)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)
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
