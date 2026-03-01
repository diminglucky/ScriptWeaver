"""GUI-level utility wrappers."""

from __future__ import annotations

import re

from src.utils.text import (
	sanitize as _sanitize,
	try_chat_api as _try_chat_api,
	try_image_api as _try_image_api,
)


def sanitize(s: str) -> str:
	"""Normalize API input text."""
	return _sanitize(s)


def try_chat_api(key: str, base_url: str, model: str) -> tuple[bool, str]:
	"""Compat wrapper that delegates to the robust shared implementation."""
	return _try_chat_api(key, base_url, model)


def try_image_api(key: str, base_url: str, model: str) -> tuple[bool, str]:
	"""Compat wrapper that delegates to the robust shared implementation."""
	return _try_image_api(key, base_url, model)


def estimate_chars_from_outline(outline: str) -> int:
	"""Estimate total chars from outline lines."""
	lines = [ln.strip() for ln in outline.splitlines() if ln.strip()]
	sections = []
	for line in lines:
		match = re.search(r"\((\d+)字\)", line)
		if match:
			sections.append(int(match.group(1)))

	if not sections:
		return len([ln for ln in lines if re.match(r"^[\d一二三四五六七八九十]+[、\.]", ln)]) * 1000

	return sum(sections)


def parse_outline_sections(outline: str) -> list[dict[str, str]]:
	"""Parse outline into section list."""
	lines = [ln.strip() for ln in outline.splitlines() if ln.strip()]
	sections = []

	for line in lines:
		match = re.match(r"^([\d一二三四五六七八九十]+)[、\.](.+)", line)
		if not match:
			continue
		num, title = match.groups()
		chars = 1000
		chars_match = re.search(r"\((\d+)字\)", title)
		if chars_match:
			chars = int(chars_match.group(1))
			title = re.sub(r"\s*\(\d+字\)", "", title).strip()

		sections.append(
			{
				"num": num,
				"title": title.strip(),
				"chars": chars,
			}
		)

	return sections
