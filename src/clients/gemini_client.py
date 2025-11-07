from __future__ import annotations

import os
from typing import List, Optional, Any, Generator
import time

try:
    import google.generativeai as genai
except ImportError:
    genai = None


class GeminiClient:
    """Google Gemini API客户端"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None, timeout_seconds: int = 300) -> None:
        """
        初始化Gemini客户端
        
        Args:
            api_key: API密钥（可选，从环境变量读取）
            base_url: API基础URL（可选，Gemini不使用base_url，但保留以兼容接口）
            model: 模型名称（可选，默认gemini-pro）
            timeout_seconds: 超时时间（秒，默认300）
        """
        if genai is None:
            raise RuntimeError("Missing google-generativeai package. Install it with: pip install google-generativeai")
        
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("Missing GEMINI_API_KEY. Please set it in .env file or pass it as parameter.")
        
        # Gemini不需要base_url，但保留参数以兼容接口
        self.base_url = base_url or ""
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-pro")
        self.timeout = timeout_seconds
        
        # 配置Gemini API
        genai.configure(api_key=self.api_key)
        
        # 创建模型实例
        try:
            self.client = genai.GenerativeModel(self.model)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Gemini model '{self.model}': {str(e)}")

    def chat(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
    ) -> str:
        """
        同步聊天接口
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}, ...]
            model: 模型名称（可选，覆盖初始化时的模型）
            temperature: 温度参数（0.0-1.0）
            max_tokens: 最大token数（可选）
            top_p: Top-p采样参数（可选）
            presence_penalty: 存在惩罚（Gemini不支持，忽略）
            frequency_penalty: 频率惩罚（Gemini不支持，忽略）
        
        Returns:
            助手回复内容
        """
        if genai is None:
            raise RuntimeError("Missing google-generativeai package. Install it with: pip install google-generativeai")
        
        # 简单重试机制，提升健壮性
        last_err: Any = None
        for attempt in range(3):
            try:
                # 如果指定了不同的模型，创建新的模型实例
                use_model = model or self.model
                if use_model != self.model:
                    client = genai.GenerativeModel(use_model)
                else:
                    client = self.client
                
                # 构建生成配置
                generation_config = {
                    "temperature": temperature,
                }
                if max_tokens:
                    generation_config["max_output_tokens"] = max_tokens
                if top_p:
                    generation_config["top_p"] = top_p
                
                # 转换消息格式
                # Gemini支持对话历史，但格式不同
                chat_history = []
                current_prompt = ""
                
                for msg in messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    
                    if role == "system":
                        # 系统消息作为prompt的一部分
                        current_prompt = content + "\n\n" if current_prompt else content + "\n\n"
                    elif role == "user":
                        if current_prompt:
                            # 如果之前有系统消息，将其添加到历史中
                            chat_history.append({"role": "user", "parts": [current_prompt]})
                            current_prompt = ""
                        chat_history.append({"role": "user", "parts": [content]})
                    elif role == "assistant":
                        chat_history.append({"role": "model", "parts": [content]})
                
                # 如果有系统消息但还没有添加到历史，将其作为最后一条用户消息的一部分
                if current_prompt:
                    if chat_history and chat_history[-1].get("role") == "user":
                        # 将系统消息添加到最后一条用户消息的开头
                        chat_history[-1]["parts"][0] = current_prompt + chat_history[-1]["parts"][0]
                    else:
                        chat_history.append({"role": "user", "parts": [current_prompt]})
                
                # 如果有历史记录，使用对话历史；否则使用简单prompt
                if len(chat_history) > 1:
                    # 使用对话历史（最后一条是用户消息）
                    last_user_msg = chat_history[-1]["parts"][0] if chat_history else ""
                    history = chat_history[:-1] if len(chat_history) > 1 else []
                    
                    if history:
                        # 使用chat方法支持历史记录
                        chat = client.start_chat(history=history)
                        response = chat.send_message(
                            last_user_msg,
                            generation_config=genai.types.GenerationConfig(**generation_config)
                        )
                    else:
                        # 没有历史，直接生成
                        response = client.generate_content(
                            last_user_msg,
                            generation_config=genai.types.GenerationConfig(**generation_config)
                        )
                else:
                    # 只有一条消息，直接生成
                    prompt = chat_history[0]["parts"][0] if chat_history else ""
                    response = client.generate_content(
                        prompt,
                        generation_config=genai.types.GenerationConfig(**generation_config)
                    )
                
                # 提取响应文本
                if response and response.text:
                    return response.text
                else:
                    raise RuntimeError("Empty response from Gemini API")
                    
            except Exception as e:
                last_err = e
                # 指数退避：0.4s, 0.8s
                time.sleep(0.4 * (2 ** attempt))
        
        # 统一抛出可理解的错误
        raise RuntimeError(f"聊天生成失败，请检查网络或API配置。详情：{last_err}")

    def stream(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
    ) -> Generator[str, None, None]:
        """
        流式聊天接口
        
        Args:
            messages: 消息列表
            model: 模型名称（可选）
            temperature: 温度参数
            max_tokens: 最大token数（可选）
            top_p: Top-p采样参数（可选）
            presence_penalty: 存在惩罚（Gemini不支持，忽略）
            frequency_penalty: 频率惩罚（Gemini不支持，忽略）
        
        Yields:
            助手回复片段
        """
        if genai is None:
            return
        
        try:
            # 如果指定了不同的模型，创建新的模型实例
            use_model = model or self.model
            if use_model != self.model:
                client = genai.GenerativeModel(use_model)
            else:
                client = self.client
            
            # 构建生成配置
            generation_config = {
                "temperature": temperature,
            }
            if max_tokens:
                generation_config["max_output_tokens"] = max_tokens
            if top_p:
                generation_config["top_p"] = top_p
            
            # 转换消息格式（与chat方法相同的逻辑）
            chat_history = []
            current_prompt = ""
            
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "system":
                    current_prompt = content + "\n\n" if current_prompt else content + "\n\n"
                elif role == "user":
                    if current_prompt:
                        chat_history.append({"role": "user", "parts": [current_prompt]})
                        current_prompt = ""
                    chat_history.append({"role": "user", "parts": [content]})
                elif role == "assistant":
                    chat_history.append({"role": "model", "parts": [content]})
            
            if current_prompt:
                if chat_history and chat_history[-1].get("role") == "user":
                    chat_history[-1]["parts"][0] = current_prompt + chat_history[-1]["parts"][0]
                else:
                    chat_history.append({"role": "user", "parts": [current_prompt]})
            
            # 流式调用API
            if len(chat_history) > 1:
                last_user_msg = chat_history[-1]["parts"][0] if chat_history else ""
                history = chat_history[:-1] if len(chat_history) > 1 else []
                
                if history:
                    chat = client.start_chat(history=history)
                    response = chat.send_message(
                        last_user_msg,
                        generation_config=genai.types.GenerationConfig(**generation_config),
                        stream=True
                    )
                else:
                    response = client.generate_content(
                        last_user_msg,
                        generation_config=genai.types.GenerationConfig(**generation_config),
                        stream=True
                    )
            else:
                prompt = chat_history[0]["parts"][0] if chat_history else ""
                response = client.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(**generation_config),
                    stream=True
                )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception:
            # 流失败直接返回空生成，避免阻塞UI
            yield from []

