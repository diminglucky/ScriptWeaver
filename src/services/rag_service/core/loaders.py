"""Document loaders for .txt / .md / .docx / .pdf. See docs/technical_architecture.md.2.

Thin wrapper over `src.utils.text.read_file_text` so GUI and service ingest
share document parsing logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_MIME_BY_EXT = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".json": "application/json",
    ".csv": "text/csv",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pdf": "application/pdf",
}

SUPPORTED_EXTENSIONS: tuple[str, ...] = tuple(_MIME_BY_EXT.keys())


@dataclass
class LoadedDocument:
    path: str
    text: str
    mime: str


def load_document(path: Path) -> LoadedDocument:
    """Read a document and return cleaned text with a mime hint.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if the extension is not supported.
        RuntimeError: if optional parsers (python-docx / pypdf) are missing.
    """
    from src.utils.text import clean_text, read_file_text

    if not path.exists():
        raise FileNotFoundError(f"document not found: {path}")
    ext = path.suffix.lower()
    if ext not in _MIME_BY_EXT:
        raise ValueError(f"unsupported document extension: {ext}")
    text = clean_text(read_file_text(path))
    return LoadedDocument(path=str(path), text=text, mime=_MIME_BY_EXT[ext])
