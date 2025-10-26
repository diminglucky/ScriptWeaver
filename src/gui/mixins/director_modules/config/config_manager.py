"""
配置管理器 - 统一管理所有配置
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path
import json


@dataclass
class APIConfig:
    """API配置"""
    provider: str  # 'sd', 'openai', 'hunyuan'
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    extra_params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'provider': self.provider,
            'base_url': self.base_url,
            'api_key': self.api_key,
            'model': self.model,
            'extra_params': self.extra_params
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'APIConfig':
        return cls(
            provider=data.get('provider', ''),
            base_url=data.get('base_url', ''),
            api_key=data.get('api_key', ''),
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
        return {
            'resolution': self.resolution,
            'style': self.style,
            'num_variants': self.num_variants,
            'video_platform': self.video_platform
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'GenerationSettings':
        return cls(
            resolution=data.get('resolution', '768x512'),
            style=data.get('style', 'photorealistic'),
            num_variants=data.get('num_variants', 3),
            video_platform=data.get('video_platform', 'jimeng')
        )


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or Path("config/director_config.json")
        self.api_configs: Dict[str, APIConfig] = {}
        self.generation_settings = GenerationSettings()
        self.preferences: Dict[str, Any] = {}
        
        self.load_config()
    
    def load_config(self) -> bool:
        """加载配置"""
        try:
            if not self.config_file.exists():
                self._init_default_config()
                return True
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 加载API配置
            api_configs_data = data.get('api_configs', {})
            for name, config_data in api_configs_data.items():
                self.api_configs[name] = APIConfig.from_dict(config_data)
            
            # 加载生成设置
            settings_data = data.get('generation_settings', {})
            self.generation_settings = GenerationSettings.from_dict(settings_data)
            
            # 加载偏好设置
            self.preferences = data.get('preferences', {})
            
            return True
        except Exception as e:
            print(f"加载配置失败: {e}")
            self._init_default_config()
            return False
    
    def save_config(self) -> bool:
        """保存配置"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'api_configs': {
                    name: config.to_dict()
                    for name, config in self.api_configs.items()
                },
                'generation_settings': self.generation_settings.to_dict(),
                'preferences': self.preferences
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    def _init_default_config(self):
        """初始化默认配置"""
        # 默认API配置
        self.api_configs = {
            'default_sd': APIConfig(
                provider='sd',
                base_url='http://localhost:7860',
                api_key='',
                model=''
            ),
            'default_openai': APIConfig(
                provider='openai',
                base_url='https://api.openai.com/v1',
                api_key='',
                model='dall-e-3'
            )
        }
        
        # 默认生成设置
        self.generation_settings = GenerationSettings()
        
        # 默认偏好
        self.preferences = {
            'auto_save': True,
            'show_tips': True,
            'theme': 'dark'
        }
        
        self.save_config()
    
    def add_api_config(self, name: str, config: APIConfig):
        """添加API配置"""
        self.api_configs[name] = config
        self.save_config()
    
    def get_api_config(self, name: str) -> Optional[APIConfig]:
        """获取API配置"""
        return self.api_configs.get(name)
    
    def remove_api_config(self, name: str) -> bool:
        """删除API配置"""
        if name in self.api_configs:
            del self.api_configs[name]
            self.save_config()
            return True
        return False
    
    def update_generation_settings(self, **kwargs):
        """更新生成设置"""
        for key, value in kwargs.items():
            if hasattr(self.generation_settings, key):
                setattr(self.generation_settings, key, value)
        self.save_config()
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """获取偏好设置"""
        return self.preferences.get(key, default)
    
    def set_preference(self, key: str, value: Any):
        """设置偏好"""
        self.preferences[key] = value
        self.save_config()
    
    def validate_api_config(self, config: APIConfig) -> tuple[bool, str]:
        """验证API配置"""
        if not config.provider:
            return False, "未指定API提供商"
        
        if config.provider == 'sd':
            if not config.base_url:
                return False, "SD API需要base_url"
        elif config.provider in ['openai', 'hunyuan']:
            if not config.api_key:
                return False, "需要API密钥"
            if not config.base_url:
                return False, "需要base_url"
        
        return True, "配置有效"

