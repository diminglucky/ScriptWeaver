# LangChain RAG Novel Framework Implementation Plan

> **Status: Superseded by [`2026-05-25-langchain-rag-novel-framework-v2.md`](./2026-05-25-langchain-rag-novel-framework-v2.md)**.
> v2 把后端拆为 3 个 FastAPI 微服务（story / rag / image），并补齐了 v1 缺失的 image-service / HTTP 契约 / 跨服务取消 / 进程 supervisor / 持久化迁移 / 现有配置对接 等关键章节。本文档保留作为设计演进记录，请按 v2 实施。

**Goal:** 将现有 ScriptWeaver 从 Tkinter Mixin 驱动的功能集合，升级为一个以 LangChain + LangGraph 为核心的小说创作框架。框架需要统一支持 RAG 知识库、小说生成、角色设计、分镜/图片提示词、质量审稿、项目记忆和 UI 事件流。

**Recommended Architecture:** 保留当前 Tkinter UI，但将 AI/RAG/长流程创作逻辑抽离到独立服务层。UI 只负责采集参数、展示进度、处理人工确认；核心创作流程由 LangGraph workflow 编排，底层模型、检索、结构化输出由 LangChain 统一封装。

**Tech Stack:** Python, Tkinter, LangChain, LangGraph, Pydantic, FAISS, SQLite, OpenAI-compatible chat APIs, pytest

---

## 1. Scope and Principles

### Goals

- 建立统一的 `CreativeService`，供现有 GUI 调用。
- 建立 `domain` 数据模型，统一故事、角色、大纲、章节、分镜、素材片段的数据结构。
- 建立新的 `rag` 包，支持素材导入、切分、向量化、检索、重排、上下文压缩和来源追踪。
- 建立 LangGraph 工作流，支持小说生成、角色设计、分镜/图片提示词生成。
- 支持长篇生成的可中断、可恢复、可预览、可审稿、可保存。
- 逐步削薄现有 `src/gui/mixins/story_modules/` 和 `src/kb/` 中的业务逻辑。

### Non-Goals

- 第一阶段不重写 Tkinter UI。
- 第一阶段不引入云端数据库。
- 第一阶段不强制替换现有项目目录格式。
- 第一阶段不做完全自主 Agent，优先使用可控 workflow。

### Design Principles

- UI 不直接依赖 LangChain/LangGraph 细节。
- 所有中间产物优先使用 Pydantic 结构化模型。
- RAG 检索结果必须携带来源、chunk id、分数和知识库类型。
- 长流程必须通过事件流向 UI 汇报进度。
- 新框架先与旧流程并行，再逐步替换，避免一次性大改。

---

## 2. Target Directory Layout

```text
src/
  app/
    __init__.py
    creative_service.py
    events.py
    runtime.py

  domain/
    __init__.py
    schemas.py
    project_store.py
    errors.py

  ai/
    __init__.py
    models.py
    prompts.py
    structured.py
    routing.py

  rag/
    __init__.py
    loaders.py
    splitters.py
    metadata.py
    index.py
    retrievers.py
    context.py
    citations.py

  workflows/
    __init__.py
    state.py
    novel_graph.py
    character_graph.py
    image_prompt_graph.py
    review_graph.py

  gui/
    mixins/
      story_modules/
        story_generator.py      # gradually calls app.creative_service
      kb_mixin.py               # gradually calls rag.index / app service
```

---

## 3. Core Data Models

Create: `src/domain/schemas.py`

```python
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class SourceRef(BaseModel):
    source_id: str
    path: str
    chunk_id: str
    score: float = 0.0
    kb_type: Literal["reference", "project_memory", "style_corpus"] = "reference"


class RetrievedContext(BaseModel):
    text: str
    source: SourceRef
    reason: str = ""


class CharacterProfile(BaseModel):
    name: str
    role: Literal["protagonist", "antagonist", "supporting", "minor"]
    motivation: str
    fear: str = ""
    secret: str = ""
    arc: str = ""
    relationship_notes: list[str] = Field(default_factory=list)
    visual_anchor: list[str] = Field(default_factory=list)
    negative_visuals: list[str] = Field(default_factory=list)
    image_prompt_base: str = ""


class OutlineSection(BaseModel):
    index: int
    title: str
    purpose: str
    conflict: str
    required_beats: list[str] = Field(default_factory=list)
    expected_chars: int = 1800


class StoryBible(BaseModel):
    requirement: str
    genre: str = ""
    style: str = ""
    theme: str = ""
    premise: str = ""
    core_conflict: str = ""
    rules: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    characters: list[CharacterProfile] = Field(default_factory=list)
    outline: list[OutlineSection] = Field(default_factory=list)
    foreshadowing: list[str] = Field(default_factory=list)
    continuity_memory: list[str] = Field(default_factory=list)


class ChapterDraft(BaseModel):
    section_index: int
    title: str
    content: str
    summary: str = ""
    continuity_updates: list[str] = Field(default_factory=list)
    citations: list[SourceRef] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)


class ShotPrompt(BaseModel):
    shot_id: str
    section_index: int | None = None
    characters: list[str] = Field(default_factory=list)
    scene: str
    camera: str = ""
    mood: str = ""
    prompt: str
    negative_prompt: str = ""
```

