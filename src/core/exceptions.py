"""自定义异常类"""

from __future__ import annotations


class APIError(Exception):
    """API相关错误"""
    pass


class ConfigError(Exception):
    """配置相关错误"""
    pass


class ValidationError(Exception):
    """数据验证错误"""
    pass


class FileOperationError(Exception):
    """文件操作错误"""
    pass


class KnowledgeBaseError(Exception):
    """知识库相关错误"""
    pass
