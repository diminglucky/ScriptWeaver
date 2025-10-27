# 知乎短故事自动化创作平台 📖

一个基于 AI 的知乎短故事全流程创作工具，支持从故事创作、角色生成、分镜脚本到自动发布知乎的完整工作流。

## ✨ 核心功能

### 🎬 故事创作模块
- **RAG增强生成** - 基于本地知识库（FAISS）检索相关素材，使用 DeepSeek 生成高质量故事
- **智能分章生成** - 自动生成目录大纲，分章节创作，支持长篇故事
- **实时预览** - 流式显示生成过程，实时查看创作进度
- **字数统计** - 自动统计每章和总字数

### 👥 角色一致性系统
- **多角度角色生成** - 支持正面、侧面、背面三视图
- **表情系统** - 8种表情（中性、开心、微笑、悲伤、惊讶、愤怒、害怕、难过）
- **一致性保证** - 使用参考图像确保角色在不同场景下的一致性
- **批量生成** - 一次生成多个角色的完整视图集

### 🎥 分镜脚本系统
- **自动分镜生成** - 从剧本自动生成详细分镜脚本
- **分段处理** - 支持长剧本智能分段生成
- **即梦AI提示词** - 自动生成适合视频生成的提示词
- **可视化预览** - 分镜脚本友好格式展示

### 📤 知乎自动发布
- **智能内容过滤** - 自动过滤目录、章节标题、进度信息
- **爆款标题生成** - AI生成简洁明了的知乎标题（10-15字）
- **智能话题匹配** - 内置23个知乎热门话题，智能匹配最相关的话题
- **全流程自动化** - 自动完成投稿问题、创作声明、话题添加、发布点击
- **浏览器自动化** - 使用 Playwright 自动操作知乎编辑器

### 🖼️ 图像生成支持
- **多API支持** - 支持混元图像、Stable Diffusion、自定义API
- **角色图像生成** - 为故事角色生成一致性的人物形象
- **场景图像生成** - 根据分镜脚本生成场景图像

## 🏗️ 项目架构

```
Zhihu_short_stories/
├── src/
│   ├── clients/                    # API客户端
│   │   ├── base_client.py         # 基础客户端
│   │   ├── deepseek_client.py     # DeepSeek API
│   │   ├── hunyuan_image_client.py # 混元图像API
│   │   ├── sd_client.py           # Stable Diffusion
│   │   └── image_client.py        # 图像生成客户端
│   │
│   ├── kb/                         # 知识库模块
│   │   ├── ingest.py              # 索引构建
│   │   └── search.py              # 向量检索
│   │
│   ├── gui/                        # 图形界面
│   │   ├── modern_app.py          # 现代化主应用
│   │   ├── theme.py               # 主题配置
│   │   ├── mixins/                # 功能模块（Mixin架构）
│   │   │   ├── story_modules/    # 故事生成模块
│   │   │   │   ├── outline_generator.py      # 大纲生成
│   │   │   │   ├── story_generator.py        # 故事生成
│   │   │   │   ├── zhihu_publisher_mixin.py  # 知乎发布
│   │   │   │   └── ui_builder.py             # UI构建
│   │   │   │
│   │   │   ├── character_modules/ # 角色生成模块
│   │   │   │   ├── character_manager.py      # 角色管理
│   │   │   │   ├── character_generator.py    # 角色生成
│   │   │   │   └── consistency_manager.py    # 一致性管理
│   │   │   │
│   │   │   ├── director_modules/  # 分镜导演模块
│   │   │   │   ├── director_mixin.py         # 分镜主模块
│   │   │   │   ├── shot_list_generator.py    # 分镜生成
│   │   │   │   ├── jimeng_prompt_generator.py # 即梦提示词
│   │   │   │   └── image_preview_methods.py  # 图像预览
│   │   │   │
│   │   │   └── project_modules/   # 项目管理模块
│   │   │       └── enhanced_manager.py       # 项目管理器
│   │   │
│   │   ├── helpers/               # 辅助工具
│   │   │   ├── character_prompt_builder.py   # 角色提示词
│   │   │   ├── character_sheet_builder.py    # 角色表构建
│   │   │   ├── consistency_optimizer.py      # 一致性优化
│   │   │   └── image_helpers.py              # 图像处理
│   │   │
│   │   └── widgets/               # 自定义控件
│   │
│   ├── services/                   # 服务层
│   │   └── zhihu_publisher.py     # 知乎发布服务
│   │
│   ├── utils/                      # 工具函数
│   │   ├── story_extractor.py     # 故事内容提取
│   │   └── text.py                # 文本处理
│   │
│   ├── core/                       # 核心模块
│   │   ├── exceptions.py          # 异常定义
│   │   └── logging_config.py      # 日志配置
│   │
│   └── project_manager.py         # 项目管理器
│
├── config/                         # 配置文件
│   └── director_config.json       # 导演模式配置
│
├── projects/                       # 项目存储目录
│   └── [项目名]_[时间戳]/
│       ├── story.txt              # 故事文本
│       ├── project.json           # 项目配置
│       ├── characters/            # 角色图像
│       ├── director/              # 分镜脚本
│       └── images/                # 生成的图像
│
├── data/                           # 知识库数据
│   └── raw/                       # 原始文章
│
├── index/                          # 向量索引
│
├── run_modern_app.py              # 启动现代化界面
├── main.py                        # 启动传统界面
├── requirements.txt               # 依赖包
└── README.md                      # 本文件
```

