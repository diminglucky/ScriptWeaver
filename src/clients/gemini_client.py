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
            model: 模型名称（可选，默认gemini-1.5-flash）
            timeout_seconds: 超时时间（秒，默认300）
        """
        if genai is None:
            raise RuntimeError("Missing google-generativeai package. Install it with: pip install google-generativeai")
        
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("Missing GEMINI_API_KEY. Please set it in .env file or pass it as parameter.")
        
        # Gemini不需要base_url，但保留参数以兼容接口
        self.base_url = base_url or ""
        # 更新默认模型为 gemini-1.5-flash（更快）或 gemini-1.5-pro（更强）
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.timeout = timeout_seconds
        
        # 配置代理（如果需要）
        # 支持通过环境变量配置代理
        http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
        https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
        
        # google-generativeai 使用 httpx，需要在配置前设置代理环境变量
        if http_proxy or https_proxy:
            if http_proxy:
                os.environ["HTTP_PROXY"] = http_proxy
                os.environ["http_proxy"] = http_proxy
            if https_proxy:
                os.environ["HTTPS_PROXY"] = https_proxy
                os.environ["https_proxy"] = https_proxy
        
        # 配置Gemini API（使用transport参数配置超时）
        try:
            # 创建自定义的transport配置以支持代理和超时
            import google.generativeai as genai_config
            
            # 配置API密钥
            genai.configure(api_key=self.api_key)
            
        except Exception as e:
            error_msg = str(e)
            if "connect" in error_msg.lower() or "timeout" in error_msg.lower() or "503" in error_msg or "unavailable" in error_msg.lower():
                # 提供更详细的代理配置指导
                proxy_hint = ""
                if not (http_proxy or https_proxy):
                    proxy_hint = (
                        "\n\n⚠️ 检测到未配置代理。如果在中国大陆，需要配置代理才能访问 Google 服务：\n"
                        "方法1：在 .env 文件中添加：\n"
                        "  HTTPS_PROXY=http://127.0.0.1:7890\n"
                        "  HTTP_PROXY=http://127.0.0.1:7890\n"
                        "方法2：在系统环境变量中设置 HTTPS_PROXY 和 HTTP_PROXY\n"
                        "方法3：启动代理软件（如 Clash、V2Ray 等）并确保系统代理已开启"
                    )
                else:
                    proxy_hint = f"\n\n当前代理配置：\n  HTTP_PROXY={http_proxy}\n  HTTPS_PROXY={https_proxy}\n请确认代理服务正在运行且配置正确。"
                
                raise RuntimeError(
                    f"无法连接到 Gemini API（已连接失败）。{proxy_hint}\n\n"
                    f"错误详情：{error_msg}"
                )
            elif "api_key" in error_msg.lower() or "401" in error_msg or "403" in error_msg:
                raise RuntimeError(f"Gemini API 密钥无效或已过期。请检查 GEMINI_API_KEY 是否正确。\n错误详情：{error_msg}")
            else:
                raise RuntimeError(f"Failed to configure Gemini API: {error_msg}")
        
        # 创建模型实例
        try:
            self.client = genai.GenerativeModel(self.model)
        except Exception as e:
            error_msg = str(e)
            if "model" in error_msg.lower() or "404" in error_msg:
                raise RuntimeError(
                    f"模型 '{self.model}' 不存在或不可用。\n"
                    f"请尝试使用以下模型之一：\n"
                    f"- gemini-1.5-flash（推荐，快速）\n"
                    f"- gemini-1.5-pro（更强，但较慢）\n"
                    f"- gemini-pro（旧版本）\n"
                    f"错误详情：{error_msg}"
                )
            else:
                raise RuntimeError(f"初始化 Gemini 模型 '{self.model}' 失败：{error_msg}")

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
        use_model = model or self.model  # 在循环外定义，以便在错误处理中使用
        for attempt in range(3):
            try:
                # 如果指定了不同的模型，创建新的模型实例
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
                error_msg = str(e).lower()
                
                # 如果是连接错误，提供更详细的提示
                if attempt == 0 and ("connect" in error_msg or "timeout" in error_msg or "network" in error_msg or "connection" in error_msg):
                    # 第一次尝试失败时，给出提示
                    print(f"⚠️  Gemini API 连接失败（尝试 {attempt + 1}/3）。如果在中国大陆，可能需要配置代理。")
                    print(f"   提示：设置环境变量 HTTP_PROXY 或 HTTPS_PROXY，例如：")
                    print(f"   export HTTPS_PROXY=http://127.0.0.1:7890")
                
                # 指数退避：0.4s, 0.8s, 1.6s
                if attempt < 2:  # 最后一次不需要等待
                    time.sleep(0.4 * (2 ** attempt))
        
        # 统一抛出可理解的错误
        error_msg = str(last_err).lower() if last_err else "未知错误"
        
        # 检查代理配置
        http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
        https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
        
        if "connect" in error_msg or "timeout" in error_msg or "network" in error_msg or "connection" in error_msg or "503" in str(last_err) or "unavailable" in error_msg:
            proxy_hint = ""
            if not (http_proxy or https_proxy):
                proxy_hint = (
                    "\n\n⚠️ 检测到未配置代理。如果在中国大陆，需要配置代理才能访问 Google 服务：\n"
                    "方法1：在 .env 文件中添加：\n"
                    "  HTTPS_PROXY=http://127.0.0.1:7890\n"
                    "  HTTP_PROXY=http://127.0.0.1:7890\n"
                    "方法2：在系统环境变量中设置 HTTPS_PROXY 和 HTTP_PROXY\n"
                    "方法3：启动代理软件（如 Clash、V2Ray 等）并确保系统代理已开启"
                )
            else:
                proxy_hint = f"\n\n当前代理配置：\n  HTTP_PROXY={http_proxy}\n  HTTPS_PROXY={https_proxy}\n请确认代理服务正在运行且配置正确。"
            
            raise RuntimeError(
                f"无法连接到 Gemini API（已重试3次）。{proxy_hint}\n\n"
                f"错误详情：{last_err}"
            )
        elif "api_key" in error_msg or "401" in str(last_err) or "403" in str(last_err):
            raise RuntimeError(f"Gemini API 密钥无效或已过期。请检查 GEMINI_API_KEY 是否正确。\n错误详情：{last_err}")
        elif "model" in error_msg or "404" in str(last_err):
            raise RuntimeError(
                f"模型 '{use_model}' 不存在或不可用。\n"
                f"请尝试使用：gemini-1.5-flash 或 gemini-1.5-pro\n"
                f"错误详情：{last_err}"
            )
        else:
            raise RuntimeError(f"聊天生成失败，请检查网络或API配置。\n错误详情：{last_err}")

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

