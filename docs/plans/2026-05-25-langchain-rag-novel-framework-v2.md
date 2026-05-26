# LangChain RAG Novel Framework Implementation Plan — v2 (FastAPI Microservices)

> **Supersedes:** `2026-05-25-langchain-rag-novel-framework.md` (v1)
> **Status:** Draft, ready for implementation Phase 0–1
> **Architecture switch:** v2 splits the backend into **3 FastAPI services** (story / rag / image). The Tk GUI talks to them only over local HTTP/SSE. v1 had a single in-process service; that boundary is gone.

**Goal:** 把 ScriptWeaver 的 AI/RAG/创作流程从 Tk Mixin 中彻底抽离为 3 个本地 FastAPI 微服务，由 LangChain + LangGraph 编排核心创作工作流，由 Pydantic 统一中间产物与 HTTP 契约。GUI 通过 BackendClient + SSE 与服务通信，模块之间不再互相 import。

**Tech Stack:** Python 3.11, Tkinter, FastAPI, uvicorn, httpx, sse-starlette, LangChain, LangGraph, Pydantic v2, FAISS, SQLite, OpenAI-compatible chat APIs, pytest, Playwright.

---

## 1. Scope and Principles

### 1.1 Goals

- 把当前混杂在 `src/gui/mixins/` 中的业务逻辑抽到 3 个进程边界清晰的微服务后端。
- 用 LangChain + LangGraph 重写小说 / 角色 / 分镜三大工作流，输出可结构化、可中断、可恢复、可审稿。
- 用 FastAPI 暴露统一 HTTP+SSE 契约，GUI 只通过 `BackendClient` 调用，不再直接 import LangChain / FAISS / openai。
- 在不破坏现有 `projects/` 目录格式的前提下，新增 `StoryBible` / `ChapterDraft` 等结构化制品。
- 保留现有 `model_routing.json`、`custom_api_presets.json`、`config/.keyfile` 配置体系作为单一来源。

### 1.2 Non-Goals

- 不重写 Tk UI 视觉样式。
- 不引入云端数据库、不引入容器化部署。
- 不做完全自主 Agent，第一阶段保持显式 LangGraph 工作流。
- 不做跨机器分布式：3 个服务一律绑 `127.0.0.1`。

### 1.3 Design Principles

- **GUI 零 LangChain 依赖**：`src/gui/` 全树不允许 `import langchain` / `import langgraph` / `import faiss`。
- **Pydantic 即契约**：所有 HTTP req/resp、所有工作流 state、所有项目持久化结构共用同一份 `src/shared/domain/schemas.py`。
- **Run-id 贯穿全链路**：每次 mutation 立即返回 `run_id`，进度走 SSE，跨服务调用通过 `X-Run-Id` 头追踪。
- **取消必须可达**：GUI cancel 一定能传播到运行中的 LangGraph 节点和正在等待的下游 HTTP 调用。
- **新旧并行**：v2 服务上线后，旧 Mixin 路径通过 env flag `STORY_USE_LEGACY_PATH=1` 保留至少一个版本。

### 1.4 Service Boundary Decisions (locked)

| # | 决策 | 选择 | 备注 |
|---|---|---|---|
| 1 | `projects/` 归属 | **α**：story-service 独占，其他经 HTTP 读 | 强契约，未来可换网络 FS |
| 2 | embedding 模型 | **α**：仅在 rag-service | 单份加载，省 ~1GB / ~20s |
| 3 | image-service 取小说正文 | **α**：HTTP 调 story-service | 不让 GUI 转发大 JSON |
| 4 | 鉴权 | **β**：共享 token (env `WSF_BACKEND_TOKEN`) | localhost + token 双层 |
| 5 | 端口分配 | **β**：随机端口写 `.runtime/ports.json` | 避免冲突 |

---

## 2. Service Topology

```
┌─────────────────────────┐
│   Tk GUI (modern_app)   │
│   src/gui/backend/*     │
└────┬──────┬───────┬─────┘
     │ HTTP │ HTTP  │ HTTP+SSE
     ▼      ▼       ▼
┌─────────┐ ┌─────────┐ ┌──────────────┐
│ story-  │ │ rag-    │ │ image-       │
│ service │ │ service │ │ service      │
│  :auto  │ │  :auto  │ │  :auto       │
└────┬────┘ └────▲────┘ └────┬─────▲───┘
     │           │           │     │
     │ HTTP      │           │ HTTP│
     └───────────┴───────────┘     │
            (检索/写入 memory)      │
                                   │
        story-service ─HTTP────────┘
        (image 拉小说正文/StoryBible)
```

### 2.1 Per-service Responsibility Matrix

| Concern | story-service | rag-service | image-service |
|---|---|---|---|
| 小说工作流 (novel_graph) | ✅ owns | — | — |
| 角色工作流 (character_graph) | ✅ owns | — | — |
| ModelRegistry / chat LLM | ✅ owns | — | ✅ owns (translate / shot 提示词增强用) |
| Embedding / Vector index | — | ✅ owns | — |
| FAISS / SQLite metadata | — | ✅ owns | — |
| `projects/` 文件读写 | ✅ owns | read-only via HTTP | read-only via HTTP |
| LangGraph checkpointer | ✅ owns | — | ✅ owns (image_prompt_graph) |
| 图片生成 / 角色照片 / 三视图 | — | — | ✅ owns |
| 知乎 Playwright 发布 | — | — | ✅ owns |

### 2.2 Process Topology Rules

- 每个服务一个独立 `uvicorn` 进程，不共享线程。
- 任何 service 进程 crash 由 `ServiceSupervisor` 在 GUI 进程检测并尝试 1 次重启；连续失败 ≥2 次进入 degraded 模式。
- 服务间调用必须经 HTTP，不允许 `from src.services.rag_service.xxx import ...`。
- 共享纯库（`src/shared/domain`、`src/shared/config`）允许各服务 import，但禁止包含运行时状态。

---

## 3. Shared Domain Models

### 3.1 Layout

```text
src/shared/
  __init__.py
  domain/
    __init__.py
    schemas.py        # Pydantic 数据模型（即 HTTP/state/持久化共用）
    errors.py         # 跨服务错误码
    events.py         # CreativeEvent + 类型枚举
    runs.py           # RunId / RunStatus / RunRegistry 协议
    project_paths.py  # projects/ 目录布局工具
  config/
    __init__.py
    paths.py          # 项目根、index/、projects/、.runtime/ 解析
    routing.py        # 加载 model_routing.json
    presets.py        # 加载 custom_api_presets.json
    keyfile.py        # 复用 src/gui/mixins/enhancements_modules/secure_config.py 解密
    settings.py       # Pydantic Settings：服务端口、token、日志级别
  http/
    __init__.py
    auth.py           # token 校验中间件 / httpx 客户端注入
    sse.py            # SSE 编码/解码工具
    run_headers.py    # X-Run-Id 透传
```

### 3.2 Core Pydantic Schemas

`src/shared/domain/schemas.py`：

```python
from __future__ import annotations
from typing import Literal, Any
from pydantic import BaseModel, Field

KbType = Literal["reference", "project_memory", "style_corpus"]


class SourceRef(BaseModel):
    source_id: str
    path: str
    chunk_id: str
    score: float = 0.0
    kb_type: KbType = "reference"
    project_id: str | None = None  # 仅 project_memory 有值


class RetrievedContext(BaseModel):
    text: str
    source: SourceRef
    reason: str = ""


class CharacterProfile(BaseModel):
    name: str
    role: str = "supporting"  # 放宽为 str，prompt 端约束（兼容中文返回）
    motivation: str = ""
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
    purpose: str = ""
    conflict: str = ""
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
    # 注意：continuity_memory 不再放在 StoryBible，由 rag-service 的 project_memory 持有。


class ChapterDraft(BaseModel):
    section_index: int
    title: str
    content: str
    summary: str = ""
    continuity_updates: list[str] = Field(default_factory=list)
    citations: list[SourceRef] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)
    char_count: int = 0
    token_usage: dict[str, int] = Field(default_factory=dict)  # {prompt, completion, total}


class ShotPrompt(BaseModel):
    shot_id: str
    section_index: int | None = None
    characters: list[str] = Field(default_factory=list)
    scene: str
    camera: str = ""
    mood: str = ""
    aspect_ratio: str = "16:9"
    style_tags: list[str] = Field(default_factory=list)
    model_hint: str = ""           # 给特定图像 API 的提示
    prompt: str                    # 中文原始 prompt
    prompt_translated: str = ""    # 英文 / 翻译后版本（image_prompt_translate 路由）
    negative_prompt: str = ""
```

### 3.3 Events Schema

`src/shared/domain/events.py`：

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal

EventType = Literal[
    "run_started",
    "node_started",
    "node_finished",
    "token",                   # 流式 token chunk
    "partial_chapter",         # 章节中间产物
    "human_input_required",    # interrupt_before 触发
    "warning",
    "failed",
    "succeeded",
    "cancelled",
]


@dataclass
class CreativeEvent:
    type: EventType
    run_id: str
    message: str = ""
    node: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    ts: str = ""  # ISO8601, 服务端填


# Wire format（SSE data: <json>）
def serialize_event(ev: CreativeEvent) -> str: ...
def deserialize_event(line: str) -> CreativeEvent: ...
```

### 3.4 Run / Cancellation Protocol

`src/shared/domain/runs.py`：

```python
from typing import Protocol
import asyncio


class RunRegistry(Protocol):
    """每个服务进程内一份。"""
    def register(self, run_id: str) -> asyncio.Event: ...
    def cancel(self, run_id: str) -> bool: ...
    def is_cancelled(self, run_id: str) -> bool: ...
    def finish(self, run_id: str) -> None: ...
```

### 3.5 Errors

`src/shared/domain/errors.py`：

```python
class CreativeError(Exception):
    code: str = "creative_error"
    http_status: int = 500


class DependencyMissing(CreativeError):       # FAISS/torch/playwright 缺失
    code = "dependency_missing";   http_status = 503


class ModelProviderError(CreativeError):      # LLM 接口报错
    code = "model_provider_error"; http_status = 502


class StructuredOutputError(CreativeError):   # JSON/Pydantic 解析失败
    code = "structured_output";    http_status = 422


class RetrievalError(CreativeError):
    code = "retrieval_error";      http_status = 502


class WorkflowInterrupted(CreativeError):     # interrupt_before 等待人审
    code = "workflow_interrupted"; http_status = 409


class WorkflowCancelled(CreativeError):
    code = "workflow_cancelled";   http_status = 499


class ProjectSaveError(CreativeError):
    code = "project_save_error";   http_status = 500


class AuthError(CreativeError):
    code = "auth_error";           http_status = 401


class NotFound(CreativeError):
    code = "not_found";            http_status = 404