## 🚀 快速开始

### 1. 安装依赖

```bash
# 克隆项目
git clone <your-repo-url>
cd Zhihu_short_stories

# 安装Python依赖
pip install -r requirements.txt

# 安装Playwright浏览器（用于知乎自动发布）
playwright install chromium
```

### 2. 配置API

在项目根目录创建 `.env` 文件：

```env
# DeepSeek API（必需）
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 图像生成API（可选）
# 混元图像
HUNYUAN_SECRET_ID=your_secret_id
HUNYUAN_SECRET_KEY=your_secret_key

# Stable Diffusion
SD_API_URL=http://localhost:7860
```

### 3. 启动应用

```bash
# 启动现代化界面（推荐）
python run_modern_app.py

# 或启动传统界面
python main.py
```

## 📖 功能模块详解

### 一、故事生成 📝

#### 1.1 基于知识库的RAG生成

**构建知识库索引**：
1. 将文章放入 `data/raw/` 目录
2. 在GUI中选择数据目录和索引目录
3. 点击「构建索引」
4. 系统会自动：
   - 清洗文本
   - 切分片段（800字/片段，重叠120字）
   - 向量化（使用sentence-transformers）
   - 构建FAISS索引

**生成故事**：
1. 输入故事主题或要求
2. 选择故事种类（校园、职场、情感、悬疑等）
3. 点击「生成目录」- 生成章节大纲
4. 点击「生成故事」- 分章节创作完整故事
5. 实时查看生成进度和字数统计

#### 1.2 智能分章系统

- **自动大纲** - AI生成4-6章的故事结构
- **分章创作** - 逐章生成，保证质量和连贯性
- **进度追踪** - 实时显示当前章节和总进度
- **字数控制** - 每章1000-1500字，总计4000-6000字

### 二、角色生成 👤

#### 2.1 角色一致性系统

**角色创建流程**：
1. 输入角色描述（外貌、性格、服装）
2. 选择角色姓名
3. 点击「生成角色」
4. 系统自动生成：
   - 正面视图
   - 侧面视图
   - 背面视图
   - 8种表情变化

**一致性保证**：
- 使用第一张生成的图像作为参考
- 所有后续图像基于参考图生成
- 保证同一角色在不同角度和表情下的一致性

#### 2.2 角色管理

- **角色列表** - 查看项目中所有已生成的角色
- **角色预览** - 点击查看角色的所有图像
- **角色导出** - 保存到项目目录 `projects/[项目名]/characters/`

### 三、分镜脚本 🎬

#### 3.1 分镜生成

**从剧本到分镜**：
1. 在「导演」模块中输入或加载剧本
2. 点击「剧本→分镜」
3. 系统自动：
   - 智能分段（每段1500字）
   - 逐段生成详细分镜
   - 包含画面描述、人物动作、镜头运动等

**分镜内容**：
- 分镜编号
- 镜头类型（Wide Shot/Medium Shot/Close-up）
- 位置描述
- 画面描述（200-300字）
- 人物细节（外貌、服装、表情、动作）
- 镜头运动（固定/推进/拉远/横摇/跟随）
- 建议时长
- 转场方式

#### 3.2 即梦AI提示词

- **自动提取** - 从分镜脚本自动提取视频生成提示词
- **格式优化** - 简洁清晰，适合直接输入视频生成AI
- **批量导出** - 一次性导出所有分镜的提示词

### 四、知乎自动发布 📤

#### 4.1 内容处理

**智能过滤**：
- 自动过滤目录、章节标题
- 过滤进度信息（"☑ 第 1 章完成！本章字数：1354 字"）
- 保留纯净的故事正文
- 压缩多余空行

**标题生成**：
- AI生成简洁明了的标题（10-15字）
- 风格：真实、平实、不夸张
- 示例："毕业后的一些改变"、"我的求职经历"

