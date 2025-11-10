"""客户端工厂函数 - 根据API名称创建相应的客户端"""

from typing import Optional, Any
from src.clients.deepseek_client import DeepSeekClient
from src.clients.gemini_client import GeminiClient
from src.utils.text import sanitize as _sanitize


def create_chat_client(
    api_name: str,
    api_key: str,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    timeout_seconds: int = 300
) -> Any:
    """
    根据API名称创建相应的聊天客户端
    
    Args:
        api_name: API名称（如 "DeepSeek", "Gemini", "OpenAI"）
        api_key: API密钥
        base_url: API基础URL（可选）
        model: 模型名称（可选）
        timeout_seconds: 超时时间（秒，默认300）
    
    Returns:
        相应的客户端实例
    
    Raises:
        ValueError: 不支持的API名称
    """
    api_name = api_name.strip()
    
    # 清理参数
    api_key = _sanitize(api_key) if api_key else ""
    base_url = _sanitize(base_url) if base_url else ""
    model = _sanitize(model) if model else ""
    
    if not api_key:
        raise ValueError(f"API密钥不能为空（{api_name}）")
    
    # 根据API名称创建相应的客户端
    if api_name.lower() == "gemini" or ("gemini" in api_name.lower()):
        # Gemini不需要base_url，但保留参数以兼容接口
        return GeminiClient(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout_seconds=timeout_seconds
        )
    elif api_name.lower() == "deepseek" or ("deepseek" in api_name.lower()):
        return DeepSeekClient(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout_seconds=timeout_seconds
        )
    elif api_name.lower() == "openai" or ("openai" in api_name.lower()):
        # OpenAI也使用OpenAI兼容的客户端（DeepSeekClient实际上就是OpenAI兼容的）
        return DeepSeekClient(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout_seconds=timeout_seconds
        )
    else:
        # 默认使用DeepSeekClient（OpenAI兼容）
        # 这样可以支持其他OpenAI兼容的API
        return DeepSeekClient(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout_seconds=timeout_seconds
        )

