# 服务模块详细技术文档

## 📋 目录

1. [模块概述](#模块概述)
2. [文件结构](#文件结构)
3. [核心服务详解](#核心服务详解)
4. [服务依赖关系](#服务依赖关系)

---

## 模块概述

### 功能定位

服务模块负责封装业务逻辑，提供可复用的服务：

1. **导演服务**: 提示词构建、分镜管理、人物管理、图像生成
2. **知乎服务**: 文章发布、浏览器管理、登录处理、话题提取
3. **业务逻辑**: 将复杂的业务逻辑封装为服务，便于复用和维护

### 模块位置

```
src/services/
├── __init__.py
│
├── director/                      # 导演模式服务
│   ├── __init__.py
│   ├── prompt_builder_service.py  # 提示词构建服务
│   ├── shot_manager_service.py     # 分镜管理服务
│   ├── character_service.py         # 人物管理服务
│   └── image_generator_service.py  # 图像生成服务
│
└── zhihu/                         # 知乎发布服务
    ├── __init__.py
    ├── article_publisher.py        # 文章发布器
    ├── browser_manager.py          # 浏览器管理器
    ├── login_handler.py             # 登录处理器
    └── topic_extractor.py           # 话题提取器
```

---

## 文件结构

### 1. prompt_builder_service.py

**职责**: 为不同API生成优化的提示词

**主要类**:
- `PromptBuilderService`: 提示词构建服务

**关键方法**:
- `build_shot_prompt()`: 为分镜构建提示词
- `_build_sd_prompt()`: 构建SD提示词（标签风格）
- `_build_openai_prompt()`: 构建OpenAI提示词（自然语言）
- `_build_hunyuan_prompt()`: 构建混元提示词（中文）

**文件大小**: 约500行

### 2. shot_manager_service.py

**职责**: 分镜的创建、修改、查询等操作

**主要类**:
- `ShotManagerService`: 分镜管理服务

**关键方法**:
- `add_shot()`: 添加分镜
- `get_shot()`: 根据编号获取分镜
- `get_shots_by_character()`: 获取包含指定人物的所有分镜
- `validate_shots()`: 验证分镜数据
- `reorder_shots()`: 重新排序分镜编号

**文件大小**: 约160行

### 3. character_service.py

**职责**: 人物数据的管理

**主要类**:
- `CharacterService`: 人物服务

**关键方法**:
- `add_character()`: 添加人物
- `get_character()`: 获取人物
- `save_characters_to_file()`: 保存人物数据到文件
- `load_characters_from_file()`: 从文件加载人物数据
- `validate_characters()`: 验证人物数据

**文件大小**: 约160行

### 4. image_generator_service.py

**职责**: 调用各种图片生成API

**主要类**:
- `ImageGeneratorService`: 图片生成服务

**关键方法**:
- `generate_shot_image()`: 生成分镜图片
- `_generate_with_sd()`: 使用SD生成
- `_generate_with_openai_compatible()`: 使用OpenAI兼容API生成

**文件大小**: 约170行

### 5. article_publisher.py

**职责**: 知乎文章发布的完整流程

**主要类**:
- `ArticlePublisher`: 文章发布器

**关键方法**:
- `publish_article()`: 发布文章到知乎
- `_navigate_to_editor()`: 导航到文章编辑器
- `_input_title_and_content()`: 输入标题和内容
- `_configure_publish_options()`: 设置发布选项

**文件大小**: 约780行

---

## 核心服务详解

### 1. PromptBuilderService类

#### 类定义

```python
class PromptBuilderService:
    """提示词构建服务"""
    
    def __init__(self):
        self.character_seed_map = {}  # 人物种子映射
        self.consistency_mode = "medium"  # 一致性模式: strong, medium, weak
```

#### `build_shot_prompt()` 详解

```python
def build_shot_prompt(
    self,
    shot: Shot,
    api_type: str,
    characters_data: Dict[str, Character] = None
) -> Tuple[str, str]:
    """
    为分镜构建提示词
    
    流程:
        1. 根据API类型选择构建方法
        2. 调用对应的构建函数
        3. 返回(正向提示词, 负向提示词)
    
    参数:
        shot: 分镜对象
        api_type: API类型 ('sd', 'openai', 'hunyuan')
        characters_data: 人物数据字典
    
    返回:
        (正向提示词, 负向提示词)
    """
    if api_type == "sd":
        return self._build_sd_prompt(shot, characters_data)
    elif api_type == "openai":
        return self._build_openai_prompt(shot, characters_data)
    elif api_type == "hunyuan":
        return self._build_hunyuan_prompt(shot, characters_data)
    else:
        return self._build_generic_prompt(shot, characters_data)
```

#### `_build_sd_prompt()` 详解

```python
def _build_sd_prompt(
    self,
    shot: Shot,
    characters_data: Optional[Dict[str, Character]] = None
) -> Tuple[str, str]:
    """
    构建Stable Diffusion提示词（标签风格）
    
    流程:
        1. 质量标签（masterpiece, best quality等）
        2. 人物描述（从character_details或characters_data获取）
        3. 场景描述（从shot的visual_description提取）
        4. 动作和表情（从shot的action和emotion提取）
        5. 镜头类型（从shot的shot_type提取）
        6. 组合提示词
        7. 构建负向提示词
    
    返回:
        (正向提示词, 负向提示词)
    """
    # === 质量标签 ===
    quality_tags = [
        "masterpiece", "best quality", "ultra detailed", "8k",
        "photorealistic", "cinematic lighting", "professional photography",
        "sharp focus", "highly detailed", "intricate details",
        "character consistency", "consistent character design", "same person"
    ]
    
    # === 人物描述 ===
    character_tags = []
    for char_name in shot.characters:
        char_tags = self._build_character_tags_for_sd(
            char_name,
            shot.get_character_detail(char_name),
            characters_data.get(char_name) if characters_data else None
        )
        if char_tags:
            character_tags.extend(char_tags)
    
    # === 场景描述 ===
    scene_tags = self._build_scene_tags_for_sd(shot)
    
    # === 动作和表情 ===
    action_tags = self._build_action_tags_for_sd(shot)
    
    # === 镜头类型 ===
    shot_type_tags = self._build_shot_type_tags_for_sd(shot)
    
    # === 组合提示词 ===
    positive_prompt = ", ".join(
        quality_tags +
        character_tags +
        action_tags +
        scene_tags +
        shot_type_tags
    )
    
    # === 负向提示词 ===
    negative_prompt = self._build_sd_negative_prompt(shot)
    
    return positive_prompt, negative_prompt
```

**关键点**:
- **标签风格**: SD使用标签风格的提示词（逗号分隔）
- **人物一致性**: 从character_details或characters_data获取人物信息
- **模块化构建**: 分别构建质量、人物、场景、动作等标签

### 2. ShotManagerService类

#### 类定义

```python
class ShotManagerService:
    """分镜管理服务"""
    
    def __init__(self):
        self.shots: List[Shot] = []
```

#### 关键方法详解

```python
def add_shot(self, shot: Shot):
    """添加分镜"""
    self.shots.append(shot)

def get_shot(self, shot_number: int) -> Optional[Shot]:
    """根据编号获取分镜"""
    for shot in self.shots:
        if shot.shot_number == shot_number:
            return shot
    return None

def get_shots_by_character(self, character_name: str) -> List[Shot]:
    """获取包含指定人物的所有分镜"""
    return [shot for shot in self.shots if shot.has_character(character_name)]

def validate_shots(self) -> List[str]:
    """验证分镜数据，返回错误信息列表"""
    errors = []
    
    # 检查分镜编号是否连续
    expected_number = 1
    for shot in sorted(self.shots, key=lambda s: s.shot_number):
        if shot.shot_number != expected_number:
            errors.append(f"分镜编号不连续：期望 {expected_number}，实际 {shot.shot_number}")
        expected_number += 1
    
    # 检查必要字段
    for shot in self.shots:
        if not shot.shot_type:
            errors.append(f"分镜 {shot.shot_number} 缺少镜头类型")
        if not shot.visual_description and not shot.scene_description:
            errors.append(f"分镜 {shot.shot_number} 缺少场景描述")
    
    return errors

def reorder_shots(self):
    """重新排序分镜编号"""
    self.shots.sort(key=lambda s: s.shot_number)
    for i, shot in enumerate(self.shots, 1):
        shot.shot_number = i
```

**关键点**:
- **简单管理**: 提供基本的CRUD操作
- **数据验证**: 验证分镜编号连续性和必要字段
- **查询功能**: 支持按人物、场景查询

### 3. CharacterService类

#### 类定义

```python
class CharacterService:
    """人物服务"""
    
    def __init__(self):
        self.characters: Dict[str, Character] = {}
```

#### 关键方法详解

```python
def add_character(self, character: Character):
    """添加人物"""
    self.characters[character.name] = character

def get_character(self, name: str) -> Optional[Character]:
    """获取人物"""
    return self.characters.get(name)

def save_characters_to_file(self, file_path: Path) -> bool:
    """保存人物数据到文件"""
    try:
        data = {
            'version': '1.0',
            'characters': {
                name: char.to_dict()
                for name, char in self.characters.items()
            }
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        logger.error(f"保存人物数据失败: {e}")
        return False

def load_characters_from_file(self, file_path: Path) -> bool:
    """从文件加载人物数据"""
    try:
        if not file_path.exists():
            return False
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        characters_data = data.get('characters', {})
        self.characters = {
            name: Character.from_dict(char_data)
            for name, char_data in characters_data.items()
        }
        
        return True
    except Exception as e:
        logger.error(f"加载人物数据失败: {e}")
        return False
```

**关键点**:
- **字典存储**: 使用字典存储，key为人物名称
- **持久化**: 支持保存和加载到文件
- **数据验证**: 提供验证方法

### 4. ImageGeneratorService类

#### 类定义

```python
class ImageGeneratorService:
    """图片生成服务"""
    
    def __init__(self):
        self.prompt_builder = PromptBuilderService()
```

#### `generate_shot_image()` 详解

```python
def generate_shot_image(
    self,
    shot: Shot,
    shot_variant: int,
    output_dir: Path,
    api_config: Dict[str, Any],
    characters_data: Dict[str, Character] = None,
    seed_offset: int = 0
) -> Optional[str]:
    """
    生成分镜图片
    
    流程:
        1. 检查provider类型
        2. 调用对应的生成方法
        3. 保存图片到output_dir
        4. 返回图片路径
    
    参数:
        shot: 分镜对象
        shot_variant: 变体编号
        output_dir: 输出目录
        api_config: API配置
        characters_data: 人物数据
        seed_offset: 种子偏移
    
    返回:
        生成的图片路径，失败返回None
    """
    try:
        provider = api_config.get("provider", "openai")
        
        if provider == "sd":
            return self._generate_with_sd(
                shot, shot_variant, output_dir, api_config,
                characters_data, seed_offset
            )
        else:
            return self._generate_with_openai_compatible(
                shot, shot_variant, output_dir, api_config,
                characters_data
            )
    
    except Exception as e:
        print(f"生成图片失败: {e}")
        import traceback
        traceback.print_exc()
        return None
```

**关键点**:
- **统一接口**: 提供统一的图片生成接口
- **多API支持**: 支持SD和OpenAI兼容API
- **错误处理**: 捕获异常并记录日志

### 5. ArticlePublisher类

#### 类定义

```python
class ArticlePublisher:
    """文章发布器 - 负责知乎文章发布的完整流程"""
    
    def __init__(self, page: Page):
        """
        初始化文章发布器
        
        参数:
            page: Playwright Page对象
        """
        self.page = page
```

#### `publish_article()` 详解

```python
async def publish_article(
    self,
    title: str,
    content: str,
    input_mode: str = "paste",
    progress_callback: Optional[Callable[[str], None]] = None
) -> tuple[bool, str]:
    """
    发布文章到知乎
    
    流程:
        1. 输入验证（标题、内容长度）
        2. 检查登录状态
        3. 进入编辑器
        4. 输入标题和内容
        5. 设置发布选项（话题、摘要等）
        6. 点击发布
        7. 等待发布完成
    
    参数:
        title: 文章标题
        content: 文章内容
        input_mode: 输入模式 ("paste"=快速粘贴, "stream"=流式输出)
        progress_callback: 进度回调函数
    
    返回:
        (是否成功, 错误信息或文章链接)
    """
    # 输入验证
    if not title or not title.strip():
        return False, "标题不能为空"
    
    if not content or not content.strip():
        return False, "内容不能为空"
    
    title = title.strip()
    content = content.strip()
    
    if len(title) > 100:
        return False, "标题过长（最多100字）"
    
    if len(content) < 100:
        return False, "内容过短（至少100字）"
    
    try:
        # 1. 检查登录状态
        if not await LoginHandler.check_login_status(self.page):
            if not await LoginHandler.wait_for_manual_login(self.page):
                return False, "登录超时或失败"
        
        # 2. 进入编辑器
        if not await self._navigate_to_editor(progress_callback):
            return False, "无法进入文章编辑器"
        
        # 3. 输入标题和内容
        if not await self._input_title_and_content(title, content, input_mode, progress_callback):
            return False, "输入标题或内容失败"
        
        # 4. 设置发布选项
        await self._configure_publish_options(title, content, progress_callback)
        
        # 5. 点击发布
        return await self._wait_for_publish_complete(progress_callback)
        
    except Exception as e:
        error_msg = f"发布过程出错: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg
```

**关键点**:
- **异步操作**: 使用async/await处理浏览器操作
- **进度回调**: 支持进度回调，实时更新状态
- **错误处理**: 详细的错误处理和日志记录
- **输入验证**: 验证标题和内容的长度和格式

---

## 服务依赖关系

```
PromptBuilderService
├── Shot (model)
└── Character (model)

ShotManagerService
└── Shot (model)

CharacterService
└── Character (model)

ImageGeneratorService
├── PromptBuilderService
├── Shot (model)
└── Character (model)

ArticlePublisher
├── LoginHandler
├── TopicExtractor
└── Playwright Page
```

---

## 总结

服务模块提供了封装良好的业务逻辑服务：

1. **导演服务**: 提示词构建、分镜管理、人物管理、图像生成
2. **知乎服务**: 文章发布、浏览器管理、登录处理、话题提取
3. **统一接口**: 提供统一的接口，便于调用和维护
4. **错误处理**: 详细的错误处理和日志记录

所有服务都经过精心设计，确保可复用性和可维护性。

