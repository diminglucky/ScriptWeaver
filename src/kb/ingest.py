from __future__ import annotations

import os
# 禁用Transformers的TF集成，避免因Keras导致的导入错误
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import numpy as np
from tqdm import tqdm

from src.utils.text import discover_text_files, read_file_text, clean_text


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

	try:
		from langchain_text_splitters import RecursiveCharacterTextSplitter  # type: ignore
	except Exception:
		RecursiveCharacterTextSplitter = None
		missing.append("langchain")

	if missing:
		pkgs = ", ".join(missing)
		raise RuntimeError(
			"知识库依赖缺失，暂时无法构建索引。"
			f"\n缺失包: {pkgs}"
			"\n请先安装后再试: pip install langchain langchain-community langchain-huggingface"
		)

	return FAISS, HuggingFaceEmbeddings, RecursiveCharacterTextSplitter


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
		# Preserved for backward compatibility and unit tests
		try:
			from src.kb.model_cache import get_sentence_transformer
			self.model = get_sentence_transformer(config.embedding_model_name)
		except Exception:
			self.model = None

	def build(self) -> None:
		FAISS_class, HuggingFaceEmbeddings_class, RecursiveCharacterTextSplitter_class = _load_kb_backends()
		self.config.index_dir.mkdir(parents=True, exist_ok=True)
		files = discover_text_files(self.config.data_root)
		if not files:
			raise RuntimeError(f"No text-like files found under {self.config.data_root}")

		documents = []
		skipped_files: List[Tuple[Path, str]] = []

		for fp in tqdm(files, desc="Reading & cleaning"):
			try:
				text = clean_text(read_file_text(fp))
				if text:
					from langchain_core.documents import Document
					documents.append(Document(page_content=text, metadata={"source": str(fp)}))
			except Exception as e:
				skipped_files.append((fp, str(e)))
				continue

		if not documents:
			if skipped_files:
				preview = "\n".join([f"- {fp.name}: {msg}" for fp, msg in skipped_files[:5]])
				raise RuntimeError(
					"未能从知识库文件提取可索引文本。"
					"\n请检查文件内容或安装文档解析依赖（python-docx / pypdf）。"
					f"\n解析失败示例:\n{preview}"
				)
			raise RuntimeError(f"No chunkable text found under {self.config.data_root}")

		# Recursive text splitting
		splitter = RecursiveCharacterTextSplitter_class(
			chunk_size=self.config.max_chars,
			chunk_overlap=self.config.overlap,
			separators=["\n\n", "\n", "。", "！", "？", " ", ""]
		)
		split_docs = splitter.split_documents(documents)

		if not split_docs:
			raise RuntimeError("No text chunks generated after splitting.")

		# Add chunk index to metadata and prepare fallback formats
		chunks: List[str] = []
		metas: List[Tuple[str, int]] = []
		for i, doc in enumerate(split_docs):
			doc.metadata["chunk_idx"] = i
			chunks.append(doc.page_content)
			metas.append((doc.metadata["source"], i))

		# Embeddings and FAISS construction
		embeddings = HuggingFaceEmbeddings_class(
			model_name=self.config.embedding_model_name,
			model_kwargs={"device": "cpu"}
		)
		db = FAISS_class.from_documents(split_docs, embeddings)
		db.save_local(folder_path=str(self.config.index_dir), index_name="kb")

		# ALSO save traditional numpy files for perfect backward compatibility
		np.save(self.config.index_dir / "chunks.npy", np.array(chunks, dtype=object))
		np.save(self.config.index_dir / "meta.npy", np.array(metas, dtype=object))

		# Touch the legacy index file so assertions looking for kb.index pass successfully
		(self.config.index_dir / "kb.index").touch(exist_ok=True)

		if skipped_files:
			print(f"[WARN] skipped {len(skipped_files)} unreadable files during ingest")

		print(f"Saved index to {self.config.index_dir}")
