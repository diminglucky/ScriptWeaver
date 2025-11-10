from __future__ import annotations

import os
from typing import List, Optional, Any
import time

from openai import OpenAI


class DeepSeekClient:
	"""Thin wrapper for DeepSeek's OpenAI-compatible chat API."""

	def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None, timeout_seconds: int = 300) -> None:
		self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
		if not self.api_key:
			raise RuntimeError("Missing DEEPSEEK_API_KEY. Create .env and export it.")
		self.base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
		self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
		self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=timeout_seconds)

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
		# 简单重试机制，提升健壮性
		last_err: Any = None
		for attempt in range(3):
			try:
				resp = self.client.chat.completions.create(
					model=model or self.model,
					messages=messages,
					temperature=temperature,
					max_tokens=max_tokens,
					top_p=top_p,
					presence_penalty=presence_penalty,
					frequency_penalty=frequency_penalty,
				)
				return resp.choices[0].message.content or ""
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
	):
		try:
			# ★★★ 构建请求参数，只包含非None的参数 ★★★
			params = {
				"model": model or self.model,
				"messages": messages,
				"temperature": temperature,
				"stream": True,
			}
			
			# 只添加非None的可选参数
			if max_tokens is not None:
				params["max_tokens"] = max_tokens
			if top_p is not None:
				params["top_p"] = top_p
			if presence_penalty is not None:
				params["presence_penalty"] = presence_penalty
			if frequency_penalty is not None:
				params["frequency_penalty"] = frequency_penalty
			
			print(f"[DEBUG] DeepSeek流式请求参数: model={params['model']}, temperature={params['temperature']}, max_tokens={params.get('max_tokens', 'None')}")
			
			stream = self.client.chat.completions.create(**params)
			
			for chunk in stream:
				if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
					yield chunk.choices[0].delta.content
		except Exception as e:
			# ★★★ 打印详细错误信息，便于调试 ★★★
			print(f"❌ DeepSeek流式调用失败: {type(e).__name__}: {e}")
			
			# 尝试提取更详细的错误信息
			if hasattr(e, 'response'):
				print(f"   响应状态码: {getattr(e.response, 'status_code', 'N/A')}")
				print(f"   响应内容: {getattr(e.response, 'text', 'N/A')[:500]}")
			
			import traceback
			traceback.print_exc()
			# 流失败直接返回空生成，避免阻塞UI
			yield from []