```

### 3.6 Project Paths Helper

`src/shared/domain/project_paths.py` 集中定义 v2 引入的子目录，确保三服务对同一份目录的解释一致：

```text
projects/<project_id>/
├── project.json           # 既有（保持兼容）
├── story.txt              # 既有（最终拼接版）
├── images/                # 既有
├── characters/            # 既有
├── storybible.json        # 新增：StoryBible 全量
├── chapters/              # 新增：ChapterDraft JSON 文件
│   ├── 001.json
│   ├── 002.json
│   └── ...
├── shots/                 # 新增：ShotPrompt 列表
│   └── shots.json
├── runs/                  # 新增：observability
│   └── <run_id>.jsonl
└── checkpoints.sqlite     # 新增：LangGraph SqliteSaver
```

`index/` 仍保留为全局 RAG 根目录，按 §4.3 重新组织。

---

## 4. rag-service Design

### 4.1 Responsibility

- 拥有 embedding 模型（仅此一处）。
- 拥有 FAISS 向量索引和 SQLite 元数据库。
- 接受文档摄入、删除、检索、写入 project_memory 的请求。
- 不持有 LLM 调用，不调用 chat 模型。
- 不读写 `projects/` 文件目录（除了 `project_memory` 索引中携带的引用）。

### 4.2 Layout

```text
src/services/rag_service/
  __init__.py
  main.py              # FastAPI app
  api/
    health.py
    kb.py              # /v1/kb/{kb_type}/documents (POST/DELETE)
    search.py          # /v1/kb/{kb_type}/search
    memory.py          # /v1/projects/{id}/memory  (project_memory CRUD)
    reindex.py         # /v1/admin/reindex
  deps.py              # DI: IndexHub / EmbeddingHub / SqliteStore
  core/
    loaders.py         # txt/md/docx/pdf
    splitters.py       # 中文友好切分（含 overlap）
    metadata.py        # DocumentMeta / ChunkMeta
    sqlite_store.py    # SQLite 接入
    embedding_hub.py   # 单例 SentenceTransformer 缓存
    index_hub.py       # FAISS 多分片管理
    retrievers.py      # CreativeRetriever
    citations.py       # 转 RetrievedContext
  runtime.py           # uvicorn entry: from src.services.rag_service.main import app
```

### 4.3 Storage Layout (multi-shard)

为解决 v1 单 FAISS 索引导致的多项目召回污染问题，rag-service 采用 **每 (kb_type, scope) 一份分片** 的多分片布局：

```text
index/
├── manifest.json                # 列出所有分片 + embedding model 版本
├── reference/
│   ├── shard.faiss
│   ├── shard.pkl
│   └── meta.sqlite3
├── style_corpus/
│   ├── shard.faiss
│   ├── shard.pkl
│   └── meta.sqlite3
└── project_memory/
    ├── <project_id_a>/
    │   ├── shard.faiss
    │   ├── shard.pkl
    │   └── meta.sqlite3
    └── <project_id_b>/
        └── ...
```

#### Shard Selection Rule

`CreativeRetriever.retrieve(query, kb_types=[...], project_id=...)` 内部并行查询多个分片，再按 score 合并：

```python
def retrieve(self, query, *, kb_types, project_id, top_k, min_score):
    shards = []
    if "reference" in kb_types:    shards.append(self.hub.shard("reference"))
    if "style_corpus" in kb_types: shards.append(self.hub.shard("style_corpus"))
    if "project_memory" in kb_types and project_id:
        shards.append(self.hub.shard("project_memory", project_id))
    futures = [s.search(query, top_k=top_k) for s in shards]
    merged = sorted(chain(*futures), key=lambda r: r.score, reverse=True)
    return [r for r in merged if r.score >= min_score][:top_k]
```

### 4.4 chunk_id Stability

`chunk_id = sha1(source_id + ":" + normalized_text[:512])[:16]`：

- 同一段文本被反复 ingest 仍是同一个 `chunk_id`。
- 用户更新参考资料后只删除消失的 `chunk_id`，保留的章节 `citations` 仍然可解析。
- 重切分（splitter 升级）会显式触发 `manifest.json` 中 schema 版本 +1，旧 `chunk_id` 不会立即失效，按 `source_id` 降级显示来源。

### 4.5 Embedding Hub

`embedding_hub.py` 是关键单例，保证 `SentenceTransformer` 只加载一次：

```python
class EmbeddingHub:
    _model: Any | None = None

    def get(self) -> SentenceTransformerLike:
        if self._model is None:
            from src.kb.model_cache import get_sentence_transformer
            self._model = get_sentence_transformer()  # 复用现有缓存
        return self._model

    def encode(self, texts: list[str]) -> list[list[float]]:
        return self.get().encode(texts, normalize_embeddings=True).tolist()

    async def encode_async(self, texts: list[str]) -> list[list[float]]:
        # 用 anyio 线程池避开 GIL 阻塞 event loop
        import anyio
        return await anyio.to_thread.run_sync(self.encode, texts)
```

**复用 `@/Volumes/F/code/play/Zhihu_short_stories/src/kb/model_cache.py:1`**，避免新框架与旧 `src/kb` 各加载一份模型。

### 4.6 Retrieval Pipeline

```text
HTTP query
  → AuthMiddleware (token)
  → RunHeader (X-Run-Id 注入)
  → CancelCheck (run cancelled? 立即返回 499)
  → embed query (EmbeddingHub.encode_async)
  → IndexHub.search per shard (并发)
  → metadata filter (tags, source_id whitelist)
  → MMR diversification (可选, k=top_k*2 → top_k)
  → score threshold
  → context compression (token budget aware, 见 §4.8)
  → citations packaging
  → 返回 list[RetrievedContext]
```

### 4.7 project_memory 协议

story-service 在每章生成完成后向 rag-service POST 章节摘要：

```
POST /v1/projects/{project_id}/memory
{
  "section_index": 3,
  "summary": "...",
  "plot_points": ["..."],
  "relation_changes": ["..."],
  "unresolved_hooks": ["..."],
  "state_shift": "..."
}
```

服务端组装为带 `kb_type=project_memory` 的 chunk，写入对应分片，返回新 `chunk_id`。

下一章生成时 story-service 通过 `POST /v1/kb/project_memory/search` 拿到前文摘要作为续写 context。

### 4.8 Token Budget for RAG Context

新增 `ContextBudget` Pydantic 模型，在 `/search` 请求里可选携带：

```python
class ContextBudget(BaseModel):
    max_total_tokens: int = 1500
    max_per_chunk_tokens: int = 400
    reserve_for_response: int = 0  # 仅作日志，不参与 RAG 截断
```

服务端使用 `tiktoken`（无该包则降级为按字符数 *0.6 估算）按 budget 裁剪 chunk 文本。截断时附 `truncated: true` 字段。

### 4.9 Exit Criteria

- `pytest tests/services/test_rag_service_*.py` 全绿。
- 现有 `index/` 旧数据可由 `POST /v1/admin/reindex` 一键迁移到新分片布局。
- 多项目并发检索召回不互相污染（端到端测试验证）。

---

## 5. story-service Design

### 5.1 Responsibility

- 拥有所有 chat LLM 调用（`ModelRegistry`）。
- 拥有 `novel_graph` / `character_graph` 两张 LangGraph 工作流。
- 拥有 `projects/` 目录的写权限（StoryBible / chapters / story.txt）。
- 拥有 LangGraph `SqliteSaver`，落盘 `projects/<id>/checkpoints.sqlite`。
- 跨服务依赖：检索调 rag-service；图像生成调 image-service（可选，UI 也可直接调 image-service）。

### 5.2 Layout

```text
src/services/story_service/
  __init__.py
  main.py
  api/
    health.py
    novel.py           # /v1/projects/{id}/novel:run / :resume / :cancel
    characters.py      # /v1/projects/{id}/characters:design
    runs.py            # /v1/runs/{run_id}/events  (SSE)
    projects.py        # /v1/projects/{id}/storybible / chapters/{idx} / story
    models.py          # /v1/models /v1/routing
    reviews.py         # /v1/runs/{run_id}/review (人审 decision)
  deps.py
  core/
    ai/
      models.py        # ModelRegistry
      prompts.py       # 提示词库（合并自 v1 + config/story_*_profile.json）
      structured.py    # invoke_structured（含 schema-fix 反馈重试）
      routing.py       # task → provider/model 解析（读 model_routing.json）
      rag_client.py    # httpx → rag-service
      image_client.py  # httpx → image-service（仅特定节点用）
    workflows/
      state.py         # NovelWorkflowState / CharacterWorkflowState
      novel_graph.py
      character_graph.py
      review_graph.py  # 通用审稿子图
      checkpoint.py    # SqliteSaver 工厂
    services/
      creative_service.py  # 业务编排：构图 → 启动 → 事件流
      project_store.py     # projects/ 读写 + StoryBible/ChapterDraft 持久化
      run_registry.py      # asyncio 取消机制
      event_bus.py         # SSE 队列（per run_id）
  runtime.py
```

### 5.3 ModelRegistry (核心)

读取 `@/Volumes/F/code/play/Zhihu_short_stories/model_routing.json:1` + `@/Volumes/F/code/play/Zhihu_short_stories/custom_api_presets.json:1` + `@/Volumes/F/code/play/Zhihu_short_stories/config/.keyfile`，统一构造 LangChain chat model。

```python
class ModelRegistry:
    def __init__(self, routing: RoutingConfig, presets: PresetsConfig, keyfile: KeyFile):
        ...

    def chat_model(
        self,
        task: TaskName,                     # Literal 见下表
        *,
        provider: str | None = None,        # 显式覆盖 routing
        model: str | None = None,
        temperature: float | None = None,
        streaming: bool = False,
        callbacks: list | None = None,
    ) -> BaseChatModel: ...

    def estimate_cost(self, task: TaskName, prompt_tokens: int, completion_tokens: int) -> float: ...
