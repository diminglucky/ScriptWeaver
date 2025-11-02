from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import faiss  # type: ignore
import numpy as np
from sentence_transformers import SentenceTransformer

from src.core.logging_config import get_logger

logger = get_logger(__name__)


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
		"""加载知识库索引"""
		index_path = self.config.index_dir / "kb.index"
		chunks_path = self.config.index_dir / "chunks.npy"
		meta_path = self.config.index_dir / "meta.npy"
		
		# 检查所有必需文件
		missing_files = []
		if not index_path.exists():
			missing_files.append("kb.index")
		if not chunks_path.exists():
			missing_files.append("chunks.npy")
		if not meta_path.exists():
			missing_files.append("meta.npy")
		
		if missing_files:
			raise RuntimeError(
				f"知识库文件缺失: {', '.join(missing_files)}\n"
				f"请先构建索引：点击「构建索引」按钮"
			)
		
		try:
			self.index = faiss.read_index(str(index_path))
			self.chunks: List[str] = list(np.load(chunks_path, allow_pickle=True))
			self.metas: List[Tuple[str, int]] = list(np.load(meta_path, allow_pickle=True))
			
			# 验证数据一致性
			if len(self.chunks) != len(self.metas):
				raise RuntimeError(f"数据不一致: chunks数量({len(self.chunks)}) != metas数量({len(self.metas)})")
			
			if self.index.ntotal != len(self.chunks):
				raise RuntimeError(f"索引不一致: 索引条目({self.index.ntotal}) != chunks数量({len(self.chunks)})")
			
			logger.info(f"成功加载知识库: {len(self.chunks)} 个片段")
		except Exception as e:
			logger.error(f"加载知识库失败: {e}", exc_info=True)
			raise RuntimeError(f"加载知识库失败: {e}")

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

