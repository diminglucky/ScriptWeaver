from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import faiss  # type: ignore
import numpy as np
from sentence_transformers import SentenceTransformer


@dataclass
class SearchConfig:
	index_dir: Path
	embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
	top_k: int = 6


class KnowledgeBaseSearcher:
	def __init__(self, config: SearchConfig) -> None:
		self.config = config
		self.model = SentenceTransformer(config.embedding_model_name)
		self._load()

	def _load(self) -> None:
		index_path = self.config.index_dir / "kb.index"
		chunks_path = self.config.index_dir / "chunks.npy"
		meta_path = self.config.index_dir / "meta.npy"
		if not index_path.exists():
			raise RuntimeError(f"Index file missing: {index_path}")
		self.index = faiss.read_index(str(index_path))
		self.chunks: List[str] = list(np.load(chunks_path, allow_pickle=True))
		self.metas: List[Tuple[str, int]] = list(np.load(meta_path, allow_pickle=True))

	def search(self, query: str, top_k: int | None = None) -> List[Tuple[str, float, Tuple[str, int]]]:
		topk = top_k or self.config.top_k
		emb = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
		scores, idxs = self.index.search(emb, topk)
		results: List[Tuple[str, float, Tuple[str, int]]] = []
		for score, idx in zip(scores[0], idxs[0]):
			if int(idx) < 0:
				continue
			results.append((self.chunks[int(idx)], float(score), self.metas[int(idx)]))
		return results

