from __future__ import annotations

import builtins
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.utils import text as text_utils


_REAL_IMPORT = builtins.__import__


def _import_without_doc_parsers(name, globals=None, locals=None, fromlist=(), level=0):
    if name in {"docx", "pypdf", "PyPDF2"}:
        raise ImportError(f"simulated missing parser dependency: {name}")
    return _REAL_IMPORT(name, globals, locals, fromlist, level)


class KBTextReadersTests(unittest.TestCase):
    def test_discover_text_files_includes_docx_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("hello", encoding="utf-8")
            (root / "b.docx").write_bytes(b"not-real-docx")
            (root / "c.pdf").write_bytes(b"not-real-pdf")
            (root / "d.png").write_bytes(b"png")

            names = [p.name for p in text_utils.discover_text_files(root)]

            self.assertIn("a.txt", names)
            self.assertIn("b.docx", names)
            self.assertIn("c.pdf", names)
            self.assertNotIn("d.png", names)

    def test_read_docx_reports_missing_dependency(self):
        with patch("builtins.__import__", side_effect=_import_without_doc_parsers):
            with self.assertRaises(RuntimeError) as ctx:
                text_utils.read_file_text(Path("dummy.docx"))
        self.assertIn("python-docx", str(ctx.exception))

    def test_read_pdf_reports_missing_dependency(self):
        with patch("builtins.__import__", side_effect=_import_without_doc_parsers):
            with self.assertRaises(RuntimeError) as ctx:
                text_utils.read_file_text(Path("dummy.pdf"))
        self.assertIn("pypdf", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