```

#### Task Name 与 model_routing.json 完全对齐

| TaskName | model_routing.json key |
|---|---|
| `story_outline` | `story_outline` |
| `story_generate` | `story_generate` |
| `character_extract` | `character_extract` |
| `character_description` | `character_description` |
| `image_prompt_translate` | `image_prompt_translate` |
| `image_prompt_enhance` | `image_prompt_enhance` |
| `image_prompt_from_story` | `image_prompt_from_story` |
| `image_prompt_from_shots` | `image_prompt_from_shots` |
| `image_shot_extract` | `image_shot_extract` |
| `image_shot_to_desc` | `image_shot_to_desc` |
| `director_script_generate` | `director_script_generate` |

> 文档 §12.1 列出 v1 文档中 9 个 prompt 类与 11 个 task 的映射差异。这里以 `model_routing.json` 为单一来源，所有节点必须使用上述 TaskName。

#### Provider 兼容

支持现有 4 类 provider，全部走 OpenAI 兼容协议：

- `DeepSeek` → `langchain_openai.ChatOpenAI(base_url=DEEPSEEK_BASE)`
- `Custom` → 读 `custom_api_presets.json` 中的 `base_url` / `api_key_alias`
- `OpenAI` → 标准
- `Anthropic` / `Gemini` → 通过现有 `custom_api_presets.json` 的 OpenAI 兼容代理（保持现状）

#### API Key 加载

复用 `@/Volumes/F/code/play/Zhihu_short_stories/src/gui/mixins/enhancements_modules/secure_config.py` 的解密逻辑，迁移到 `src/shared/config/keyfile.py`。**story-service 启动时一次性解密**，密钥保存在进程内存的 `KeyVault`，不写日志、不进 trace。

### 5.4 Workflow State

`src/services/story_service/core/workflows/state.py`：

```python
from typing import TypedDict
from src.shared.domain.schemas import StoryBible, ChapterDraft, RetrievedContext


class NovelWorkflowState(TypedDict, total=False):
    project_id: str
    run_id: str

    # Inputs
    requirement: str
    genre: str
    style: str
    target_chars: int
    use_rag: bool
    chapter_count: int

    # Stage outputs
    retrieved_contexts: list[RetrievedContext]
    story_bible: StoryBible
    chapters: list[ChapterDraft]
    current_section_index: int

    # Memory ledger（每章追加；存入 rag-service 的 project_memory 后从 state 弹出最旧条目）
    rolling_memory: list[dict]   # 最近 N 条（默认 N=3）

    # Final
    final_text: str

    # Failures
    errors: list[str]
    last_failed_node: str
    # 注意：不再持久化 events 到 state；事件通过 EventBus 外部分发。
```

### 5.5 Novel Graph (LangGraph)

```
START
  → parse_requirement
  → retrieve_reference_context     (httpx → rag-service /search reference + style_corpus)
  → build_story_bible              (structured output: StoryBible)
  → save_storybible                (project_store.save_storybible)
  → design_characters              (structured output: list[CharacterProfile])
  → generate_outline               (structured output: list[OutlineSection])
  → review_outline                 (子图 review_graph)
  → human_review_outline*          (interrupt_before, 等待 /v1/runs/{id}/review)
  → chapter_loop                   (子图：每章一次循环)
       ├ retrieve_chapter_context  (rag /search project_memory + reference)
       ├ generate_chapter          (流式 token, 推 partial_chapter)
       ├ review_chapter            (评分 + key_fix)
       ├ repair_chapter*           (低于阈值时一次重写)
       ├ summarize_chapter         (memory_ledger schema)
       └ push_to_project_memory    (httpx → rag-service /memory)
  → assemble_final_story           (拼 ChapterDraft.content → story.txt)
  → save_project                   (project_store.save_final)
  → END
```

`*` 表示 `interrupt_before`，由 checkpointer 配合 `Command(resume=...)` 续跑（详见 §8.4）。

### 5.6 Character Graph (LangGraph)

```
START
  → load_or_parse_story_context
  → retrieve_character_references  (rag /search reference)
  → generate_character_profiles    (structured output)
  → review_character_consistency
  → generate_visual_anchors        (output ≥ 3 visual_anchor / character)
  → save_character_profiles        (落 projects/<id>/characters/)
  → END
```

### 5.7 Structured Output Helper

`structured.py`：

```python
def invoke_structured(
    llm: BaseChatModel,
    prompt: ChatPromptValue,
    schema: type[BaseModel],
    *,
    max_retries: int = 2,
    repair: bool = True,                 # 失败时把 validation error 喂回 LLM
    on_attempt: Callable | None = None,  # 给观测用
) -> tuple[BaseModel, AttemptStats]: ...
```

行为：
1. 第一次：`llm.with_structured_output(schema)`。
2. 失败：捕获 `pydantic.ValidationError`，构造修复 prompt（含错误 path 列表），重新调用，**仍走结构化输出**而非裸 JSON。
3. `repair=False` 时退化为单纯重试。
4. 所有尝试记入 `AttemptStats`，并写 `runs/<run_id>.jsonl`。

### 5.8 Prompt Library 与现有配置融合

`prompts.py` 不重新发明轮子，而是从 `@/Volumes/F/code/play/Zhihu_short_stories/config/story_pipeline_profile.json:1`、`story_prompt_profile.json`、`story_guardrails.json` 加载用户已定制的内容：

| v1 文档中的 prompt 类 | 来源策略 |
|---|---|
| requirement parser | 新写，无既有配置 |
| story bible builder | 新写 + 合并 `story_prompt_profile.json` 中的风格规则 |
| character designer | 新写 + 合并 |
| outline generator | 新写 + 合并 `story_pipeline_profile.json.emotion_arc.story_lines` |
| chapter writer | 合并 `story_prompt_profile.json` 用户自定义模板 |
| chapter reviewer | **直接复用** `story_pipeline_profile.json.quality_review`（schema 字符串 → Pydantic） |
| continuity updater | **直接复用** `story_pipeline_profile.json.memory_ledger` |
| polish / fix | **直接复用** `story_pipeline_profile.json.polish` |
| image prompt writer | 走 image-service，不在此 |
| guardrails | **直接复用** `story_guardrails.json` 作为 system prompt 前缀 |

策略：v2 启动时读取这 3 份 JSON，**用户自定义优先**，`prompts.py` 只在缺失时提供默认值。

### 5.9 Project Store (持久化策略)

`project_store.py` 是 `projects/<id>/` 的唯一写入入口，方法清单：

```python
class ProjectStore:
    def __init__(self, project_id: str): ...

    # StoryBible
    def save_storybible(self, bible: StoryBible) -> None: ...
    def load_storybible(self) -> StoryBible | None: ...

    # Chapters
    def save_chapter(self, draft: ChapterDraft) -> None: ...
    def load_chapter(self, idx: int) -> ChapterDraft | None: ...
    def list_chapters(self) -> list[ChapterDraft]: ...

    # Final
    def save_final_story(self, text: str) -> None: ...
    def load_final_story(self) -> str: ...

    # 兼容：把 v1 旧 project.json 字段迁移到 StoryBible
    @classmethod
    def migrate_legacy(cls, project_id: str) -> StoryBible: ...
```

向下兼容规则（详见 §11）：

- 已有项目仅有 `project.json` + `story.txt` 时，`load_storybible()` 返回 `None`。
- 工作流可在缺 `StoryBible` 时从 `project.json.requirement` + `story.txt` 反推一个 minimal bible。
- 章节落盘格式：`chapters/001.json`，文件名 = `f"{section_index:03d}.json"`。
- 写 `story.txt` 时 atomic（先写 `.tmp` 再 rename），避免 GUI 读到半文件。

### 5.10 Cancellation & Checkpointing

- **取消**：`run_registry.cancel(run_id)` 设置 `asyncio.Event`。LangGraph 节点开头 `if registry.is_cancelled(run_id): raise WorkflowCancelled()`。所有 httpx 调用使用 `httpx.AsyncClient(timeout=...)` 并在 `cancel` 时 `client.aclose()`。
- **Checkpoint**：`SqliteSaver(database=projects/<id>/checkpoints.sqlite)`，`thread_id = run_id`（不是 `project_id`，因为同一项目可能多次重跑）。
- **Resume**：`POST /v1/runs/{run_id}/resume` 携带 `{ "decision": "approve" | "revise", "patch": {...} }`，`creative_service` 用 `Command(resume=patch)` 续跑。
- **保留时间**：`checkpoints.sqlite` 默认保留 30 天，由 supervisor 启动时清理过期记录。

### 5.11 Exit Criteria

- 启动 story-service 后 `GET /v1/health` 返回 `{ "status": "ok", "models_loaded": true }`。
- 用 fake LLM 跑通 `novel:run` → SSE → `succeeded`。
- 用 fake LLM 跑通 `novel:run` → 中断 outline → `resume` → `succeeded`。
- 用 fake LLM 跑通 `novel:run` → cancel → 返回 `cancelled` 事件并清理 checkpoint。

---

## 6. image-service Design

### 6.1 Responsibility

承接现有 `@/Volumes/F/code/play/Zhihu_short_stories/src/gui/mixins/image_modules/` 22 个 mixin 中所有非 UI 业务逻辑：

- 图像生成（`hunyuan_image_client`、其他自定义 image API）。
- 角色三视图、角色照片批量、分镜批量。
- 分镜 prompt 工作流（`image_prompt_graph`）+ 中文 → 英文翻译。
- 导演脚本生成（`director_script_generate`）。
- 知乎 Playwright 发布（`zhihu_publisher`）。

> **重要决策**：导演脚本与知乎发布也归 image-service，理由：(1) 它们都是"小说写完后"的下游产物，与图片产线在同一时间窗发生；(2) 都依赖 Playwright/外部进程；(3) 避免新设第 4 个服务进程。如未来发布业务膨胀，可拆出 `publish-service`。

### 6.2 Layout

```text
src/services/image_service/
  __init__.py
  main.py
  api/
    health.py
    prompts.py         # /v1/projects/{id}/image-prompts:generate
    characters.py      # /v1/projects/{id}/characters/{name}/turnaround
                       # /v1/projects/{id}/characters/{name}/photo
    shots.py           # /v1/projects/{id}/shots:batch  /v1/projects/{id}/shots/{sid}:render
    images.py          # /v1/images:generate (单图)
    director.py        # /v1/projects/{id}/director:script
    publish.py         # /v1/projects/{id}/zhihu:publish
    runs.py            # /v1/runs/{run_id}/events  (SSE，与 story 同协议)
  deps.py
  core/
    ai/
      models.py        # 复用 ModelRegistry（仅 image_* / director_script_generate task）
      prompts.py       # 分镜 / 翻译 / 角色描述提示词
      structured.py    # 同 story-service
      story_client.py  # httpx → story-service（拉 StoryBible / chapter）
      rag_client.py    # httpx → rag-service（取人物 visual_anchor / 场景参考）
    workflows/
      state.py
      image_prompt_graph.py
      director_graph.py
    services/
      image_pipeline.py        # 编排"翻译 + 增强 + 调 image API + 落盘"
      character_pipeline.py    # 角色三视图 / 角色照片
      shot_pipeline.py         # 分镜批量
      publisher_service.py     # 知乎 Playwright 包装
      run_registry.py
      event_bus.py
    clients/
      hunyuan.py       # 迁自 src/clients/hunyuan_image_client.py
      custom_image.py  # 迁自 src/clients/image_client.py
  runtime.py