Exit Criteria:

- 所有新模型可被 `pytest` 导入。
- 模型字段覆盖现有故事、大纲、角色、分镜的核心数据。
- 旧项目保存格式暂不迁移，但可以从这些模型导出 JSON。

---

## 4. RAG Framework Design

### 4.1 Knowledge Types

RAG 不再只是一组文件向量，而是三类知识库：

- `reference`: 用户导入的参考文章、知乎回答、小说片段、资料文档。
- `project_memory`: 当前项目生成出的设定、章节摘要、伏笔、角色状态。
- `style_corpus`: 风格样本、爆款结构、语言节奏、禁止表达。

### 4.2 Metadata Schema

Create: `src/rag/metadata.py`

```python
from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentMeta(BaseModel):
    source_id: str
    path: str
    title: str = ""
    kb_type: str = "reference"
    tags: list[str] = Field(default_factory=list)
    created_at: str = ""


class ChunkMeta(BaseModel):
    chunk_id: str
    source_id: str
    path: str
    chunk_index: int
    kb_type: str = "reference"
    start_char: int | None = None
    end_char: int | None = None
    tags: list[str] = Field(default_factory=list)
```

### 4.3 Storage Design

Use:

- FAISS for vectors.
- SQLite for document metadata and chunk metadata.
- Existing `index/` directory remains the default local storage root.

Target layout:

```text
index/
  vector/
    kb.faiss
    kb.pkl
  metadata.sqlite3
  manifest.json
```

### 4.4 RAG Modules

Create:

- `src/rag/loaders.py`: load txt, md, docx, pdf.
- `src/rag/splitters.py`: story-aware splitting.
- `src/rag/index.py`: build, update, delete, save, load.
- `src/rag/retrievers.py`: retrieve by query, scene, character, style.
- `src/rag/context.py`: assemble prompt context with budgets.
- `src/rag/citations.py`: convert LangChain documents to `RetrievedContext`.

### 4.5 Retrieval Strategy

Default retrieval pipeline:

```text
query
-> vector similarity search
-> metadata filter by kb_type/tags/project
-> optional MMR diversification
-> optional rerank
-> score threshold
-> context compression
-> citation packaging
```

Initial implementation can skip rerank, but keep the interface:

```python
class CreativeRetriever:
    def retrieve(
        self,
        query: str,
        *,
        kb_types: list[str] | None = None,
        tags: list[str] | None = None,
        top_k: int = 6,
        min_score: float = 0.12,
    ) -> list[RetrievedContext]:
        ...
```

Exit Criteria:

- Existing KB build/search tests still pass.
- New retriever can read current `data/` and write to `index/`.
- Search results include `text`, `source.path`, `source.chunk_id`, `source.score`.

---

## 5. AI Model and Prompt Layer

### 5.1 Model Registry

Create: `src/ai/models.py`

Responsibilities:

- Convert existing provider settings into LangChain chat models.
- Support OpenAI-compatible providers such as DeepSeek and custom APIs.
- Centralize timeout, streaming, temperature, max tokens.
- Keep existing custom HTTP behavior if needed.

Interface:

```python
class ModelRegistry:
    def chat_model(self, task: str, provider: str | None = None, model: str | None = None):
        ...

    def embedding_model(self, provider: str | None = None):
        ...
```

### 5.2 Structured Output Helpers

Create: `src/ai/structured.py`

Responsibilities:

- Call LLM with Pydantic schema output.
- Retry invalid JSON/invalid schema.
- Record validation errors for UI and tests.

Interface:

```python
def invoke_structured(llm, prompt, schema_type, *, max_retries: int = 2):
    ...
```

