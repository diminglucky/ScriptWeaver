from __future__ import annotations

import base64
import os
import requests
from dataclasses import dataclass
from io import BytesIO
from typing import List, Optional, Tuple

from PIL import Image
from openai import OpenAI
import time


@dataclass
class ImageResult:
	image: Image.Image
	seed: Optional[int]
	provider: str
	model: str


class OpenAIImageClient:
	"""Minimal OpenAI image client using images.generate.

	Note: OpenAI does not expose a stable seed for perfect determinism. We keep
	the parameter for a unified interface; the backend may ignore it.
	"""

	def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "gpt-image-1", timeout_seconds: int = 120) -> None:
		key = api_key or os.getenv("OPENAI_API_KEY", "")
		if not key:
			raise RuntimeError("Missing OPENAI_API_KEY for image generation")
		# 空字符串时不传 base_url，避免SDK报错
		self.client = OpenAI(api_key=key, base_url=(base_url or None), timeout=timeout_seconds)
		self.model = model

	def generate(self, prompt: str, *, seed: Optional[int] = None, size: str = "1024x1024", n: int = 1) -> List[ImageResult]:
		# 先尝试使用 base64 格式
		try:
			resp = self.client.images.generate(
				model=self.model, 
				prompt=prompt, 
				size=size, 
				n=n,
				response_format="b64_json"
			)
			
			# 检查响应是否有效
			if resp is None:
				raise RuntimeError("API调用返回None，可能是网络问题或API服务异常")
			if not hasattr(resp, 'data') or resp.data is None:
				raise RuntimeError("API响应中缺少data字段，可能是API格式不兼容")
			
			results: List[ImageResult] = []
			for d in resp.data:
				b64 = d.b64_json
				img_bytes = base64.b64decode(b64)
				img = Image.open(BytesIO(img_bytes)).convert("RGB")
				results.append(ImageResult(image=img, seed=seed, provider="openai", model=self.model))
			return results
		except Exception as e:
			# 如果 base64 失败，尝试 URL 格式（V-API 默认格式）
			error_msg = str(e).lower()
			if "response_format" in error_msg or "format" in error_msg or "b64_json" in error_msg:
				# 带简单重试的兜底
				last_err: Exception | None = None
				resp = None
				for attempt in range(3):
					try:
						resp = self.client.images.generate(
							model=self.model, 
							prompt=prompt, 
							size=size, 
							n=n
						)
						break
					except Exception as gen_err:
						last_err = gen_err
						time.sleep(0.4 * (2 ** attempt))
				if resp is None:
					raise RuntimeError(f"API调用失败：{last_err}")
				
				# 检查响应是否有效
				if not hasattr(resp, 'data') or resp.data is None:
					raise RuntimeError("API响应中缺少data字段，可能是API格式不兼容")
				
				results: List[ImageResult] = []
				for d in resp.data:
					# 从 URL 下载图片
					if hasattr(d, 'url') and d.url:
						img_bytes = None
						last_req_err: Exception | None = None
						for attempt in range(3):
							try:
								img_response = requests.get(d.url, timeout=30)
								img_response.raise_for_status()
								img_bytes = img_response.content
								break
							except Exception as req_err:
								last_req_err = req_err
								time.sleep(0.4 * (2 ** attempt))
						if img_bytes is None:
							raise RuntimeError(f"下载图片失败：{last_req_err}")
						img = Image.open(BytesIO(img_bytes)).convert("RGB")
						results.append(ImageResult(image=img, seed=seed, provider="openai", model=self.model))
					else:
						raise RuntimeError("API返回的数据中既没有b64_json也没有url")
				return results
			else:
				raise

	def generate_with_reference(self, prompt: str, reference_image_path: str, *, size: str = "1024x1024") -> List[ImageResult]:
		"""Create images guided by a reference image (identity consistency).

		This uses the images.edits API with the reference image and prompt.
		If the backend ignores edits for the chosen model, we gracefully fall
		back to plain generation.
		"""
		try:
			# 先尝试使用 base64 格式
			try:
				with open(reference_image_path, "rb") as f:
					resp = self.client.images.edits(
						model=self.model, 
						image=f, 
						prompt=prompt, 
						size=size,
						response_format="b64_json"
					)
				results: List[ImageResult] = []
				for d in resp.data:
					b64 = d.b64_json
					img_bytes = base64.b64decode(b64)
					img = Image.open(BytesIO(img_bytes)).convert("RGB")
					results.append(ImageResult(image=img, seed=None, provider="openai", model=self.model))
				return results
			except Exception as e:
				# 如果 base64 失败，尝试 URL 格式
				error_msg = str(e).lower()
				if "response_format" in error_msg or "format" in error_msg:
					with open(reference_image_path, "rb") as f:
						resp = self.client.images.edits(
							model=self.model, 
							image=f, 
							prompt=prompt, 
							size=size
						)
					results: List[ImageResult] = []
					for d in resp.data:
						# 从 URL 下载图片
						if hasattr(d, 'url') and d.url:
							img_bytes = None
							last_req_err: Exception | None = None
							for attempt in range(3):
								try:
									img_response = requests.get(d.url, timeout=30)
									img_response.raise_for_status()
									img_bytes = img_response.content
									break
								except Exception as req_err:
									last_req_err = req_err
									time.sleep(0.4 * (2 ** attempt))
							if img_bytes is None:
								raise RuntimeError(f"下载图片失败：{last_req_err}")
							img = Image.open(BytesIO(img_bytes)).convert("RGB")
							results.append(ImageResult(image=img, seed=None, provider="openai", model=self.model))
						else:
							raise RuntimeError("API返回的数据中既没有b64_json也没有url")
					return results
				else:
					raise
		except Exception:
			# Fallback to pure text prompt if edits unsupported
			return self.generate(prompt=prompt, size=size, n=1)


