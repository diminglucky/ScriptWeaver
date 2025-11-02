# 图像生成模块详细技术文档

## 📋 目录

1. [模块概述](#模块概述)
2. [文件结构](#文件结构)
3. [核心组件详解](#核心组件详解)
4. [API客户端详解](#api客户端详解)
5. [完整执行流程](#完整执行流程)
6. [人物一致性机制](#人物一致性机制)

---

## 模块概述

### 功能定位

图像生成模块负责：

1. **人物照片生成**：生成不同角度、表情的人物照片
2. **分镜图片生成**：为导演模式生成分镜图片
3. **场景图片生成**：生成场景和背景图片
4. **多API支持**：支持OpenAI、Stable Diffusion、腾讯混元等多种API
5. **人物一致性**：确保同一人物在不同图片中保持一致

### 模块位置

```
src/
├── clients/                          # API客户端
│   ├── image_client.py                # OpenAI兼容API客户端
│   ├── sd_client.py                   # Stable Diffusion客户端
│   └── hunyuan_image_client.py        # 腾讯混元客户端
└── gui/mixins/
    ├── image_modules/                 # 图像生成模块
    │   ├── __init__.py                # ImageMixin主类
    │   ├── ui_main.py                 # 主界面构建
    │   ├── ui_setup.py                # 设置界面
    │   ├── ui_character.py             # 人物界面
    │   ├── handlers/                  # 事件处理器
    │   │   ├── character_photo_generator.py   # 人物照片生成器
    │   │   ├── character_photo_handler.py     # 人物照片事件处理
    │   │   ├── character_photo_preview.py     # 预览处理
    │   │   └── character_photo_saver.py       # 保存处理
    │   ├── char_description.py       # 人物描述生成
    │   ├── char_sheet.py              # 人物设定表
    │   ├── char_photo.py              # 人物照片UI
    │   ├── prompt_ops.py              # 提示词操作
    │   └── file_ops.py                # 文件操作
    └── director_modules/              # 导演模式（分镜图片生成）
        └── handlers/
            └── image_generation_handler.py    # 分镜图片生成处理
```

### 模块依赖关系

```
ImageMixin
├── OpenAIImageClient              # OpenAI兼容API
├── StableDiffusionClient         # SD本地API
├── HunyuanImageClient            # 腾讯混元API
├── CharacterPromptBuilder        # 提示词构建器
└── ProjectManager                # 项目管理
```

---

## 文件结构

### 1. image_client.py

**职责**: OpenAI兼容图像生成API客户端

**主要类**:
- `ImageResult`: 图像生成结果数据类
- `OpenAIImageClient`: OpenAI兼容API客户端

**关键方法**:
- `generate()`: 文本生成图片
- `generate_with_reference()`: 参考图生成图片（一致性）

**文件大小**: 178行

### 2. sd_client.py

**职责**: Stable Diffusion本地API客户端

**主要类**:
- `StableDiffusionClient`: SD WebUI API客户端

**关键方法**:
- `txt2img()`: 文本生成图片
- `img2img()`: 图片生成图片（一致性）

**文件大小**: 约300行

### 3. hunyuan_image_client.py

**职责**: 腾讯混元图像生成API客户端

**主要类**:
- `HunyuanImageResult`: 混元结果数据类
- `HunyuanImageClient`: 混元API客户端

**关键方法**:
- `generate()`: 生成图片

**文件大小**: 约230行

### 4. character_photo_generator.py

**职责**: 人物照片生成核心逻辑

**主要类**:
- `CharacterPhotoGenerator`: 人物照片生成器

**关键方法**:
- `generate_photo()`: 生成单张人物照片
- `_generate_with_hunyuan()`: 使用混元API生成
- `_generate_with_sd()`: 使用SD生成
- `_generate_with_openai()`: 使用OpenAI生成

**文件大小**: 350行

---

## 核心组件详解

### 1. CharacterPhotoGenerator类

#### 类定义

```python
class CharacterPhotoGenerator:
    """人物照片生成器 - 负责人物照片的生成逻辑"""
    
    @staticmethod
    def generate_photo(
        mixin_instance,
        character: Dict,
        angle: str,
        angle_name: str,
        expression: str,
        expression_name: str,
        style: str,
        extra_desc: str,
        variant_value: str,
        variant_mode: str,
        consistency_level: str,
        batch_type: str,
        generated_photos: List,
        current_index: int,
        total_count: int
    ) -> Optional[Image.Image]:
```

#### `generate_photo()` 详解

```python
def generate_photo(...) -> Optional[Image.Image]:
    """
    生成单张人物照片
    
    流程:
        1. 检查API配置
        2. 根据API类型选择生成方法
        3. 调用对应的生成函数
        4. 返回生成的图片
    
    参数:
        character: 人物信息字典 {name, description}
        angle: 视角（front/side/back）
        angle_name: 视角名称（正面/侧面/背面）
        expression: 表情（neutral/happy/sad等）
        expression_name: 表情名称
        style: 图片风格
        consistency_level: 一致性级别
        current_index: 当前生成索引（用于一致性）
        generated_photos: 已生成的照片列表
    """
    # 步骤1: 检查API配置
    img_api_type = mixin_instance.img_api_type.get()
    
    # 步骤2: 选择生成方法
    if img_api_type == "hunyuan":
        return _generate_with_hunyuan(...)
    else:
        provider = mixin_instance.img_api_presets.get(current_preset, {}).get("provider", "openai")
        if provider == "sd":
            return _generate_with_sd(...)
        else:
            return _generate_with_openai(...)
```

#### `_generate_with_sd()` 详解

```python
def _generate_with_sd(...) -> Optional[Image.Image]:
    """
    使用Stable Diffusion生成人物照片
    
    流程:
        1. 检查是否需要使用img2img（一致性）
        2. 构建提示词
        3. 优化提示词（标签化）
        4. 调用SD API生成
        5. 返回图片
    """
    # 步骤1: 检查是否需要img2img
    use_img2img = False
    reference_image = None
    
    if current_index > 1 and generated_photos and len(generated_photos) > 0:
        reference_image = generated_photos[0].get("image")
        if reference_image:
            use_img2img = True
            logger.info("使用第一张图片作为参考（强制一致性）")
    
    # 步骤2: 构建提示词
    if use_img2img:
        # img2img模式：简化描述，只保留视角和表情
        full_prompt = CharacterPromptBuilder.build_character_photo_prompt(
            description="",
            style=style,
            view_angle=angle,
            expression=expression,
            composition=composition,
            extra_details=f"{angle_name} view, {expression_name} expression",
            language="en",
            consistency_level="high",
            ...
        )
    else:
        # txt2img模式：完整描述
        full_prompt = CharacterPromptBuilder.build_character_photo_prompt(
            description=description,
            style=style,
            view_angle=angle,
            expression=expression,
            composition=composition,
            extra_details=extra_desc,
            language="en",
            variant=variant_value,
            variant_mode=variant_mode,
            consistency_level=consistency_level,
            api_type="sd"
        )
    
    # 步骤3: 优化提示词（标签化）
    full_prompt = CharacterPromptBuilder.optimize_for_api(full_prompt, "sd", 1000)
    
    # 步骤4: 调用SD API
    sd_client = StableDiffusionClient(base_url=sd_base_url)
    negative_prompt = CharacterPromptBuilder.get_negative_prompt_for_character("sd")
    
    if use_img2img:
        # img2img模式：使用参考图，denoising_strength=0.4
        images = sd_client.img2img(
            init_image=reference_image,
            prompt=full_prompt,
            negative_prompt=negative_prompt + ", " + consistency_negative,
            denoising_strength=0.4,  # 较低的重绘幅度，保持一致性
            width=1024,
            height=1024,
            steps=25,
            cfg_scale=8.5,
            sampler_name="Euler a"
        )
    else:
        # txt2img模式：生成基准图，使用固定seed
        import hashlib
        seed = int(hashlib.md5(character_name.encode()).hexdigest()[:8], 16)
        logger.info(f"固定 seed: {seed}")
        
        images = sd_client.txt2img(
            prompt=full_prompt,
            negative_prompt=negative_prompt,
            width=1024,
            height=1024,
            steps=20,
            cfg_scale=7.5,
            sampler_name="Euler a",
            seed=seed  # 固定seed确保一致性
        )
    
    # 步骤5: 返回图片
    if images:
        return images[0]
    else:
        raise RuntimeError("SD生成失败")
```

**关键点**:
- **一致性机制**: 第一张用txt2img生成基准图，后续用img2img基于基准图生成
- **固定seed**: txt2img时使用人物名称的MD5哈希作为seed，确保可复现
- **去噪强度**: img2img使用0.4的denoising_strength，平衡一致性和变化

#### `_generate_with_openai()` 详解

```python
def _generate_with_openai(...) -> Optional[Image.Image]:
    """
    使用OpenAI或兼容API生成人物照片
    
    流程:
        1. 构建自然语言提示词
        2. 优化提示词（自然语言）
        3. 调用API生成
        4. 返回图片
    """
    # 步骤1: 构建提示词
    full_prompt = CharacterPromptBuilder.build_character_photo_prompt(
        description=description,
        style=style,
        view_angle=angle,
        expression=expression,
        composition=composition,
        extra_details=extra_desc,
        language="en",
        variant=variant_value,
        variant_mode=variant_mode,
        consistency_level=consistency_level,
        api_type=current_api_type
    )
    
    # 步骤2: 优化提示词（自然语言）
    full_prompt = CharacterPromptBuilder.optimize_for_api(full_prompt, current_api_type, 1000)
    
    # 步骤3: 调用API
    client = OpenAIImageClient(api_key=api_key, base_url=base_url, model=model)
    results = client.generate(full_prompt, size="1024x1024")
    
    # 步骤4: 返回图片
    if results:
        return results[0].image
```

**关键点**:
- **自然语言提示词**: OpenAI API使用自然语言描述，而非标签
- **API兼容性**: 支持OpenAI和兼容OpenAI格式的API（如V-API）

#### `_generate_with_hunyuan()` 详解

```python
def _generate_with_hunyuan(...) -> Optional[Image.Image]:
    """
    使用腾讯混元API生成人物照片
    
    流程:
        1. 构建中文提示词
        2. 优化提示词（中文，限制长度）
        3. 调用混元API
        4. 返回图片
    """
    # 步骤1: 构建中文提示词
    full_prompt = CharacterPromptBuilder.build_character_photo_prompt(
        description=description,
        style=style,
        view_angle=angle,
        expression=expression,
        composition=composition,
        extra_details=extra_desc,
        language="zh",  # 中文提示词
        default_nationality="chinese",
        variant=variant_value,
        variant_mode=variant_mode,
        consistency_level=consistency_level,
        batch_type=batch_type
    )
    
    # 步骤2: 优化提示词（中文，限制256字符）
    full_prompt = CharacterPromptBuilder.optimize_for_api(full_prompt, "hunyuan", 256)
    
    # 步骤3: 调用混元API
    client = HunyuanImageClient(secret_id=secret_id, secret_key=secret_key)
    result = client.generate(
        prompt=full_prompt,
        resolution="1024:1024",
        style="201"  # 日系动漫风格
    )
    
    # 步骤4: 解码base64图片
    img_base64 = result["ResultImage"]
    img_data = base64.b64decode(img_base64)
    img = Image.open(BytesIO(img_data))
    return img
```

**关键点**:
- **中文提示词**: 混元API支持中文提示词
- **长度限制**: 提示词限制在256字符以内
- **风格编号**: 使用数字编号指定风格（201=日系动漫）

### 2. ImageGenerationHandler类（导演模式）

#### 类定义

```python
class ImageGenerationHandler:
    """图片生成事件处理器"""
    
    @staticmethod
    def handle_generate_selected_shot(mixin_instance) -> None:
        """处理生成选中分镜图片的事件"""
    
    @staticmethod
    def _generate_all_shots(mixin_instance) -> None:
        """生成所有分镜的图片"""
    
    @staticmethod
    def _generate_single_shot(mixin_instance, shot_num: int) -> None:
        """生成单个分镜的图片"""
```

#### `_generate_single_shot()` 详解

```python
def _generate_single_shot(mixin_instance, shot_num: int) -> None:
    """
    生成单个分镜的图片
    
    流程:
        1. 验证分镜数据
        2. 创建输出目录
        3. 获取生成参数（每分镜生成数量）
        4. 循环生成多张变体
        5. 刷新预览
    """
    # 步骤1: 验证分镜数据
    shot = mixin_instance.current_shots[shot_num - 1]
    if not isinstance(shot, dict):
        logger.error(f"分镜 {shot_num} 不是字典格式")
        return
    
    # 步骤2: 创建输出目录
    project_dir = Path(mixin_instance.current_project.project_dir)
    shots_dir = project_dir / "director" / "shots"
    shots_dir.mkdir(parents=True, exist_ok=True)
    
    # 步骤3: 获取生成参数
    images_per_shot = getattr(mixin_instance, 'images_per_shot_var', tk.IntVar(value=1)).get()
    
    # 步骤4: 循环生成
    def generate_task():
        for variant in range(1, images_per_shot + 1):
            image_path = mixin_instance._generate_single_shot_image(
                shot_num=shot_num,
                description=shot.get('visual_description', ''),
                output_dir=str(shots_dir),
                shot_variant=variant,
                seed_offset=(variant - 1) * 1000  # 每个变体使用不同的seed
            )
            if image_path:
                logger.info(f"分镜 {shot_num} 变体 {variant} 生成成功")
        
        # 步骤5: 刷新预览
        mixin_instance.after(0, lambda: ImageGenerationHandler._refresh_preview_images(mixin_instance))
    
    threading.Thread(target=generate_task, daemon=True).start()
```

**关键点**:
- **多线程生成**: 使用后台线程避免阻塞UI
- **seed偏移**: 每个变体使用不同的seed偏移，确保多样性
- **预览刷新**: 生成完成后自动刷新预览

---

## API客户端详解

### 1. OpenAIImageClient

#### 类定义

```python
class OpenAIImageClient:
    """Minimal OpenAI image client using images.generate"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "gpt-image-1", timeout_seconds: int = 120):
        """
        初始化客户端
        
        参数:
            api_key: API密钥
            base_url: API基础URL（可选，用于兼容API）
            model: 模型名称（默认gpt-image-1）
            timeout_seconds: 超时时间（秒）
        """
        key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not key:
            raise RuntimeError("Missing OPENAI_API_KEY for image generation")
        
        self.client = OpenAI(api_key=key, base_url=(base_url or None), timeout=timeout_seconds)
        self.model = model
```

#### `generate()` 详解

```python
def generate(self, prompt: str, *, seed: Optional[int] = None, size: str = "1024x1024", n: int = 1) -> List[ImageResult]:
    """
    文本生成图片
    
    流程:
        1. 尝试使用base64格式（优先）
        2. 如果失败，回退到URL格式
        3. 解析响应，返回图片列表
    
    参数:
        prompt: 文本提示词
        seed: 随机种子（可选，OpenAI可能忽略）
        size: 图片尺寸（如"1024x1024"）
        n: 生成数量
    
    返回:
        ImageResult列表
    """
    # 步骤1: 尝试base64格式
    try:
        resp = self.client.images.generate(
            model=self.model,
            prompt=prompt,
            size=size,
            n=n,
            response_format="b64_json"  # 优先使用base64
        )
        
        results: List[ImageResult] = []
        for d in resp.data:
            b64 = d.b64_json
            img_bytes = base64.b64decode(b64)
            img = Image.open(BytesIO(img_bytes)).convert("RGB")
            results.append(ImageResult(image=img, seed=seed, provider="openai", model=self.model))
        return results
        
    except Exception as e:
        # 步骤2: 回退到URL格式
        error_msg = str(e).lower()
        if "response_format" in error_msg or "format" in error_msg:
            # 带重试的URL格式请求
            resp = None
            for attempt in range(3):
                try:
                    resp = self.client.images.generate(
                        model=self.model,
                        prompt=prompt,
                        size=size,
                        n=n
                    )
                    break
                except Exception as gen_err:
                    time.sleep(0.4 * (2 ** attempt))
            
            # 步骤3: 下载URL图片
            results: List[ImageResult] = []
            for d in resp.data:
                if hasattr(d, 'url') and d.url:
                    img_bytes = None
                    for attempt in range(3):
                        try:
                            img_response = requests.get(d.url, timeout=30)
                            img_response.raise_for_status()
                            img_bytes = img_response.content
                            break
                        except Exception as req_err:
                            time.sleep(0.4 * (2 ** attempt))
                    
                    img = Image.open(BytesIO(img_bytes)).convert("RGB")
                    results.append(ImageResult(image=img, seed=seed, provider="openai", model=self.model))
            return results
        else:
            raise
```

**关键点**:
- **格式兼容**: 优先使用base64，失败时回退到URL
- **重试机制**: URL下载失败时自动重试3次
- **错误处理**: 详细的错误处理和日志记录

#### `generate_with_reference()` 详解

```python
def generate_with_reference(self, prompt: str, reference_image_path: str, *, size: str = "1024x1024") -> List[ImageResult]:
    """
    使用参考图生成图片（一致性）
    
    流程:
        1. 使用images.edits API
        2. 尝试base64格式
        3. 失败时回退到URL格式
        4. 如果API不支持，回退到纯文本生成
    
    参数:
        prompt: 文本提示词
        reference_image_path: 参考图片路径
        size: 图片尺寸
    
    返回:
        ImageResult列表
    """
    try:
        # 使用images.edits API
        with open(reference_image_path, "rb") as f:
            resp = self.client.images.edits(
                model=self.model,
                image=f,
                prompt=prompt,
                size=size,
                response_format="b64_json"
            )
        # ... 解析响应 ...
    except Exception:
        # 回退到纯文本生成
        return self.generate(prompt=prompt, size=size, n=1)
```

**关键点**:
- **一致性支持**: 使用images.edits API实现人物一致性
- **优雅降级**: 如果API不支持，回退到纯文本生成

### 2. StableDiffusionClient

#### 类定义

```python
class StableDiffusionClient:
    """Stable Diffusion WebUI API 客户端"""
    
    def __init__(self, base_url: str = None):
        """
        初始化SD客户端
        
        参数:
            base_url: SD WebUI API地址（默认http://localhost:7860）
        """
        self.base_url = base_url or os.getenv("SD_BASE_URL", "http://localhost:7860")
        self.timeout = 300  # 5分钟超时
```

#### `txt2img()` 详解

```python
def txt2img(
    self,
    prompt: str,
    negative_prompt: str = "",
    width: int = 512,
    height: int = 512,
    steps: int = 20,
    cfg_scale: float = 7.0,
    sampler_name: str = "Euler a",
    seed: int = -1,
    batch_size: int = 1,
    return_info: bool = False,
    **kwargs
) -> Optional[list[Image.Image]]:
    """
    文本生成图片
    
    流程:
        1. 构建请求payload
        2. 发送POST请求到/sdapi/v1/txt2img
        3. 解析base64图片
        4. 返回图片列表
    
    参数:
        prompt: 正面提示词
        negative_prompt: 负面提示词
        width/height: 图片尺寸
        steps: 采样步数
        cfg_scale: CFG系数
        sampler_name: 采样器名称
        seed: 随机种子（-1为随机）
        batch_size: 批次大小
    
    返回:
        图片列表，失败返回None
    """
    url = f"{self.base_url}/sdapi/v1/txt2img"
    
    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "width": width,
        "height": height,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "sampler_name": sampler_name,
        "seed": seed,
        "batch_size": batch_size,
        **kwargs
    }
    
    # 重试机制（最多3次）
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            images = []
            for img_data in result.get("images", []):
                img_bytes = base64.b64decode(img_data)
                img = Image.open(BytesIO(img_bytes))
                images.append(img)
            
            return images if images else None
            
        except requests.exceptions.ConnectionError as e:
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise ConnectionError(f"无法连接到SD服务器: {self.base_url}")
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            raise RuntimeError(f"SD API错误: {str(e)}")
```

**关键点**:
- **重试机制**: 连接失败时自动重试3次，递增延迟
- **超时处理**: 5分钟超时，适合长时间生成任务
- **灵活参数**: 支持所有SD WebUI参数

#### `img2img()` 详解

```python
def img2img(
    self,
    init_image: Image.Image,
    prompt: str,
    negative_prompt: str = "",
    denoising_strength: float = 0.75,
    width: int = 512,
    height: int = 512,
    steps: int = 20,
    cfg_scale: float = 7.0,
    sampler_name: str = "Euler a",
    seed: int = -1,
    return_info: bool = False,
    **kwargs
) -> Optional[list[Image.Image]]:
    """
    图片生成图片（一致性）
    
    流程:
        1. 将PIL图片转为base64
        2. 构建请求payload
        3. 发送POST请求到/sdapi/v1/img2img
        4. 解析响应，返回图片列表
    
    参数:
        init_image: 初始图片（PIL Image对象）
        prompt: 正面提示词
        negative_prompt: 负面提示词
        denoising_strength: 重绘幅度（0-1，0.4适合一致性）
        ... 其他参数同txt2img
    
    返回:
        图片列表，失败返回None
    """
    url = f"{self.base_url}/sdapi/v1/img2img"
    
    # 步骤1: 转为base64
    buffered = BytesIO()
    init_image.save(buffered, format="PNG")
    init_image_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    payload = {
        "init_images": [init_image_base64],
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "denoising_strength": denoising_strength,
        ...
    }
    
    # 步骤2-4: 发送请求并解析（同txt2img）
    # ...
```

**关键点**:
- **一致性控制**: denoising_strength控制一致性程度（0.4适合人物一致性）
- **图片格式**: 自动转换为PNG格式的base64编码

### 3. HunyuanImageClient

#### 类定义

```python
class HunyuanImageClient:
    """腾讯混元文生图客户端"""
    
    def __init__(
        self,
        secret_id: str,
        secret_key: str,
        region: str = "ap-guangzhou",
        timeout_seconds: int = 120
    ):
        """
        初始化混元客户端
        
        参数:
            secret_id: 腾讯云SecretId
            secret_key: 腾讯云SecretKey
            region: 地域（默认广州）
            timeout_seconds: 超时时间
        """
        if not secret_id or not secret_key:
            raise RuntimeError("需要提供腾讯云SecretId和SecretKey")
        
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region
        self.timeout = timeout_seconds
        self.endpoint = "hunyuan.tencentcloudapi.com"
        self.service = "hunyuan"
        self.version = "2023-09-01"
```

#### `_sign()` 详解

```python
def _sign(self, params: dict, timestamp: int) -> str:
    """
    生成腾讯云API签名（TC3-HMAC-SHA256）
    
    流程:
        1. 构建规范请求串
        2. 构建待签名字符串
        3. 计算签名（HMAC-SHA256）
        4. 拼接Authorization头
    
    返回:
        Authorization字符串
    """
    # 步骤1: 构建规范请求串
    canonical_request = (
        f"{http_request_method}\n"
        f"{canonical_uri}\n"
        f"{canonical_querystring}\n"
        f"{canonical_headers}\n"
        f"{signed_headers}\n"
        f"{hashed_request_payload}"
    )
    
    # 步骤2: 构建待签名字符串
    algorithm = "TC3-HMAC-SHA256"
    date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
    credential_scope = f"{date}/{self.service}/tc3_request"
    string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashed_canonical_request}"
    
    # 步骤3: 计算签名
    secret_date = _hmac_sha256(("TC3" + self.secret_key).encode("utf-8"), date)
    secret_service = _hmac_sha256(secret_date, self.service)
    secret_signing = _hmac_sha256(secret_service, "tc3_request")
    signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    
    # 步骤4: 拼接Authorization
    authorization = (
        f"{algorithm} "
        f"Credential={self.secret_id}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )
    
    return authorization
```

**关键点**:
- **腾讯云签名**: 使用TC3-HMAC-SHA256签名算法
- **安全认证**: 签名确保请求的完整性和安全性

#### `generate()` 详解

```python
def generate(
    self,
    prompt: str,
    negative_prompt: Optional[str] = None,
    style: Optional[str] = "201",
    resolution: str = "1024x1024",
    logo_add: int = 1,
    rsp_img_type: str = "base64"
) -> HunyuanImageResult:
    """
    生成图片
    
    流程:
        1. 构建请求参数
        2. 生成签名
        3. 发送POST请求
        4. 解析响应，返回图片
    
    参数:
        prompt: 文本描述（必选）
        negative_prompt: 反向文本描述（可选）
        style: 绘画风格编号（201=日系动漫）
        resolution: 分辨率（如"1024x1024"）
        logo_add: 是否添加标识（1-添加）
        rsp_img_type: 返回格式（base64或url）
    
    返回:
        HunyuanImageResult对象
    """
    # 步骤1: 构建请求参数
    params = {
        "Prompt": prompt,
        "Resolution": resolution,
        "LogoAdd": logo_add,
        "RspImgType": rsp_img_type
    }
    if negative_prompt:
        params["NegativePrompt"] = negative_prompt
    if style:
        params["Style"] = style
    
    # 步骤2: 生成签名
    timestamp = int(time.time())
    authorization = self._sign(params, timestamp)
    
    # 步骤3: 发送请求
    headers = {
        "Content-Type": "application/json",
        "Authorization": authorization,
        "X-TC-Action": "ImageToImage",
        "X-TC-Timestamp": str(timestamp),
        "X-TC-Version": self.version,
        "X-TC-Region": self.region
    }
    
    response = requests.post(
        f"https://{self.endpoint}/",
        json=params,
        headers=headers,
        timeout=self.timeout
    )
    response.raise_for_status()
    
    # 步骤4: 解析响应
    result = response.json()
    img_base64 = result["Response"]["ResultImage"]
    img_data = base64.b64decode(img_base64)
    img = Image.open(BytesIO(img_data))
    
    return HunyuanImageResult(image=img, provider="hunyuan", model="hunyuan-turbo")
```

**关键点**:
- **API 3.0规范**: 使用腾讯云API 3.0规范
- **风格编号**: 使用数字编号指定风格（201=日系动漫）
- **base64返回**: 默认返回base64格式图片

---

## 完整执行流程

### 人物照片生成流程

```
用户操作
  │
  ├─→ 点击"生成照片"按钮
  │   └─→ CharacterPhotoHandler.handle_generate_photo()
  │       │
  │       ├─→ 步骤1: 验证输入
  │       │   ├─→ 检查人物列表
  │       │   ├─→ 检查角度选择
  │       │   └─→ 检查表情选择
  │       │
  │       ├─→ 步骤2: 准备生成参数
  │       │   ├─→ 获取人物信息
  │       │   ├─→ 获取角度、表情
  │       │   ├─→ 获取风格、一致性级别
  │       │   └─→ 计算生成总数
  │       │
  │       ├─→ 步骤3: 开始生成（后台线程）
  │       │   └─→ threading.Thread(target=generate_photo_thread)
  │       │       │
  │       │       ├─→ 循环：为每个人物生成照片
  │       │       │   └─→ CharacterPhotoGenerator.generate_photo()
  │       │       │       │
  │       │       │       ├─→ 步骤3.1: 检查API配置
  │       │       │       │   └─→ 选择生成方法（混元/SD/OpenAI）
  │       │       │       │
  │       │       │       ├─→ 步骤3.2: 构建提示词
  │       │       │       │   └─→ CharacterPromptBuilder.build_character_photo_prompt()
  │       │       │       │
  │       │       │       ├─→ 步骤3.3: 优化提示词
  │       │       │       │   └─→ CharacterPromptBuilder.optimize_for_api()
  │       │       │       │
  │       │       │       ├─→ 步骤3.4: 调用API生成
  │       │       │       │   ├─→ SD: txt2img/img2img
  │       │       │       │   ├─→ OpenAI: generate/generate_with_reference
  │       │       │       │   └─→ 混元: generate
  │       │       │       │
  │       │       │       └─→ 步骤3.5: 返回图片
  │       │       │
  │       │       ├─→ 步骤4: 更新预览
  │       │       │   └─→ CharacterPhotoPreview.update_preview()
  │       │       │       └─→ 显示到UI
  │       │       │
  │       │       └─→ 步骤5: 自动保存
  │       │           └─→ CharacterPhotoSaver.auto_save()
  │       │               └─→ 保存到项目characters目录
```

### 分镜图片生成流程

```
用户操作
  │
  ├─→ 点击"生成分镜图片"按钮
  │   └─→ ImageGenerationHandler.handle_generate_selected_shot()
  │       │
  │       ├─→ 步骤1: 检查分镜数据
  │       │   └─→ 验证current_shots是否存在
  │       │
  │       ├─→ 步骤2: 选择生成模式
  │       │   ├─→ "全部分镜" → _generate_all_shots()
  │       │   └─→ 单个分镜 → _generate_single_shot()
  │       │
  │       ├─→ 步骤3: 确认生成（批量模式）
  │       │   └─→ messagebox.askyesno("确认", ...)
  │       │
  │       ├─→ 步骤4: 开始生成（后台线程）
  │       │   └─→ threading.Thread(target=generate_task)
  │       │       │
  │       │       ├─→ 循环：为每个分镜生成图片
  │       │       │   └─→ _generate_single_shot_image()
  │       │       │       │
  │       │       │       ├─→ 步骤4.1: 构建提示词
  │       │       │       │   └─→ 使用分镜的visual_description
  │       │       │       │
  │       │       │       ├─→ 步骤4.2: 获取API配置
  │       │       │       │   └─→ 获取provider、base_url等
  │       │       │       │
  │       │       │       ├─→ 步骤4.3: 调用生成服务
  │       │       │       │   └─→ ImageGeneratorService.generate_shot_image()
  │       │       │       │       ├─→ SD: _generate_with_sd()
  │       │       │       │       └─→ OpenAI: _generate_with_openai_compatible()
  │       │       │       │
  │       │       │       └─→ 步骤4.4: 保存图片
  │       │       │           └─→ 保存到project/director/shots/
  │       │       │
  │       │       └─→ 步骤5: 刷新预览
  │       │           └─→ _refresh_preview_images()
  │       │               └─→ 更新图片预览区域
```

---

## 人物一致性机制

### SD一致性策略

**策略1: 固定seed + img2img**

```python
# 第一张：txt2img + 固定seed
seed = int(hashlib.md5(character_name.encode()).hexdigest()[:8], 16)
images = sd_client.txt2img(
    prompt=full_prompt,
    seed=seed,  # 固定seed
    ...
)

# 后续：img2img + 第一张作为参考
images = sd_client.img2img(
    init_image=reference_image,  # 第一张图片
    prompt=full_prompt,
    denoising_strength=0.4,  # 较低的重绘幅度
    ...
)
```

**优点**:
- 第一张图片可复现（固定seed）
- 后续图片与第一张高度一致
- 适合批量生成同一人物的不同角度/表情

**缺点**:
- 依赖第一张图片的质量
- denoising_strength需要调优

### OpenAI一致性策略

**策略: generate_with_reference**

```python
# 第一张：纯文本生成
results = client.generate(prompt=full_prompt)

# 后续：参考图生成
results = client.generate_with_reference(
    prompt=prompt,
    reference_image_path=reference_image_path
)
```

**优点**:
- 简单易用
- API自动处理一致性

**缺点**:
- 依赖API支持
- 一致性程度不可控

### 提示词一致性策略

**策略: 简化描述 + 固定关键特征**

```python
# 第一张：完整描述
full_prompt = CharacterPromptBuilder.build_character_photo_prompt(
    description=description,  # 完整描述
    ...
)

# 后续：简化描述（只保留视角和表情）
full_prompt = CharacterPromptBuilder.build_character_photo_prompt(
    description="",  # 空描述
    view_angle=angle,  # 只保留视角
    expression=expression,  # 只保留表情
    extra_details=f"{angle_name} view, {expression_name} expression",
    consistency_level="high"
)
```

**优点**:
- 减少干扰因素
- 专注于保持一致性

**缺点**:
- 需要精心设计提示词

---

## 总结

图像生成模块提供了完整的图像生成功能：

1. **多API支持**: OpenAI、Stable Diffusion、腾讯混元
2. **人物一致性**: 固定seed、img2img、参考图等多种策略
3. **批量生成**: 支持批量生成多张图片
4. **灵活配置**: 支持自定义提示词、风格、尺寸等参数
5. **预览和保存**: 自动预览和保存到项目目录

所有API客户端都经过精心设计，支持重试、错误处理和格式兼容。

