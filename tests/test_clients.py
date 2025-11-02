"""
API客户端测试用例
"""

import pytest
from unittest.mock import Mock, patch
from src.clients.base_client import BaseAPIClient, BaseChatClient
from src.core.exceptions import APIError


class TestAPIClient(BaseAPIClient):
    """测试用的API客户端"""
    
    def _make_request(self, **kwargs):
        return {"status": "ok"}


class TestChatClient(BaseChatClient):
    """测试用的聊天客户端"""
    
    def _make_request(self, **kwargs):
        return {"status": "ok"}
    
    def chat(self, messages, **kwargs):
        return "Test response"
    
    def stream(self, messages, **kwargs):
        yield "Test"
        yield " response"


class TestBaseAPIClient:
    """测试基础API客户端"""
    
    def test_init_valid(self):
        """测试有效初始化"""
        client = TestAPIClient(
            api_key="test_key",
            base_url="https://api.test.com",
            model="test-model"
        )
        assert client.api_key == "test_key"
        assert client.base_url == "https://api.test.com"
        assert client.model == "test-model"
    
    def test_init_empty_api_key(self):
        """测试空API密钥"""
        with pytest.raises(APIError, match="API密钥不能为空"):
            TestAPIClient(api_key="", base_url="https://api.test.com", model="test")
    
    def test_init_empty_base_url(self):
        """测试空基础URL"""
        with pytest.raises(APIError, match="API基础URL不能为空"):
            TestAPIClient(api_key="key", base_url="", model="test")
    
    def test_init_empty_model(self):
        """测试空模型名称"""
        with pytest.raises(APIError, match="模型名称不能为空"):
            TestAPIClient(api_key="key", base_url="https://api.test.com", model="")
    
    def test_base_url_stripping(self):
        """测试基础URL尾部斜杠去除"""
        client = TestAPIClient(
            api_key="key",
            base_url="https://api.test.com/",
            model="test"
        )
        assert client.base_url == "https://api.test.com"
    
    def test_handle_error_timeout(self):
        """测试超时错误处理"""
        client = TestAPIClient(
            api_key="key",
            base_url="https://api.test.com",
            model="test"
        )
        with pytest.raises(APIError, match="API请求超时"):
            client._handle_error(Exception("Connection timeout"))
    
    def test_handle_error_401(self):
        """测试401错误处理"""
        client = TestAPIClient(
            api_key="key",
            base_url="https://api.test.com",
            model="test"
        )
        with pytest.raises(APIError, match="API密钥无效"):
            client._handle_error(Exception("401 Unauthorized"))


class TestBaseChatClient:
    """测试聊天API客户端"""
    
    def test_chat_method(self):
        """测试聊天方法"""
        client = TestChatClient(
            api_key="key",
            base_url="https://api.test.com",
            model="test"
        )
        response = client.chat([{"role": "user", "content": "Hello"}])
        assert response == "Test response"
    
    def test_stream_method(self):
        """测试流式方法"""
        client = TestChatClient(
            api_key="key",
            base_url="https://api.test.com",
            model="test"
        )
        chunks = list(client.stream([{"role": "user", "content": "Hello"}]))
        assert chunks == ["Test", " response"]

