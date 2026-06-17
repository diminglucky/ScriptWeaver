from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from src.services.rag_service.core.embedding_hub import DEFAULT_MODEL_NAME, EmbeddingHub
from src.services.rag_service.core.index_hub import IndexHub


def _load_kb_backends():
	"""Load Chroma + embedding dependencies lazily."""
	missing: list[str] = []
	try:
		import chromadb  # noqa: F401
	except Exception:
		missing.append("chromadb")
	try:
		import sentence_transformers  # noqa: F401
	except Exception:
		missing.append("sentence-transformers")
	if missing:
		pkgs = ", ".join(missing)
		raise RuntimeError(
			"知识库依赖缺失，暂时无法检索索引。"
			f"\n缺失包: {pkgs}"
			"\n请先安装后再试: pip install chromadb sentence-transformers"
		)
	return True


@dataclass
class SearchConfig:
	index_dir: Path
	embedding_model_name: str = DEFAULT_MODEL_NAME
	top_k: int = 6
	kb_type: str = "reference"
	project_id: str | None = None


class KnowledgeBaseSearcher:
	def __init__(self, config: SearchConfig) -> None:
		self.config = config
		_load_kb_backends()
		self.embedder = EmbeddingHub(config.embedding_model_name)
		try:
			from src.kb.model_cache import get_sentence_transformer
			self.model = get_sentence_transformer(config.embedding_model_name)
		except Exception:
			self.model = None
		self.hub = IndexHub(
			index_root=config.index_dir,
			embedding_model=config.embedding_model_name,
		)
		self.shard = self.hub.shard(config.kb_type, config.project_id)

	def search(self, query: str, top_k: int | None = None) -> List[Tuple[str, float, Tuple[str, int]]]:
		text = str(query or "").strip()
		if not text:
			return []
		vecs = self.embedder.encode([text])
		if not vecs:
			return []
		hits = self.shard.search(vecs[0], top_k=top_k or self.config.top_k)
		results: List[Tuple[str, float, Tuple[str, int]]] = []
		for hit in hits:
			meta = hit.meta or {}
			source = str(meta.get("path") or meta.get("source_id") or "unknown")
			try:
				position = int(meta.get("position", 0))
			except Exception:
				position = 0
			results.append((str(meta.get("text", "")), float(hit.score), (source, position)))
		return results
