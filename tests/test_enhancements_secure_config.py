import tempfile
import unittest

from src.gui.mixins.enhancements_modules.secure_config import SecureConfigMixin


class _DummySecure(SecureConfigMixin):
    pass


class SecureConfigMixinTests(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        obj = _DummySecure()
        obj._init_secure_storage()

        with tempfile.TemporaryDirectory() as tmp:
            path = f"{tmp}/api_config.json"
            src = {"api_key": "k1", "key": "k2", "secret": "k3", "x": 1}
            obj.save_encrypted_config(src, path=path)
            loaded = obj.load_encrypted_config(path=path)

            self.assertEqual(loaded.get("api_key"), "k1")
            self.assertEqual(loaded.get("key"), "k2")
            self.assertEqual(loaded.get("secret"), "k3")
            self.assertEqual(loaded.get("x"), 1)

    def test_missing_file_returns_empty_dict(self):
        obj = _DummySecure()
        obj._init_secure_storage()
        with tempfile.TemporaryDirectory() as tmp:
            loaded = obj.load_encrypted_config(path=f"{tmp}/missing.json")
            self.assertEqual(loaded, {})


if __name__ == "__main__":
    unittest.main()
