from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple
import numpy as np


def _load_kb_backends():
	"""Load LangChain & FAISS backends lazily so app startup is platform-safe."""
	missing: list[str] = []
	try:
		from langchain_community.vectorstores import FAISS  # type: ignore
	except Exception:
		FAISS = None
		missing.append("langchain-community")

	try:
		from langchain_huggingface import HuggingFaceEmbeddings  # type: ignore
	except Exception:
		HuggingFaceEmbeddings = None
		missing.append("langchain-huggingface")

	if missing:
		pkgs = ", ".join(missing)
		raise RuntimeError(
			"知识库依赖缺失，暂时无法检索索引。"
			f"\n缺失包: {pkgs}"
			"\n请先安装后再试: pip install langchain langchain-community langchain-huggingface"
		)

	return FAISS, HuggingFaceEmbeddings


@dataclass
class SearchConfig:
	index_dir: Path
	embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
	top_k: int = 6


class KnowledgeBaseSearcher:
	def __init__(self, config: SearchConfig) -> None:
		self.config = config
		self.faiss_class, self.embeddings_class = _load_kb_backends()
		self.embeddings = self.embeddings_class(
			model_name=config.embedding_model_name,
			model_kwargs={"device": "cpu"}
		)
		# Preserved for backward compatibility and unit tests
		try:
			from src.kb.model_cache import get_sentence_transformer
			self.model = get_sentence_transformer(config.embedding_model_name)
		except Exception:
			self.model = None
		self.db = None
		self.legacy_index = None
		self.legacy_chunks = None
		self.legacy_metas = None
		self._load()

	def _load(self) -> None:
		# Check if LangChain FAISS files exist
		lc_faiss_path = self.config.index_dir / "kb.faiss"
		lc_pkl_path = self.config.index_dir / "kb.pkl"

		if lc_faiss_path.exists() and lc_pkl_path.exists():
			# Load LangChain FAISS VectorStore
			self.db = self.faiss_class.load_local(
				folder_path=str(self.config.index_dir),
				embeddings=self.embeddings,
				index_name="kb",
				allow_dangerous_deserialization=True
			)
		else:
			# Fallback to legacy custom numpy/faiss loading
			import faiss
			index_path = self.config.index_dir / "kb.index"
			chunks_path = self.config.index_dir / "chunks.npy"
			meta_path = self.config.index_dir / "meta.npy"

			if not index_path.exists() or not chunks_path.exists() or not meta_path.exists():
				raise RuntimeError(f"Index or fallback files missing under: {self.config.index_dir}")

			self.legacy_index = faiss.read_index(str(index_path))
			self.legacy_chunks = list(np.load(chunks_path, allow_pickle=True))
			self.legacy_metas = list(np.load(meta_path, allow_pickle=True))

	def search(self, query: str, top_k: int | None = None) -> List[Tuple[str, float, Tuple[str, int]]]:
		topk = top_k or self.config.top_k

		# 1. New LangChain retrieval path
		if self.db is not None:
			try:
				# Use similarity search with relevance scores
				results = self.db.similarity_search_with_relevance_scores(query, k=topk)
				formatted_results: List[Tuple[str, float, Tuple[str, int]]] = []
				for doc, score in results:
					source = doc.metadata.get("source", "unknown")
					chunk_idx = doc.metadata.get("chunk_idx", 0)
					formatted_results.append((doc.page_content, float(score), (source, int(chunk_idx))))
				return formatted_results
			except Exception:
				# If similarity_search fails for some reason (e.g. empty index), fallback to standard search
				results = self.db.similarity_search_with_score(query, k=topk)
				formatted_results = []
				for doc, score in results:
					source = doc.metadata.get("source", "unknown")
					chunk_idx = doc.metadata.get("chunk_idx", 0)
					# similarity_search_with_score returns L2 distance; convert to a similarity-like score
					sim_score = max(0.0, 1.0 - float(score))
					formatted_results.append((doc.page_content, sim_score, (source, int(chunk_idx))))
				return formatted_results

		# 2. Legacy fallback retrieval path
		if self.legacy_index is not None:
			# Replicate the original vector search exactly
			# get raw SentenceTransformer model via HuggingFaceEmbeddings' client
			model = self.embeddings.client
			emb = model.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
			scores, idxs = self.legacy_index.search(emb, topk)
			results: List[Tuple[str, float, Tuple[str, int]]] = []
			for score, idx in zip(scores[0], idxs[0]):
				if int(idx) < 0:
					continue
				results.append((self.legacy_chunks[int(idx)], float(score), self.legacy_metas[int(idx)]))
			return results

		return []
