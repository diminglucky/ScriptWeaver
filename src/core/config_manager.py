"""
统一配置管理模块
提供统一的配置加载、验证和管理功能
"""
import os
import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv, find_dotenv

from src.core.logging_config import get_logger
from src.core.exceptions import ConfigError

logger = get_logger(__name__)


@dataclass
class APIConfig:
    """API配置"""
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    provider: str = "openai"  # 'sd', 'openai', 'hunyuan'
    extra_params: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> list[str]:
        """验证配置有效性"""
        errors = []
        if self.provider != "sd" and not self.api_key:
            errors.append("API密钥不能为空")
        if self.provider != "sd" and not self.base_url:
            errors.append("API基础URL不能为空")
        if not self.model:
            errors.append("模型名称不能为空")
        return errors
    
    def is_valid(self) -> bool:
        """检查配置是否有效"""
        return len(self.validate()) == 0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'provider': self.provider,
            'api_key': self.api_key,
            'base_url': self.base_url,
            'model': self.model,
            'extra_params': self.extra_params
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'APIConfig':
        """从字典创建"""
        return cls(
            provider=data.get('provider', 'openai'),
            api_key=data.get('api_key', ''),
            base_url=data.get('base_url', ''),
            model=data.get('model', ''),
            extra_params=data.get('extra_params', {})
        )


@dataclass
class GenerationSettings:
    """生成设置"""
    resolution: str = "768x512"
    style: str = "photorealistic"
    num_variants: int = 3
    video_platform: str = "jimeng"
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'resolution': self.resolution,
            'style': self.style,
            'num_variants': self.num_variants,
            'video_platform': self.video_platform
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'GenerationSettings':
        """从字典创建"""
        return cls(
            resolution=data.get('resolution', '768x512'),
            style=data.get('style', 'photorealistic'),
            num_variants=data.get('num_variants', 3),
            video_platform=data.get('video_platform', 'jimeng')
        )


@dataclass
class DirectorConfig:
    """导演模块配置"""
    api_configs: Dict[str, APIConfig] = field(default_factory=dict)
    generation_settings: GenerationSettings = field(default_factory=GenerationSettings)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'api_configs': {
                name: config.to_dict()
                for name, config in self.api_configs.items()
            },
            'generation_settings': self.generation_settings.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DirectorConfig':
        """从字典创建"""
        api_configs = {
            name: APIConfig.from_dict(config_data)
            for name, config_data in data.get('api_configs', {}).items()
        }
        generation_settings = GenerationSettings.from_dict(
            data.get('generation_settings', {})
        )
        return cls(
            api_configs=api_configs,
            generation_settings=generation_settings
        )


@dataclass
class AppConfig:
    """应用配置"""
    # 故事生成API配置
    story_api: Optional[APIConfig] = None
    
    # 图片生成API配置
    image_api: Optional[APIConfig] = None
    
    # 项目目录
    projects_dir: Path = Path("projects")
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.projects_dir, str):
            self.projects_dir = Path(self.projects_dir)
    
    def validate(self) -> list[str]:
        """验证配置"""
        errors = []
        if self.story_api and not self.story_api.is_valid():
            errors.extend([f"故事API: {e}" for e in self.story_api.validate()])
        if self.image_api and not self.image_api.is_valid():
            errors.extend([f"图片API: {e}" for e in self.image_api.validate()])
        return errors
    
    def is_valid(self) -> bool:
        """检查配置是否有效"""
        return len(self.validate()) == 0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'story_api': self.story_api.to_dict() if self.story_api else None,
            'image_api': self.image_api.to_dict() if self.image_api else None,
            'projects_dir': str(self.projects_dir)
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AppConfig':
        """从字典创建"""
        story_api = APIConfig.from_dict(data['story_api']) if data.get('story_api') else None
        image_api = APIConfig.from_dict(data['image_api']) if data.get('image_api') else None
        projects_dir = Path(data.get('projects_dir', 'projects'))
        return cls(
            story_api=story_api,
            image_api=image_api,
            projects_dir=projects_dir
        )


class ConfigManager:
    """统一配置管理器"""
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径，默认为项目根目录下的 config.json
        """
        if config_file is None:
            config_file = Path(__file__).parent.parent.parent / "config" / "config.json"
        
        self.config_file = Path(config_file)
        self.app_config = AppConfig()
        self.director_config = DirectorConfig()
        
        # 加载环境变量
        self._load_env()
        
        # 加载配置文件
        self.load()
    
    def _load_env(self):
        """从环境变量加载配置"""
        env_file = find_dotenv()
        if env_file:
            load_dotenv(env_file)
            logger.info(f"已加载环境变量文件: {env_file}")
        
        # 从环境变量读取API配置
        story_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        if story_api_key:
            self.app_config.story_api = APIConfig(
                api_key=story_api_key,
                base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
                provider="openai"
            )
        
        image_api_key = os.getenv("OPENAI_API_KEY", "")
        if image_api_key:
            self.app_config.image_api = APIConfig(
                api_key=image_api_key,
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                model=os.getenv("OPENAI_MODEL", "dall-e-3"),
                provider="openai"
            )
    
    def load(self) -> bool:
        """从文件加载配置"""
        try:
            if not self.config_file.exists():
                logger.warning(f"配置文件不存在: {self.config_file}，使用默认配置")
                return False
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 加载应用配置
            if 'app_config' in data:
                self.app_config = AppConfig.from_dict(data['app_config'])
            
            # 加载导演配置
            if 'director_config' in data:
                self.director_config = DirectorConfig.from_dict(data['director_config'])
            
            logger.info(f"已加载配置文件: {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}", exc_info=True)
            return False
    
    def save(self) -> bool:
        """保存配置到文件"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'app_config': self.app_config.to_dict(),
                'director_config': self.director_config.to_dict()
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已保存配置文件: {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}", exc_info=True)
            return False
    
    def get_api_config(self, name: str) -> Optional[APIConfig]:
        """获取API配置"""
        return self.director_config.api_configs.get(name)
    
    def set_api_config(self, name: str, config: APIConfig):
        """设置API配置"""
        self.director_config.api_configs[name] = config
    
    def get_generation_settings(self) -> GenerationSettings:
        """获取生成设置"""
        return self.director_config.generation_settings
    
    def set_generation_settings(self, settings: GenerationSettings):
        """设置生成设置"""
        self.director_config.generation_settings = settings
    
    def validate(self) -> list[str]:
        """验证所有配置"""
        errors = []
        errors.extend(self.app_config.validate())
        # 可以添加导演配置的验证
        return errors