### 5.3 Prompt Library

Create: `src/ai/prompts.py`

Prompt categories:

- requirement parser
- story bible builder
- character designer
- outline generator
- chapter writer
- chapter reviewer
- continuity updater
- image prompt writer
- style rewriter

Exit Criteria:

- No prompt template reads Tkinter widgets directly.
- Prompts accept plain data models or dictionaries.
- Unit tests can call prompts without creating GUI.

---

## 6. LangGraph Workflow Design

Create: `src/workflows/state.py`

```python
from __future__ import annotations

from typing import TypedDict, Any
from src.domain.schemas import StoryBible, ChapterDraft, RetrievedContext, ShotPrompt


class NovelWorkflowState(TypedDict, total=False):
    project_id: str
    requirement: str
    genre: str
    style: str
    target_chars: int
    use_rag: bool
    retrieved_contexts: list[RetrievedContext]
    story_bible: StoryBible
    chapters: list[ChapterDraft]
    current_section_index: int
    final_text: str
    errors: list[str]
    events: list[dict[str, Any]]
```

### 6.1 Novel Graph

Create: `src/workflows/novel_graph.py`

Graph:

```text
parse_requirement
-> retrieve_reference_context
-> build_story_bible
-> design_characters
-> generate_outline
-> review_outline
-> human_review_outline?
-> generate_chapter_loop
-> review_chapter
-> repair_chapter?
-> update_project_memory
-> assemble_final_story
-> save_project
```

Key rules:

- First version supports a non-interrupt path.
- Second version adds human review before applying outline/chapter.
- Chapter loop must update `StoryBible.continuity_memory`.
- Each chapter saves partial output to project storage.

### 6.2 Character Graph

Create: `src/workflows/character_graph.py`

Graph:

```text
parse_story_context
-> retrieve_character_references
-> generate_character_profiles
-> review_character_consistency
-> generate_visual_anchors
-> save_character_profiles
```

### 6.3 Image Prompt Graph

Create: `src/workflows/image_prompt_graph.py`

Graph:

```text
select_scene_or_section
-> retrieve_story_context
-> retrieve_character_visuals
-> generate_shot_list
-> generate_image_prompts
-> review_prompt_safety
-> save_shot_prompts
```

Exit Criteria:

- Workflows can run headlessly in tests.
- Workflow emits progress events.
- Workflow can return partial results after failure.

---

## 7. Application Service and Event Stream

Create: `src/app/events.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CreativeEvent:
    type: str
    message: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
```

Create: `src/app/creative_service.py`

Responsibilities:

- Provide GUI-friendly methods.
- Start workflows in background threads.
- Convert workflow stream output into `CreativeEvent`.
- Save project snapshots.
- Surface errors in a stable format.

Interface:

```python
class CreativeService:
    def generate_novel(self, request, event_handler=None):
        ...

    def design_characters(self, request, event_handler=None):
        ...

    def generate_image_prompts(self, request, event_handler=None):
        ...

    def build_knowledge_base(self, request, event_handler=None):
        ...
```

Exit Criteria:

- GUI can call `CreativeService` without importing LangGraph.
- CLI/test can call `CreativeService` without Tkinter.
- All service methods support progress callback.

---

## 8. GUI Integration Plan

### Phase A: Adapter Only

Modify existing GUI methods to optionally call new service behind an env flag:

- `STORY_USE_LANGCHAIN_WORKFLOW=1`
- `RAG_USE_LANGCHAIN_FRAMEWORK=1`

Target files:

- `src/gui/mixins/story_modules/story_generator.py`
- `src/gui/mixins/story_modules/outline_generate_mixin.py`
- `src/gui/mixins/kb_mixin.py`
- `src/gui/mixins/image_modules/shot_prompt_mixin.py`

### Phase B: Default New Flow

After tests and manual smoke pass:

- Make new workflow default.
- Keep old path behind fallback flag:
  - `STORY_USE_LEGACY_GENERATOR=1`

### Phase C: Remove Duplication

Gradually remove:

- prompt parsing code duplicated in GUI mixins
- direct RAG calls from GUI
- direct DeepSeek client construction from story modules

Exit Criteria:

- UI behavior remains the same for normal users.
- Generated stories still auto-save into existing `projects/`.
- Preview dialog still works.
- Cancellation or failure leaves partial project data recoverable.

---

## 9. Implementation Phases

## Phase 0: Stabilize Current Baseline

