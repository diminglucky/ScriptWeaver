"""ScriptWeaver backend microservices.

Three independent FastAPI processes:

- `rag_service`: embeddings, Chroma shards, and project memory.
- `story_service`: LLM workflows for novels and character design.
- `image_service`: image prompts, shots, characters, director, and publishing.

See docs/technical_architecture.md.
"""
