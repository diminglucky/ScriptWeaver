import tempfile
import unittest
from pathlib import Path

from src.gui.mixins.kb_enhancements import _clear_known_index_artifacts
from src.gui.mixins.kb_enhancements import _discover_supported_files
from src.gui.mixins.kb_enhancements import _discover_index_shards
from src.gui.mixins.kb_enhancements import _has_valid_index_artifacts
from src.gui.mixins.kb_enhancements import _load_index_chunks
from src.gui.mixins.kb_enhancements import _search_text_matches


class KBPreviewHelperTests(unittest.TestCase):
    def test_discover_supported_files_filters_extensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("hello", encoding="utf-8")
            (root / "b.md").write_text("world", encoding="utf-8")
            (root / "c.py").write_text("print('x')", encoding="utf-8")
            (root / "sub").mkdir()
            (root / "sub" / "d.csv").write_text("x,y", encoding="utf-8")

            files = _discover_supported_files(root)
            names = [f.name for f in files]

            self.assertEqual(names, ["a.txt", "b.md", "d.csv"])

    def test_search_text_matches_returns_context_and_limits_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = []
            for i in range(3):
                path = root / f"f{i}.txt"
                path.write_text(f"prefix target-{i} suffix", encoding="utf-8")
                files.append(path)

            results = _search_text_matches(files, root, "target", max_results=2, context_chars=6)

            self.assertEqual(len(results), 2)
            self.assertIn("target", results[0]["context"])
            self.assertEqual(str(results[0]["file"]).endswith(".txt"), True)

    def test_search_text_matches_ignores_non_text_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            txt = root / "ok.txt"
            txt.write_text("hello target world", encoding="utf-8")
            pdf = root / "fake.pdf"
            pdf.write_bytes(b"binary")

            results = _search_text_matches([txt, pdf], root, "target")

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["file"], Path("ok.txt"))

    def test_clear_known_index_artifacts_keeps_non_index_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            v2 = root / "v2" / "reference" / "_global" / "chroma"
            v2.mkdir(parents=True)
            (root / "v2" / "manifest.json").write_text("{}", encoding="utf-8")
            keep = root / "notes.txt"
            keep.write_text("keep", encoding="utf-8")

            removed, kept = _clear_known_index_artifacts(root)

            self.assertEqual(removed, 1)
            self.assertEqual(kept, 0)
            self.assertFalse((root / "v2").exists())
            self.assertTrue(keep.exists())

    def test_has_valid_index_artifacts_accepts_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "v2").mkdir()
            (root / "v2" / "manifest.json").write_text("{}", encoding="utf-8")
            self.assertTrue(_has_valid_index_artifacts(root))

    def test_has_valid_index_artifacts_accepts_chroma_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "v2" / "reference" / "_global" / "chroma").mkdir(parents=True)
            self.assertTrue(_has_valid_index_artifacts(root))

    def test_has_valid_index_artifacts_rejects_unrelated_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "notes.txt").write_text("not an index", encoding="utf-8")
            (root / "manifest.json").write_text("{}", encoding="utf-8")
            self.assertFalse(_has_valid_index_artifacts(root))

    def test_discover_index_shards_and_load_chunks(self):
        import json
        import sqlite3

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shard = root / "v2" / "reference" / "_global"
            shard.mkdir(parents=True)
            db = shard / "meta.sqlite"
            conn = sqlite3.connect(db)
            try:
                conn.execute(
                    """
                    CREATE TABLE chunks (
                        chunk_id TEXT PRIMARY KEY,
                        source_id TEXT NOT NULL,
                        path TEXT NOT NULL,
                        position INTEGER NOT NULL DEFAULT 0,
                        text TEXT NOT NULL,
                        kb_type TEXT NOT NULL,
                        project_id TEXT,
                        tags_json TEXT NOT NULL DEFAULT '[]',
                        ordinal INTEGER NOT NULL UNIQUE
                    )
                    """
                )
                conn.execute(
                    """
                    INSERT INTO chunks
                        (chunk_id, source_id, path, position, text, kb_type, project_id, tags_json, ordinal)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("c1", "novel", "novel.txt", 0, "chunk text", "reference", None, json.dumps(["tag"]), 0),
                )
                conn.commit()
            finally:
                conn.close()

            shards = _discover_index_shards(root)
            self.assertEqual(len(shards), 1)
            self.assertEqual(shards[0]["label"], "reference/_global")
            self.assertEqual(shards[0]["count"], 1)

            chunks = _load_index_chunks(shards[0]["db_path"])
            self.assertEqual(chunks[0]["text"], "chunk text")
            self.assertEqual(chunks[0]["tags"], ["tag"])


if __name__ == "__main__":
    unittest.main()