### Task 0.1: Fix current failing KB cache tests

Files:

- Modify: `src/kb/ingest.py`
- Modify: `src/kb/search.py`

Plan:

- Expose `get_sentence_transformer` at module level.
- Keep lazy dependency behavior for LangChain backends.
- Re-run `pytest -q`.

Acceptance:

- `pytest -q` returns all tests passing.

---

## Phase 1: Domain Models and Service Skeleton

### Task 1.1: Add Pydantic schemas

Files:

- Create: `src/domain/__init__.py`
- Create: `src/domain/schemas.py`
- Create: `tests/test_domain_schemas.py`

Acceptance:

- Models instantiate from simple dictionaries.
- Models serialize to JSON-compatible dictionaries.

### Task 1.2: Add event model and empty service

Files:

- Create: `src/app/__init__.py`
- Create: `src/app/events.py`
- Create: `src/app/creative_service.py`
- Create: `tests/test_creative_service_skeleton.py`

Acceptance:

- Service imports without Tkinter.
- Event callback receives start/done events in a fake method.

---

## Phase 2: New RAG Package

### Task 2.1: Add loaders and splitters

Files:

- Create: `src/rag/__init__.py`
- Create: `src/rag/loaders.py`
- Create: `src/rag/splitters.py`
- Create: `tests/test_rag_loaders_splitters.py`

Acceptance:

- Loads `.txt` and `.md`.
- Existing optional `.docx`/`.pdf` behavior preserved.
- Splits long Chinese text with overlap.

### Task 2.2: Add metadata store

Files:

- Create: `src/rag/metadata.py`
- Create: `src/rag/sqlite_store.py`
- Create: `tests/test_rag_metadata_store.py`

Acceptance:

- Can insert document and chunk metadata.
- Can query chunks by source id and kb type.

### Task 2.3: Add index builder and retriever

Files:

- Create: `src/rag/index.py`
- Create: `src/rag/retrievers.py`
- Create: `src/rag/citations.py`
- Create: `tests/test_rag_index_retriever.py`

Acceptance:

- Builds FAISS index from sample documents.
- Retrieves context with score and source metadata.
- Missing optional dependencies produce actionable errors.

---

## Phase 3: AI Model Layer

### Task 3.1: Add model registry

Files:

- Create: `src/ai/__init__.py`
- Create: `src/ai/models.py`
- Create: `src/ai/routing.py`
- Create: `tests/test_ai_model_registry.py`

Acceptance:

- Can construct chat model from existing provider config.
- Does not require GUI.
- Does not read secret values in tests.

### Task 3.2: Add structured output helper

Files:

- Create: `src/ai/structured.py`
- Create: `tests/test_ai_structured.py`

Acceptance:

- Fake LLM can return valid Pydantic model.
- Invalid structured output retries or returns clear error.

---

## Phase 4: Novel Workflow MVP

### Task 4.1: Add workflow state and graph skeleton

Files:

- Create: `src/workflows/__init__.py`
- Create: `src/workflows/state.py`
- Create: `src/workflows/novel_graph.py`
- Create: `tests/test_novel_graph_skeleton.py`

Acceptance:

- Graph runs with fake LLM and fake retriever.
- Emits states for parse, outline, chapter, save.

### Task 4.2: Implement StoryBible generation

Files:

- Modify: `src/workflows/novel_graph.py`
- Modify: `src/ai/prompts.py`
- Create: `tests/test_novel_graph_story_bible.py`

Acceptance:

- Requirement becomes `StoryBible`.
- Characters and outline are structured.
- Validation failure is recoverable.

### Task 4.3: Implement chapter loop

Files:

- Modify: `src/workflows/novel_graph.py`
- Create: `tests/test_novel_graph_chapters.py`

Acceptance:

- Generates all outline sections with fake LLM.
- Updates continuity memory per chapter.
- Produces final assembled text.

---

## Phase 5: Project Memory and Persistence

### Task 5.1: Add domain project store adapter

Files:

- Create: `src/domain/project_store.py`
- Modify: `src/project_manager.py` only if needed
- Create: `tests/test_domain_project_store.py`

Acceptance:

- Saves StoryBible JSON.
- Saves chapter drafts.
- Saves final story in existing `story.txt`.
- Existing project loading still works.

### Task 5.2: Add project memory indexing

Files:

- Modify: `src/rag/index.py`
- Modify: `src/workflows/novel_graph.py`
- Create: `tests/test_project_memory_indexing.py`

