# 工具模块详细技术文档

## 📋 目录

1. [模块概述](#模块概述)
2. [文件结构](#文件结构)
3. [核心工具详解](#核心工具详解)

---

## 模块概述

### 功能定位

工具模块提供各种实用工具函数：

1. **文本处理**: 文件发现、文本清理、文本分割
2. **字符串处理**: 字符串清理、特殊字符处理
3. **API测试**: API连接测试
4. **图像处理**: 图像工具函数

### 模块位置

```
src/utils/
├── __init__.py
├── text.py                    # 文本处理工具
├── image_utils.py             # 图像处理工具
├── file_utils.py              # 文件处理工具
├── prompt_translator.py       # 提示词翻译工具
├── story_extractor.py         # 故事提取工具
├── tag_extractor.py           # 标签提取工具
└── validators.py              # 验证工具
```

---

## 文件结构

### 1. text.py

**职责**: 文本处理相关工具函数

**关键函数**:
- `discover_text_files()`: 递归发现文本文件
- `read_file_text()`: 读取文件内容
- `clean_text()`: 清理文本（规范化换行、去除多余空白）
- `split_by_length()`: 按长度分割文本（保持句子边界）
- `sanitize()`: 清理字符串中的特殊字符
- `try_chat_api()`: 测试聊天API
- `try_image_api()`: 测试图片API

**文件大小**: 约200行

### 2. split_by_length() 详解

```python
def split_by_length(text: str, max_chars: int = 800, overlap: int = 120) -> List[str]:
    """
    按长度分割文本，尽量保持句子边界
    
    流程:
        1. 按句子分割（。！？!?.）
        2. 累积句子直到达到max_chars
        3. 添加重叠部分（overlap字符）
        4. 过滤太小的块（<20字符）
    
    参数:
        text: 要分割的文本
        max_chars: 最大字符数（默认800）
        overlap: 重叠字符数（默认120）
    
    返回:
        文本块列表
    """
    if not text:
        return []
    
    # 按句子分割
    sentences = re.split(r"(?<=[。！？!?.])\s+", text)
    chunks: List[str] = []
    current: List[str] = []
    current_len = 0
    
    for s in sentences:
        s_len = len(s)
        if current_len + s_len <= max_chars or not current:
            current.append(s)
            current_len += s_len
        else:
            chunks.append("".join(current).strip())
            # 添加重叠部分
            if overlap > 0 and chunks[-1]:
                tail = chunks[-1][-overlap:]
                current = [tail, s]
                current_len = len(tail) + s_len
            else:
                current = [s]
                current_len = s_len
    
    if current:
        chunks.append("".join(current).strip())
    
    # 过滤太小的块
    return [c for c in chunks if len(c) > 20]
```

**关键点**:
- **句子边界**: 尽量在句子边界处分割
- **重叠处理**: 添加重叠部分，保持上下文连续性
- **过滤小块**: 过滤太小的文本块

---

## 核心模块详细技术文档

## 📋 目录

1. [模块概述](#模块概述)
2. [文件结构](#文件结构)
3. [核心组件详解](#核心组件详解)

---

## 模块概述

### 功能定位

核心模块提供项目的基础设施：

1. **日志系统**: 统一的日志配置和管理
2. **配置管理**: 统一的配置加载和验证
3. **异常处理**: 自定义异常类
4. **基础工具**: 项目的基础功能

### 模块位置

```
src/core/
├── logging_config.py          # 日志配置
├── config_manager.py          # 配置管理
├── exceptions.py              # 自定义异常
└── exception_handler.py       # 异常处理
```

---

## 文件结构

### 1. logging_config.py

**职责**: 统一的日志配置

**关键函数**:
- `setup_logging()`: 设置应用程序日志
- `get_logger()`: 获取日志记录器

**文件大小**: 约140行

### 2. config_manager.py

**职责**: 统一的配置管理

**主要类**:
- `APIConfig`: API配置数据类
- `GenerationSettings`: 生成设置数据类
- `DirectorConfig`: 导演模块配置数据类
- `ConfigManager`: 配置管理器

**文件大小**: 约300行

### 3. setup_logging() 详解

```python
def setup_logging(
    log_dir: Optional[Path] = None,
    log_level: str = "INFO",
    log_to_file: bool = True,
    log_to_console: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    console_level: Optional[str] = None
) -> logging.Logger:
    """
    设置应用程序日志
    
    功能:
        1. 文件日志（按大小轮转）
        2. 错误日志单独记录
        3. 控制台日志（简化格式）
        4. 日志级别配置
    
    参数:
        log_dir: 日志文件目录（默认：项目根目录/logs）
        log_level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_to_file: 是否记录到文件
        log_to_console: 是否输出到控制台
        max_bytes: 单个日志文件最大大小（字节，默认10MB）
        backup_count: 保留的备份文件数量（默认5）
        console_level: 控制台日志级别（默认与log_level相同）
    
    返回:
        配置好的根日志记录器
    """
    # 确定日志目录
    if log_dir is None:
        log_dir = Path(__file__).parent.parent.parent / "logs"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # 文件处理器（按大小轮转）
    if log_to_file:
        file_handler = RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # 错误日志单独记录
        error_handler = RotatingFileHandler(
            log_dir / "error.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)
    
    # 控制台处理器
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    return root_logger
```

**关键点**:
- **日志轮转**: 按大小轮转，避免日志文件过大
- **分离错误**: 错误日志单独记录到error.log
- **格式配置**: 文件和控制台使用不同的格式

---

## 总结

工具模块和核心模块提供了项目的基础设施：

1. **文本处理**: 文件发现、文本清理、文本分割
2. **日志系统**: 统一的日志配置和管理
3. **配置管理**: 统一的配置加载和验证
4. **异常处理**: 自定义异常类

所有工具都经过精心设计，确保易用性和健壮性。

