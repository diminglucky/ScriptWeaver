# 核心模块详细技术文档

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

### 3. ConfigManager类

#### 类定义

```python
class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        初始化配置管理器
        
        参数:
            config_file: 配置文件路径（默认：项目根目录/config.json）
        """
        self.config_file = config_file or Path(__file__).parent.parent.parent / "config.json"
        self.director_config = DirectorConfig()
        self._load_config()
```

#### 关键方法

```python
def _load_config(self):
    """加载配置文件"""
    if self.config_file.exists():
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.director_config = DirectorConfig.from_dict(data)
        except Exception as e:
            logger.warning(f"加载配置文件失败: {e}，使用默认配置")

def save_config(self) -> bool:
    """保存配置到文件"""
    try:
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.director_config.to_dict(), f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存配置文件失败: {e}")
        return False

def get_api_config(self, name: str) -> Optional[APIConfig]:
    """获取API配置"""
    return self.director_config.api_configs.get(name)

def set_api_config(self, name: str, config: APIConfig):
    """设置API配置"""
    self.director_config.api_configs[name] = config
```

**关键点**:
- **统一配置**: 所有配置统一管理
- **持久化**: 支持保存和加载配置
- **验证**: 配置验证功能

---

## 总结

核心模块提供了项目的基础设施：

1. **日志系统**: 统一的日志配置和管理，支持日志轮转和分离错误日志
2. **配置管理**: 统一的配置加载和验证，支持多种配置类型
3. **异常处理**: 自定义异常类，提供友好的错误信息

所有核心功能都经过精心设计，确保项目的健壮性和可维护性。

