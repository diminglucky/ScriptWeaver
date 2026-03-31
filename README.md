# AI Story Creator Pro

智能故事创作平台 - 基于知识库检索增强的AI小说创作工具

## 功能特点

### 📚 知识库驱动创作
- 导入参考小说/素材，构建向量索引
- AI 根据主题检索相关段落，结合素材创作
- 支持仿写特定风格的故事

### 🎨 角色一致性系统
- **角色DNA技术**：为每个角色生成固定的核心描述模板
- **三视图策略**：正面→斜侧→侧面→背面渐进生成
- **禁止漂移说明**：负面提示词防止特征变化
- 支持多角度、多表情批量生成

### 🖼️ 图片生成
- 支持 OpenAI DALL-E、腾讯混元等多种 API
- 一致性优化的提示词构建器
- 角色设定表、分镜头图片生成

### 📝 故事生成
- 目录大纲生成
- 分章节创作
- 自动连续生成

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

可选（知识库高级能力需要）：

```bash
pip install faiss-cpu
pip install python-docx pypdf
```

说明：
- `faiss-cpu`：向量索引/检索必需。
- `python-docx`：读取 `.docx` 必需。
- `pypdf`：读取 `.pdf` 必需（也兼容已安装 `PyPDF2` 的环境）。
- 以上依赖缺失时应用仍可启动，但对应能力会提示缺依赖。

### 2. 配置 API

创建 `.env` 文件或在应用内配置：

```env
API_PRESET=DeepSeek
STORY_DeepSeek_KEY=your_key_here
STORY_DeepSeek_BASE_URL=https://api.deepseek.com/v1
STORY_DeepSeek_MODEL=deepseek-chat
STORY_TEMPLATE_KEY=zhihu_realistic
STORY_TEMPLATE_STRATEGY=fixed # fixed / rotate / shuffle
STORY_CREATIVITY_MODE=blend  # stable / blend / wild
MODEL_ONLY=0                 # 1=仅模型, 0=启用知识库检索
RAG_MIN_SCORE=0.12           # 检索最低相似度阈值（0-1）

# 兼容旧配置（可选）
# DEEPSEEK_API_KEY=your_key_here
# DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
# DEEPSEEK_MODEL=deepseek-chat
```

说明：
- `STORY_TEMPLATE_STRATEGY`：控制模版多样性。`fixed` 稳定、`rotate` 轮换、`shuffle` 随机。
- `blend/wild` 会启用“跨模版融合引擎”，在主模版不变的前提下借入副模版规则，提高题材与叙事差异度。
- `RAG_MIN_SCORE`：检索过滤阈值，数值越高越严格。

### 3. 启动应用

```bash
python run_modern_app.py
```

或使用快捷脚本：
- macOS/Linux: `./启动应用.sh`
- Windows: `启动应用.bat`

## 使用流程

### 知识库仿写模式

```
1. 准备素材
   将参考素材(.txt/.md/.markdown/.json/.csv/.docx/.pdf)放入 data/ 目录

2. 构建索引
   点击「构建索引」按钮

3. 创作故事
   输入主题 → 选择字数 → 生成故事
```

### 纯模型模式

勾选「仅使用模型」，无需知识库直接创作。

## 项目结构

```
├── src/
│   ├── clients/          # API客户端
│   │   ├── deepseek_client.py
│   │   ├── image_client.py
│   │   └── hunyuan_image_client.py
│   ├── gui/
│   │   ├── models/       # 数据模型
│   │   │   └── character.py    # 角色DNA系统
│   │   ├── services/     # 服务层
│   │   │   ├── ai_service.py   # AI服务
│   │   │   └── image_service.py # 图片服务
│   │   ├── helpers/      # 辅助工具
│   │   └── mixins/       # 功能模块
│   ├── kb/               # 知识库
│   │   ├── ingest.py     # 索引构建
│   │   └── search.py     # 向量检索
│   └── utils/
├── data/                 # 素材目录
├── index/                # 索引目录
├── projects/             # 项目目录
└── run_modern_app.py     # 启动入口
```

## 技术栈

- **GUI**: Tkinter + 自定义主题
- **向量检索**: sentence-transformers + FAISS
- **AI**: DeepSeek / OpenAI 兼容 API
- **图片**: DALL-E / 腾讯混元

## 角色一致性最佳实践

基于 2025 年 AI 图片生成最佳实践：

1. **角色DNA模板** - 每次生成使用完全相同的核心描述
2. **三视图策略** - 从正面开始，渐进建立一致性
3. **独特标记** - 疤痕/痣/配饰提高辨识度
4. **禁止漂移** - 负面提示词防止特征变化

## 许可证

MIT License
