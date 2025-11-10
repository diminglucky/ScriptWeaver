from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List


def discover_text_files(root: str | os.PathLike[str]) -> List[Path]:
	"""Recursively discover likely text files (.txt, .md, .markdown, .md.txt)."""
	root_path = Path(root)
	candidates: List[Path] = []
	for path in root_path.rglob("*"):
		if path.is_file():
			lower = path.name.lower()
			if lower.endswith(".txt") or lower.endswith(".md") or lower.endswith(".markdown"):
				candidates.append(path)
	return sorted(candidates)


def read_file_text(path: Path) -> str:
	with path.open("r", encoding="utf-8", errors="ignore") as f:
		return f.read()


def clean_text(text: str) -> str:
	# Normalize line breaks and collapse excessive whitespace.
	text = text.replace("\r\n", "\n").replace("\r", "\n")
	text = re.sub("\u3000", " ", text)  # full-width space
	text = re.sub("\n{3,}", "\n\n", text)
	return text.strip()


def split_by_length(text: str, max_chars: int = 800, overlap: int = 120) -> List[str]:
	"""Character-based splitter that tries to respect sentence boundaries."""
	if not text:
		return []
	sentences = re.split(r"(?<=[。！？!?.])\s+", text)
	chunks: List[str] = []
	current: List[str] = []
	current_len = 0
	for s in sentences:
		s_len = len(s)
		if current_len + s_len <= max_chars or not current:
			current.append(s)
			current_len += s_len
		else:
			chunks.append("".join(current).strip())
			# Add overlap by taking tail of previous chunk
			if overlap > 0 and chunks[-1]:
				tail = chunks[-1][-overlap:]
				current = [tail, s]
				current_len = len(tail) + s_len
			else:
				current = [s]
				current_len = s_len
	if current:
		chunks.append("".join(current).strip())
	# Filter tiny chunks
	return [c for c in chunks if len(c) > 20]


def sanitize(s: str) -> str:
	"""清理字符串中的特殊字符和前缀"""
	# Remove quotes, bearer prefix, and exotic spaces
	val = (s or "")
	val = val.replace("\u200b", "").replace("\u2003", " ").replace("\u00A0", " ")
	val = val.strip().strip('"').strip("'")
	if val.lower().startswith("bearer "):
		val = val[7:].strip()
	return val


def try_chat_api(key: str, base_url: str, model: str) -> tuple[bool, str]:
	"""测试聊天API是否可用"""
	# 检查是否是 Gemini API（通过模型名称判断）
	# 确保model是字符串且包含gemini
	is_gemini = bool(model and isinstance(model, str) and "gemini" in model.lower())
	
	if is_gemini:
		try:
			from src.clients.gemini_client import GeminiClient
			# Gemini 不需要 base_url，使用空字符串
			client = GeminiClient(api_key=key, base_url="", model=model, timeout_seconds=30)
			# 发送一个简单的测试消息
			response = client.chat(
				messages=[{"role": "user", "content": "ping"}],
				max_tokens=5
			)
			if response:
				return True, "Gemini API 连接成功"
			else:
				return False, "Gemini API 返回空响应"
		except Exception as e:
			error_msg = str(e)
			# 提供更友好的错误信息
			if "connect" in error_msg.lower() or "timeout" in error_msg.lower():
				return False, f"连接失败: {error_msg}（可能需要配置代理）"
			elif "api_key" in error_msg.lower() or "401" in error_msg or "403" in error_msg:
				return False, f"API密钥无效: {error_msg}"
			elif "model" in error_msg.lower() or "404" in error_msg:
				return False, f"模型不存在: {error_msg}（请检查模型名称，如 gemini-1.5-flash）"
			else:
				return False, f"Gemini API 错误: {error_msg}"
	
	# 其他 API 使用 OpenAI 兼容接口
	# 注意：Gemini API 不应该走到这里
	if is_gemini:
		return False, f"错误：检测到 Gemini 模型 '{model}' 但使用了错误的测试方法"
	
	try:
		from openai import OpenAI
		client = OpenAI(api_key=key, base_url=base_url, timeout=200)
		resp = client.chat.completions.create(
			model=model,
			messages=[{"role": "user", "content": "ping"}],
			max_tokens=5
		)
		_ok = bool(resp.choices and resp.choices[0].message)
		return True, "ok"
	except Exception as e:
		return False, str(e)


