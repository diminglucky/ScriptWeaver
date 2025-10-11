# 创作知乎故事（RAG + DeepSeek）

一个基于本地知识库的知乎故事创作工具：先将你爬取的文章建立向量索引（FAISS），再用 DeepSeek 聊天模型进行检索增强生成（RAG）。支持命令行与图形界面（Tkinter）。

## 目录结构
```
创作知乎故事/
  data/
    raw/            # 放置你爬取到的文章（.txt/.md/.markdown/.md.txt）
    processed/
  index/            # 生成的向量索引与片段缓存
  src/
    clients/        # DeepSeek 客户端封装
    kb/             # 知识库构建与检索
    utils/          # 文本处理工具
    story_cli.py    # CLI 入口（ingest/generate）
    gui_app.py      # 图形界面入口
  main.py           # 直接启动 GUI 的入口
```

## 安装
1. Python 3.10+
2. 安装依赖：
```bash
pip install -r requirements.txt
```
3. 配置环境变量（任选其一）：
   - 在 GUI 中设置：启动 GUI 后，在“API Key / Base URL / Model”栏填写后点击“保存配置”，将写入项目根目录的 `.env`；也可点击“加载配置”从 `.env` 读取。
   - 或复制 `.env.example` 为 `.env`，填入 `DEEPSEEK_API_KEY`（可选 `DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`）。
   - 或在 shell 中导出（macOS/Linux）：
```bash
export DEEPSEEK_API_KEY="your_api_key_here"
```

## 直接启动 GUI

### 现代化专业UI（推荐）✨
```bash
python run_modern_app.py
```
全新设计的专业级UI界面，包含：
- 优雅的深色主题配色
- 现代化的侧边导航栏
- 专业的状态指示
- 流畅的交互体验

### 传统UI
```bash
python main.py
```

## 使用说明（GUI）
- 数据目录：选择你的文本数据目录。
- 索引目录：向量索引输出位置。
- 构建索引：清洗/切分/向量化，并写入“索引目录”。
- 种类：选择或输入（支持下拉选择或直接编辑）。
- 生成目录：先产出结构化“目录”（不写正文），并在上方显示“预估字数”。
- 生成故事：参考“目录”和检索的片段进行创作，流式显示结果。
- 保存为...：将当前输出保存为 `.md` 或 `.txt`。

## CLI（可选）
构建索引：
```bash
python -m src.story_cli ingest --data-root data/raw --index-dir index
```

生成知乎故事：
```bash
python -m src.story_cli generate "请写一篇关于病娇题材的故事，面向知乎读者" --index-dir index --top-k 6 --show-context
```

## 备注
- 检索到的资料用于启发写作，请进行改写与整合，避免直接复制。
- 如需中文多语种更强的向量效果，可以替换为其他 `sentence-transformers` 模型。
