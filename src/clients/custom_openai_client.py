"""
自定义 OpenAI 客户端 - 移除会被 Cloudflare 阻止的请求头
"""

from openai import OpenAI
import httpx
from typing import Optional


class CustomHTTPTransport(httpx.HTTPTransport):
    """自定义 HTTP Transport - 移除会被 Cloudflare 阻止的请求头"""
    
    def handle_request(self, request: httpx.Request) -> httpx.Response:
        # 移除所有 x-stainless-* 请求头
        headers_to_remove = [key for key in request.headers.keys() if key.lower().startswith('x-stainless-')]
        for header in headers_to_remove:
            del request.headers[header]
        
        # 修改 User-Agent 为通用值（避免被识别为 OpenAI SDK）
        if 'user-agent' in request.headers:
            # 使用 httpx 的默认 User-Agent
            request.headers['user-agent'] = f'python-httpx/{httpx.__version__}'
        
        # 发送请求
        return super().handle_request(request)


def create_compatible_client(
    api_key: str,
    base_url: str,
    timeout: float = 300.0
) -> OpenAI:
    """
    创建兼容 Cloudflare 防火墙的 OpenAI 客户端
    
    移除 x-stainless-* 请求头并修改 User-Agent，避免被某些 API 平台的防火墙阻止
    
    参数:
        api_key: API 密钥
        base_url: API 基础 URL
        timeout: 超时时间（秒）
    
    返回:
        配置好的 OpenAI 客户端
    """
    http_client = httpx.Client(
        transport=CustomHTTPTransport(),
        timeout=timeout
    )
    
    return OpenAI(
        api_key=api_key,
        base_url=base_url,
        http_client=http_client
    )