Acceptance:

- Chapter summaries can be inserted into `project_memory`.
- Later chapters retrieve prior memory.

---

## Phase 6: GUI Adapter

### Task 6.1: Wire story generation behind env flag

Files:

- Modify: `src/gui/mixins/story_modules/story_generator.py`
- Create: `tests/test_story_generator_langchain_adapter.py`

Acceptance:

- With `STORY_USE_LANGCHAIN_WORKFLOW=1`, GUI calls `CreativeService`.
- With flag off, legacy path still works.
- Event messages update status/output safely.

### Task 6.2: Wire KB build/search behind service

Files:

- Modify: `src/gui/mixins/kb_mixin.py`
- Modify: `src/gui/mixins/kb_enhancements.py`
- Create: `tests/test_kb_gui_adapter.py`

Acceptance:

- Existing KB buttons still work.
- New RAG package receives build/search requests.
- User-facing errors remain understandable.

---

## Phase 7: Character and Image Prompt Workflows

### Task 7.1: Character graph

Files:

- Create: `src/workflows/character_graph.py`
- Create: `tests/test_character_graph.py`

Acceptance:

- Creates structured `CharacterProfile` list.
- Stores visual anchors for image generation.
- Can run from story requirement or existing StoryBible.

### Task 7.2: Image prompt graph

Files:

- Create: `src/workflows/image_prompt_graph.py`
- Create: `tests/test_image_prompt_graph.py`

Acceptance:

- Creates structured `ShotPrompt` list.
- Uses character visual anchors.
- Supports scene/section-level prompt generation.

### Task 7.3: GUI integration

Files:

- Modify: `src/gui/mixins/image_modules/shot_prompt_mixin.py`
- Modify: `src/gui/mixins/image_modules/char_description.py`

Acceptance:

- Existing image page can request AI shot prompts.
- Character visual consistency improves without changing image API.

---

## 10. Error Handling and Recovery

Use stable domain errors:

- `DependencyMissingError`
- `ModelProviderError`
- `StructuredOutputError`
- `RetrievalError`
- `WorkflowInterrupted`
- `ProjectSaveError`

Rules:

- Workflow nodes catch expected errors and append them to state.
- Fatal errors emit `workflow_failed` event.
- Partial outputs are saved whenever possible.
- GUI displays friendly messages and keeps raw error in logs.

---

## 11. Testing Strategy

### Unit Tests

- Domain schemas validation.
- RAG loader/splitter/index/retriever.
- Model registry with fake config.
- Structured output parser with fake LLM.
- Workflow nodes with fake LLM/retriever/project store.

### Integration Tests

- Build mini KB from test fixtures.
- Run novel workflow MVP with fake LLM.
- Save and reload generated project.

### Regression Tests

- Existing `pytest -q` must stay green.
- Existing story generation legacy tests must keep passing until legacy removal.

### Manual Smoke

- Launch app.
- Build KB from sample txt.
- Generate short story with new workflow flag.
- Confirm preview and project auto-save.
- Generate characters from story.
- Generate image prompts from one chapter.

---

## 12. Rollback Plan

- Keep legacy story generation path behind `STORY_USE_LEGACY_GENERATOR=1`.
- Keep existing `src/kb` package until new `src/rag` is fully validated.
- New files are additive through Phase 5.
- GUI adapter is guarded by env flags in Phase 6.
- If workflow fails in production use, UI can fall back to current `_run_story_generation`.

---

## 13. Recommended Implementation Order

1. Fix current KB cache test failures.
2. Add `domain` schemas and `app` event/service skeleton.
3. Build new `rag` package with FAISS + SQLite.
4. Add `ai` model registry and structured output helpers.
5. Implement `novel_graph` with fake LLM tests first.
6. Add project memory persistence.
7. Wire GUI story generation behind env flag.
8. Add character workflow.
9. Add image prompt workflow.
10. Make new workflow default after manual smoke tests.

---

## 14. Acceptance Criteria for the Full Framework

- `pytest -q` passes.
- GUI starts normally.
- RAG build/search works with local documents.
- Novel generation creates `StoryBible`, structured outline, chapters, final text.
- Character design creates structured role profiles and visual anchors.
- Image prompt generation creates reusable shot prompts.
- Project output remains compatible with existing `projects/` directory.
- New framework can run without Tkinter in tests or CLI.
- User can recover partial results after workflow failure.
