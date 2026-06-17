from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from tqdm import tqdm

os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

from src.services.rag_service.core.embedding_hub import DEFAULT_MODEL_NAME, EmbeddingHub
from src.services.rag_service.core.index_hub import IndexHub
from src.services.rag_service.core.metadata import compute_chunk_id
from src.services.rag_service.core.splitters import split_text
from src.utils.text import clean_text, discover_text_files, read_file_text


def _load_kb_backends():
	"""Load the local RAG backend lazily so app startup remains safe."""
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
			"知识库依赖缺失，暂时无法构建索引。"
			f"\n缺失包: {pkgs}"
			"\n请先安装后再试: pip install chromadb sentence-transformers"
		)
	return True


@dataclass
class IngestConfig:
	data_root: Path
	index_dir: Path
	embedding_model_name: str = DEFAULT_MODEL_NAME
	max_chars: int = 800
	overlap: int = 120
	overlap_paragraphs: int = 1
	kb_type: str = "reference"
	project_id: str | None = None


class KnowledgeBaseIngestor:
	def __init__(self, config: IngestConfig) -> None:
		self.config = config
		try:
			from src.kb.model_cache import get_sentence_transformer
			self.model = get_sentence_transformer(config.embedding_model_name)
		except Exception:
			self.model = None

	def build(self) -> None:
		_load_kb_backends()
		self.config.index_dir.mkdir(parents=True, exist_ok=True)
		files = discover_text_files(self.config.data_root)
		if not files:
			raise RuntimeError(f"No text-like files found under {self.config.data_root}")

		chunk_ids: list[str] = []
		metas: list[dict] = []
		skipped_files: List[Tuple[Path, str]] = []

		for fp in tqdm(files, desc="Reading, paragraph-splitting & cleaning"):
			try:
				text = clean_text(read_file_text(fp))
				if not text:
					continue
				for pos, chunk in enumerate(
					split_text(
						text,
						chunk_size=self.config.max_chars,
						overlap=self.config.overlap,
						overlap_paragraphs=self.config.overlap_paragraphs,
					)
				):
					source = str(fp)
					cid = compute_chunk_id(source, chunk.text)
					chunk_ids.append(cid)
					metas.append(
						{
							"source_id": source,
							"path": source,
							"position": pos,
							"text": chunk.text,
							"kb_type": self.config.kb_type,
							"project_id": self.config.project_id,
							"tags": ["reference"],
							"start": chunk.start,
							"end": chunk.end,
						}
					)
			except Exception as e:
				skipped_files.append((fp, str(e)))

		if not chunk_ids:
			if skipped_files:
				preview = "\n".join([f"- {fp.name}: {msg}" for fp, msg in skipped_files[:5]])
				raise RuntimeError(
					"未能从知识库文件提取可索引文本。"
					"\n请检查文件内容或安装文档解析依赖（python-docx / pypdf）。"
					f"\n解析失败示例:\n{preview}"
				)
			raise RuntimeError(f"No chunkable text found under {self.config.data_root}")

		embedder = EmbeddingHub(self.config.embedding_model_name)
		vectors = embedder.encode([m["text"] for m in metas])
		hub = IndexHub(
			index_root=self.config.index_dir,
			embedding_model=self.config.embedding_model_name,
		)
		try:
			shard = hub.shard(self.config.kb_type, self.config.project_id)
			shard.upsert(chunk_ids, vectors, metas)
			hub.write_manifest()
		finally:
			hub.close()

		if skipped_files:
			print(f"[WARN] skipped {len(skipped_files)} unreadable files during ingest")

		print(f"Saved Chroma RAG index to {self.config.index_dir}")
