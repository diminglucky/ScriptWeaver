"""
基础测试用例
"""

import pytest
from pathlib import Path
from src.core.exceptions import APIError, ConfigError
from src.core.exception_handler import ExceptionHandler, AppException


class TestExceptionHandler:
    """测试异常处理器"""
    
    def test_handle_app_exception(self):
        """测试处理应用异常"""
        exc = AppException("测试错误", user_message="用户友好的错误消息")
        msg = ExceptionHandler.handle_exception(exc)
        assert "用户友好的错误消息" in msg
    
    def test_handle_api_error(self):
        """测试处理API错误"""
        exc = APIError("API请求失败")
        msg = ExceptionHandler.handle_exception(exc)
        assert "API请求失败" in msg
    
    def test_handle_generic_exception(self):
        """测试处理通用异常"""
        exc = ValueError("值错误")
        msg = ExceptionHandler.handle_exception(exc)
        assert "输入值错误" in msg
    
    def test_safe_execute_success(self):
        """测试安全执行成功"""
        def test_func(x, y):
            return x + y
        
        result = ExceptionHandler.safe_execute(test_func, 2, 3)
        assert result == 5
    
    def test_safe_execute_failure(self):
        """测试安全执行失败"""
        def test_func():
            raise ValueError("测试错误")
        
        result = ExceptionHandler.safe_execute(test_func, default_return="默认值")
        assert result == "默认值"


class TestProjectStructure:
    """测试项目结构"""
    
    def test_project_root_exists(self, project_root_path):
        """测试项目根目录存在"""
        assert project_root_path.exists()
        assert project_root_path.is_dir()
    
    def test_src_directory_exists(self, project_root_path):
        """测试src目录存在"""
        src_dir = project_root_path / "src"
        assert src_dir.exists()
        assert src_dir.is_dir()
    
    def test_requirements_file_exists(self, project_root_path):
        """测试requirements.txt存在"""
        req_file = project_root_path / "requirements.txt"
        assert req_file.exists()


class TestImports:
    """测试关键模块导入"""
    
    def test_import_core_modules(self):
        """测试核心模块导入"""
        from src.core.exceptions import APIError, ConfigError
        from src.core.exception_handler import ExceptionHandler
        assert APIError
        assert ConfigError
        assert ExceptionHandler
    
    def test_import_client_modules(self):
        """测试客户端模块导入"""
        from src.clients.base_client import BaseAPIClient
        assert BaseAPIClient
    
    def test_import_project_manager(self):
        """测试项目管理器导入"""
        from src.project_manager import ProjectManager
        assert ProjectManager

