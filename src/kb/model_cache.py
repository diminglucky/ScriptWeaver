from __future__ import annotations

from functools import lru_cache

try:
	from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:  # pragma: no cover - optional dependency
	SentenceTransformer = None  # type: ignore


@lru_cache(maxsize=4)
def get_sentence_transformer(model_name: str):
	"""缓存 SentenceTransformer，避免重复加载模型导致卡顿"""
	if SentenceTransformer is None:
		raise RuntimeError(
			"知识库依赖缺失，暂时无法加载向量模型。"
			"\n缺失包: sentence-transformers"
			"\n请先安装后再试: pip install sentence-transformers"
		)
	return SentenceTransformer(model_name)