```

### 6.3 image_prompt_graph

```
START
  → load_chapter_or_section        (httpx → story-service GET chapter)
  → retrieve_visual_context        (rag /search reference + project_memory)
  → load_character_anchors         (httpx → story-service GET characters)
  → extract_shots                  (image_shot_extract task)
  → generate_shot_prompts          (image_prompt_from_shots task, structured ShotPrompt)
  → translate_prompts*             (image_prompt_translate task, 仅当 model_hint 要求英文)
  → review_prompt_safety           (规则校验 + LLM 审稿可选)
  → save_shot_prompts              (写 projects/<id>/shots/shots.json)
  → END
```

### 6.4 character_pipeline

不是 LangGraph，而是直接的协程编排（节点少、结构线性）：

```python
async def generate_character_turnaround(project_id, character_name, ...):
    bible = await story_client.get_storybible(project_id)
    char  = bible.find_character(character_name)
    if not char.image_prompt_base:
        char.image_prompt_base = await build_base_prompt(char)
    prompts = build_turnaround_prompts(char.image_prompt_base, views=["front", "side", "back"])
    images  = await asyncio.gather(*[image_client.generate(p) for p in prompts])
    saved   = await save_to_project(project_id, character_name, images)
    return saved
```

`character_pipeline` 直接复用 `@/Volumes/F/code/play/Zhihu_short_stories/src/gui/mixins/image_modules/char_turnaround_mixin.py:1` 与 `char_photo_generation_mixin.py` 中的纯函数部分，UI 部分留在 GUI。

### 6.5 director Pipeline

```python
async def generate_director_script(project_id, ...):
    bible    = await story_client.get_storybible(project_id)
    chapters = await story_client.list_chapters(project_id)
    shots    = await load_shots(project_id)  # 可选
    llm      = registry.chat_model("director_script_generate")
    script   = await invoke_structured(llm, build_prompt(bible, chapters, shots), DirectorScript)
    save_director_package(project_id, script)
    return script
```

`DirectorScript` 是新增 Pydantic 模型，包含：场次、画面描述、对白、镜头建议、配乐 hint。

### 6.6 publisher_service

包装现有 `src/gui/services/zhihu_publisher.publish_to_zhihu_sync`（详见 `@/Volumes/F/code/play/Zhihu_short_stories/src/gui/mixins/story_modules/zhihu_publisher_mixin.py:498-541`），改为 async 接口：

```python
async def publish_to_zhihu(
    project_id: str,
    *,
    title: str | None = None,        # 缺省时调 LLM 生成
    headless: bool = False,
    neutralize_mentions: bool = True,
    progress: Callable[[str], None] | None = None,
) -> PublishResult: ...
```

发布过程通过 SSE 推 `node_started("playwright_init")` → `node_finished("login_check")` → `node_finished("post_submitted")` → `succeeded`。

`progress_callback` 在 service 端被转换为 SSE 事件，GUI 侧通过 `/v1/runs/{id}/events` 订阅。

### 6.7 Image API 兼容

- 默认使用现有 `@/Volumes/F/code/play/Zhihu_short_stories/src/clients/hunyuan_image_client.py`。
- 自定义 image API 由 `@/Volumes/F/code/play/Zhihu_short_stories/custom_image_api_presets.json:1` 驱动，由 `core/clients/custom_image.py` 加载。
- 鉴权 / API key 走 §5.3 同一套 `KeyVault`。

### 6.8 Exit Criteria

- 已有项目能用 image-service 重新生成分镜 prompt 并保持 prompt 兼容。
- 角色三视图能通过 HTTP 触发并正常落到 `projects/<id>/characters/<name>/`。
- 知乎发布：headless=False 模式人工点击后能成功，错误 SSE 事件清晰。
- 端到端：story-service 完成 novel → 调 image-service 自动生成分镜 → image-service 调 story-service 拉文本 → 全链路 run_id 可追踪。

---

## 7. HTTP API Contracts

### 7.1 通用约定

- **Base URL**：每服务自己的 `http://127.0.0.1:<port>`，由 `.runtime/ports.json` 提供。
- **Auth**：所有请求必须带 `Authorization: Bearer <WSF_BACKEND_TOKEN>`。token 由 supervisor 启动时随机生成，写入子进程 env 与 `.runtime/ports.json`。
- **Run ID**：`X-Run-Id: <uuid>` 跨服务透传。Mutation 立即返回 `{ "run_id": ... }`，进度走对应 service 的 `/v1/runs/{run_id}/events` SSE。
- **错误**：所有错误返回统一格式 `{ "error": { "code": "...", "message": "...", "detail": {...} } }`，HTTP status 见 §3.5。
- **版本**：路径前缀 `/v1`，破坏性变更 bump 到 `/v2`。

### 7.2 story-service

```
GET    /v1/health
GET    /v1/models                              -> { "providers": [...], "tasks": [...] }
GET    /v1/routing                             -> 当前 model_routing.json 内容（脱敏）
PUT    /v1/routing                             -> 更新（GUI 设置页用）

POST   /v1/projects                            -> 创建项目，返回 { project_id, paths }
GET    /v1/projects                            -> 列表
GET    /v1/projects/{id}                       -> 元数据
GET    /v1/projects/{id}/storybible            -> StoryBible
GET    /v1/projects/{id}/chapters              -> ChapterDraft 列表
GET    /v1/projects/{id}/chapters/{idx}        -> 单个 ChapterDraft
GET    /v1/projects/{id}/story                 -> story.txt 内容

POST   /v1/projects/{id}/novel:run             -> { "run_id": ... }
POST   /v1/projects/{id}/characters:design     -> { "run_id": ... }

GET    /v1/runs/{run_id}                       -> { status, current_node, started_at, ... }
GET    /v1/runs/{run_id}/events                -> SSE 流
POST   /v1/runs/{run_id}/cancel                -> 200 / 409
POST   /v1/runs/{run_id}/resume                -> body: { decision, patch }
POST   /v1/runs/{run_id}/review                -> 人审决定（reviews.py）
```

### 7.3 rag-service

```
GET    /v1/health

POST   /v1/kb/{kb_type}/documents              -> ingest
       body: { "files": [path,...] } 或 { "documents": [{"text","path","tags"}] }
       returns: { "ingested": [{source_id, chunk_count}, ...] }

DELETE /v1/kb/{kb_type}/documents/{source_id}

POST   /v1/kb/{kb_type}/search
       body: {
         "query": str,
         "project_id": str | null,           # project_memory 必填
         "top_k": int, "min_score": float,
         "tags": [str,...],
         "budget": ContextBudget | null
       }
       returns: { "contexts": [RetrievedContext, ...] }

POST   /v1/projects/{id}/memory                -> 写 project_memory chunk
GET    /v1/projects/{id}/memory                -> 列出已写 chunk
DELETE /v1/projects/{id}/memory                -> 清空（重新生成场景）

POST   /v1/admin/reindex                       -> 旧 index/ 数据迁移
GET    /v1/admin/manifest                      -> 当前分片状况
```

### 7.4 image-service

```
GET    /v1/health

POST   /v1/projects/{id}/image-prompts:generate           -> { "run_id" }
       body: { "section_index": int | null, "options": {...} }

POST   /v1/projects/{id}/shots:batch                      -> { "run_id" }
POST   /v1/projects/{id}/shots/{shot_id}:render           -> { "run_id" }
GET    /v1/projects/{id}/shots                            -> ShotPrompt[]

POST   /v1/projects/{id}/characters/{name}/turnaround     -> { "run_id" }
POST   /v1/projects/{id}/characters/{name}/photo          -> { "run_id" }

POST   /v1/images:generate                                -> 单图同步生成 { "image_path" }
       body: { "prompt", "negative_prompt", "aspect_ratio", "model_hint" }

POST   /v1/projects/{id}/director:script                  -> { "run_id" }
GET    /v1/projects/{id}/director/script                  -> DirectorScript

POST   /v1/projects/{id}/zhihu:publish                    -> { "run_id" }
       body: { "title": str | null, "headless": bool, "neutralize_mentions": bool }
GET    /v1/projects/{id}/zhihu/last-result                -> 最近一次发布结果

GET    /v1/runs/{run_id}/events
POST   /v1/runs/{run_id}/cancel
```

### 7.5 SSE Event Format

每条事件遵循 `text/event-stream` 标准：

```
event: creative
data: {"type":"node_started","run_id":"...","node":"build_story_bible","ts":"...","message":"","payload":{}}

event: creative
data: {"type":"token","run_id":"...","node":"generate_chapter","payload":{"chunk":"...","section":3}}

event: creative
data: {"type":"succeeded","run_id":"...","payload":{"final_text_chars":18234}}
```

GUI 用 `httpx.AsyncClient.stream` + `sse-starlette` 协议解析，若连接断开自动 `Last-Event-ID` 续传（首版可不实现续传，断开后弹出"连接丢失，可重连"）。

### 7.6 Cross-service Internal Endpoints

服务间互调（不暴露给 GUI）：

```
# 任意 service:
POST   /internal/runs/{run_id}/cancel        # 上游 service 取消时通知下游

# rag-service:
POST   /internal/embed                        # 仅给同进程其他 module，不走外网
```

`/internal/*` 仅接受来自 `127.0.0.1` 且带 `X-Service-Token`（与 `WSF_BACKEND_TOKEN` 不同的 process-local secret）的请求。

### 7.7 OpenAPI

每个 service 开启 FastAPI 自动 OpenAPI（`/openapi.json` + `/docs`），仅在 `WSF_DEBUG=1` 时暴露 `/docs`，避免误用。

---

## 8. Cross-service Concerns

### 8.1 Auth & Token

- **`WSF_BACKEND_TOKEN`**：supervisor 启动时调用 `secrets.token_urlsafe(32)`，写入 3 个 service 子进程的 env，同时存到 `.runtime/ports.json`。
- **`X-Service-Token`**：另一份 token，仅服务间互调使用，不下发给 GUI。
- **中间件**：`src/shared/http/auth.py` 提供 `bearer_required(token_source)` 依赖注入，所有 `/v1/*` 必须装；`/v1/health` 例外不需要 token。
- **失败行为**：缺 token / token 不匹配 → `401 AuthError`，记 access log（不打印 token 值）。

### 8.2 X-Run-Id 透传

- 所有 mutation 请求由发起方生成 `run_id = uuid4().hex`。
- `httpx.AsyncClient` 默认拦截器：`request.headers["X-Run-Id"] = current_run_id_var.get()`，使用 `contextvars` 让 LangGraph 节点内的下游调用自动携带。
- 服务收到请求时把 `X-Run-Id` 写入 `runs/<run_id>.jsonl` 与日志 `extra={"run_id": ...}`。
- 跨服务调用必须使用同一 `run_id`，便于 observability 聚合。

### 8.3 Cancellation Propagation