#### 4.2 全自动发布流程

点击「📤 发布到知乎」后，系统会自动：

1. **打开知乎编辑器** - 自动跳转到文章编辑页面
2. **填充标题和内容** - 自动输入标题和纯净正文
3. **投稿至问题** - 自动选择推荐问题
4. **设置创作声明** - 自动选择"虚构创作"
5. **添加话题标签** - 智能提取话题并自动添加
6. **点击发布** - 自动点击发布按钮
7. **等待跳转** - 发布成功后跳转到文章页面

**智能话题系统**：
- 内置23个知乎热门话题
- 根据故事内容智能匹配
- 覆盖：校园、职场、情感、成长、悬疑、都市等所有类型

### 五、项目管理 📁

- **项目创建** - 为每个故事创建独立项目
- **自动保存** - 自动保存故事、角色、分镜等所有资源
- **项目加载** - 随时加载历史项目继续创作
- **资源管理** - 统一管理故事文本、角色图像、分镜脚本

## 🎨 界面预览

### 现代化UI（推荐）

- **深色主题** - 专业优雅的深色配色
- **侧边导航** - 清晰的功能模块导航
- **实时状态** - 顶部状态栏实时显示操作进度
- **响应式布局** - 自适应窗口大小

**功能模块**：
- 📝 故事生成 - 创作故事和生成目录
- 👥 角色生成 - 创建一致性角色
- 🎬 导演模式 - 分镜脚本和提示词
- 📁 项目管理 - 管理所有创作项目

## 🛠️ 技术栈

### 核心技术
- **Python 3.10+** - 主要编程语言
- **Tkinter** - GUI界面框架
- **FAISS** - 向量数据库（相似度检索）
- **Sentence Transformers** - 文本向量化
- **DeepSeek API** - 大语言模型
- **Playwright** - 浏览器自动化

### AI模型
- **文本生成** - DeepSeek Chat（或兼容OpenAI的其他模型）
- **文本向量化** - sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
- **图像生成** - 腾讯混元、Stable Diffusion、自定义API

### 架构设计
- **Mixin模式** - 模块化的GUI功能组织
- **异步处理** - Threading实现长时任务不阻塞UI
- **配置管理** - JSON配置文件+环境变量

## 📦 安装部署

### 环境要求

- Python 3.10 或更高版本
- Windows / macOS / Linux
- 8GB+ 内存（推荐）
- 稳定的网络连接（调用API）

### 安装步骤

```bash
# 1. 克隆项目
git clone <your-repo-url>
cd Zhihu_short_stories

# 2. 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装Playwright浏览器
playwright install chromium

# 5. 配置API密钥
cp .env.example .env  # 如果有示例文件
# 编辑.env文件，填入你的API密钥
```

### 配置说明

创建 `.env` 文件并配置以下内容：

```env
# DeepSeek API（必需）
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 图像生成API（可选，根据需要配置）
# 腾讯混元图像
HUNYUAN_SECRET_ID=your_secret_id
HUNYUAN_SECRET_KEY=your_secret_key

# Stable Diffusion
SD_API_URL=http://127.0.0.1:7860
```

## 📚 使用教程

### 教程1：创作第一个故事

1. **启动应用**
   ```bash
   python run_modern_app.py
   ```

2. **配置API**
   - 在应用顶部输入 DeepSeek API Key
   - 点击「保存配置」

3. **生成故事**
   - 输入故事主题（例如："一个校园霸凌后逆袭的故事"）
   - 选择种类："校园"
   - 点击「生成目录」- 等待大纲生成
   - 点击「生成故事」- 等待完整故事生成（约1-2分钟）

4. **保存故事**
   - 点击「保存为...」
   - 选择保存格式（.txt 或 .md）

### 教程2：发布到知乎

1. **生成故事**（按教程1）

2. **生成标题**
   - 点击「🤖 AI生成标题」
   - 获得10-15字的简洁标题

3. **一键发布**
   - 点击「📤 发布到知乎」
   - 系统会自动：
     - 打开知乎编辑器（首次需手动登录）
     - 填充标题和内容
     - 选择投稿问题
     - 设置创作声明
     - 添加话题标签
     - 点击发布
   - 等待浏览器跳转到已发布的文章

### 教程3：生成角色图像

1. **创建项目**
   - 在「项目管理」中创建新项目

2. **添加角色**
   - 切换到「角色生成」模块
   - 输入角色描述：
     ```
     姓名：林小雨
     外貌：18岁女生，清秀可爱，大眼睛
     发型：黑色长发，马尾辫
     服装：蓝白色校服，白色运动鞋
     ```

