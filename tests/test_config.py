"""
配置管理测试用例
"""

import pytest
import tempfile
import json
from pathlib import Path
from src.core.config_manager import ConfigManager, AppConfig, APIConfig


class TestAPIConfig:
    """测试API配置"""
    
    def test_validate_valid(self):
        """测试有效配置验证"""
        config = APIConfig(
            api_key="test_key",
            base_url="https://api.test.com",
            model="test-model"
        )
        errors = config.validate()
        assert len(errors) == 0
        assert config.is_valid()
    
    def test_validate_empty_api_key(self):
        """测试空API密钥"""
        config = APIConfig(api_key="", base_url="https://api.test.com", model="test")
        errors = config.validate()
        assert len(errors) > 0
        assert "API密钥不能为空" in errors[0]
    
    def test_validate_empty_base_url(self):
        """测试空基础URL"""
        config = APIConfig(api_key="key", base_url="", model="test")
        errors = config.validate()
        assert len(errors) > 0
        assert "API基础URL不能为空" in errors[0]
    
    def test_validate_empty_model(self):
        """测试空模型名称"""
        config = APIConfig(api_key="key", base_url="https://api.test.com", model="")
        errors = config.validate()
        assert len(errors) > 0
        assert "模型名称不能为空" in errors[0]


class TestAppConfig:
    """测试应用配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = AppConfig()
        assert config.kb_data_dir == "data/raw"
        assert config.kb_index_dir == "index"
        assert config.projects_dir == "projects"
        assert config.log_level == "INFO"
        assert config.log_to_file is True
    
    def test_to_dict(self):
        """测试转换为字典"""
        config = AppConfig()
        data = config.to_dict()
        assert "story_api" in data
        assert "image_api" in data
        assert data["kb_data_dir"] == "data/raw"
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "story_api": {"api_key": "key", "base_url": "https://api.test.com", "model": "test"},
            "image_api": {"api_key": "", "base_url": "", "model": ""},
            "kb_data_dir": "custom/data",
            "kb_index_dir": "custom/index",
            "projects_dir": "custom/projects",
            "log_level": "DEBUG",
            "log_to_file": False
        }
        config = AppConfig.from_dict(data)
        assert config.kb_data_dir == "custom/data"
        assert config.log_level == "DEBUG"
        assert config.log_to_file is False


class TestConfigManager:
    """测试配置管理器"""
    
    def test_init_default_config(self):
        """测试默认初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            manager = ConfigManager(config_file=config_file)
            config = manager.get_config()
            assert isinstance(config, AppConfig)
    
    def test_save_and_load_config(self):
        """测试保存和加载配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            manager = ConfigManager(config_file=config_file)
            
            # 修改配置
            config = manager.get_config()
            config.kb_data_dir = "test/data"
            manager.save_config(config)
            
            # 重新加载
            manager2 = ConfigManager(config_file=config_file)
            config2 = manager2.get_config()
            assert config2.kb_data_dir == "test/data"
    
    def test_update_config(self):
        """测试更新配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            manager = ConfigManager(config_file=config_file)
            
            success = manager.update_config(kb_data_dir="updated/data")
            assert success
            
            config = manager.get_config()
            assert config.kb_data_dir == "updated/data"
    
    def test_validate_config(self):
        """测试配置验证"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            manager = ConfigManager(config_file=config_file)
            
            errors = manager.validate_config()
            # 默认配置应该有一些验证错误（API密钥为空等）
            assert isinstance(errors, list)

