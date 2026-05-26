"""ScriptWeaver v2 backend microservices.

Three independent FastAPI processes:

- `rag_service`   – embeddings, FAISS shards, project memory.
- `story_service` – LLM workflows for novel + character design.
- `image_service` – image prompts / shots / characters / director / publishing.

See docs/plans/2026-05-25-langchain-rag-novel-framework-v2.md.
"""
