"""GUI工具函数"""

from openai import OpenAI


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
		client = OpenAI(api_key=key, base_url=base_url, timeout=20)
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


import re