```
GUI cancel
  → POST /v1/runs/{rid}/cancel  to story-service
       1. story-service.run_registry.cancel(rid)
       2. story-service 异步广播：
            POST /internal/runs/{rid}/cancel  → rag-service
            POST /internal/runs/{rid}/cancel  → image-service
       3. story-service 内 LangGraph 节点检测 cancelled，抛 WorkflowCancelled
       4. 进行中的 httpx 调用通过 cancel 信号 client.aclose()（asyncio.Task.cancel）
       5. SSE 推 cancelled 事件
       6. checkpoint 保留，便于复盘；30 天后清理
```

每个 service 都实现 `RunRegistry`：

```python
class RunRegistry:
    def __init__(self):
        self._events: dict[str, asyncio.Event] = {}
        self._clients: dict[str, list[httpx.AsyncClient]] = {}

    def register(self, run_id: str) -> asyncio.Event:
        ev = asyncio.Event()
        self._events[run_id] = ev
        return ev

    def attach_client(self, run_id: str, client: httpx.AsyncClient):
        self._clients.setdefault(run_id, []).append(client)

    async def cancel(self, run_id: str) -> bool:
        ev = self._events.get(run_id)
        if not ev: return False
        ev.set()
        for c in self._clients.get(run_id, []):
            try: await c.aclose()
            except Exception: pass
        return True
```

### 8.4 Human-in-the-loop (interrupt + resume)

LangGraph 配置：

```python
graph = StateGraph(NovelWorkflowState)
# ... add nodes ...
graph.add_conditional_edges(...)
checkpointer = SqliteSaver.from_conn_string(f"projects/{pid}/checkpoints.sqlite")
app = graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["human_review_outline", "repair_chapter"],
)
```

运行：

```python
config = {"configurable": {"thread_id": run_id}}
async for chunk in app.astream(initial_state, config=config):
    bus.publish(run_id, to_event(chunk))
# 执行到 interrupt_before 节点会自然停止
# state 已被 checkpointer 落盘
```

恢复：

```python
# /v1/runs/{rid}/resume
patch = {"approved": True, "edits": {...}}
async for chunk in app.astream(Command(resume=patch), config=config):
    ...
```

GUI 收到 `human_input_required` 事件后弹审稿对话框，POST `/resume`。

### 8.5 SSE Event Bus

每个 service 内部维护一个 `EventBus`：

```python
class EventBus:
    def __init__(self):
        self._queues: dict[str, asyncio.Queue[CreativeEvent]] = {}
        self._buffers: dict[str, list[CreativeEvent]] = {}  # 重连用

    def publish(self, run_id: str, ev: CreativeEvent):
        self._buffers.setdefault(run_id, []).append(ev)
        q = self._queues.get(run_id)
        if q: q.put_nowait(ev)

    async def subscribe(self, run_id: str, last_event_id: str | None) -> AsyncIterator[CreativeEvent]:
        # 先吐 buffer 中 last_event_id 之后的事件
        # 然后阻塞读 queue
        ...
```

- **缓冲容量**：每 run 最多保留最后 500 条事件，超过淘汰最早的。
- **生命周期**：终止事件（`succeeded`/`failed`/`cancelled`）后保留 5 分钟，过期回收。

### 8.6 Token & Cost Telemetry

- LangChain `callbacks` 注入 `TokenUsageCallback`，每次 LLM 调用记录 `prompt_tokens / completion_tokens / model / task / run_id` 到 `runs/<run_id>.jsonl`。
- `ModelRegistry.estimate_cost(...)` 读取 `config/cost_table.json`（新增，可选），计算成本估算。
- 单 run 累计成本通过 SSE `warning` 事件推送（超阈值时），阈值由 `config/runtime.json.cost_warning_cny` 配置。

### 8.7 Rate Limit & Retry

- `ModelRegistry` 包装 chat model 时统一加 `tenacity` retry：429/5xx 指数退避，最多 3 次，总超时 60s。
- 每 provider 设并发上限（默认 4），用 `asyncio.Semaphore` 节流，避免 burst 导致 provider 拒绝。
- 超限错误向上抛 `ModelProviderError`，工作流节点决定是否进 `errors` state 并继续 / 失败。

### 8.8 Logging

- 所有 service 用 `logging.getLogger("wsf")` 命名空间，formatter 统一 `[{ts}] [{service}] [{run_id}] {level} {message}`。
- 日志输出三路：stderr（supervisor 聚合）、`logs/<service>.log`（rotating）、`projects/<pid>/runs/<run_id>.jsonl`（结构化事件）。
- 不打印 API key、token、用户文档原文（只打字数）。

---

## 9. Service Supervisor & Lifecycle

### 9.1 Goal

- 把 3 个 service 的启动 / 健康检查 / 取消 / 关闭 收拢到一个由 GUI 进程持有的 `ServiceSupervisor` 中。
- 兼容 `@/Volumes/F/code/play/Zhihu_short_stories/run_modern_app.py:87-108` 现有的 macOS Python 3.11 re-exec 行为。

### 9.2 Layout

```text
src/gui/backend/
  __init__.py
  supervisor.py       # ServiceSupervisor
  ports.py            # .runtime/ports.json 读写
  story_client.py     # httpx 包装 + SSE 解析
  rag_client.py
  image_client.py
  errors.py           # 把 HTTP error JSON 转回 CreativeError 子类
  events.py           # SSE → CreativeEvent
  threading_bridge.py # asyncio ↔ Tk 主线程 marshal
```

### 9.3 Supervisor 行为

```python
class ServiceSupervisor:
    services = ("story", "rag", "image")

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.processes: dict[str, subprocess.Popen] = {}
        self.token = secrets.token_urlsafe(32)
        self.ports: dict[str, int] = {}

    def start_all(self) -> dict[str, str]:
        """阻塞启动 3 个 service，返回 base_url 映射。"""
        for name in self.services:
            self._start_one(name)
        self._wait_healthy(timeout=30)
        self._write_runtime_file()
        return {name: f"http://127.0.0.1:{p}" for name, p in self.ports.items()}

    def _start_one(self, name: str): ...
    def _wait_healthy(self, timeout: int): ...
    def _write_runtime_file(self): ...

    def shutdown(self, timeout: int = 10):
        """反序 SIGTERM，超时 SIGKILL。"""

    def restart(self, name: str): ...
```

### 9.4 启动顺序

```
1. supervisor.start_all()
   1.1 spawn rag-service     (随机端口)
   1.2 wait /v1/health (rag)  ≤ 15s
   1.3 spawn story-service   (env: RAG_BASE_URL=...)
   1.4 wait /v1/health (story) ≤ 15s
   1.5 spawn image-service   (env: STORY_BASE_URL=..., RAG_BASE_URL=...)
   1.6 wait /v1/health (image) ≤ 15s
2. 写入 .runtime/ports.json:
   { "token": "...", "story": 53210, "rag": 53211, "image": 53212, "pid_story": 1234, ... }
3. ModernApp 启动，从 .runtime/ports.json 读取，构造 BackendClient
```

### 9.5 关闭顺序

```
1. ModernApp 收到 WM_DELETE_WINDOW
2. supervisor.shutdown() 异步执行：
   2.1 SIGTERM image-service
   2.2 等 image flush（5s）→ SIGKILL if 仍存活
   2.3 SIGTERM story-service
   2.4 等 story flush（5s）→ SIGKILL if 仍存活
   2.5 SIGTERM rag-service
   2.6 等 rag flush（5s）→ SIGKILL if 仍存活
3. 删除 .runtime/ports.json
4. ModernApp.destroy()
```

### 9.6 异常恢复

- 子进程未触发 health 检查 → supervisor 抓 stderr，把最后 50 行写到 `logs/startup-failure.log`，弹错误窗。
- 运行中 crash：supervisor 检测到 `Popen.poll() != None` → 自动重启 1 次；连续 2 次失败标记 service 为 degraded，相关 GUI 功能 disable。
- macOS 3.11 re-exec：保留现有 `_maybe_reexec_safe_python_on_macos` 行为，supervisor 用 `sys.executable` 启动子进程，自动继承 3.11 runtime。

### 9.7 开发模式

`WSF_DEV=1` 时：

- 不 spawn 子进程，期望开发者自己启动 3 个 service。
- supervisor 只读 `.runtime/ports.json`（开发者用 `make dev` 启动，写入 `.runtime/ports.json`）。
- 提供脚本 `scripts/dev/start_services.sh`：用 `tmux` 起 3 个 panel 跑 `uvicorn`。

---

## 10. GUI Integration

### 10.1 BackendClient 抽象

GUI 唯一与后端的接口：

```python
class BackendClient:
    def __init__(self, ports_file: Path):
        cfg = json.loads(ports_file.read_text())
        self.token = cfg["token"]
        self.story = StoryClient(cfg["story"], self.token)
        self.rag   = RagClient(cfg["rag"],   self.token)
        self.image = ImageClient(cfg["image"], self.token)
```

### 10.2 各 Client API（GUI 视角）

```python
# 一律返回 RunHandle，封装 run_id + 事件流 + cancel
class RunHandle:
    run_id: str
    async def events(self) -> AsyncIterator[CreativeEvent]: ...
    async def cancel(self) -> None: ...
    async def wait(self) -> dict: ...    # 阻塞至 succeeded/failed


class StoryClient:
    async def generate_novel(self, project_id, request) -> RunHandle: ...
    async def design_characters(self, project_id, request) -> RunHandle: ...
    async def get_storybible(self, project_id) -> StoryBible | None: ...
    async def list_chapters(self, project_id) -> list[ChapterDraft]: ...
    async def review(self, run_id, decision) -> None: ...
    async def resume(self, run_id, patch) -> None: ...

class RagClient:
    async def ingest(self, kb_type, files_or_docs) -> IngestResult: ...
    async def search(self, kb_type, query, **kwargs) -> list[RetrievedContext]: ...

class ImageClient:
    async def generate_shot_prompts(self, project_id, request) -> RunHandle: ...
    async def generate_turnaround(self, project_id, name) -> RunHandle: ...
    async def publish_zhihu(self, project_id, **kwargs) -> RunHandle: ...
```

### 10.3 GUI Mixin 改造

