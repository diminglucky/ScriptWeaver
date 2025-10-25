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
			stream = self.client.chat.completions.create(
				model=model or self.model,
				messages=messages,
				temperature=temperature,
				max_tokens=max_tokens,
				top_p=top_p,
				presence_penalty=presence_penalty,
				frequency_penalty=frequency_penalty,
				stream=True,
			)
			for chunk in stream:
				if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
					yield chunk.choices[0].delta.content
		except Exception:
			# 流失败直接返回空生成，避免阻塞UI
			yield from []

