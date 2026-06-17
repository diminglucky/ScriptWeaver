"""Dependency-injection providers for rag-service routes."""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def get_embedding_hub():
    """Return the singleton EmbeddingHub."""
    from src.services.rag_service.core.embedding_hub import EmbeddingHub

    return EmbeddingHub()


@lru_cache(maxsize=1)
def get_index_hub():
    """Return the singleton IndexHub managing Chroma shards."""
    from src.services.rag_service.core.index_hub import IndexHub

    return IndexHub()


@lru_cache(maxsize=1)
def get_retriever():
    from src.services.rag_service.core.retrievers import CreativeRetriever

    return CreativeRetriever(hub=get_index_hub(), embedder=get_embedding_hub())
