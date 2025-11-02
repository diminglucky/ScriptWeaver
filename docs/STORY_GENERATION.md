# 故事生成模块详细技术文档

## 📋 目录

1. [模块概述](#模块概述)
2. [文件结构](#文件结构)
3. [核心组件详解](#核心组件详解)
4. [完整执行流程](#完整执行流程)
5. [Prompt构建详解](#prompt构建详解)
6. [目录生成详解](#目录生成详解)
7. [分段生成详解](#分段生成详解)
8. [知乎发布详解](#知乎发布详解)

---

## 模块概述

### 功能定位

故事生成模块是系统的核心功能模块，负责：

1. **故事生成**：使用AI生成完整的故事内容
2. **目录生成**：自动生成结构化故事大纲
3. **分段生成**：支持按章节分段生成长故事
4. **知乎发布**：将生成的故事发布到知乎平台
5. **输入缓存**：自动保存和恢复用户输入

### 模块位置

```
src/gui/mixins/story_modules/
├── __init__.py              # 模块导出
├── ui_builder.py            # UI构建和Prompt构建
├── story_generator.py       # 故事生成逻辑
├── outline_generator.py     # 目录生成逻辑
├── input_cache.py           # 输入缓存
├── config_handler.py        # 配置处理
└── zhihu_publisher_mixin.py # 知乎发布
```

### 模块依赖关系

```
StoryMixin (主入口)
├── StoryUIBuilderMixin      # UI构建
│   └── _build_prompt()      # Prompt构建
│   └── _extract_explicit_opening()  # 提取明确开头
│   └── _get_category_guidance()    # 类型指导
│
├── StoryGeneratorMixin      # 故事生成
│   └── on_generate()        # 生成入口
│   └── _generate_model_only()      # 仅模型生成
│   └── _generate_in_sections()     # 分段生成
│
├── OutlineGeneratorMixin    # 目录生成
│   └── on_generate_outline()       # 生成目录
│   └── on_generate_section()       # 生成章节
│   └── _build_section_prompt()     # 章节Prompt
│
├── InputCacheMixin          # 输入缓存
│   └── _save_input_cache()  # 保存缓存
│   └── _load_input_cache()  # 加载缓存
│
├── StoryConfigMixin         # 配置处理
│   └── on_save_as()         # 保存文件
│   └── on_test_story_api()  # API测试
│
└── ZhihuPublisherMixin      # 知乎发布
    └── _on_generate_zhihu_title()  # 生成标题
    └── _on_publish_to_zhihu()      # 发布到知乎
```

---

## 文件结构

### 1. ui_builder.py

**职责**: UI构建和Prompt构建

**主要类**:
- `StoryUIBuilderMixin`: UI构建和Prompt构建功能

**主要方法**:
- `_build_story_page()`: 构建故事生成页面
- `_build_story_create_tab()`: 构建创作标签页
- `_build_story_setup_tab()`: 构建配置标签页
- `_build_prompt()`: 构建用户Prompt（核心方法）
- `_build_outline_prompt()`: 构建目录Prompt
- `_extract_explicit_opening()`: 提取用户指定的开头
- `_get_category_guidance()`: 获取类型特定指导

**文件大小**: 847行

### 2. story_generator.py

**职责**: 故事生成逻辑

**主要类**:
- `StoryGeneratorMixin`: 故事生成功能

**主要方法**:
- `on_generate()`: 生成故事主入口
- `_generate_model_only()`: 仅使用模型生成（无RAG）
- `_generate_in_sections()`: 分段生成（长故事）
- `_insert_text_safe()`: 线程安全的文本插入

**文件大小**: 417行

### 3. outline_generator.py

**职责**: 目录生成和章节生成逻辑

**主要类**:
- `OutlineGeneratorMixin`: 目录生成功能

**主要方法**:
- `on_generate_outline()`: 生成目录
- `on_generate_section()`: 生成单个章节
- `on_generate_all_sections()`: 生成所有章节
- `on_continue_next_section()`: 继续生成下一章
- `_generate_in_sections()`: 分段生成实现
- `_build_section_prompt()`: 构建章节Prompt
- `_parse_outline_sections()`: 解析目录章节
- `_update_section_selector()`: 更新章节选择器

**文件大小**: 929行

### 4. input_cache.py

**职责**: 输入缓存功能

**主要类**:
- `InputCacheMixin`: 输入缓存功能

**主要方法**:
- `_init_input_cache()`: 初始化输入缓存
- `_load_input_cache()`: 加载输入缓存
- `_save_input_cache()`: 保存输入缓存
- `_bind_input_cache_events()`: 绑定输入事件

**文件大小**: 180行

### 5. config_handler.py

**职责**: 配置处理和文件操作

**主要类**:
- `StoryConfigMixin`: 配置处理功能

**主要方法**:
- `on_save_as()`: 保存文件
- `on_clear_output()`: 清空输出
- `on_copy_output()`: 复制输出
- `on_test_story_api()`: 测试API
- `_save_story_assist_api_config()`: 保存API配置
- `_estimate_chars()`: 估算字数

**文件大小**: 205行

### 6. zhihu_publisher_mixin.py

**职责**: 知乎发布功能

**主要类**:
- `ZhihuPublisherMixin`: 知乎发布功能

**主要方法**:
- `_build_zhihu_publish_ui()`: 构建发布UI
- `_on_generate_zhihu_title()`: AI生成标题
- `_on_publish_to_zhihu()`: 发布到知乎

**文件大小**: 509行

---

## 核心组件详解

### 1. StoryUIBuilderMixin

#### 类定义

```python
class StoryUIBuilderMixin:
    """Story ui_builder 功能"""
    
    def _build_story_page(self) -> None:
        """构建故事生成页面"""
        # 创建内部标签页（创作、配置）
        # 构建各个子页面
```

#### `_build_story_create_tab()` 详解

```python
def _build_story_create_tab(self) -> None:
    """构建故事创作标签页"""
    
    # 步骤1: 创建左侧输入区域
    left_frame = ttk.Frame(self.story_tab_create)
    left_frame.pack(side=LEFT, fill=BOTH, expand=True)
    
    # 步骤2: 创建创作需求输入框
    requirement_label = ttk.Label(left_frame, text="📝 创作需求/主题")
    requirement_label.pack(anchor="w", pady=(0, 5))
    
    self.prompt_text = scrolledtext.ScrolledText(
        left_frame,
        height=15,
        wrap=tk.WORD,
        font=("Microsoft YaHei", 10)
    )
    self.prompt_text.pack(fill=BOTH, expand=True)
    
    # 步骤3: 创建控制面板
    control_frame = ttk.Frame(left_frame)
    control_frame.pack(fill="x", pady=(10, 0))
    
    # 步骤4: 创建故事类型选择
    self.category = tk.StringVar(value="")
    category_combo = ttk.Combobox(
        control_frame,
        textvariable=self.category,
        values=["", "爱情", "悬疑", "职场", "成长", "亲情"],
        width=10
    )
    category_combo.pack(side=LEFT, padx=(0, 10))
    
    # 步骤5: 创建字数设置
    self.target_chars = tk.IntVar(value=1800)
    chars_entry = ttk.Entry(control_frame, textvariable=self.target_chars, width=10)
    chars_entry.pack(side=LEFT, padx=(0, 10))
    
    # 步骤6: 创建生成按钮
    generate_btn = ttk.Button(
        control_frame,
        text="🚀 生成故事",
        command=self.on_generate
    )
    generate_btn.pack(side=LEFT, padx=(10, 0))
    
    # 步骤7: 创建右侧输出区域
    right_frame = ttk.Frame(self.story_tab_create)
    right_frame.pack(side=RIGHT, fill=BOTH, expand=True)
    
    self.output = scrolledtext.ScrolledText(
        right_frame,
        height=30,
        wrap=tk.WORD,
        font=("Microsoft YaHei", 10)
    )
    self.output.pack(fill=BOTH, expand=True)
    
    # 步骤8: 创建操作按钮区域
    action_frame = ttk.Frame(right_frame)
    action_frame.pack(fill="x", pady=(10, 0))
    
    save_btn = ttk.Button(action_frame, text="💾 保存", command=self.on_save_story)
    save_btn.pack(side=LEFT, padx=(0, 5))
    
    clear_btn = ttk.Button(action_frame, text="🗑️ 清空", command=self.on_clear_output)
    clear_btn.pack(side=LEFT, padx=(0, 5))
    
    copy_btn = ttk.Button(action_frame, text="📋 复制", command=self.on_copy_output)
    copy_btn.pack(side=LEFT)
    
    # 步骤9: 创建知乎发布UI
    self._build_zhihu_publish_ui(action_frame)
```

#### `_extract_explicit_opening()` 详解

这个方法从用户输入中提取明确指定的开头：

```python
def _extract_explicit_opening(self, requirement):
    """
    提取用户明确指定的开头
    
    支持的格式:
    - "以「这是我死去的第十年」为开头"
    - "以「这是我死去的第十年」开头"
    - "开头是「这是我死去的第十年」"
    - "开头用「这是我死去的第十年」"
    - "开头「这是我死去的第十年」"
    - "以这是我死去的第十年为开头"
    - "开头是这是我死去的第十年"
    
    参数:
        requirement: 用户输入的创作需求
    
    返回:
        提取的开头字符串，如果没有则返回None
    """
    import re
    
    # 定义匹配模式列表
    patterns = [
        r'以[「"]([^「」""]+)[」"]为开头',      # "以「...」为开头"
        r'以[「"]([^「」""]+)[」"]开头',        # "以「...」开头"
        r'开头是[「"]([^「」""]+)[」"]',         # "开头是「...」"
        r'开头用[「"]([^「」""]+)[」"]',         # "开头用「...」"
        r'开头[「"]([^「」""]+)[」"]',           # "开头「...」"
        r'以([^为]+)为开头',                    # "以...为开头"（无引号）
        r'开头是([^，。]+)',                     # "开头是..."（无引号）
    ]
    
    # 遍历所有模式，找到第一个匹配
    for pattern in patterns:
        match = re.search(pattern, requirement)
        if match:
            opening = match.group(1).strip()
            # 清理可能的引号（防止有多层引号）
            opening = opening.strip('"\'「」""')
            return opening
    
    return None
```

**示例**:

```python
# 输入
requirement = "如何以「这是我死去的第十年」为开头，写一个故事？"

# 执行
opening = self._extract_explicit_opening(requirement)

# 返回
"这是我死去的第十年"
```

#### `_get_category_guidance()` 详解

根据故事类型返回特定的创作指导：

```python
def _get_category_guidance(self, category):
    """
    根据故事类型获取特定指导
    
    参数:
        category: 故事类型（爱情/悬疑/职场/成长/亲情）
    
    返回:
        类型特定的指导文本
    """
    category_map = {
        "爱情": (
            "【💕 爱情故事特别要求】\n"
            "• 必须甜美：让人感觉特别甜蜜、温暖、心动\n"
            "• 但不无脑：要有真实感、有冲突、有深度\n"
            "• 真实细节：\"我记得那时候\"、\"我记得那天\"、\"我记得那时候我的心跳\"\n"
            "• 真实情感：\"我当时真的心动了\"、\"说实话，我现在想起来还觉得甜\"\n\n"
        ),
        "悬疑": (
            "【🔍 悬疑/惊悚故事特别要求】\n"
            "• 必须惊悚：让人感觉特别害怕、紧张、恐惧\n"
            "• 真实感就是最好的恐怖：真实感会让读者更害怕，因为\"如果这是真的...\"\n"
            "• 真实细节：\"我当时真的吓到了\"、\"我那时候心跳特别快\"\n"
            "• 真实反应：\"我当时就愣住了\"、\"我当时都不知道该怎么办\"\n\n"
        ),
        # ... 其他类型
    }
    return category_map.get(category, "")
```

#### `_build_prompt()` 详解（核心方法）

这是构建完整用户Prompt的核心方法，包含所有创作要求：

```python
def _build_prompt(self, requirement, contexts, category, outline=""):
    """
    构建完整的用户Prompt
    
    参数:
        requirement: 用户输入的创作需求
        contexts: 检索到的参考故事列表
        category: 故事类型（爱情/悬疑/职场等）
        outline: 目录（如果有）
    
    返回:
        完整的Prompt字符串（约2000-3000字）
    
    构建过程:
        1. 格式化参考故事
        2. 格式化目录部分
        3. 检测用户明确指定的开头
        4. 获取类型特定指导
        5. 构建RAG指导文本
        6. 组合完整的prompt
    """
    
    # 步骤1: 格式化参考故事
    ctx = "\n\n".join(f"【参考故事{i+1}】\n{c}" for i, c in enumerate(contexts))
    
    # 步骤2: 格式化目录部分
    outline_part = ("\n\n请严格参照下述目录完成写作：\n" + outline.strip()) if outline else ""
    
    # 步骤3: 获取风格设置
    style_part = self.style.get().strip()
    
    # 步骤4: 计算字数范围
    target = self.target_chars.get()
    min_chars = int(target * 0.9)
    max_chars = int(target * 1.1)
    
    # 步骤5: 检测用户是否明确指定了开头
    explicit_opening = self._extract_explicit_opening(requirement)
    
    # 步骤6: 根据故事类型生成针对性要求
    category_guidance = self._get_category_guidance(category)
    
    # 步骤7: 判断是否使用项目故事库
    use_project_stories = self.use_project_stories.get()
    
    # 步骤8: 构建RAG指导文本
    rag_guidance = ""
    if contexts:
        if use_project_stories:
            rag_guidance = """
【🎯 RAG增强创作指导】
以下是系统从你的过往优秀故事中检索到的相关片段...
"""
        else:
            rag_guidance = """
【📚 参考资料使用指导】
以下是检索到的相关资料，请作为创作参考...
"""
    
    # 步骤9: 构建完整的prompt（使用列表然后join）
    parts = [
        "🚨🚨🚨 **强制要求：你必须像在跟最好的朋友分享你的亲身经历一样写这个故事！** 🚨🚨🚨\n\n",
    ]
    
    # 步骤10: 如果用户明确指定了开头，优先使用用户指定的开头
    if explicit_opening:
        parts.append(
            f"🎯🎯🎯 **用户明确指定的开头（最高优先级！必须严格遵守！）** 🎯🎯🎯\n"
            f"用户明确要求：故事必须以以下内容开头：\n"
            f"【{explicit_opening}】\n\n"
            f"⚠️ 重要：\n"
            f"1. 故事的第一句话必须是：{explicit_opening}\n"
            f"2. 不能添加任何前缀，不能修改这句话\n"
            f"3. 这是用户明确要求的，优先级高于所有其他规则\n"
            f"4. 在这句话之后，再按照下面的要求继续写作\n\n"
        )
    
    # 步骤11: 添加核心目标
    parts.extend([
        "🎯 **核心目标**：像**用户亲身经历写出来的**，不是创作出来的小说。\n"
        "   • 读者要感觉：\"这是他的真实经历，不是编的\"\n"
        "   • 语言要像：真实的人在回忆和讲述自己的经历\n"
        "   • 细节要像：只有亲身经历的人才有的细节\n"
        "   • 情感要像：真实经历过的人才会有的反应\n\n",
    ])
    
    # 步骤12: 添加开头要求（如果没有明确指定）
    if not explicit_opening:
        parts.append(
            "⚠️⚠️⚠️ **开头的绝对要求（必须严格遵守！）** ⚠️⚠️⚠️\n"
            "1. **开头必须符合故事的时代背景**：\n"
            "   ❌ 如果故事发生在70年代、80年代等没有手机的年代，绝对不能用手机相关开头！\n"
            "   ✅ 只有现代城市故事才可以用手机相关开头，且不能千篇一律！\n"
            "2. **开头必须自然、多样、独特，绝对不能千篇一律**：\n"
            "   ❌ 禁止每次都用同一个开头模式\n"
            "   ✅ 必须在以下方式中随机选择...\n"
        )
    
    # 步骤13: 添加核心原则
    parts.extend([
        "⚠️ **核心原则（必须严格遵守）**：\n",
        "1. **这是你的亲身经历**：写的时候要问：如果这件事真的发生在我身上，我会怎么跟朋友说？\n",
        "2. **禁止比喻和文学化**：不能用\"像...一样\"、\"飘得像血\"等\n",
        "3. **必须像亲身经历**：记忆模糊、真实时间感、真实情感、真实细节\n",
        "4. **必须口语化**：多用\"说实话\"、\"真的\"（每300字至少用1次）\n",
        "5. **必须简单直接**：\"头发很长\"而不是\"长发垂到腰际\"\n",
        "6. **对话必须短**：\"这什么情况？\"而不是\"这到底是什么情况？\"\n\n",
    ])
    
    # 步骤14: 添加任务要求
    parts.extend([
        "═══════════════════════════════════════\n",
        "🎯 **任务**：用第一人称分享一个真实的故事，像在跟朋友聊天\n",
        "═══════════════════════════════════════\n\n",
        "【核心要求】\n",
        f"1. **字数要求（强制）**：必须写足 {min_chars}-{max_chars} 字，目标 {target} 字\n",
        f"2. **种类**：{category}\n",
        f"3. **风格倾向**：{style_part}\n",
        f"4. **创作主题/需求**：{requirement}\n\n",
    ])
    
    # 步骤15: 添加类型特定指导
    if category_guidance:
        parts.append(f"{category_guidance}\n")
    
    # 步骤16: 添加目录（如果有）
    if outline_part:
        parts.append(f"{outline_part}\n\n")
    
    # 步骤17: 添加RAG指导
    if rag_guidance:
        parts.append(f"{rag_guidance}\n")
    
    # 步骤18: 添加参考故事
    if ctx:
        parts.append(f"【参考故事】\n{ctx}\n\n")
    
    # 步骤19: 添加最后提醒
    parts.append("🚨 **最后提醒（必须严格遵守！）**：\n")
    if explicit_opening:
        parts.append(
            f"1. **最高优先级：故事的第一句话必须是：{explicit_opening}（用户明确要求，必须严格遵守！）**\n"
            "2. 这是你的亲身经历！写的时候要问：如果这件事真的发生在我身上，我会怎么跟朋友说？\n"
            "3. 写每一句话前都要问：这句话我会说给朋友听吗？如果不会，改！\n"
        )
    else:
        parts.append(
            "1. **开头必须符合故事的时代背景！**如果故事发生在70年代/80年代/乡村/古代等，绝对不能用手机相关开头！\n"
            "2. **开头绝对不能千篇一律！**每次都要用不同的开头方式！\n"
            "3. 这是你的亲身经历！写的时候要问：如果这件事真的发生在我身上，我会怎么跟朋友说？\n"
        )
    
    # 步骤20: 组合完整的prompt
    return "".join(parts)
```

**Prompt长度**: 通常2000-3000字，包含详细的创作要求、禁止项、示例等

**Prompt结构**:

```
1. 强制要求（强调亲身经历）
2. 用户明确指定的开头（如果有）
3. 核心目标
4. 开头要求（如果没有明确指定）
5. 核心原则（6条）
6. 任务要求（字数、种类、风格、主题）
7. 类型特定指导（如果有）
8. 目录（如果有）
9. RAG指导（如果有）
10. 参考故事（如果有）
11. 最后提醒
```

### 2. StoryGeneratorMixin

#### `on_generate()` 详解

这是故事生成的主入口，处理完整的生成流程：

```python
def on_generate(self) -> None:
    """生成故事主入口"""
    
    # 步骤1: 获取用户输入
    query = self._get_prompt_content()
    if not query:
        messagebox.showwarning("提示", "请先输入创作需求/主题")
        return
    
    # 步骤2: 获取选中的API配置
    selected_api = self.story_gen_api.get()
    if selected_api not in self.api_presets:
        messagebox.showerror("错误", f"未找到API预设: {selected_api}")
        return
    
    api_config = self.api_presets[selected_api]
    api_key = _sanitize(api_config.get("key", ""))
    if not api_key:
        messagebox.showwarning("提示", f"API Key 为空")
        return
    
    # 步骤3: 检查是否使用项目故事库
    use_project_stories = self.use_project_stories.get()
    
    # 步骤4: 如果启用了项目故事库，确保不使用model_only模式
    if use_project_stories and self.model_only.get():
        self.model_only.set(False)
    
    # 步骤5: 检查是否仅使用模型（无RAG）
    if self.model_only.get():
        self._generate_model_only(query)
        return
    
    # 步骤6: 检查知识库索引是否存在
    index_path = Path(self.index_dir.get()) / "kb.index"
    if not index_path.exists():
        if messagebox.askyesno("提示", "未找到索引，是否现在构建？"):
            need_build = True
        else:
            return
    
    # 步骤7: 启动后台线程执行生成任务
    def task():
        # 这个函数在后台线程中执行
        # ... 详见下方完整流程
    
    threading.Thread(target=task, daemon=True).start()
```

#### 后台任务执行流程

```python
def task():
    try:
        # 步骤1: 延迟导入知识库模块
        from src.kb.ingest import KnowledgeBaseIngestor, IngestConfig
        from src.kb.search import KnowledgeBaseSearcher, SearchConfig
        
        # 步骤2: 设置UI状态（使用after()确保线程安全）
        self.after(0, lambda: self.set_busy(True))
        self.after(0, lambda: self.status.set("使用 {api_name} 检索素材并生成正文中..."))
        
        # 步骤3: 构建知识库索引（如果需要）
        if need_build:
            cfg = IngestConfig(
                data_root=Path(self.data_dir.get()),
                index_dir=Path(self.index_dir.get())
            )
            KnowledgeBaseIngestor(cfg).build()
        
        # 步骤4: 检索相关素材
        searcher = KnowledgeBaseSearcher(
            SearchConfig(
                index_dir=Path(self.index_dir.get()),
                top_k=self.top_k.get()
            )
        )
        results = searcher.search(query, self.top_k.get())
        contexts = [c for c, _s, _m in results]
        
        # 步骤5: 创建API客户端
        client = DeepSeekClient(
            api_key=api_key,
            base_url=_sanitize(api_config.get("base_url", "")),
            model=_sanitize(api_config.get("model", "")),
        )
        
        # 步骤6: 清空输出区域
        self.after(0, lambda: self.output.delete("1.0", END))
        time.sleep(0.05)
        
        # 步骤7: 检查是否需要分段生成
        target_chars = self.target_chars.get()
        parsed_sections = self._parse_outline_sections(self.current_outline) if self.current_outline else []
        
        # 如果字数 > 8000 且有目录，则分段生成
        if target_chars > 8000 and parsed_sections:
            section_titles = [s['title'] for s in parsed_sections]
            self._generate_in_sections(client, query, contexts, section_titles, target_chars)
        else:
            # 步骤8: 一次性生成
            
            # 构建系统提示词
            system_prompt = self._build_system_prompt(...)
            
            # 构建用户提示词
            prompt = self._build_prompt(query, contexts, self.category.get(), self.current_outline)
            
            # 步骤9: 流式生成（打字机效果）
            for delta in client.stream([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ], temperature=self.temperature.get(), max_tokens=int(target_chars*2.5)):
                # 使用after()在主线程更新UI，实现线程安全的打字机效果
                self.after(0, lambda text=delta: self._insert_text_safe(text))
        
        # 步骤10: 生成完成
        self.after(0, lambda: self.status.set("生成完成"))
        self.after(100, lambda: self._auto_save_to_project())
        
    except Exception as e:
        # 错误处理
        error_msg = "生成出错:\n" + traceback.format_exc() + "\n"
        self.after(0, lambda msg=error_msg: self.output.insert(END, msg))
        self.after(0, lambda err=str(e): messagebox.showerror("错误", err))
    finally:
        self.after(0, lambda: self.set_busy(False))
```

#### `_insert_text_safe()` 详解

线程安全的文本插入方法：

```python
def _insert_text_safe(self, text: str) -> None:
    """
    线程安全地插入文本到output，实现打字机效果
    
    参数:
        text: 要插入的文本片段
    
    注意:
        - 这个方法在主线程中调用（通过after()）
        - 确保UI更新是线程安全的
    """
    try:
        self.output.insert(END, text)
        self.output.see(END)  # 自动滚动到底部
        self.update_idletasks()  # 更新UI
    except Exception as e:
        # 静默处理错误，避免中断生成
        pass
```

### 3. OutlineGeneratorMixin

#### `on_generate_outline()` 详解

生成目录的主入口：

```python
def on_generate_outline(self) -> None:
    """生成目录"""
    
    # 步骤1: 获取用户输入
    requirement = self._get_prompt_content()
    if not requirement:
        messagebox.showwarning("提示", "请先输入创作需求/主题")
        return
    
    # 步骤2: 获取选中的目录生成API配置
    selected_api = self.outline_gen_api.get()
    api_config = self.api_presets[selected_api]
    api_key = _sanitize(api_config.get("key", ""))
    
    # 步骤3: 检查是否仅使用模型
    if self.model_only.get():
        self._generate_outline_model_only(requirement)
        return
    
    # 步骤4: 检查知识库索引
    need_build = False
    index_path = Path(self.index_dir.get()) / "kb.index"
    if not index_path.exists():
        if messagebox.askyesno("提示", "未找到索引，是否现在构建？"):
            need_build = True
        else:
            return
    
    # 步骤5: 启动后台任务
    def task():
        try:
            # 延迟导入
            from src.kb.ingest import KnowledgeBaseIngestor, IngestConfig
            from src.kb.search import KnowledgeBaseSearcher, SearchConfig
            
            # 设置状态
            self.set_busy(True)
            self.status.set(f"使用 {selected_api} 检索素材并生成目录中...")
            
            # 构建索引（如果需要）
            if need_build:
                cfg = IngestConfig(
                    data_root=Path(self.data_dir.get()),
                    index_dir=Path(self.index_dir.get())
                )
                KnowledgeBaseIngestor(cfg).build()
            
            # 检索相关素材
            searcher = KnowledgeBaseSearcher(
                SearchConfig(
                    index_dir=Path(self.index_dir.get()),
                    top_k=self.top_k.get()
                )
            )
            results = searcher.search(requirement, self.top_k.get())
            contexts = [c for c, _s, _m in results]
            
            # 创建API客户端
            client = DeepSeekClient(
                api_key=api_key,
                base_url=_sanitize(api_config.get("base_url", "")),
                model=_sanitize(api_config.get("model", "")),
            )
            
            # 构建目录Prompt
            outline_prompt = self._build_outline_prompt(requirement, contexts, self.category.get())
            
            # 清空输出区域
            self.after(0, lambda: self.output.delete("1.0", END))
            time.sleep(0.05)
            
            # 生成目录
            outline_text = client.chat([
                {"role": "system", "content": "你是资深知乎创作者与编辑。请先产出结构化目录，不要写正文。"},
                {"role": "user", "content": outline_prompt},
            ], temperature=max(0.4, self.temperature.get() - 0.2))
            
            # 保存目录
            self.current_outline = outline_text.strip()
            
            # 解析章节并更新选择器
            self.parsed_sections = self._parse_outline_sections(self.current_outline)
            self._update_section_selector()
            
            # 显示目录
            outline_content = f"{self.current_outline}\n\n"
            self.after(0, lambda content=outline_content: self.output.insert(END, content))
            self.after(0, lambda: self.status.set("目录已生成"))
            
        except Exception as e:
            # 错误处理
            error_msg = "生成目录出错:\n" + traceback.format_exc() + "\n"
            self.after(0, lambda msg=error_msg: self.output.insert(END, msg))
            self.after(0, lambda err=str(e): messagebox.showerror("错误", err))
        finally:
            self.after(0, lambda: self.set_busy(False))
    
    threading.Thread(target=task, daemon=True).start()
```

#### `_build_outline_prompt()` 详解

构建目录生成的Prompt：

```python
def _build_outline_prompt(self, requirement, contexts, category):
    """
    构建目录生成的Prompt
    
    参数:
        requirement: 用户输入的创作需求
        contexts: 检索到的参考故事列表
        category: 故事类型
    
    返回:
        目录Prompt字符串
    """
    ctx = "\n\n".join(f"【资料{i+1}】\n{c}" for i, c in enumerate(contexts))
    target_chars = self.target_chars.get()
    
    # 根据目标字数动态决定章节数
    if target_chars <= 3000:
        suggested_sections = "3-4"
    elif target_chars <= 8000:
        suggested_sections = "4-6"
    elif target_chars <= 15000:
        suggested_sections = "6-8"
    else:
        suggested_sections = "8-10"
    
    return (
        "基于资料，为知乎读者产出一个简洁的写作目录（仅目录，不要正文）。\n\n"
        "【核心要求】\n"
        f"- 只输出 {suggested_sections} 个主要章节标题，不要子标题、不要要点列表\n"
        "- 每个章节用数字编号（1. 2. 3. ...）\n"
        "- 章节名简短有力（5-10字），能体现故事发展\n"
        "- 结构要符合：开端 → 发展 → 高潮 → 结局\n"
        "- 不要写\"第一章\"、\"第二章\"，直接写章节内容主题\n\n"
        "【章节标题吸引力要求】\n"
        "- 每个章节标题都要有吸引力，包含冲突/悬念/情绪词\n"
        "- 避免平淡的描述性标题，要用能激起好奇心的标题\n"
        f"【创作信息】\n"
        f"- 主题/需求：{requirement}\n"
        f"- 种类：{category}\n"
        f"- 目标字数：{target_chars}字\n\n"
        f"【参考资料】\n{ctx if ctx else '无特定资料'}\n\n"
        "请直接输出章节列表，格式如下：\n"
        "1. 平安夜初遇\n"
        "2. 疯狂追求记\n"
        "3. 暧昧升温时\n"
        "4. 浪漫告白夜\n"
        "5. 终成眷属日"
    )
```

#### `_parse_outline_sections()` 详解

解析目录文本，提取章节信息：

```python
def _parse_outline_sections(self, outline):
    """
    解析目录文本，提取章节
    
    参数:
        outline: 目录文本（例如："1. 第一章\n2. 第二章\n..."）
    
    返回:
        章节列表，每个元素包含：
        - title: 章节标题
        - line: 原始行文本
    """
    sections = []
    lines = outline.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        # 匹配数字开头的章节
        if re.match(r'^\d+[\.\、\s]', line):
            # 提取章节标题
            title = re.sub(r'^\d+[\.\、\s]+', '', line).strip()
            if title:
                sections.append({
                    'title': title,
                    'line': line
                })
    
    return sections
```

**示例**:

```python
# 输入
outline = """
1. 平安夜初遇
2. 疯狂追求记
3. 暧昧升温时
"""

# 执行
sections = self._parse_outline_sections(outline)

# 返回
[
    {'title': '平安夜初遇', 'line': '1. 平安夜初遇'},
    {'title': '疯狂追求记', 'line': '2. 疯狂追求记'},
    {'title': '暧昧升温时', 'line': '3. 暧昧升温时'}
]
```

#### `_generate_in_sections()` 详解

分段生成长文本的实现：

```python
def _generate_in_sections(self, client, requirement, contexts, sections, target_chars) -> None:
    """
    分段生成长文本（线程安全版本）- 保持连贯性
    
    参数:
        client: API客户端
        requirement: 创作需求
        contexts: 检索到的参考故事
        sections: 章节标题列表
        target_chars: 目标总字数
    
    流程:
        1. 计算每章目标字数
        2. 逐章生成，保持连贯性
        3. 使用前文内容作为上下文
    """
    total_sections = len(sections)
    target_per_section = int(target_chars / total_sections)
    
    total_generated = 0
    previous_content = ""  # 存储前面章节的内容，保持连贯性
    
    for idx, section in enumerate(sections):
        # 更新状态
        chapter_num = idx + 1
        status_msg = f"生成第 {chapter_num}/{total_sections} 章..."
        self.after(0, lambda msg=status_msg: self.status.set(msg))
        
        # 计算本段需要的字数
        remaining_chars = target_chars - total_generated
        remaining_sections = total_sections - idx
        section_target = min(target_per_section + 500, int(remaining_chars / remaining_sections))
        
        # 输出章节标题
        chapter_title = f"【第 {chapter_num}/{total_sections} 章. {section}】\n\n"
        self.after(0, lambda title=chapter_title: self.output.insert(END, title))
        time.sleep(0.05)
        
        # 构建章节Prompt（传入前文内容以保持连贯性）
        section_prompt = self._build_section_prompt(
            requirement, section, contexts, section_target, 
            chapter_num, total_sections, previous_content
        )
        
        # 使用流式输出实现打字机效果
        section_text = ""
        for delta in client.stream([
            {"role": "system", "content": "你是2024年的知乎爆款故事作者..."},
            {"role": "user", "content": section_prompt},
        ], temperature=self.temperature.get()):
            section_text += delta
            # 线程安全的打字机效果
            self.after(0, lambda text=delta: self._insert_text_safe(text))
        
        # 保存当前章节内容到前文记录（用于下一章保持连贯性）
        previous_content += section_text + "\n\n"
        
        # 章节之间添加空行
        self.after(0, lambda: self.output.insert(END, "\n\n"))
        time.sleep(0.05)
        
        # 统计字数
        section_chars = len(section_text)
        total_generated += section_chars
        
        # 休息一下避免触发限流
        if idx < total_sections - 1:
            time.sleep(0.5)
    
    # 更新完成状态
    final_msg = f"生成完成！总字数：{total_generated} 字"
    self.after(0, lambda msg=final_msg: self.status.set(msg))
    self.after(100, lambda: self._auto_save_to_project())
```

#### `_build_section_prompt()` 详解

构建章节生成的Prompt（包含连贯性要求）：

```python
def _build_section_prompt(self, requirement, section_title, contexts, target_chars, current_num, total_num, previous_content="") -> str:
    """
    构建章节生成的优化提示词（保持连贯性）
    
    参数:
        requirement: 创作需求
        section_title: 章节标题
        contexts: 检索到的参考故事
        target_chars: 章节目标字数
        current_num: 当前章节编号
        total_num: 总章节数
        previous_content: 前文内容（用于保持连贯性）
    
    返回:
        章节Prompt字符串（约1500-2000字）
    """
    ctx = "\n\n".join(f"【资料{i+1}】\n{c}" for i, c in enumerate(contexts)) if contexts else ""
    
    # 计算字数范围
    min_chars = int(target_chars * 0.85)
    max_chars = int(target_chars * 1.15)
    
    # 准备前文摘要（只取最后1500字，避免token过多）
    previous_summary = ""
    if previous_content and current_num > 1:
        prev_text = previous_content.strip()
        if len(prev_text) > 1500:
            prev_text = "..." + prev_text[-1500:]
        previous_summary = f"""
【前文内容摘要】（请仔细阅读，保持连贯！）
{prev_text}

⚠️ **连贯性要求**：
✓ 人物性格、说话方式必须与前文一致
✓ 情节发展要自然承接前文，不能突兀
✓ 已经铺垫的线索要记得呼应
✓ 语气、叙事风格要统一
"""
    
    # 根据位置定制提示
    position_hint = ""
    if current_num == 1:
        position_hint = """
【开篇要求】（极其重要！）
✓ 必须用一个吸引人的场景或冲突开场
✓ 前100字就要制造悬念或冲突，抓住读者
"""
    elif current_num == total_num:
        position_hint = """
【收尾要求】
✓ 情节要有结局，不要留太多悬念
✓ 情感要升华，给读者回味
"""
    else:
        position_hint = f"""
【中段要求】（第 {current_num}/{total_num} 部分）
✓ 本节必须有新的冲突或转折，推进情节
"""
    
    return (
        f"你是2024年知乎爆款故事作者，正在创作第 {current_num}/{total_num} 章...\n\n"
        f"{previous_summary}\n"
        f"【本章要求】\n"
        f"1. **字数**：必须写足 {min_chars}-{max_chars} 字，目标 {target_chars} 字\n"
        f"2. **章节主题**：{section_title}\n"
        f"3. **整体主题**：{requirement}\n\n"
        f"{position_hint}\n"
        f"{f'【参考资料】\n{ctx}\n' if ctx else ''}"
        f"现在开始创作！"
    )
```

### 4. InputCacheMixin

#### `_save_input_cache()` 详解

保存用户输入的缓存：

```python
def _save_input_cache(self, delay=True):
    """
    保存输入缓存
    
    参数:
        delay: 是否延迟保存（避免频繁写文件）
    
    延迟保存机制:
        - 用户输入时，不立即保存
        - 等待2秒，如果用户继续输入，取消之前的保存
        - 2秒内没有新输入，才真正保存
    """
    if delay:
        # 取消之前的计时器
        if self._save_timer:
            self.after_cancel(self._save_timer)
        # 设置新的延迟保存（2秒后）
        self._save_timer = self.after(2000, lambda: self._save_input_cache(delay=False))
        return
    
    try:
        # 获取当前输入
        cache = {}
        
        # 保存创作需求（检查是否是占位符）
        if hasattr(self, 'prompt_text'):
            content = self.prompt_text.get("1.0", "end-1c").strip()
            is_placeholder = False
            if content:
                tags = self.prompt_text.tag_names("1.0")
                if "placeholder" in tags:
                    is_placeholder = True
                # 检查常见占位符文本
                placeholder_texts = ["例如：", "📝 请详细描述你的故事创意", ...]
                for placeholder in placeholder_texts:
                    if placeholder in content and len(content) < 200:
                        is_placeholder = True
                        break
            
            # 只保存非占位符内容
            if content and not is_placeholder:
                cache['requirement'] = content
        
        # 保存风格、种类、字数
        if hasattr(self, 'entry_style'):
            style = self.entry_style.get().strip()
            if style:
                cache['style'] = style
        
        if hasattr(self, 'category'):
            cache['category'] = self.category.get()
        
        if hasattr(self, 'target_chars'):
            cache['target_chars'] = self.target_chars.get()
        
        # 写入文件
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.warning(f"保存输入缓存失败: {e}")
```

#### `_load_input_cache()` 详解

加载输入缓存并恢复到UI：

```python
def _load_input_cache(self):
    """
    加载输入缓存并恢复到UI
    
    恢复内容:
        - 创作需求（如果存在且不是占位符）
        - 风格（如果当前是默认值）
        - 种类
        - 字数
    """
    try:
        if not hasattr(self, 'cache_file') or not self.cache_file.exists():
            return
        
        with open(self.cache_file, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        
        # 恢复创作需求
        if 'requirement' in cache and cache['requirement']:
            if hasattr(self, 'prompt_text'):
                self.prompt_text.delete("1.0", END)
                self.prompt_text.insert("1.0", cache['requirement'])
                self.prompt_text.tag_remove("placeholder", "1.0", "end")
        
        # 恢复风格（只有当前是默认值时才恢复）
        if 'style' in cache and cache['style']:
            current_style = self.style.get()
            if current_style == "情感起伏/反转/细节描写/有画面感/口语化":
                if hasattr(self, 'entry_style'):
                    self.entry_style.delete(0, END)
                    self.entry_style.insert(0, cache['style'])
        
        # 恢复种类和字数
        if 'category' in cache and cache['category']:
            try:
                self.category.set(cache['category'])
            except:
                pass
        
        if 'target_chars' in cache and cache['target_chars']:
            try:
                self.target_chars.set(cache['target_chars'])
            except:
                pass
        
        logger.info("已恢复上次输入内容")
        
    except Exception as e:
        logger.warning(f"加载输入缓存失败: {e}")
```

### 5. StoryConfigMixin

#### `on_test_story_api()` 详解

测试故事生成API的可用性：

```python
def on_test_story_api(self) -> None:
    """测试故事生成API（输出到配置页面的测试日志）"""
    try:
        self.set_busy(True)
        self.status.set("测试故事生成 API 中...")
        
        # 确保使用故事配置页面的日志框
        if not hasattr(self, 'story_test_log'):
            messagebox.showwarning("提示", "请先切换到【故事生成 → 配置】标签页")
            return
        
        log_widget = self.story_test_log
        log_widget.delete("1.0", END)
        
        # 获取配置
        key = _sanitize(self.api_key.get())
        base = _sanitize(self.base_url.get())
        model = _sanitize(self.model.get()) or "deepseek-chat"
        
        # 测试多个可能的base_url
        candidates = []
        candidates.append(base.rstrip("/"))
        if base.rstrip("/").endswith("/v1"):
            candidates.append(base.rstrip("/")[:-3])
        else:
            candidates.append(base.rstrip("/") + "/v1")
        
        # 逐个测试
        for i, b in enumerate(candidates, 1):
            log_widget.insert(END, f"\n[{i}/{len(candidates)}] 测试: {b}\n")
            log_widget.update()
            
            ok, msg = _try_chat(key, b, model)
            
            if ok:
                log_widget.insert(END, f"✅ 成功: {msg}\n")
                self.base_url.set(b)
                messagebox.showinfo("测试成功", f"故事生成 API 可用\n{b}")
                return
            else:
                log_widget.insert(END, f"❌ 失败: {msg}\n")
        
        # 所有尝试都失败
        messagebox.showerror("API 错误", "故事API鉴权失败")
        
    except Exception as e:
        # 错误处理
        messagebox.showerror("API 错误", f"测试时发生异常:\n{str(e)}")
    finally:
        self.set_busy(False)
```

### 6. ZhihuPublisherMixin

#### `_on_generate_zhihu_title()` 详解

使用AI生成文章标题：

```python
def _on_generate_zhihu_title(self) -> None:
    """使用AI生成文章标题"""
    
    # 步骤1: 获取故事内容
    raw_story_text = self.output.get("1.0", END).strip()
    if not raw_story_text or len(raw_story_text) < 100:
        messagebox.showwarning("提示", "请先生成故事内容")
        return
    
    # 步骤2: 提取纯净的故事内容
    from src.utils.story_extractor import StoryExtractor
    story_text = StoryExtractor.extract_pure_story(raw_story_text)
    
    # 步骤3: 获取API配置
    selected_api = self.story_gen_api.get()
    api_config = self.api_presets[selected_api]
    api_key = _sanitize(api_config.get("key", ""))
    
    # 步骤4: 禁用按钮
    self.zhihu_publish_btn.config(state="disabled")
    self.zhihu_progress_label.config(text="正在生成标题...")
    
    def generate_title_task():
        try:
            # 创建API客户端
            client = DeepSeekClient(
                api_key=api_key,
                base_url=_sanitize(api_config.get("base_url", "")),
                model=_sanitize(api_config.get("model", "")),
            )
            
            # 提取故事前800字作为摘要
            summary = story_text[:800]
            
            # 系统提示词
            system_prompt = """你是知乎创作者，擅长写简洁、精准的标题。
你的标题简单但能直通故事要点或精髓，一句话抓住故事的核心。"""
            
            # 用户提示词
            user_prompt = f"""为以下故事生成一个简短、精准的标题。

核心要求：
1. **简单但直通要点** - 10-15字以内，但要抓住故事的核心/精髓
2. **直通故事要点** - 不要流于表面，要体现故事最核心的点或精髓
3. **精准** - 一句话说清楚故事主题，不要啰嗦
4. **真实** - 不夸张、不煽情，贴合故事内容

✅ 好的标题示例：
"一支520烟，毁了我三年"
"我妈给我打电话，说我爸不见了"
"我在平安夜对他说：让我追你"

❌ 不好的标题：
"从班级角落的受气包到职场精英的完整蜕变之路"  ← 太长太啰嗦
"我的校园往事"  ← 太泛泛，没有抓住故事要点

故事内容：
{summary}

请生成一个10-15字的标题，要求简单但能直通故事要点或精髓："""
            
            # 生成标题
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            title = client.chat(messages, temperature=0.5).strip()
            
            # 移除可能的引号
            title = title.strip('"\'「」『』""''')
            
            # 更新UI
            self.after(0, lambda: self.zhihu_title_var.set(title))
            self.after(0, lambda: self.zhihu_progress_label.config(text="✅ 标题生成完成"))
            self.after(0, lambda: messagebox.showinfo("成功", f"标题已生成:\n\n{title}"))
            
        except Exception as e:
            error_msg = f"生成标题失败: {str(e)}"
            self.after(0, lambda: messagebox.showerror("错误", error_msg))
        finally:
            self.after(0, lambda: self.zhihu_publish_btn.config(state="normal"))
    
    threading.Thread(target=generate_title_task, daemon=True).start()
```

#### `_on_publish_to_zhihu()` 详解

发布到知乎的完整流程：

```python
def _on_publish_to_zhihu(self) -> None:
    """发布到知乎"""
    
    # 步骤1: 获取标题和内容
    title = self.zhihu_title_var.get().strip()
    raw_content = self.output.get("1.0", END).strip()
    
    # 步骤2: 提取纯净的故事内容
    from src.utils.story_extractor import StoryExtractor
    content = StoryExtractor.extract_pure_story(raw_content)
    
    # 步骤3: 显示预览窗口（用户确认）
    preview_window = tk.Toplevel(self)
    # ... 构建预览窗口UI ...
    
    # 步骤4: 等待用户确认
    self.wait_window(preview_window)
    
    # 步骤5: 检查是否安装了playwright
    try:
        import playwright
    except ImportError:
        messagebox.showerror("缺少依赖", "请安装 playwright")
        return
    
    # 步骤6: 启动发布任务
    def publish_task():
        try:
            from src.services.zhihu_publisher import publish_to_zhihu_sync
            
            # 进度回调
            def progress_callback(message: str):
                self.after(0, lambda msg=message: self.zhihu_progress_label.config(text=msg))
            
            # 执行发布
            success, result = publish_to_zhihu_sync(
                title=title,
                content=content,
                headless=self.zhihu_headless_var.get(),
                input_mode=input_mode,
                progress_callback=progress_callback
            )
            
            # 显示结果
            if success:
                if result.startswith("http"):
                    # 成功发布并获得链接
                    self.after(0, lambda: messagebox.showinfo("发布成功", f"文章已成功发布到知乎！\n\n链接: {result}"))
                    self.after(0, lambda: self.clipboard_append(result))
                else:
                    # 内容已填充，等待手动发布
                    self.after(0, lambda: messagebox.showinfo("内容已填充", f"{result}"))
        except Exception as e:
            error_msg = f"发布过程出错: {str(e)}"
            self.after(0, lambda: messagebox.showerror("错误", error_msg))
        finally:
            self.after(0, lambda: self.zhihu_publish_btn.config(state="normal"))
    
    threading.Thread(target=publish_task, daemon=True).start()
```

---

## 完整执行流程

### 故事生成完整流程

```
用户操作
  │
  ├─→ 点击"生成故事"按钮
  │   └─→ StoryGeneratorMixin.on_generate()
  │       │
  │       ├─→ 步骤1: 获取用户输入
  │       │   └─→ _get_prompt_content()
  │       │
  │       ├─→ 步骤2: 验证输入
  │       │   └─→ 检查是否为空
  │       │
  │       ├─→ 步骤3: 获取API配置
  │       │   └─→ story_gen_api.get()
  │       │   └─→ api_presets[selected_api]
  │       │
  │       ├─→ 步骤4: 检查是否使用项目故事库
  │       │   └─→ use_project_stories.get()
  │       │
  │       ├─→ 步骤5: 检查是否仅使用模型
  │       │   └─→ model_only.get()
  │       │       ├─→ True: _generate_model_only()
  │       │       └─→ False: 继续RAG流程
  │       │
  │       ├─→ 步骤6: 检查知识库索引
  │       │   └─→ 如果不存在，询问是否构建
  │       │
  │       └─→ 步骤7: 启动后台线程
  │           └─→ threading.Thread(target=task, daemon=True).start()
  │
  ├─→ 后台任务执行
  │   │
  │   ├─→ 步骤1: 延迟导入知识库模块
  │   │   └─→ from src.kb.ingest import ...
  │   │
  │   ├─→ 步骤2: 设置UI状态
  │   │   └─→ self.after(0, lambda: self.set_busy(True))
  │   │
  │   ├─→ 步骤3: 构建知识库索引（如果需要）
  │   │   └─→ KnowledgeBaseIngestor(cfg).build()
  │   │
  │   ├─→ 步骤4: 检索相关素材
  │   │   └─→ searcher.search(query, top_k)
  │   │       └─→ 返回 contexts 列表
  │   │
  │   ├─→ 步骤5: 创建API客户端
  │   │   └─→ DeepSeekClient(api_key, base_url, model)
  │   │
  │   ├─→ 步骤6: 清空输出区域
  │   │   └─→ self.after(0, lambda: self.output.delete("1.0", END))
  │   │
  │   ├─→ 步骤7: 检查是否需要分段生成
  │   │   ├─→ target_chars > 8000 且有目录: 分段生成
  │   │   └─→ 否则: 一次性生成
  │   │
  │   ├─→ 步骤8: 构建Prompt
  │   │   ├─→ 构建系统提示词
  │   │   └─→ 构建用户提示词（_build_prompt）
  │   │
  │   └─→ 步骤9: 流式生成
  │       └─→ client.stream([system, user], ...)
  │           └─→ 对每个delta:
  │               └─→ self.after(0, lambda: _insert_text_safe(delta))
  │
  └─→ 生成完成
      ├─→ 更新状态: "生成完成"
      └─→ 自动保存到项目
```

### 目录生成完整流程

```
用户操作
  │
  ├─→ 点击"生成目录"按钮
  │   └─→ OutlineGeneratorMixin.on_generate_outline()
  │       │
  │       ├─→ 步骤1: 获取用户输入
  │       ├─→ 步骤2: 获取API配置
  │       ├─→ 步骤3: 检查是否仅使用模型
  │       ├─→ 步骤4: 检查知识库索引
  │       └─→ 步骤5: 启动后台线程
  │
  ├─→ 后台任务执行
  │   │
  │   ├─→ 步骤1: 构建索引（如果需要）
  │   ├─→ 步骤2: 检索相关素材
  │   ├─→ 步骤3: 构建目录Prompt
  │   │   └─→ _build_outline_prompt()
  │   ├─→ 步骤4: 生成目录
  │   │   └─→ client.chat([system, user])
  │   ├─→ 步骤5: 解析目录
  │   │   └─→ _parse_outline_sections()
  │   └─→ 步骤6: 更新章节选择器
  │       └─→ _update_section_selector()
  │
  └─→ 显示目录
      └─→ self.output.insert(END, outline_content)
```

### 章节生成完整流程

```
用户操作
  │
  ├─→ 点击"生成章节"按钮
  │   └─→ OutlineGeneratorMixin.on_generate_section()
  │       │
  │       ├─→ 步骤1: 检查是否有目录
  │       ├─→ 步骤2: 获取选中的章节索引
  │       ├─→ 步骤3: 检查是否仅使用模型
  │       └─→ 步骤4: 启动生成任务
  │
  ├─→ 后台任务执行
  │   │
  │   ├─→ 步骤1: 检索相关素材（如果需要）
  │   ├─→ 步骤2: 获取已有内容（保持连贯性）
  │   │   └─→ self.output.get("1.0", END)
  │   ├─→ 步骤3: 构建章节Prompt
  │   │   └─→ _build_section_prompt(..., previous_content)
  │   ├─→ 步骤4: 插入章节标题
  │   ├─→ 步骤5: 流式生成章节内容
  │   └─→ 步骤6: 自动保存到项目
  │
  └─→ 章节生成完成
      └─→ 更新状态和字数统计
```

---

## Prompt构建详解

### 故事生成Prompt结构

```
1. 强制要求（强调亲身经历）
   └─→ "🚨🚨🚨 **强制要求：你必须像在跟最好的朋友分享你的亲身经历一样写这个故事！** 🚨🚨🚨"

2. 用户明确指定的开头（如果有）
   └─→ "🎯🎯🎯 **用户明确指定的开头（最高优先级！必须严格遵守！）** 🎯🎯🎯"

3. 核心目标
   └─→ "🎯 **核心目标**：像**用户亲身经历写出来的**，不是创作出来的小说。"

4. 开头要求（如果没有明确指定）
   └─→ "⚠️⚠️⚠️ **开头的绝对要求（必须严格遵守！）** ⚠️⚠️⚠️"
   ├─→ 时代背景要求
   └─→ 多样性要求

5. 核心原则（6条）
   ├─→ 这是你的亲身经历
   ├─→ 禁止比喻和文学化
   ├─→ 必须像亲身经历
   ├─→ 必须口语化
   ├─→ 必须简单直接
   └─→ 对话必须短

6. 任务要求
   ├─→ 字数要求
   ├─→ 种类
   ├─→ 风格倾向
   └─→ 创作主题/需求

7. 类型特定指导（如果有）
   └─→ _get_category_guidance(category)

8. 目录（如果有）
   └─→ outline_part

9. RAG指导（如果有）
   └─→ rag_guidance

10. 参考故事（如果有）
    └─→ contexts

11. 最后提醒
    └─→ 根据是否有明确开头，添加不同的提醒
```

### 目录生成Prompt结构

```
1. 核心要求
   ├─→ 章节数量（根据目标字数动态决定）
   ├─→ 章节编号格式
   ├─→ 章节名要求
   └─→ 结构要求

2. 章节标题吸引力要求
   ├─→ 必须包含冲突/悬念/情绪词
   └─→ 避免平淡的描述性标题

3. 创作信息
   ├─→ 主题/需求
   ├─→ 种类
   └─→ 目标字数

4. 参考资料（如果有）
   └─→ contexts

5. 格式示例
   └─→ 示例章节列表
```

### 章节生成Prompt结构

```
1. 角色设定
   └─→ "你是2024年知乎爆款故事作者..."

2. 前文内容摘要（如果有）
   └─→ previous_summary
   └─→ 连贯性要求

3. 本章要求
   ├─→ 字数要求
   ├─→ 章节主题
   └─→ 整体主题

4. 位置特定要求
   ├─→ 开篇要求（如果是第一章）
   ├─→ 收尾要求（如果是最后一章）
   └─→ 中段要求（如果是中间章节）

5. 现代文风格要求
   ├─→ 语言现代化
   ├─→ 节奏紧凑
   ├─→ 冲突频繁
   ├─→ 铺垫扎实
   └─→ 细节生动

6. 本章核心任务
   ├─→ 制造冲突转折
   ├─→ 扎实铺垫与反转
   ├─→ 细节生动有画面感
   └─→ 节奏控制

7. 写作规范
   ├─→ 语言现代化
   ├─→ 不写标题
   ├─→ Show不Tell
   ├─→ 纯文本
   └─→ 保持连贯

8. 风格对比示例
   ├─→ 90/00年代老土风格（别这么写）
   └─→ 2024现代风格（就这么写）

9. 参考资料（如果有）
   └─→ contexts

10. 特别强调
    └─→ 字数要求、禁止输出元信息等
```

---

## 目录生成详解

### `_build_outline_prompt()` 详细说明

这个方法根据目标字数动态决定章节数：

```python
# 根据目标字数动态决定章节数
if target_chars <= 3000:
    suggested_sections = "3-4"
elif target_chars <= 8000:
    suggested_sections = "4-6"
elif target_chars <= 15000:
    suggested_sections = "6-8"
else:
    suggested_sections = "8-10"
```

**逻辑说明**:
- 字数少（≤3000）：章节少（3-4章）
- 字数中等（3000-8000）：章节中等（4-6章）
- 字数多（8000-15000）：章节多（6-8章）
- 字数非常多（>15000）：章节很多（8-10章）

### 章节标题吸引力要求

Prompt中明确要求：

```python
"【章节标题吸引力要求】\n"
"- 每个章节标题都要有吸引力，包含冲突/悬念/情绪词\n"
"- 避免平淡的描述性标题，要用能激起好奇心的标题\n"
"- 示例对比：\n"
"  ❌ 差：\"平静的开端\"、\"意外降临\"、\"危机爆发\"（太常见）\n"
"  ✅ 好：\"平安夜初遇\"、\"疯狂追求记\"、\"浪漫告白夜\"（有画面感）\n"
"  ✅ 好：\"凌晨两点的医院\"、\"死者的照片\"、\"消失的真相\"（有悬念）\n"
```

---

## 分段生成详解

### 为什么要分段生成

1. **Token限制**: 一次性生成太长可能超出模型token限制
2. **连贯性**: 分段生成可以保持更好的连贯性（使用前文作为上下文）
3. **可控性**: 可以逐章检查、修改、重新生成

### 连贯性机制

```python
previous_content = ""  # 存储前面章节的内容

for idx, section in enumerate(sections):
    # 构建章节Prompt时传入前文内容
    section_prompt = self._build_section_prompt(
        requirement, section, contexts, section_target, 
        chapter_num, total_sections, previous_content  # ← 传入前文
    )
    
    # 生成章节内容
    section_text = ...
    
    # 保存当前章节内容到前文记录
    previous_content += section_text + "\n\n"  # ← 累积前文
```

**前文摘要机制**:

```python
# 只取最后1500字，避免token过多
if len(prev_text) > 1500:
    prev_text = "..." + prev_text[-1500:]
```

**连贯性要求**:

```python
previous_summary = f"""
【前文内容摘要】（请仔细阅读，保持连贯！）
{prev_text}

⚠️ **连贯性要求**：
✓ 人物性格、说话方式必须与前文一致
✓ 情节发展要自然承接前文，不能突兀
✓ 已经铺垫的线索要记得呼应
✓ 语气、叙事风格要统一
"""
```

### 字数分配机制

```python
# 计算每章目标字数
target_per_section = int(target_chars / total_sections)

for idx, section in enumerate(sections):
    # 动态计算本段需要的字数
    remaining_chars = target_chars - total_generated
    remaining_sections = total_sections - idx
    section_target = min(target_per_section + 500, int(remaining_chars / remaining_sections))
```

**逻辑说明**:
- 每章目标字数 = 总字数 / 章节数
- 最后一章的字数 = 剩余字数 / 剩余章节数
- 允许每章有±500字的浮动

---

## 知乎发布详解

### 标题生成流程

```
用户点击"AI生成标题"按钮
  │
  ├─→ ZhihuPublisherMixin._on_generate_zhihu_title()
  │   │
  │   ├─→ 步骤1: 获取故事内容
  │   │   └─→ self.output.get("1.0", END)
  │   │
  │   ├─→ 步骤2: 提取纯净的故事内容
  │   │   └─→ StoryExtractor.extract_pure_story()
  │   │
  │   ├─→ 步骤3: 提取前800字作为摘要
  │   │   └─→ summary = story_text[:800]
  │   │
  │   ├─→ 步骤4: 构建标题生成Prompt
  │   │   ├─→ 系统提示词: "你是知乎创作者..."
  │   │   └─→ 用户提示词: 包含要求、示例、故事摘要
  │   │
  │   ├─→ 步骤5: 调用API生成标题
  │   │   └─→ client.chat(messages, temperature=0.5)
  │   │
  │   ├─→ 步骤6: 清理标题（移除引号）
  │   │   └─→ title.strip('"\'「」『』""''')
  │   │
  │   └─→ 步骤7: 更新UI
  │       └─→ self.zhihu_title_var.set(title)
```

### 发布流程

```
用户点击"发布到知乎"按钮
  │
  ├─→ ZhihuPublisherMixin._on_publish_to_zhihu()
  │   │
  │   ├─→ 步骤1: 获取标题和内容
  │   │   ├─→ title = self.zhihu_title_var.get()
  │   │   └─→ raw_content = self.output.get("1.0", END)
  │   │
  │   ├─→ 步骤2: 提取纯净的故事内容
  │   │   └─→ StoryExtractor.extract_pure_story(raw_content)
  │   │
  │   ├─→ 步骤3: 显示预览窗口
  │   │   ├─→ 创建预览窗口（80%屏幕大小）
  │   │   ├─→ 显示标题（可编辑）
  │   │   ├─→ 显示内容（可编辑）
  │   │   ├─→ 选择输入模式（流式/粘贴）
  │   │   └─→ 确认/取消按钮
  │   │
  │   ├─→ 步骤4: 等待用户确认
  │   │   └─→ self.wait_window(preview_window)
  │   │
  │   ├─→ 步骤5: 检查依赖
  │   │   └─→ import playwright
  │   │
  │   └─→ 步骤6: 启动发布任务
  │       └─→ threading.Thread(target=publish_task, daemon=True).start()
  │
  ├─→ 发布任务执行
  │   │
  │   ├─→ 步骤1: 导入发布服务
  │   │   └─→ from src.services.zhihu_publisher import publish_to_zhihu_sync
  │   │
  │   ├─→ 步骤2: 创建进度回调
  │   │   └─→ progress_callback(message: str)
  │   │
  │   ├─→ 步骤3: 调用发布服务
  │   │   └─→ publish_to_zhihu_sync(
  │   │           title=title,
  │   │           content=content,
  │   │           headless=headless,
  │   │           input_mode=input_mode,
  │   │           progress_callback=progress_callback
  │   │       )
  │   │
  │   └─→ 步骤4: 显示结果
  │       ├─→ 成功: 显示链接，复制到剪贴板
  │       └─→ 失败: 显示错误信息
  │
  └─→ 发布完成
```

---

## 总结

故事生成模块是系统的核心功能，提供了：

1. **灵活的故事生成**：支持RAG增强、仅模型生成、分段生成
2. **智能的目录生成**：根据字数动态决定章节数，生成有吸引力的标题
3. **完整的章节管理**：支持逐章生成、连续生成、自定义生成
4. **便捷的知乎发布**：AI生成标题、内容预览、自动发布
5. **用户友好的缓存**：自动保存和恢复用户输入

每个功能都经过精心设计，确保用户体验和生成质量。