3. **生成角色图像**
   - 点击「生成角色」
   - 等待生成完成（约30秒）
   - 查看：正面、侧面、背面、多种表情

4. **使用角色**
   - 角色图像自动保存到项目目录
   - 可在分镜生成中引用角色

### 教程4：生成分镜脚本

1. **准备剧本**
   - 在「导演」模块输入剧本文本
   - 或从已生成的故事导入

2. **生成分镜**
   - 点击「剧本→分镜」
   - 系统自动生成详细分镜（包含画面、动作、镜头等）

3. **查看分镜**
   - 切换到「分镜」标签查看友好格式
   - 切换到「即梦AI提示词」标签查看视频提示词

4. **导出使用**
   - 复制即梦AI提示词
   - 直接用于视频生成工具

## ⚙️ 配置文件

### API预设配置

编辑 `custom_api_presets.json`：

```json
{
  "DeepSeek": {
    "key": "your_api_key",
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-chat"
  },
  "自定义API": {
    "key": "your_api_key",
    "base_url": "https://your-api-endpoint",
    "model": "your-model"
  }
}
```

### 图像API预设

编辑 `custom_image_api_presets.json`：

```json
{
  "混元图像": {
    "type": "hunyuan",
    "secret_id": "your_secret_id",
    "secret_key": "your_secret_key"
  },
  "Stable Diffusion": {
    "type": "sd",
    "api_url": "http://127.0.0.1:7860"
  }
}
```

## 💡 使用技巧

### 提升故事质量
1. **丰富知识库** - 添加更多高质量文章到 `data/raw/`
2. **精准主题** - 输入详细的故事要求，包括人物、情节、风格
3. **调整参数** - temperature 0.7-0.9之间（0.7更稳定，0.9更有创意）

### 角色一致性技巧
1. **详细描述** - 提供详细的外貌、服装、发型描述
2. **参考图像** - 第一张生成的图像很重要，会影响后续所有图像
3. **重新生成** - 如果不满意，可以删除重新生成

### 知乎发布技巧
1. **首次使用** - 需要手动登录知乎，之后会记住登录状态
2. **检查内容** - 发布前在预览窗口检查内容
3. **标题优化** - 可以在AI生成的基础上手动微调
4. **多生成几次** - 如果标题不满意，可以多生成几次选最好的

## 🔧 常见问题

### Q1: 安装playwright失败？
```bash
# 使用国内镜像
pip install playwright -i https://pypi.tuna.tsinghua.edu.cn/simple
playwright install chromium
```

### Q2: API调用失败？
- 检查 API Key 是否正确
- 检查网络连接
- 检查 API 额度是否充足

### Q3: 向量索引构建失败？
- 确保 `data/raw/` 目录中有文本文件
- 检查文件编码（建议UTF-8）
- 查看控制台错误信息

### Q4: 知乎发布失败？
- 首次使用需要手动登录知乎
- 确保已安装 Playwright 浏览器
- 查看控制台日志，了解具体失败原因

### Q5: 图像生成失败？
- 检查图像API配置是否正确
- 确保API服务正常运行
- 检查API额度或限流

## 🎯 完整工作流示例

### 从创作到发布的完整流程

```
1. 📝 故事创作
   ├── 输入主题："一个关于校园霸凌后成长的故事"
   ├── 生成目录 → 获得4章大纲
   ├── 生成故事 → 获得完整故事（约5000字）
   └── 保存故事

2. 👥 角色生成（可选）
   ├── 创建主角：林小雨（18岁女生，校服）
   ├── 生成三视图 + 8种表情
   └── 保存到项目

3. 🎬 分镜脚本（可选）
   ├── 导入故事作为剧本
   ├── 生成详细分镜
   ├── 提取即梦AI提示词
   └── 导出分镜脚本

4. 📤 发布到知乎
   ├── AI生成标题："说说我的校园往事"
   ├── 预览发布内容（已过滤进度信息）
   ├── 点击发布 → 自动完成所有步骤
   └── 发布成功！获得文章链接
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目仅供学习和研究使用。

## 🙏 致谢

- [DeepSeek](https://www.deepseek.com/) - 优秀的大语言模型
- [FAISS](https://github.com/facebookresearch/faiss) - 高效的向量检索库
- [Sentence Transformers](https://www.sbert.net/) - 文本向量化工具
- [Playwright](https://playwright.dev/) - 浏览器自动化工具

## 📞 联系方式

如有问题或建议，欢迎通过以下方式联系：
- Issue: 在GitHub上提交Issue
- Email: your-email@example.com

---

**让AI帮你创作知乎爆款故事！** 🚀✨
