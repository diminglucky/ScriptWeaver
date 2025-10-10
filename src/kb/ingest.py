from __future__ import annotations

import os
# 禁用Transformers的TF集成，避免因Keras导致的导入错误
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import faiss  # type: ignore
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from src.utils.text import discover_text_files, read_file_text, clean_text, split_by_length


@dataclass
class IngestConfig:
	data_root: Path
	index_dir: Path
	embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
	max_chars: int = 800
	overlap: int = 120


class KnowledgeBaseIngestor:
	def __init__(self, config: IngestConfig) -> None:
		self.config = config
		self.model = SentenceTransformer(config.embedding_model_name)

	def _embed(self, texts: List[str]) -> np.ndarray:
		return self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=True)

	def build(self) -> None:
		self.config.index_dir.mkdir(parents=True, exist_ok=True)
		files = discover_text_files(self.config.data_root)
		if not files:
			raise RuntimeError(f"No text-like files found under {self.config.data_root}")

		chunks: List[str] = []
		metas: List[Tuple[str, int]] = []  # (source_path, chunk_idx)

		for fp in tqdm(files, desc="Reading & chunking"):
			text = clean_text(read_file_text(fp))
			parts = split_by_length(text, self.config.max_chars, self.config.overlap)
			for i, part in enumerate(parts):
				chunks.append(part)
				metas.append((str(fp), i))

		embeddings = self._embed(chunks).astype("float32")
		index = faiss.IndexFlatIP(embeddings.shape[1])
		index.add(embeddings)

		faiss.write_index(index, str(self.config.index_dir / "kb.index"))
		np.save(self.config.index_dir / "chunks.npy", np.array(chunks, dtype=object))
		np.save(self.config.index_dir / "meta.npy", np.array(metas, dtype=object))

		print(f"Saved index to {self.config.index_dir}")