| 旧文件 | 改造方式 |
|---|---|
| `@/Volumes/F/code/play/Zhihu_short_stories/src/gui/mixins/story_modules/story_generator.py:1` | 业务部分剥离到 story-service；mixin 只负责采集表单 → 调 `client.story.generate_novel` → 在 `events()` 循环里更新 UI |
| `@/Volumes/F/code/play/Zhihu_short_stories/src/gui/mixins/story_modules/outline_section_generate_mixin.py:1` | 大部分 prompt 构造逻辑迁到 story-service prompts.py；mixin 简化为调用 + 渲染 |
| `@/Volumes/F/code/play/Zhihu_short_stories/src/gui/mixins/story_modules/outline_overview_mixin.py:1` | 同上 |
| `@/Volumes/F/code/play/Zhihu_short_stories/src/gui/mixins/kb_mixin.py:1` | 全部走 `client.rag.*` |
| `@/Volumes/F/code/play/Zhihu_short_stories/src/gui/mixins/kb_enhancements.py:1` | 同上 |
| `@/Volumes/F/code/play/Zhihu_short_stories/src/gui/mixins/image_modules/shot_prompt_mixin.py:1` | 走 `client.image.generate_shot_prompts` |
| `@/Volumes/F/code/play/Zhihu_short_stories/src/gui/mixins/image_modules/char_turnaround_mixin.py:1` | 走 `client.image.generate_turnaround` |
| `@/Volumes/F/code/play/Zhihu_short_stories/src/gui/mixins/image_modules/char_photo_generation_mixin.py:1` | 走 image-service 角色照片端点 |
| `@/Volumes/F/code/play/Zhihu_short_stories/src/gui/mixins/director_mixin.py:1` | 走 `client.image.director_script` |
| `@/Volumes/F/code/play/Zhihu_short_stories/src/gui/mixins/story_modules/zhihu_publisher_mixin.py:1` | 走 `client.image.publish_zhihu` |

### 10.4 Threading Bridge

`threading_bridge.py` 解决 Tk 主线程 + asyncio 协程的桥接：

```python
def run_in_background(coro_factory) -> threading.Thread:
    def runner():
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(coro_factory())
        finally:
            loop.close()
    t = threading.Thread(target=runner, daemon=True)
    t.start()
    return t


def marshal_to_tk(widget, fn):
    """从 worker thread 安全调用 Tk update：widget.after(0, fn)。"""
    widget.after(0, fn)
```

订阅 SSE 的标准模式：

```python
async def consume(handle: RunHandle):
    async for ev in handle.events():
        marshal_to_tk(self, lambda: self._render_event(ev))
```

### 10.5 旧 `async_utils.TaskQueue` 的去留

- **保留**：批量生成 dialog 等 GUI 局部并发工具继续用现有 `TaskQueue`。
- **不再用 TaskQueue 跑业务**：所有"生成小说 / 角色 / 图片"的长任务一律走 BackendClient + RunHandle，不再塞进 TaskQueue。
- v2 上线后，`TaskQueue.cancel_all()` 仅取消"等待启动"的批次；运行中的服务调用通过 `RunHandle.cancel()` 取消。

### 10.6 Env Flag 双轨期

```
STORY_USE_LEGACY_PATH=1   # 仍走旧 mixin 直连 client（默认 0，新流程为默认）
WSF_DEV=1                  # supervisor 不 spawn，期望开发者手动起 service
WSF_DEBUG=1                # 暴露 /docs，开启 verbose log
WSF_BACKEND_TOKEN          # 由 supervisor 写入；手动启动 service 时需设置
WSF_NO_AUTH=1              # 仅本地开发，关闭 auth 中间件（生产禁用）
```

### 10.7 Exit Criteria

- ModernApp 启动后 3 个 service 自动起，关窗后全部回收。
- 旧 mixin 全部改为 BackendClient 调用，且无任何 `import langchain` / `import faiss`。
- `pytest tests/gui/test_backend_client_*.py` 全绿（mock backend）。

---

## 11. Persistence & Migration

### 11.1 现有 `Project` schema 兼容矩阵

参考 `@/Volumes/F/code/play/Zhihu_short_stories/src/project_manager.py:39-47` 现有字段：

| 旧字段（`project.json`） | v2 归属 | 处理方式 |
|---|---|---|
| `name` | `project.json`（保留） | 不变 |
| `created_at` | `project.json`（保留） | 不变 |
| `updated_at` | `project.json`（保留） | 每次 mutation 更新 |
| `category` | `storybible.json.genre` | 启动时迁移到 StoryBible |
| `requirement` | `storybible.json.requirement` | 同上 |
| `style` | `storybible.json.style` | 同上 |
| `target_chars` | `storybible.json` 顶层新增 `target_chars` 字段 | 同上 |
| `story.txt` | 不变 | story-service 写"最终拼接版" |
| `images/` | 不变 | image-service 写 |
| `characters/` | 不变 | image-service 写角色照片；StoryBible 持有结构化 profile |

> **决策**：`project.json` 不做破坏性改动，旧 GUI 即使不升级也能读。`StoryBible.requirement / genre / style` 与 `project.json` 中同名字段 **以 StoryBible 为准**，每次 storybible 写入后同步刷一遍 project.json（向下兼容）。

### 11.2 章节落盘格式

`projects/<id>/chapters/<NNN>.json`：

```json
{
  "section_index": 1,
  "title": "...",
  "content": "...",
  "summary": "...",
  "continuity_updates": ["..."],
  "citations": [{"source_id":"...","path":"...","chunk_id":"...","score":0.78,"kb_type":"reference"}],
  "review_notes": ["..."],
  "char_count": 1842,
  "token_usage": {"prompt": 1230, "completion": 1842, "total": 3072}
}
```

### 11.3 `story.txt` 的拼装规则

`assemble_final_story` 节点：

1. 按 `section_index` 升序读 `chapters/*.json`。
2. 拼装为：

```
<title 或 chapter index>

<content>


<title 或 chapter index>

<content>
```

3. atomic 写入 `story.txt.tmp` → `os.replace` → `story.txt`。
4. 同时更新 `project.json.updated_at`。

### 11.4 `index/` 旧数据迁移

`POST /v1/admin/reindex` 行为：

1. 读旧 `index/kb.faiss` + 旧 `metadata.sqlite3`。
2. 重新生成 `chunk_id`（按 §4.4 规则）。
3. 按 `kb_type` / `project_id` 写入新分片。
4. 写新 `manifest.json`，旧 `kb.faiss` 重命名 `kb.faiss.bak`，保留 7 天。
5. 期间所有 `/search` 请求返回 `503 service_unavailable, reindexing`。

### 11.5 LangGraph Checkpoint 清理

- supervisor 启动时遍历 `projects/*/checkpoints.sqlite`，清理超过 30 天的 thread。
- 单个 checkpoints.sqlite > 50MB 时按 LRU 删除最旧 thread 至 ≤ 30MB。

### 11.6 Migration 时序

```
1. v2 部署后第一次启动
2. supervisor 启动 rag-service → 触发自动 reindex（如检测到旧 index/ 但无 manifest.json）
3. supervisor 启动 story-service → 遍历 projects/*：
   3.1 缺 storybible.json：从 project.json 反推 minimal StoryBible，写入
   3.2 缺 chapters/：尝试将 story.txt 按章节标题切分为 ChapterDraft 列表（best-effort，失败则跳过）
4. 用户手动重新生成可获得完整结构化数据
```

### 11.7 Exit Criteria

- 用 6 个真实 project 跑迁移：全部通过 `pytest tests/migration/test_legacy_projects.py`。
- 迁移后 GUI 老页面读出的 `requirement` / `style` 与原值一致。
- `index/` 旧数据 reindex 后 `/search` 返回 chunk 数量与原始 chunk 数差距 < 5%。

---

## 12. Configuration Bridging

### 12.1 现有配置文件清单

| 文件 | 当前用途 | v2 归属 |
|---|---|---|
| `@/Volumes/F/code/play/Zhihu_short_stories/model_routing.json:1` | 11 类 task 路由到 provider+model | `src/shared/config/routing.py` 加载，story-service / image-service 读 |
| `@/Volumes/F/code/play/Zhihu_short_stories/custom_api_presets.json:1` | 自定义 OpenAI 兼容端点列表 | `src/shared/config/presets.py` |
| `@/Volumes/F/code/play/Zhihu_short_stories/custom_image_api_presets.json:1` | 自定义图像 API | image-service core/clients/custom_image.py |
| `@/Volumes/F/code/play/Zhihu_short_stories/custom_model_routing.json:1` | 自定义 model 别名 | merge 进 routing.py 解析 |
| `@/Volumes/F/code/play/Zhihu_short_stories/available_models.json:1` | provider 可用 model 缓存 | story-service `/v1/models` 暴露 |
| `@/Volumes/F/code/play/Zhihu_short_stories/config/.keyfile` | 加密 API key | `src/shared/config/keyfile.py` 加载 |
| `@/Volumes/F/code/play/Zhihu_short_stories/config/story_pipeline_profile.json:1` | quality_review / memory_ledger / polish schema 与规则 | story-service prompts.py 加载 |
| `@/Volumes/F/code/play/Zhihu_short_stories/config/story_prompt_profile.json:1` | 用户自定义 prompt 模板 | story-service prompts.py 加载 |
| `@/Volumes/F/code/play/Zhihu_short_stories/config/story_guardrails.json:1` | 内容守卫规则 | story-service prompts.py 作为 system prompt 前缀 |
| `@/Volumes/F/code/play/Zhihu_short_stories/config/theme_config.json:1` | UI 主题 | 不变，仅 GUI 用 |
| `@/Volumes/F/code/play/Zhihu_short_stories/.env`、`.env.example` | 通用环境变量 | 启动时 `python-dotenv` 加载 |

### 12.2 配置加载顺序

每个 service 启动时：

```
1. 加载 .env (dotenv)
2. 读 config/.keyfile -> 解密 → KeyVault（仅内存）
3. 读 model_routing.json + custom_model_routing.json -> 合并 -> RoutingConfig
4. 读 custom_api_presets.json + custom_image_api_presets.json -> PresetsConfig
5. story-service 额外：读 config/story_*_profile.json + story_guardrails.json -> PromptLibrary
6. 通过 Pydantic Settings 校验：
   class ServiceSettings(BaseSettings):
       backend_token: str = Field(..., env="WSF_BACKEND_TOKEN")
       service_token: str = Field(..., env="WSF_SERVICE_TOKEN")
       rag_base_url:  str = Field("", env="RAG_BASE_URL")
       story_base_url:str = Field("", env="STORY_BASE_URL")
       debug: bool = Field(False, env="WSF_DEBUG")
       no_auth: bool = Field(False, env="WSF_NO_AUTH")
```

### 12.3 设置变更协议

- GUI 修改 routing 时 `PUT /v1/routing` → story-service 验证后写 `model_routing.json`，并通过 `/internal/reload-config` 通知 image-service 热更新。
- 修改 prompt 模板时同样走 story-service `/v1/prompts/profile`，避免 GUI 直接写文件。
- 修改 API key 时走 story-service `/v1/keys/<alias>`，重新加密写 `.keyfile`，更新内存 KeyVault。

### 12.4 现有 v1 文档与 model_routing.json 的差异修正

