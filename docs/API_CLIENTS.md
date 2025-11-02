# API客户端模块详细技术文档

## 📋 目录

1. [模块概述](#模块概述)
2. [文件结构](#文件结构)
3. [核心组件详解](#核心组件详解)
4. [API客户端详解](#api客户端详解)
5. [错误处理机制](#错误处理机制)

---

## 模块概述

### 功能定位

API客户端模块负责封装各种外部API的调用：

1. **文本生成API**: DeepSeek（OpenAI兼容）
2. **图像生成API**: OpenAI兼容API、Stable Diffusion、腾讯混元
3. **统一接口**: 提供统一的API调用接口
4. **错误处理**: 统一的错误处理和重试机制
5. **流式支持**: 支持流式响应（文本生成）

### 模块位置

```
src/clients/
├── __init__.py                    # 包初始化
├── base_client.py                 # 基础客户端类（抽象基类）
├── deepseek_client.py             # DeepSeek文本生成客户端
├── image_client.py                # OpenAI兼容图像生成客户端
├── sd_client.py                   # Stable Diffusion客户端
└── hunyuan_image_client.py        # 腾讯混元图像生成客户端
```

### 模块依赖关系

```
BaseAPIClient (抽象基类)
├── BaseChatClient                # 聊天API基类
│   └── DeepSeekClient           # DeepSeek实现
└── BaseImageClient              # 图像API基类
    ├── OpenAIImageClient        # OpenAI兼容实现
    ├── StableDiffusionClient   # SD实现
    └── HunyuanImageClient       # 混元实现
```

---

## 文件结构

### 1. base_client.py

**职责**: 定义API客户端的基础类和抽象接口

**主要类**:
- `BaseAPIClient`: API客户端基类
- `BaseChatClient`: 聊天API客户端基类
- `BaseImageClient`: 图像API客户端基类

**文件大小**: 161行

### 2. deepseek_client.py

**职责**: DeepSeek文本生成API客户端

**主要类**:
- `DeepSeekClient`: DeepSeek客户端

**关键方法**:
- `chat()`: 同步聊天接口
- `stream()`: 流式聊天接口

**文件大小**: 79行

### 3. image_client.py

**职责**: OpenAI兼容图像生成API客户端

**主要类**:
- `ImageResult`: 图像生成结果数据类
- `OpenAIImageClient`: OpenAI兼容图像客户端

**关键方法**:
- `generate()`: 文本生成图片
- `generate_with_reference()`: 参考图生成图片（一致性）

**文件大小**: 178行

### 4. sd_client.py

**职责**: Stable Diffusion本地API客户端

**主要类**:
- `StableDiffusionClient`: SD WebUI API客户端

**关键方法**:
- `txt2img()`: 文本生成图片
- `img2img()`: 图片生成图片（一致性）

**文件大小**: 约320行

### 5. hunyuan_image_client.py

**职责**: 腾讯混元图像生成API客户端

**主要类**:
- `HunyuanImageResult`: 混元结果数据类
- `HunyuanImageClient`: 混元API客户端

**关键方法**:
- `generate()`: 生成图片

**文件大小**: 约230行

---

## 核心组件详解

### 1. BaseAPIClient类

#### 类定义

```python
class BaseAPIClient(ABC):
    """API客户端基类"""
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: int = 120,
    ) -> None:
        """
        初始化API客户端
        
        参数:
            api_key: API密钥
            base_url: API基础URL
            model: 模型名称
            timeout: 超时时间（秒）
        
        异常:
            APIError: API配置无效
        """
        if not api_key:
            raise APIError("API密钥不能为空")
        if not base_url:
            raise APIError("API基础URL不能为空")
        if not model:
            raise APIError("模型名称不能为空")
        
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        
        logger.info(f"初始化API客户端: {self.__class__.__name__}, 模型: {model}")
```

#### `_handle_error()` 详解

```python
def _handle_error(self, error: Exception) -> None:
    """
    统一错误处理
    
    流程:
        1. 记录错误日志
        2. 解析常见错误类型
        3. 抛出友好的APIError异常
    
    常见错误类型:
        - timeout: 请求超时
        - 401: 未授权（API密钥无效）
        - 403: 禁止访问（无权限）
        - 429: 频率限制（调用过频）
        - 500/502/503: 服务器错误（服务不可用）
    
    参数:
        error: 原始异常
    
    异常:
        APIError: 处理后的API错误
    """
    error_msg = str(error)
    logger.error(f"API请求失败: {error_msg}")
    
    # 解析常见错误
    if "timeout" in error_msg.lower():
        raise APIError("API请求超时，请检查网络连接")
    elif "401" in error_msg or "unauthorized" in error_msg.lower():
        raise APIError("API密钥无效或已过期")
    elif "403" in error_msg or "forbidden" in error_msg.lower():
        raise APIError("无权访问该API")
    elif "429" in error_msg or "rate limit" in error_msg.lower():
        raise APIError("API调用频率超限，请稍后重试")
    elif "500" in error_msg or "502" in error_msg or "503" in error_msg:
        raise APIError("API服务暂时不可用，请稍后重试")
    else:
        raise APIError(f"API请求失败: {error_msg}")
```

**关键点**:
- **统一错误处理**: 所有API客户端使用统一的错误处理机制
- **友好错误信息**: 将技术错误转换为用户友好的错误信息
- **错误分类**: 根据错误类型提供不同的处理建议

### 2. BaseChatClient类

#### 类定义

```python
class BaseChatClient(BaseAPIClient):
    """聊天API客户端基类"""
    
    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs: Any,
    ) -> str:
        """
        同步聊天接口
        
        参数:
            messages: 消息列表
            **kwargs: 其他参数
        
        返回:
            助手回复内容
        
        异常:
            APIError: API请求失败
        """
        pass
    
    @abstractmethod
    def stream(
        self,
        messages: List[Dict[str, str]],
        **kwargs: Any,
    ) -> Generator[str, None, None]:
        """
        流式聊天接口
        
        参数:
            messages: 消息列表
            **kwargs: 其他参数
        
        生成:
            助手回复片段
        
        异常:
            APIError: API请求失败
        """
        pass
```

**关键点**:
- **抽象接口**: 定义了聊天API的标准接口
- **同步和流式**: 支持同步和流式两种调用方式
- **消息格式**: 使用标准的消息列表格式（role + content）

### 3. BaseImageClient类

#### 类定义

```python
class BaseImageClient(BaseAPIClient):
    """图片生成API客户端基类"""
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> Any:
        """
        生成图片
        
        参数:
            prompt: 提示词
            **kwargs: 其他参数
        
        返回:
            生成的图片
        
        异常:
            APIError: API请求失败
        """
        pass
```

**关键点**:
- **抽象接口**: 定义了图像生成API的标准接口
- **灵活参数**: 支持通过kwargs传递额外参数

---

## API客户端详解

### 1. DeepSeekClient类

#### 类定义

```python
class DeepSeekClient:
    """Thin wrapper for DeepSeek's OpenAI-compatible chat API"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None, timeout_seconds: int = 300):
        """
        初始化DeepSeek客户端
        
        参数:
            api_key: API密钥（可选，从环境变量读取）
            base_url: API基础URL（可选，默认https://api.deepseek.com/v1）
            model: 模型名称（可选，默认deepseek-chat）
            timeout_seconds: 超时时间（秒，默认300）
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("Missing DEEPSEEK_API_KEY. Create .env and export it.")
        self.base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=timeout_seconds)
```

**关键点**:
- **OpenAI兼容**: 使用OpenAI SDK，兼容OpenAI格式的API
- **环境变量支持**: 支持从环境变量读取配置
- **默认值**: 提供合理的默认值

#### `chat()` 详解

```python
def chat(
    self,
    messages: List[dict],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    top_p: Optional[float] = None,
    presence_penalty: Optional[float] = None,
    frequency_penalty: Optional[float] = None,
) -> str:
    """
    同步聊天接口
    
    流程:
        1. 重试机制（最多3次）
        2. 指数退避（0.4s, 0.8s）
        3. 调用OpenAI SDK
        4. 返回回复内容
    
    参数:
        messages: 消息列表（格式：[{"role": "user", "content": "..."}])
        model: 模型名称（可选，使用默认模型）
        temperature: 温度参数（0-1，默认0.7）
        max_tokens: 最大token数（可选）
        top_p: nucleus采样参数（可选）
        presence_penalty: 存在惩罚（可选）
        frequency_penalty: 频率惩罚（可选）
    
    返回:
        助手回复内容（字符串）
    
    异常:
        RuntimeError: 聊天生成失败
    """
    last_err: Any = None
    for attempt in range(3):
        try:
            resp = self.client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                presence_penalty=presence_penalty,
                frequency_penalty=frequency_penalty,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            last_err = e
            # 指数退避：0.4s, 0.8s
            time.sleep(0.4 * (2 ** attempt))
    # 统一抛出可理解的错误
    raise RuntimeError(f"聊天生成失败，请检查网络或API配置。详情：{last_err}")
```

**关键点**:
- **重试机制**: 最多重试3次，提升健壮性
- **指数退避**: 重试间隔递增（0.4s, 0.8s），避免频繁请求
- **错误处理**: 统一抛出友好的错误信息

#### `stream()` 详解

```python
def stream(
    self,
    messages: List[dict],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    top_p: Optional[float] = None,
    presence_penalty: Optional[float] = None,
    frequency_penalty: Optional[float] = None,
):
    """
    流式聊天接口
    
    流程:
        1. 调用OpenAI SDK流式接口
        2. 逐块生成回复
        3. 错误时返回空生成，避免阻塞UI
    
    参数:
        同chat()方法
    
    生成:
        助手回复片段（字符串）
    """
    try:
        stream = self.client.chat.completions.create(
            model=model or self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            stream=True,  # 启用流式
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception:
        # 流失败直接返回空生成，避免阻塞UI
        yield from []
```

**关键点**:
- **流式响应**: 支持实时显示生成内容
- **优雅降级**: 错误时返回空生成，避免阻塞UI
- **增量输出**: 逐块生成，提升用户体验

### 2. OpenAIImageClient类

#### 类定义

```python
class OpenAIImageClient:
    """Minimal OpenAI image client using images.generate"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "gpt-image-1", timeout_seconds: int = 120):
        """
        初始化OpenAI图像客户端
        
        参数:
            api_key: API密钥（可选，从环境变量读取）
            base_url: API基础URL（可选，用于兼容API）
            model: 模型名称（默认gpt-image-1）
            timeout_seconds: 超时时间（秒，默认120）
        """
        key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not key:
            raise RuntimeError("Missing OPENAI_API_KEY for image generation")
        # 空字符串时不传 base_url，避免SDK报错
        self.client = OpenAI(api_key=key, base_url=(base_url or None), timeout=timeout_seconds)
        self.model = model
```

**关键点**:
- **OpenAI兼容**: 使用OpenAI SDK，支持OpenAI和兼容API
- **base_url可选**: 空字符串时不传base_url，避免SDK报错
- **环境变量支持**: 支持从环境变量读取API密钥

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
    
    异常:
        RuntimeError: API调用失败
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
        if "response_format" in error_msg or "format" in error_msg or "b64_json" in error_msg:
            # 带简单重试的兜底
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

### 3. StableDiffusionClient类

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

**关键点**:
- **本地部署**: 支持本地部署的SD WebUI
- **长超时**: 5分钟超时，适合长时间生成任务

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

### 4. HunyuanImageClient类

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

**关键点**:
- **腾讯云API**: 使用腾讯云API 3.0规范
- **签名认证**: 需要SecretId和SecretKey进行签名

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
        2. 生成签名（TC3-HMAC-SHA256）
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
- **签名机制**: 使用TC3-HMAC-SHA256签名算法
- **风格编号**: 使用数字编号指定风格（201=日系动漫）

---

## 错误处理机制

### 统一错误处理

所有API客户端都使用统一的错误处理机制：

```python
# BaseAPIClient._handle_error()
def _handle_error(self, error: Exception) -> None:
    """
    统一错误处理
    
    错误类型映射:
        - timeout → "API请求超时，请检查网络连接"
        - 401 → "API密钥无效或已过期"
        - 403 → "无权访问该API"
        - 429 → "API调用频率超限，请稍后重试"
        - 500/502/503 → "API服务暂时不可用，请稍后重试"
        - 其他 → "API请求失败: {error_msg}"
    """
```

### 重试机制

所有API客户端都实现了重试机制：

```python
# DeepSeekClient.chat()
for attempt in range(3):
    try:
        resp = self.client.chat.completions.create(...)
        return resp.choices[0].message.content or ""
    except Exception as e:
        last_err = e
        # 指数退避：0.4s, 0.8s
        time.sleep(0.4 * (2 ** attempt))
raise RuntimeError(f"聊天生成失败，请检查网络或API配置。详情：{last_err}")
```

**重试策略**:
- **最大重试次数**: 3次
- **退避策略**: 指数退避（0.4s, 0.8s, 1.6s）
- **错误记录**: 记录最后一次错误信息

### 超时处理

不同API客户端使用不同的超时时间：

```python
# DeepSeekClient: 300秒（文本生成可能较长）
self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=300)

# OpenAIImageClient: 120秒（图像生成通常较快）
self.client = OpenAI(api_key=key, base_url=(base_url or None), timeout=120)

# StableDiffusionClient: 300秒（本地生成可能较长）
self.timeout = 300  # 5分钟超时
```

---

## 总结

API客户端模块提供了统一的API调用接口：

1. **统一接口**: 定义了聊天和图像生成的标准接口
2. **多API支持**: 支持DeepSeek、OpenAI、SD、混元等多种API
3. **错误处理**: 统一的错误处理和重试机制
4. **流式支持**: 支持流式响应（文本生成）
5. **格式兼容**: 支持base64和URL两种图片格式

所有API客户端都经过精心设计，确保健壮性和用户体验。

