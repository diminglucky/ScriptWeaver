# ScriptWeaver / Zhihu Short Stories

ScriptWeaver 是一个面向知乎短篇、长篇连载和图文内容生产的本地创作工作台。项目当前同时保留成熟的 Tkinter 现代化 GUI，并引入 v2 微服务架构：`rag-service`、`story-service`、`image-service` 通过 FastAPI 提供可测试、可扩展的后端能力。

## 当前状态

- **GUI 入口**：使用 `run_modern_app.py` 启动现代化 UI。
- **不要使用旧入口**：不要用旧 `main.py` 启动，它会进入旧版 GUI。
- **v2 后端**：已提供 RAG、故事生成、图片生成的 FastAPI skeleton 与 deterministic workflow，可在无真实 API Key 的情况下跑通测试和基本流程。
- **测试状态**：当前全量回归通过，覆盖 GUI backend、RAG、Story workflow、Image API、配置、SSE、运行管理等模块。

## 功能概览

### 1. 现代化本地 GUI

- 基于 Tkinter 的现代化 UI：`src/gui/modern_app.py`。
- 支持故事生成、知识库、图片生成、导演脚本、项目管理、API 配置等工作区。
- macOS 环境下推荐 Python 3.11，`run_modern_app.py` 包含启动保护逻辑。

### 2. RAG 知识库

- 传统 GUI 知识库能力位于 `src/kb/`。
- v2 RAG 微服务位于 `src/services/rag_service/`。
- 支持文档 ingest、文本切分、embedding hub、SQLite metadata store、vector shard/index hub。
- 支持 `reference`、`project_memory`、`style_corpus` 三类知识库。
- 提供 HTTP search、project memory、manifest API。

### 3. Story Service

`src/services/story_service/` 提供故事工作流后端：

- `ModelRegistry`：统一模型路由和 deterministic fallback。
- `PromptLibrary`：集中构建 story bible、character、outline、chapter、review prompts。
- `SimpleCompiledGraph`：不强依赖 LangGraph runtime 的可测试 compiled graph 兼容层。
- Novel / Character / Review workflows：story bible、角色设计、大纲、章节、review skeleton、ProjectStore 持久化。
- `WorkflowRunner`：接入 `CreativeService`，通过 run/event 协议驱动后台任务。
- HTTP API 覆盖 projects、novel run、character run、runs、reviews、models/routing。

### 4. Image Service

`src/services/image_service/` 提供 deterministic image-service skeleton：

- image prompt generation
- shot prompt list/render/batch
- character turnaround/photo run
- single image render
- director script generation/read
- Zhihu publish dry-run result
- run SSE events and cancel

当前实现优先保证 API contract 和端到端测试可运行；真实图片 provider、真实发布能力可在后续替换 deterministic adapter。

### 5. GUI Backend Client

`src/gui/backend/` 是 GUI 与 v2 微服务之间的 facade，包含 `BackendClient`、`RagClient`、`StoryClient`、`ImageClient`、`ServiceSupervisor`、SSE event parsing、ports/runtime 管理和 HTTP error envelope 转换。

## 推荐启动方式

### 启动现代化 GUI

```bash
/opt/homebrew/bin/python3.11 run_modern_app.py
```

或：

```bash
python3.11 run_modern_app.py
```

### 使用本地 Conda work 环境

```bash
./start_with_work_env.sh
```

### 启动 v2 微服务

可以通过 GUI backend supervisor 管理，也可以直接用 uvicorn：

```bash
python3.11 -m uvicorn src.services.rag_service.runtime:app --host 127.0.0.1 --port 8101
python3.11 -m uvicorn src.services.story_service.runtime:app --host 127.0.0.1 --port 8102
python3.11 -m uvicorn src.services.image_service.runtime:app --host 127.0.0.1 --port 8103
```

常用环境变量：

```bash
export WSF_REPO_ROOT=/path/to/ScriptWeaver
export WSF_BACKEND_TOKEN=dev-token
export WSF_SERVICE_TOKEN=dev-service-token
export WSF_RAG_BASE_URL=http://127.0.0.1:8101
export WSF_STORY_BASE_URL=http://127.0.0.1:8102
export WSF_IMAGE_BASE_URL=http://127.0.0.1:8103
```

## 安装依赖

```bash
python3.11 -m pip install -r requirements.txt
```