v1 §5.3 列出 9 类 prompt：`requirement parser / story bible builder / character designer / outline generator / chapter writer / chapter reviewer / continuity updater / image prompt writer / style rewriter`。

实际 `model_routing.json` 有 11 个 task。映射如下（在 v2 中以 routing 为单一来源）：

| v1 prompt 类 | v2 TaskName 对应 | 备注 |
|---|---|---|
| requirement parser | `story_outline` 或新增 `requirement_parse` | 需新增 routing 项 |
| story bible builder | `story_outline` | 复用 |
| character designer | `character_extract` + `character_description` | 拆两步 |
| outline generator | `story_outline` | 复用 |
| chapter writer | `story_generate` | 复用 |
| chapter reviewer | `story_generate` 同 model | 不单独 routing，复用 quality_review 配置 |
| continuity updater | `story_generate` 同 model | 同上 |
| image prompt writer | `image_prompt_from_story` / `image_prompt_from_shots` / `image_prompt_enhance` | 走 image-service |
| style rewriter | `story_generate` 同 model | 用 polish prompt |

> 落地时若发现 model_routing.json 缺 `requirement_parse`，由 Phase 1 任务在 routing 文件中补一项默认值（与 `story_outline` 同 provider+model）。

---

## 13. Implementation Phases

> 实施顺序较 v1 整体重排：先做 shared 与 rag-service（最少跨服务依赖），再做 story-service，再做 GUI 整合，最后接 image-service。

### Phase 0 — Stabilize Baseline

#### Task 0.1 修复当前 KB cache 测试

- 跑 `pytest -q` 拿到完整失败堆栈。
- 确认 `tests/test_kb_*` 中失败的根因（极可能是 `get_sentence_transformer` 导出位置问题）。
- 修：`@/Volumes/F/code/play/Zhihu_short_stories/src/kb/ingest.py:1`、`@/Volumes/F/code/play/Zhihu_short_stories/src/kb/search.py:1`、`@/Volumes/F/code/play/Zhihu_short_stories/src/kb/model_cache.py:1`。

#### Task 0.2 补 requirements

- `requirements.txt` 增加：`fastapi>=0.110`、`uvicorn[standard]>=0.27`、`httpx>=0.27`、`sse-starlette>=2.0`、`langgraph>=0.2`、`tenacity>=8.2`、`anyio>=4.3`、`pydantic-settings>=2.2`、`tiktoken>=0.6`（可选）。

**Acceptance**：`pytest -q` 全绿；新依赖可安装。

### Phase 1 — Shared Domain & Config

#### Task 1.1 创建 `src/shared/`

- 创建 `domain/{schemas,events,errors,runs,project_paths}.py`。
- 创建 `config/{paths,routing,presets,keyfile,settings}.py`。
- 创建 `http/{auth,sse,run_headers}.py`。
- `keyfile.py` 把 `@/Volumes/F/code/play/Zhihu_short_stories/src/gui/mixins/enhancements_modules/secure_config.py:1` 的解密函数迁过来（保留旧位置作为兼容入口）。

#### Task 1.2 写测试

- `tests/shared/test_schemas.py`：模型 round-trip。
- `tests/shared/test_routing.py`：合并 `model_routing.json` + `custom_model_routing.json`。
- `tests/shared/test_keyfile.py`：解密一份测试 keyfile。

**Acceptance**：`pytest tests/shared/` 全绿；GUI/旧 mixin 仍能 import 旧 secure_config。

### Phase 2 — rag-service MVP

#### Task 2.1 FastAPI 骨架 + health

- 创建 `src/services/rag_service/{main,runtime}.py` + `api/health.py`。
- `uvicorn src.services.rag_service.main:app --port 0` 能起。

#### Task 2.2 EmbeddingHub + IndexHub

- 复用 `src/kb/model_cache.get_sentence_transformer`。
- 实现 §4.3 多分片布局；提供 `manifest.json` 读写。

#### Task 2.3 ingest / search / memory

- 实现 `api/kb.py` + `api/search.py` + `api/memory.py`。
- chunk_id stability 按 §4.4 实现。
- 单元测试 + httpx in-process 集成测试。

#### Task 2.4 reindex 工具

- `api/reindex.py` + `tests/services/rag_service/test_reindex_legacy.py`：用一份 fixture 旧 `index/` 跑迁移。

**Acceptance**：rag-service 能独立跑通 ingest + search + project_memory + reindex。

### Phase 3 — story-service MVP

#### Task 3.1 ModelRegistry

- `core/ai/{routing,models}.py`：从 routing.json/presets.json/keyfile 构造 chat model。
- `tests/services/story_service/test_model_registry.py`：mock provider，断言 task 路由正确、key 注入正确。

#### Task 3.2 prompts + structured

- `core/ai/{prompts,structured}.py`，加载 config/story_*_profile.json。
- `tests/services/story_service/test_prompts_load.py` + `test_structured.py`（含 schema-fix 测试）。

#### Task 3.3 novel_graph 骨架

- `core/workflows/{state,novel_graph,checkpoint}.py`。
- 用 fake LLM 跑通：parse → retrieve → bible → outline → chapter_loop（2 章）→ assemble → save。
- `tests/services/story_service/test_novel_graph_fake_llm.py`。

#### Task 3.4 SSE + RunRegistry + EventBus

- `api/runs.py` + `services/{run_registry,event_bus}.py`。
- 端到端测试：发起 run → 订阅 SSE → 收齐事件序列。

#### Task 3.5 Cancel + Resume

- `interrupt_before` 配置；`/cancel` `/resume` 端点。
- `tests/services/story_service/test_human_in_the_loop.py`。

#### Task 3.6 ProjectStore

- `services/project_store.py` + 兼容旧 `project_manager.py`。
- `tests/services/story_service/test_project_store_migration.py`：用 6 个真实 project 跑迁移。

**Acceptance**：story-service 端到端 fake-LLM 测试全绿；可与 rag-service 通过 httpx 跑联调。

### Phase 4 — Supervisor & BackendClient (无业务集成)

#### Task 4.1 ServiceSupervisor

- `src/gui/backend/{supervisor,ports}.py`。
- `tests/gui/test_supervisor_lifecycle.py`：起 + 等 health + 关。

#### Task 4.2 BackendClient

- `src/gui/backend/{story_client,rag_client,image_client,events,errors,threading_bridge}.py`。
- `tests/gui/test_backend_client_with_mock_server.py`：用 httpx ASGI in-process。

#### Task 4.3 改造 `run_modern_app.py`

- 启动时 supervisor.start_all()，关闭时 supervisor.shutdown()。
- env flag 兜底：`WSF_DEV=1` 跳过 spawn。

**Acceptance**：`python run_modern_app.py` 启动正常，`/health` 全绿，关窗清理 ports.json。

### Phase 5 — GUI 接入 story / rag

#### Task 5.1 KB Mixin 切换

- 修 `@/Volumes/F/code/play/Zhihu_short_stories/src/gui/mixins/kb_mixin.py:1` 与 `kb_enhancements.py` 调用 `client.rag.*`。
- env flag `STORY_USE_LEGACY_PATH=1` 仍走旧路径。

#### Task 5.2 Story Mixin 切换

- 修 `story_modules/story_generator.py` 与 `outline_generate_mixin.py` 调用 `client.story.generate_novel`。
- 章节级流式预览：把 SSE `partial_chapter` 事件写进现有预览 widget。
- 取消按钮：`RunHandle.cancel()`。
- 人审对话框：监听 `human_input_required` 事件，弹审稿窗口，提交 `/review` + `/resume`。

#### Task 5.3 现有测试迁移

- 13 个受影响测试（见 §15.3）改为：
  - 涉及 RAG / LangChain 的：mock BackendClient，仅测 GUI 行为。
  - 涉及业务逻辑的：搬到 `tests/services/story_service/`。

**Acceptance**：以新流程为默认，能完整跑一次"故事生成 → 知乎发布"（发布走旧路径暂时保留）。

### Phase 6 — image-service

#### Task 6.1 image_prompt_graph + ShotPrompt 持久化

#### Task 6.2 角色三视图 + 角色照片

#### Task 6.3 director script

#### Task 6.4 知乎 Playwright 包装

#### Task 6.5 GUI image_modules 切换

**Acceptance**：所有图像/角色/导演/发布功能都通过 image-service；旧 mixin 保留 fallback。

### Phase 7 — Polish & Cleanup

- 删除旧 `src/kb` 包（保留 `model_cache.py`）。
- 删除 mixin 中已迁移的业务函数。
- 更新 `README.md` + `docs/技术架构.md`。
- 删除 v1 设计文档或标记为 superseded。

---

## 14. Errors & Observability

### 14.1 错误响应格式

所有 service 走统一异常中间件，把 `CreativeError` 子类转成：

```json
{
  "error": {
    "code": "structured_output",
    "message": "LLM returned invalid JSON for StoryBible",
    "detail": {
      "attempts": 3,
      "last_error_path": "$.characters[0].role",
      "run_id": "abc123"
    }
  }
}
```

未知异常 → `code: "internal_error"`、`http_status: 500`，detail 仅包含 `exception_type`，不暴露 traceback；traceback 写日志。

### 14.2 SSE 错误事件

```
event: creative
data: {"type":"failed","run_id":"...","payload":{
  "code":"model_provider_error",
  "node":"generate_chapter",
  "section_index":3,
  "message":"DeepSeek 429 after 3 retries"
}}
```

GUI 收到 `failed` 事件后停止订阅，主动调 `/v1/runs/{rid}` 拿最终状态以确认是否需要 resume。

### 14.3 部分输出保留

工作流节点失败时按下规则保留中间产物：

- StoryBible 已生成 → 落盘 `storybible.json`，可独立查看。
- 部分 chapter 已生成 → 落盘对应 `chapters/<NNN>.json`，下次 resume 从下一章继续。
- LangGraph checkpointer 保留 state，30 天内可 resume。

### 14.4 Observability 三层

1. **结构化运行日志**：`projects/<id>/runs/<run_id>.jsonl`，每个节点 start/end + token usage + duration + 错误。
2. **服务日志**：`logs/<service>.log`，rotating 50MB × 5。
3. **可选 LangSmith**：`LANGSMITH_API_KEY` 设置后自动上报；不依赖。

### 14.5 Health Endpoint 详情

```
GET /v1/health
{
  "status": "ok",
  "service": "story",
  "version": "2.0.0",
  "uptime_s": 12345,
  "deps": {
    "rag":   { "url": "...", "ok": true,  "latency_ms": 12 },
    "image": { "url": "...", "ok": true,  "latency_ms": 23 }
  },
  "models_loaded": true,
  "in_flight_runs": 2
}
```

