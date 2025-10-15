"""基础客户端类"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, List, Optional

from src.core.exceptions import APIError
from src.core.logging_config import get_logger

logger = get_logger(__name__)


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
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            model: 模型名称
            timeout: 超时时间（秒）
        
        Raises:
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
    
    @abstractmethod
    def _make_request(self, **kwargs: Any) -> Any:
        """
        执行API请求（需子类实现）
        
        Returns:
            API响应
        
        Raises:
            APIError: API请求失败
        """
        pass
    
    def _handle_error(self, error: Exception) -> None:
        """
        统一错误处理
        
        Args:
            error: 原始异常
        
        Raises:
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
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
        
        Returns:
            助手回复内容
        
        Raises:
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
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
        
        Yields:
            助手回复片段
        
        Raises:
            APIError: API请求失败
        """
        pass


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
        
        Args:
            prompt: 提示词
            **kwargs: 其他参数
        
        Returns:
            生成的图片
        
        Raises:
            APIError: API请求失败
        """
        pass