def try_image_api(key: str, base_url: str, model: str) -> tuple[bool, str]:
	"""测试图片生成API是否可用"""
	try:
		# 检查是否是本地SD（根据model或base_url判断）
		if model == "sd-local" or "localhost" in base_url or "127.0.0.1" in base_url:
			return _try_sd_api(base_url, model)
		
		# 否则使用OpenAI兼容API
		from openai import OpenAI
		client = OpenAI(api_key=key, base_url=base_url, timeout=30)
		
		# 根据模型选择合适的测试参数
		if "dall-e-2" in model.lower():
			# DALL-E-2 建议用较小的尺寸测试，速度快且省钱
			size = "512x512"
		else:
			# DALL-E-3 和其他模型用标准尺寸
			size = "1024x1024"
		
		# 尝试生成一个简单的测试图片（不强制要求格式）
		resp = client.images.generate(
			model=model,
			prompt="a simple test image",
			n=1,
			size=size
		)
		_ok = bool(resp.data and len(resp.data) > 0)
		
		# 检查返回的数据类型
		has_url = hasattr(resp.data[0], 'url') and resp.data[0].url
		has_b64 = hasattr(resp.data[0], 'b64_json') and resp.data[0].b64_json
		
		if has_url:
			return True, f"图片API测试成功 (返回URL格式，尺寸:{size})"
		elif has_b64:
			return True, f"图片API测试成功 (返回Base64格式，尺寸:{size})"
		else:
			return True, f"图片API测试成功 (尺寸:{size})"
	except Exception as e:
		return False, str(e)


def _try_sd_api(base_url: str, model: str) -> tuple[bool, str]:
	"""测试本地Stable Diffusion API"""
	try:
		import requests
		import json
		
		# 确保base_url不以/v1结尾（SD API不需要）
		base_url = base_url.rstrip('/')
		if base_url.endswith('/v1'):
			base_url = base_url[:-3].rstrip('/')
		
		# 测试连接：获取模型列表
		test_url = f"{base_url}/sdapi/v1/sd-models"
		response = requests.get(test_url, timeout=10)
		
		if response.status_code == 200:
			models = response.json()
			return True, f"SD WebUI连接成功，找到{len(models)}个模型"
		else:
			return False, f"Error code: {response.status_code}"
	
	except requests.exceptions.ConnectionError:
		return False, "无法连接到Stable Diffusion WebUI（检查是否启动且带--api参数）"
	except requests.exceptions.Timeout:
		return False, "连接超时（WebUI响应过慢）"
	except Exception as e:
		return False, str(e)


def estimate_chars_from_outline(outline: str) -> int:
	"""根据大纲估算总字数"""
	lines = [ln.strip() for ln in outline.splitlines() if ln.strip()]
	sections = []
	for line in lines:
		# 匹配：1. XXX (1000字) 或 一、XXX (1000字)
		match = re.search(r'\((\d+)字\)', line)
		if match:
			sections.append(int(match.group(1)))
	
	if not sections:
		# 如果没有标注字数，按默认每段1000字估算
		return len([ln for ln in lines if re.match(r'^[\d一二三四五六七八九十]+[、\.]', ln)]) * 1000
	
	return sum(sections)


def parse_outline_sections(outline: str) -> list[dict[str, str]]:
	"""解析大纲为章节列表"""
	lines = [ln.strip() for ln in outline.splitlines() if ln.strip()]
	sections = []
	
	for line in lines:
		# 匹配序号开头的行
		match = re.match(r'^([\d一二三四五六七八九十]+)[、\.](.+)', line)
		if match:
			num, title = match.groups()
			
			# 提取字数（如果有）
			chars = 1000  # 默认字数
			chars_match = re.search(r'\((\d+)字\)', title)
			if chars_match:
				chars = int(chars_match.group(1))
				# 去掉字数标注
				title = re.sub(r'\s*\(\d+字\)', '', title).strip()
			
			sections.append({
				'num': num,
				'title': title.strip(),
				'chars': chars
			})
	
	return sections

