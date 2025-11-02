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
from src.core.logging_config import get_logger

logger = get_logger(__name__)


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
		"""构建知识库索引"""
		try:
			self.config.index_dir.mkdir(parents=True, exist_ok=True)
			files = discover_text_files(self.config.data_root)
			
			if not files:
				raise RuntimeError(f"未在 {self.config.data_root} 下找到文本文件（支持.txt/.md/.markdown）")

			chunks: List[str] = []
			metas: List[Tuple[str, int]] = []  # (source_path, chunk_idx)

			for fp in tqdm(files, desc="Reading & chunking"):
				try:
					text = clean_text(read_file_text(fp))
					if not text or len(text) < 50:  # 跳过太短的文件
						logger.warning(f"跳过空文件或过短文件: {fp.name}")
						continue
					
					parts = split_by_length(text, self.config.max_chars, self.config.overlap)
					for i, part in enumerate(parts):
						if part and len(part) > 20:  # 再次验证片段有效性
							chunks.append(part)
							metas.append((str(fp), i))
				except Exception as e:
					logger.warning(f"处理文件失败，跳过: {fp.name}, 错误: {e}")
					continue

			if not chunks:
				raise RuntimeError("没有生成任何有效的文本片段，请检查数据文件")

			logger.info(f"共生成 {len(chunks)} 个文本片段，开始向量化...")
			
			embeddings = self._embed(chunks).astype("float32")
			
			if embeddings.shape[0] == 0:
				raise RuntimeError("向量化失败，没有生成任何embedding")
			
			index = faiss.IndexFlatIP(embeddings.shape[1])
			index.add(embeddings)

			faiss.write_index(index, str(self.config.index_dir / "kb.index"))
			np.save(self.config.index_dir / "chunks.npy", np.array(chunks, dtype=object))
			np.save(self.config.index_dir / "meta.npy", np.array(metas, dtype=object))

			logger.info(f"索引已保存到 {self.config.index_dir}")
			logger.info(f"文件数: {len(files)}, 片段数: {len(chunks)}")
		except Exception as e:
			logger.error(f"构建索引失败: {e}", exc_info=True)
			raise