GUI 启动后定期轮询（每 30s），degraded 时弹横幅。

---

## 15. Testing Strategy

### 15.1 测试层次

| 层 | 工具 | 范围 | 是否需要起进程 |
|---|---|---|---|
| 单元测试 | pytest | shared/, 各 service core/ 内函数 | 否 |
| Service 集成 | pytest + httpx ASGITransport | 单个 FastAPI app in-process | 否 |
| 跨 service 集成 | pytest + Supervisor (real subprocess) | 3 个 service 真实启动 | 是 |
| GUI smoke | pytest-tk + mock BackendClient | mixin 行为 | 否 |
| 端到端 | Playwright + 完整启动 | 用户路径 | 是 |

### 15.2 共用 Fixture

`tests/conftest.py` 增加：

```python
@pytest.fixture
def fake_chat_model(monkeypatch):
    """统一假 LLM。"""
    ...

@pytest.fixture
def fake_retriever():
    """无依赖的内存 RetrievedContext 列表。"""
    ...

@pytest.fixture
def in_process_rag_app():
    """用 ASGITransport 启 rag-service 应用。"""
    ...

@pytest.fixture
def isolated_project(tmp_path) -> Path:
    """每个测试一个全新 projects/<id>/ 目录。"""
    ...

@pytest.fixture
def supervised_services(tmp_path) -> dict:
    """真实起 3 个子进程，yield base_urls，结束 shutdown。"""
    ...
```

### 15.3 现有测试迁移矩阵

50 个现有测试中受影响 13 个：

| 现有测试 | 决策 | 新位置 |
|---|---|---|
| `tests/test_outline_section_generate_rag_path.py` | **重写为 service 测试** | `tests/services/story_service/test_chapter_rag_path.py` |
| `tests/test_outline_section_regenerate_policy.py` | **重写** | `tests/services/story_service/test_regenerate_policy.py` |
| `tests/test_story_template_headless.py` | **保留** | 改为 mock BackendClient |
| `tests/test_story_pipeline_profile.py` | **重写** | `tests/services/story_service/test_pipeline_profile_load.py` |
| `tests/test_story_prompt_profile.py` | **重写** | `tests/services/story_service/test_prompt_profile_load.py` |
| `tests/test_story_rag_postprocess.py` | **重写** | `tests/services/rag_service/test_postprocess.py` |
| `tests/test_story_writing_guardrails.py` | **重写** | `tests/services/story_service/test_guardrails.py` |
| `tests/test_story_generator_preview_cancel.py` | **保留** | 改为通过 RunHandle.cancel 测 |
| `tests/test_story_generator_retry.py` | **重写** | `tests/services/story_service/test_retry.py` |
| `tests/test_story_creativity.py` | **保留** | 不变（纯函数） |
| `tests/test_story_quality.py` | **重写** | `tests/services/story_service/test_quality_review.py` |
| `tests/test_director_script_builder.py` | **重写** | `tests/services/image_service/test_director_script.py` |
| `tests/test_flow_smoke.py` | **重写为端到端** | `tests/e2e/test_flow_smoke.py` |
| `tests/test_full_flow.py` | **重写为端到端** | `tests/e2e/test_full_flow.py` |

非受影响的 36 个测试保持原位。

### 15.4 关键测试用例

- **多项目召回不污染**：`tests/services/rag_service/test_multi_project_isolation.py`：建 3 个项目 memory，每个项目检索仅返回自己的 chunk。
- **Cancel 跨服务传播**：`tests/e2e/test_cancel_propagation.py`：发起 novel:run → 在 chapter 节点 cancel → 断言 rag-service 上对应 run 也被 cancel。
- **Resume 后产出一致**：`tests/services/story_service/test_resume_idempotent.py`：跑到 outline 中断 → resume → 与不中断结果对比，章节内容一致（除 timestamp）。
- **`projects/` 迁移**：`tests/migration/test_legacy_projects.py`：6 个真实 project fixture（脱敏后）。

### 15.5 Smoke 检查清单

- 启动 ModernApp 后所有 service health 返回 200。
- 用 fake LLM 跑通："建项目 → 生成 → 预览 → 保存"。
- 用 fake LLM 跑通："建项目 → 生成 → outline 审稿 → resume → 完成"。
- KB ingest 一份 .txt → search 出至少 1 条结果。
- 角色三视图：生成 3 张图（mock image API）。
- 知乎发布 headless=True：能进到 Playwright 启动这一步即视为通过（不真发）。

---

## 16. Rollback Plan

### 16.1 双轨期保护

- 直到 Phase 6 完成前，所有迁移功能默认走新路径，但 `STORY_USE_LEGACY_PATH=1` 可一键回到旧 mixin。
- 旧 `src/kb`、旧 mixin 业务函数在 Phase 7 之前不删除。

### 16.2 故障级别

| 级别 | 表现 | 自动行为 | 用户感知 |
|---|---|---|---|
| L1 | 单个 SSE 事件解析失败 | 跳过 + 警告 | 无 |
| L2 | 单次 mutation 失败 | 返回 error，可重试 | 弹错误窗 |
| L3 | 单个 service crash | supervisor 重启 1 次 | 横幅"服务重启中" |
| L4 | service 重启失败 | 标记 degraded，相关功能 disable | 横幅"功能临时不可用，可用 STORY_USE_LEGACY_PATH=1 回退" |
| L5 | supervisor 启动失败 | 弹错误窗，保留旧入口 | "无法启动后端服务，请检查日志" |

### 16.3 数据回滚

- 任何 mutation 都先写 `.tmp` 再 atomic rename，crash 不会留半文件。
- `index/` reindex 会保留 `kb.faiss.bak` 7 天。
- LangGraph checkpoint 保留 30 天，可手动 resume。

### 16.4 紧急退路

如果 v2 上线后 1 周内出现严重问题：

1. 设全局 env `STORY_USE_LEGACY_PATH=1`。
2. supervisor 跳过 service 启动，GUI 直接 fallback 到旧 mixin。
3. v1 路径在 Phase 7 完成前一直可用。

---

## 17. Acceptance Criteria for the Full Framework

### 17.1 功能性

- 启动：`python run_modern_app.py` 一次启动，3 个 service 全部 healthy，关窗后 ports.json 清理。
- 小说生成：从需求到 `story.txt` 全流程跑通；含 outline 人审、章节流式预览、章节失败重写。
- 角色：可生成 `CharacterProfile` 列表 + 三视图 + 角色照片。
- 分镜：可从某章生成 `ShotPrompt[]` 并批量调图像 API 出图。
- 导演脚本：可生成 `DirectorScript` 并保存到 `projects/<id>/director/`。
- 知乎发布：可一键发布（headless=False）。
- KB：可 ingest reference / style_corpus / project_memory；search 不互相污染。

### 17.2 非功能性

- GUI 全树无 `import langchain` / `import faiss` / `import openai`。
- `pytest -q` 全绿，新测试覆盖率 ≥ 70%（service core），≥ 50%（GUI）。
- LLM 调用 100% 走 ModelRegistry，cost telemetry 可见。
- 任意 mutation 可被 cancel，且取消传播跨 service ≤ 2s 生效。
- 任意 service crash 后 supervisor 自动重启 1 次，重启失败不会 crash GUI。
- 6 个旧项目无需手动操作即可在 v2 中读出 requirement / style 与原值一致。

### 17.3 文档

- `README.md` 更新启动方式、env flag、配置文件清单。
- `docs/技术架构.md` 新增 v2 服务拓扑图。
- v1 文档头部加 `> Superseded by v2.md`。

---

## 18. Open Questions / 未来工作

非阻塞，但落地后值得跟进：

- **Web UI**：v2 的 HTTP 后端为未来 React/Web 前端预留了可能；目前不做，但避免在 endpoint 设计中引入 Tk-only 假设。
- **多机部署**：当前严格 `127.0.0.1`，未来若要拆云端，rag-service 与 story-service 都要支持网络存储路径（替换 `projects/` 与 `index/`）。
- **流式章节写盘**：当前 chapter 整体写完落盘，后续可改为按 token 增量 append `chapters/<NNN>.partial.txt`，便于 GUI 更平滑预览。
- **Agentic mode**：当前 LangGraph 是显式 workflow，后续可在节点里嵌入受限 ReAct agent（仅用于人物 / 场景检索类节点）。
- **WebSocket 升级**：当前 SSE 单向，下一阶段可换 WebSocket 支持双向控制（暂停 / 调速）。
- **本地小模型**：`llama.cpp` / `ollama` 接入 ModelRegistry 仅是 provider 适配题，可后续做。

---

## 19. Migration from v1 Design

| v1 章节 | v2 对应 | 变化 |
|---|---|---|
| §1 Scope | §1 | 新增"零 GUI 直接 import LangChain"原则、§1.4 边界决策表 |
| §2 Directory | §3 + §4.2 + §5.2 + §6.2 + §9.2 + §10.2 | 拆分为四个服务的 layout |
| §3 Models | §3.2 | 移到 `src/shared/domain/`；移除 `events` from state；放宽 role 类型 |
| §4 RAG | §4 | 多分片 + chunk_id 稳定性 + ContextBudget |
| §5 AI Layer | §5.3 + §5.7 + §5.8 | ModelRegistry 对齐 model_routing.json；prompts 与现有 JSON 配置融合 |
| §6 Workflows | §5.5 + §5.6 + §6.3 + §8.4 | 拆 story/image；显式 checkpointer + interrupt + resume |
| §7 App Service | §5 + §7.2 + §8 | 改为 FastAPI router；event 流通过 SSE 推；run_id 贯穿 |
| §8 GUI | §10 | 改为 BackendClient + RunHandle 模式 |
| §9 Phases | §13 | Phase 顺序重排；Phase 4 新增 Supervisor；Phase 6 新增 image-service |
| §10 Errors | §3.5 + §14 | 错误统一 HTTP 编码 |
| §11 Testing | §15 | 加 ASGITransport / Supervisor fixture / 测试迁移矩阵 |
| §12 Rollback | §16 | 加 supervisor degraded 模式 |
| §13 Order | §13 | 重排 |
| §14 Acceptance | §17 | 加非功能性 + 文档项 |
| —（v1 缺）— | §6 image-service | v1 完全没覆盖图像 / 角色 / 导演 / 知乎 |
| —（v1 缺）— | §7 HTTP Contracts | v1 无 HTTP 设计 |
| —（v1 缺）— | §8 Cross-service Concerns | v1 无跨服务考虑 |
| —（v1 缺）— | §9 Supervisor & Lifecycle | v1 无进程管理 |
| —（v1 缺）— | §11 Persistence & Migration | v1 仅口头说兼容 |
| —（v1 缺）— | §12 Configuration Bridging | v1 没对接现有 `model_routing.json` 等配置 |
