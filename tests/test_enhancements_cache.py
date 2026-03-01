import tempfile
import unittest
from pathlib import Path

from src.gui.mixins.enhancements_modules.cache import CacheManager


class CacheManagerTests(unittest.TestCase):
    def test_set_get_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = CacheManager(cache_dir=tmp, max_size_mb=1)
            cache.set("k1", {"v": 1})
            self.assertEqual(cache.get("k1"), {"v": 1})
            cache.delete("k1")
            self.assertIsNone(cache.get("k1"))

    def test_clear(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = CacheManager(cache_dir=tmp, max_size_mb=1)
            cache.set("a", 1)
            cache.set("b", 2)
            cache.clear()
            self.assertIsNone(cache.get("a"))
            self.assertIsNone(cache.get("b"))

    def test_ttl_expiration(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = CacheManager(cache_dir=tmp, max_size_mb=1)
            cache.set("k1", {"v": 1}, ttl=0)
            self.assertIsNone(cache.get("k1"))

    def test_missing_cache_file_prunes_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = CacheManager(cache_dir=tmp, max_size_mb=1)
            cache.set("k1", {"v": 1})
            cache_key = cache._get_key("k1")
            cache_file = Path(tmp) / f"{cache_key}.json"
            cache_file.unlink()

            self.assertIsNone(cache.get("k1"))
            self.assertNotIn(cache_key, cache.index)


if __name__ == "__main__":
    unittest.main()