主要依赖包括 FastAPI、uvicorn、httpx、Pydantic v2、LangGraph、ChromaDB、transformers、sentence-transformers、requests、Pillow、tqdm、playwright。

## 项目结构

```text
.
├── config/                         # prompt/profile/guardrail/theme 等配置
├── docs/                           # 架构文档与实施计划
├── projects/                       # 本地项目数据与生成结果
├── scripts/dev/                    # 开发辅助脚本
├── src/
│   ├── clients/                    # 传统 GUI 使用的外部 API client
│   ├── gui/                        # Tkinter GUI 与 GUI backend facade
│   ├── kb/                         # 传统 GUI 知识库模块
│   ├── services/
│   │   ├── rag_service/            # v2 RAG FastAPI service
│   │   ├── story_service/          # v2 Story FastAPI service + workflows
│   │   └── image_service/          # v2 Image FastAPI service skeleton
│   └── shared/                     # domain schemas/errors/events/config/http helpers
├── tests/                          # 原有测试
├── tests/v2/                       # v2 微服务与 backend 测试
├── requirements.txt
├── run_modern_app.py               # 推荐 GUI 启动入口
└── start_with_work_env.sh
```

## 测试

### 全量回归

```bash
/opt/homebrew/bin/python3.11 -m pytest -q --no-header --tb=short -p no:cacheprovider
```

### v2 测试

```bash
/opt/homebrew/bin/python3.11 -m pytest tests/v2 -q --no-header --tb=short -p no:cacheprovider
```

### import smoke

```bash
/opt/homebrew/bin/python3.11 scripts/dev/smoke_imports.py
```

## API 概览

### rag-service

- `GET /v1/health`
- `POST /v1/kb/{kb_type}/ingest`
- `DELETE /v1/kb/{kb_type}/sources/{source_id}`
- `POST /v1/kb/{kb_type}/search`
- `POST /v1/projects/{project_id}/memory`
- `GET /v1/projects/{project_id}/memory`
- `DELETE /v1/projects/{project_id}/memory`
- `POST /v1/admin/manifest:rebuild`
- `GET /v1/admin/manifest`

### story-service

- `GET /v1/health`
- `POST /v1/projects`
- `GET /v1/projects`
- `GET /v1/projects/{project_id}`
- `GET /v1/projects/{project_id}/storybible`
- `GET /v1/projects/{project_id}/chapters`
- `GET /v1/projects/{project_id}/chapters/{idx}`
- `GET /v1/projects/{project_id}/story`
- `POST /v1/projects/{project_id}/novel:run`
- `POST /v1/projects/{project_id}/characters:design`
- `GET /v1/runs/{run_id}`
- `GET /v1/runs/{run_id}/events`
- `POST /v1/runs/{run_id}/cancel`
- `POST /v1/runs/{run_id}/resume`
- `POST /v1/runs/{run_id}/review`
- `GET /v1/models`
- `GET /v1/routing`
- `PUT /v1/routing`

### image-service

- `GET /v1/health`
- `POST /v1/projects/{project_id}/image-prompts:generate`
- `GET /v1/projects/{project_id}/shots`
- `POST /v1/projects/{project_id}/shots:batch`
- `POST /v1/projects/{project_id}/shots/{shot_id}:render`
- `POST /v1/images:generate`
- `POST /v1/projects/{project_id}/characters/{name}/turnaround`
- `POST /v1/projects/{project_id}/characters/{name}/photo`
- `POST /v1/projects/{project_id}/director:script`
- `GET /v1/projects/{project_id}/director/script`
- `POST /v1/projects/{project_id}/zhihu:publish`
- `GET /v1/projects/{project_id}/zhihu/last-result`
- `GET /v1/runs/{run_id}/events`
- `POST /v1/runs/{run_id}/cancel`

## 数据与安全

- 不要提交真实 API Key。
- `.env`、`custom_api_presets.json`、`custom_image_api_presets.json`、`config/.keyfile` 已被 `.gitignore` 忽略。
- `.runtime/`、索引文件、缓存、项目运行时 checkpoint/run logs 不应提交。

## 开发约定

- 入口优先使用 `run_modern_app.py`。
- v2 公共 schema 放在 `src/shared/domain/`。
- 服务间错误使用 `CreativeError` envelope。
- 长任务通过 `CreativeEvent` + SSE 暴露进度。
- 新增后端能力应补充 `tests/v2/` 覆盖。

## License

MIT License. 使用生成内容时请遵守对应平台规则和当地法律法规。
