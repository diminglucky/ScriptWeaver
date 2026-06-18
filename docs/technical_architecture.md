# ScriptWeaver Technical Architecture

This document describes the current RAG and writing pipeline architecture.

## Runtime Shape

ScriptWeaver keeps the Tkinter GUI separate from backend services. The v2
backend is split into local FastAPI services:

- `rag_service`: ChromaDB vector storage, SQLite chunk metadata, search, and project memory.
- `story_service`: model routing, prompts, novel and character workflows.
- `image_service`: image prompt and publishing workflows.

The GUI talks to services through backend clients instead of importing model,
vector, or HTTP provider internals directly.

## RAG Storage

The production vector backend is ChromaDB. Each knowledge scope is stored as a
separate shard under `index/v2`:

```text
index/
  v2/
    manifest.json
    reference/
      _global/
        chroma/
        meta.sqlite
    project_memory/
      <project_id>/
        chroma/
        meta.sqlite
    style_corpus/
      _global/
        chroma/
        meta.sqlite
```

`meta.sqlite` contains two coordinated tables:

- `chunks`: source of truth for retrievable chunk text, source id, path, tags,
  project id, chunk position, and deterministic insertion order.
- `documents`: source manifest for each indexed document, including path,
  content hash, size, chunk count, chunk settings, embedding model, and indexed
  timestamp.

ChromaDB stores normalized embedding vectors and performs cosine search. SQLite
keeps the auditable text/provenance layer so the GUI can preview built chunks
and document-level index state without reading Chroma internals.

## Ingestion

Documents are read through shared loaders and split by paragraph windows, not
fixed character windows. The splitter treats each non-empty line as a prose
paragraph, groups `paragraphs_per_chunk` whole paragraphs per chunk, and carries
`overlap_paragraphs` whole paragraphs from the previous chunk into the next.
`chunk_size` is only a safety cap for sentence-aware fallback when a single
paragraph is extremely long.

Ingest writes:

- `chunk_id`: deterministic id from source and chunk text.
- `text`: paragraph-aware chunk text.
- `source_id` and `path`: provenance.
- `kb_type`: `reference`, `project_memory`, or `style_corpus`.
- `project_id`: set only for project memory.
- `tags`: retrieval filters such as `reference`, `chapter_summary`, and `continuity`.
- Chroma embedding vector.
- Document manifest row in `documents`, keyed by `source_id`.

Incremental ingestion compares the current file hash, embedding model, and chunk
settings against the `documents` manifest:

- Unchanged documents are skipped.
- Changed documents replace all chunks for that source and refresh the manifest row.
- New documents append new chunks and a new manifest row.
- Missing source files are pruned when deleted-document pruning is enabled.

The HTTP ingestion API writes the same document manifest as the GUI/CLI ingestion
path, so API-added documents can also be inspected and deleted consistently.

## Retrieval

`CreativeRetriever` embeds the query once, fans out across requested shards,
filters by score and tags, then returns `RetrievedContext` objects with source
citations. `project_memory` searches are scoped to a single project id, which
prevents cross-project continuity leakage.

## Writing Pipeline Integration

Novel generation uses RAG in two places:

- Before building the story bible, it retrieves global `reference` context from the user requirement.
- Before each chapter, it retrieves both global `reference` and project-scoped `project_memory`.

The chapter prompt receives:

- `chapter_contexts`: structured retrieved chunks.
- `chapter_context_text`: compact source-labeled context lines.
- `previous_chapter_summaries`: recent summaries for local continuity.

After each chapter, the workflow writes a structured project-memory entry with
the chapter number, title, summary, and continuity updates. The next chapter can
retrieve those entries, so the RAG layer supports forward consistency rather
than acting as a one-off reference lookup.

## Admin and Manifest

`GET /v1/admin/manifest` returns the current RAG manifest.
`POST /v1/admin/manifest:rebuild` rewrites manifest metadata for the current
shards. There is no legacy index migration endpoint in the active architecture.

## Dependency Boundary

Required RAG dependencies:

- `chromadb`
- `sentence-transformers`
- `fastapi`, `uvicorn`, `httpx`, `sse-starlette`
- `pydantic` / `pydantic-settings`

The active RAG implementation talks directly to ChromaDB and does not depend on
vector-store wrapper frameworks.
