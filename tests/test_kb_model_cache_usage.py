from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from src.kb.ingest import IngestConfig, KnowledgeBaseIngestor
from src.kb.search import KnowledgeBaseSearcher, SearchConfig


class _FakeEmbeddings:
    """Minimal stand-in for HuggingFaceEmbeddings used in unit tests."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs


class KBModelCacheUsageTests(unittest.TestCase):
    def test_ingestor_uses_cached_sentence_transformer(self):
        fake_faiss = object()
        fake_model = object()
        with patch("src.kb.ingest._load_kb_backends", return_value=(fake_faiss, _FakeEmbeddings)):
            with patch("src.kb.model_cache.get_sentence_transformer", return_value=fake_model) as mock_get:
                cfg = IngestConfig(data_root=Path("."), index_dir=Path(".kb_test"), embedding_model_name="m-x")
                ingestor = KnowledgeBaseIngestor(cfg)
                self.assertIs(ingestor.model, fake_model)
                mock_get.assert_called_once_with("m-x")

    def test_searcher_uses_cached_sentence_transformer(self):
        class _FakeFaiss:
            @staticmethod
            def read_index(_path):
                return object()

        fake_model = object()
        with patch("src.kb.search._load_kb_backends", return_value=(_FakeFaiss(), _FakeEmbeddings)):
            with patch("src.kb.model_cache.get_sentence_transformer", return_value=fake_model) as mock_get:
                with patch.object(KnowledgeBaseSearcher, "_load", return_value=None):
                    cfg = SearchConfig(index_dir=Path(".kb_test"), embedding_model_name="m-y")
                    searcher = KnowledgeBaseSearcher(cfg)
                    self.assertIs(searcher.model, fake_model)
                    mock_get.assert_called_once_with("m-y")


if __name__ == "__main__":
    unittest.main()

