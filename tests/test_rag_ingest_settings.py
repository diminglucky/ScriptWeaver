from __future__ import annotations

import unittest

from src.gui.mixins.kb_mixin import KbMixin


class _Var:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class _Dummy(KbMixin):
    pass


class RagIngestSettingsTests(unittest.TestCase):
    def test_rag_ingest_kwargs_uses_paragraph_window_settings(self):
        obj = _Dummy()
        obj.rag_paragraphs_per_chunk = _Var(6)
        obj.rag_overlap_paragraphs = _Var(2)
        obj.rag_long_paragraph_chars = _Var(1200)

        self.assertEqual(
            obj._rag_ingest_kwargs(),
            {
                "max_chars": 1200,
                "overlap_paragraphs": 2,
                "paragraphs_per_chunk": 6,
            },
        )

    def test_rag_ingest_kwargs_clamps_overlap_below_chunk_size(self):
        obj = _Dummy()
        obj.rag_paragraphs_per_chunk = _Var(3)
        obj.rag_overlap_paragraphs = _Var(9)
        obj.rag_long_paragraph_chars = _Var(50)

        self.assertEqual(
            obj._rag_ingest_kwargs(),
            {
                "max_chars": 200,
                "overlap_paragraphs": 2,
                "paragraphs_per_chunk": 3,
            },
        )


if __name__ == "__main__":
    unittest.main()
