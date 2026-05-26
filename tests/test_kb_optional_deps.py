from __future__ import annotations

import builtins
import unittest
from unittest.mock import patch


def _import_without_kb_backends(name, globals=None, locals=None, fromlist=(), level=0):
    if name in {
        "faiss",
        "sentence_transformers",
        "langchain",
        "langchain_community",
        "langchain_huggingface",
        "langchain_text_splitters",
    }:
        raise ImportError(f"simulated missing dependency: {name}")
    return _REAL_IMPORT(name, globals, locals, fromlist, level)


_REAL_IMPORT = builtins.__import__


class KBOptionalDepsTests(unittest.TestCase):
    def test_ingest_reports_missing_optional_deps(self):
        import src.kb.ingest as ingest

        with patch("builtins.__import__", side_effect=_import_without_kb_backends):
            with self.assertRaises(RuntimeError) as ctx:
                ingest._load_kb_backends()

        msg = str(ctx.exception)
        self.assertTrue(any(pkg in msg for pkg in ("faiss-cpu", "langchain-community")))
        self.assertTrue(any(pkg in msg for pkg in ("sentence-transformers", "langchain-huggingface")))

    def test_search_reports_missing_optional_deps(self):
        import src.kb.search as search

        with patch("builtins.__import__", side_effect=_import_without_kb_backends):
            with self.assertRaises(RuntimeError) as ctx:
                search._load_kb_backends()

        msg = str(ctx.exception)
        self.assertTrue(any(pkg in msg for pkg in ("faiss-cpu", "langchain-community")))
        self.assertTrue(any(pkg in msg for pkg in ("sentence-transformers", "langchain-huggingface")))


if __name__ == "__main__":
    unittest.main()
