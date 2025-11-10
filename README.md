# AI Story Creator Pro

> AI驱动的专业故事创作平台

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## ✨ 功能特性

### 📝 故事创作
- **智能故事生成**：基于AI的创意故事生成
- **RAG增强创作**：使用知识库检索增强生成质量
- **章节管理**：自动生成目录和章节内容
- **多种风格**：支持多种故事风格和类型

### 🎨 图像生成
- **多API支持**：DeepSeek、OpenAI、Stable Diffusion、腾讯混元
- **人物一致性**：支持角色一致性生成
- **批量生成**：快速生成多张图片

### 📚 知识库管理
- **RAG检索**：向量相似度检索
- **快速添加**：轻松添加故事文件到知识库
- **自动索引**：自动构建向量索引

### 🎬 导演模式
- **剧本生成**：自动生成拍摄剧本
- **分镜设计**：智能分镜生成
- **章节选择**：⭐ 支持按章节生成分镜，快速测试（节省80%时间）
- **视频提示词**：生成视频制作提示词

### 📁 项目管理
- **完整保存**：保存故事、图片、配置等所有内容
- **自动备份**：自动创建备份文件
- **项目导入导出**：方便的项目管理

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置API密钥

创建 `.env` 文件：

```env
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
```

### 启动应用

**Windows:**
```bash
start_app.bat
# 或
python run_modern_app.py
```

**Linux/Mac:**
```bash
python run_modern_app.py
```

## 📖 使用指南

### 基本流程

1. **创建项目**
   - 点击"项目管理"标签
   - 输入项目名称
   - 点击"新建项目"

2. **生成故事**
   - 进入"故事生成"标签
   - 输入创作需求
   - 配置生成参数
   - 点击"生成故事"

3. **使用知识库**
   - 点击"快速添加故事文件"添加故事
   - 点击"构建索引"创建知识库
   - 勾选"使用项目故事作为知识库"

4. **生成图片**
   - 进入"图片生成"标签
   - 配置图片API
   - 输入提示词
   - 生成图片

## 🛠️ 开发

### 项目结构

```
├── src/
│   ├── gui/              # GUI界面
│   ├── clients/           # API客户端
│   ├── kb/               # 知识库模块
│   ├── services/         # 服务模块
│   └── utils/            # 工具函数
├── docs/                 # 文档
├── config/               # 配置文件
├── projects/             # 项目文件
└── requirements.txt      # 依赖列表
```

### 代码规范

- 使用类型注解
- 遵循PEP 8规范
- 添加文档字符串
- 使用logging而非print

## 📚 详细技术文档

本文档库包含非常详细的技术文档，涵盖项目的每个细节：

### 核心文档

- **[项目总体概述](docs/PROJECT_OVERVIEW.md)** - 完整的系统架构、启动流程、核心模块详解、数据流与执行流程、技术栈详解
  - 系统架构层次图
  - 完整启动流程（从main.py到ModernApp初始化的每一步）
  - 故事生成模块的完整实现细节
  - Prompt构建详解（包含代码示例）
  - 知识库构建和检索的完整数据流
  - 技术栈详解（Tkinter、FAISS、Sentence Transformers等）

- **[知识库模块详解](docs/KNOWLEDGE_BASE.md)** - 知识库构建流程、检索流程、文本处理、向量化与索引的完整说明
  - KnowledgeBaseIngestor和KnowledgeBaseSearcher的详细实现
  - 文本分块算法的完整说明（包含代码示例）
  - 向量化和FAISS索引的详细说明
  - 项目故事库的使用方法

### 文档特点

- ✅ **代码级详细**：每个函数、每个步骤都有详细说明
- ✅ **完整执行流程**：从用户操作到最终结果的完整数据流
- ✅ **实际代码示例**：包含大量实际代码示例和注释
- ✅ **算法详解**：核心算法（如文本分块、向量化）的详细说明

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

感谢所有贡献者和用户的支持！

---

**注意**：本项目正在积极开发中，部分功能可能不稳定。如有问题，请提交Issue。

