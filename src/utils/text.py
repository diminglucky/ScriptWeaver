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

