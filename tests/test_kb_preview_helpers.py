import tempfile
import unittest
from pathlib import Path

from src.gui.mixins.kb_enhancements import _clear_known_index_artifacts
from src.gui.mixins.kb_enhancements import _discover_supported_files
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
            (root / "kb.index").write_bytes(b"a")
            (root / "chunks.npy").write_bytes(b"b")
            keep = root / "notes.txt"
            keep.write_text("keep", encoding="utf-8")

            removed, kept = _clear_known_index_artifacts(root)

            self.assertEqual(removed, 2)
            self.assertEqual(kept, 1)
            self.assertFalse((root / "kb.index").exists())
            self.assertFalse((root / "chunks.npy").exists())
            self.assertTrue(keep.exists())


if __name__ == "__main__":
    unittest.main()
