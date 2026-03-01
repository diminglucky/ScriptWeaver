import tempfile
import unittest
from pathlib import Path

from src.gui.mixins.config_modules.api_config import _fallback_set_key


class ApiConfigFallbackTests(unittest.TestCase):
    def test_fallback_set_key_creates_and_updates_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"

            self.assertTrue(_fallback_set_key(str(env_path), "FOO", "bar"))
            self.assertTrue(env_path.exists())
            text = env_path.read_text(encoding="utf-8")
            self.assertIn("FOO=bar", text)

            self.assertTrue(_fallback_set_key(str(env_path), "FOO", "baz value"))
            text = env_path.read_text(encoding="utf-8")
            self.assertIn('FOO="baz value"', text)
            self.assertNotIn("FOO=bar", text)


if __name__ == "__main__":
    unittest.main()
