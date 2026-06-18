from __future__ import annotations

import os
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from tqdm import tqdm

os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

from src.services.rag_service.core.embedding_hub import DEFAULT_MODEL_NAME, EmbeddingHub
from src.services.rag_service.core.index_hub import IndexHub
from src.services.rag_service.core.metadata import compute_chunk_id
from src.services.rag_service.core.splitters import split_text
from src.kb.sync import SyncStats
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
	paragraphs_per_chunk: int = 4
	kb_type: str = "reference"
	project_id: str | None = None
	rebuild: bool = True
	prune_deleted: bool = True


class KnowledgeBaseIngestor:
	def __init__(self, config: IngestConfig) -> None:
		self.config = config
		try:
			from src.kb.model_cache import get_sentence_transformer
			self.model = get_sentence_transformer(config.embedding_model_name)
		except Exception:
			self.model = None

	def _chunk_settings(self) -> dict:
		return {
			"max_chars": int(self.config.max_chars),
			"overlap": int(self.config.overlap),
			"overlap_paragraphs": int(self.config.overlap_paragraphs),
			"paragraphs_per_chunk": int(self.config.paragraphs_per_chunk),
		}

	def _file_hash(self, path: Path) -> str:
		h = hashlib.sha256()
		with path.open("rb") as fh:
			for block in iter(lambda: fh.read(1024 * 1024), b""):
				h.update(block)
		return h.hexdigest()

	def _document_record(self, *, source: str, fp: Path, content_hash: str, chunk_count: int) -> dict:
		try:
			stat = fp.stat()
			mtime_ns = int(stat.st_mtime_ns)
			size_bytes = int(stat.st_size)
		except OSError:
			mtime_ns = 0
			size_bytes = 0
		return {
			"source_id": source,
			"path": source,
			"content_hash": content_hash,
			"mtime_ns": mtime_ns,
			"size_bytes": size_bytes,
			"chunk_count": chunk_count,
			"chunk_settings": self._chunk_settings(),
			"embedding_model": self.config.embedding_model_name,
		}

	def _is_document_current(self, existing: dict | None, *, content_hash: str) -> bool:
		if not existing:
			return False
		return (
			existing.get("content_hash") == content_hash
			and existing.get("embedding_model") == self.config.embedding_model_name
			and existing.get("chunk_settings") == self._chunk_settings()
		)

	def build(self) -> SyncStats:
		_load_kb_backends()
		self.config.index_dir.mkdir(parents=True, exist_ok=True)
		files = discover_text_files(self.config.data_root)
		if not files:
			raise RuntimeError(f"No text-like files found under {self.config.data_root}")
		stats = SyncStats(scanned=len(files))
		hub = IndexHub(
			index_root=self.config.index_dir,
			embedding_model=self.config.embedding_model_name,
		)
		try:
			return self._build_with_hub(hub, files, stats)
		finally:
			hub.close()

	def _build_with_hub(self, hub: IndexHub, files: list[Path], stats: SyncStats) -> SyncStats:

		chunk_ids: list[str] = []
		metas: list[dict] = []
		doc_records: list[dict] = []
		skipped_files: List[Tuple[Path, str]] = []
		shard = hub.shard(self.config.kb_type, self.config.project_id)
		if self.config.rebuild:
			stats.removed = shard.clear()
			existing_docs: dict[str, dict] = {}
		else:
			existing_docs = shard.store.fetch_documents([str(fp) for fp in files])
			if self.config.prune_deleted:
				current_sources = {str(fp) for fp in files}
				for doc in shard.store.list_documents():
					source_id = str(doc.get("source_id") or "")
					if source_id and source_id not in current_sources:
						stats.removed += shard.delete_source(source_id)

		for fp in tqdm(files, desc="Reading, paragraph-splitting & cleaning"):
			try:
				source = str(fp)
				content_hash = self._file_hash(fp)
				if not self.config.rebuild and self._is_document_current(existing_docs.get(source), content_hash=content_hash):
					stats.skipped += 1
					continue
				text = clean_text(read_file_text(fp))
				if not text:
					continue
				source_chunk_ids: list[str] = []
				source_metas: list[dict] = []
				for pos, chunk in enumerate(
					split_text(
						text,
						chunk_size=self.config.max_chars,
						overlap=self.config.overlap,
						overlap_paragraphs=self.config.overlap_paragraphs,
						paragraphs_per_chunk=self.config.paragraphs_per_chunk,
					)
				):
					cid = compute_chunk_id(source, chunk.text)
					source_chunk_ids.append(cid)
					source_metas.append(
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
				if source_chunk_ids:
					chunk_ids.extend(source_chunk_ids)
					metas.extend(source_metas)
					doc_records.append(
						self._document_record(
							source=source,
							fp=fp,
							content_hash=content_hash,
							chunk_count=len(source_chunk_ids),
						)
					)
					if not self.config.rebuild and source in existing_docs:
						stats.updated += 1
					else:
						stats.indexed += 1
			except Exception as e:
				skipped_files.append((fp, str(e)))
				stats.errors.append(f"{fp.name}: {e}")

		if not chunk_ids:
			if skipped_files:
				preview = "\n".join([f"- {fp.name}: {msg}" for fp, msg in skipped_files[:5]])
				raise RuntimeError(
					"未能从知识库文件提取可索引文本。"
					"\n请检查文件内容或安装文档解析依赖（python-docx / pypdf）。"
					f"\n解析失败示例:\n{preview}"
				)
			hub.write_manifest()
			print(f"Saved Chroma RAG index to {self.config.index_dir}")
			print(f"Ingest summary: {stats.summary()}")
			return stats

		embedder = EmbeddingHub(self.config.embedding_model_name)
		vectors = embedder.encode([m["text"] for m in metas])
		if self.config.rebuild:
			shard.upsert(chunk_ids, vectors, metas)
		else:
			shard.replace_sources(chunk_ids, vectors, metas)
		shard.store.upsert_documents(doc_records)
		stats.chunk_count = len(chunk_ids)
		hub.write_manifest()

		if skipped_files:
			print(f"[WARN] skipped {len(skipped_files)} unreadable files during ingest")

		print(f"Saved Chroma RAG index to {self.config.index_dir}")
		print(f"Ingest summary: {stats.summary()}")
		return stats
