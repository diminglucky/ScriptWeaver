"""Dependency-injection providers for rag-service routes.

The functions here are referenced by FastAPI routers via `Depends(...)`.
They are stubs in the scaffold and must be wired during Phase 2.
"""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def get_embedding_hub():
    """Return the singleton EmbeddingHub. See v2 plan §4.5."""
    from src.services.rag_service.core.embedding_hub import EmbeddingHub

    return EmbeddingHub()


@lru_cache(maxsize=1)
def get_index_hub():
    """Return the singleton IndexHub managing all FAISS shards."""
    from src.services.rag_service.core.index_hub import IndexHub

    return IndexHub()


@lru_cache(maxsize=1)
def get_retriever():
    from src.services.rag_service.core.retrievers import CreativeRetriever

    return CreativeRetriever(hub=get_index_hub(), embedder=get_embedding_hub())
