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

