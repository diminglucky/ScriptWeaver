import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.gui.mixins.config_modules.api_config import APIConfigMixin
from src.gui.mixins.config_modules.api_config import _safe_preset_env_name


class _Var:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _Dummy(APIConfigMixin):
    def __init__(self):
        self.img_api_preset = _Var("腾讯混元")
        self.img_size = _Var("1024x1024")
        self.img_api_key = _Var("sid")
        self.img_base_url = _Var("https://img.example/v1")
        self.img_model = _Var("hunyuan")
        self.img_secret_key = _Var("skey")
        self.img_api_type = _Var("")
        self.status = _Var("")
        self.img_api_presets = {
            "腾讯混元": {"key": "", "base_url": "", "model": "", "provider": "hunyuan", "secret_key": ""},
            "OpenAI (DALL-E)": {"key": "", "base_url": "", "model": "", "provider": "openai"},
        }


class APIConfigImageEnvTests(unittest.TestCase):
    def test_safe_preset_env_name_hashes_non_ascii(self):
        safe = _safe_preset_env_name("腾讯混元")
        self.assertTrue(safe.startswith("CUSTOM_"))
        self.assertEqual(len(safe), len("CUSTOM_") + 8)

    @patch("src.gui.mixins.config_modules.api_config.messagebox.showinfo")
    @patch("src.gui.mixins.config_modules.api_config.messagebox.showwarning")
    @patch("src.gui.mixins.config_modules.api_config.load_dotenv")
    def test_save_image_api_config_writes_consistent_env_keys(self, _mock_load, _mock_warn, _mock_info):
        obj = _Dummy()
        safe_name = _safe_preset_env_name("腾讯混元")

        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            with patch("src.gui.mixins.config_modules.api_config.find_dotenv", return_value=str(env_path)):
                obj._save_image_api_config()

            text = env_path.read_text(encoding="utf-8")
            self.assertIn("IMAGE_GEN_API", text)
            self.assertIn("IMG_API_PRESET", text)
            self.assertIn(f"IMG_{safe_name}_KEY", text)
            self.assertIn(f"IMG_{safe_name}_BASE_URL", text)
            self.assertIn(f"IMG_{safe_name}_MODEL", text)
            self.assertIn(f"IMG_{safe_name}_SECRET_KEY", text)

    @patch("src.gui.mixins.config_modules.api_config.load_dotenv", return_value=False)
    def test_auto_load_image_api_config_reads_safe_preset_keys(self, _mock_load):
        obj = _Dummy()
        safe_name = _safe_preset_env_name("腾讯混元")
        env = {
            f"IMG_{safe_name}_KEY": "k_safe",
            f"IMG_{safe_name}_BASE_URL": "https://safe.example/v1",
            f"IMG_{safe_name}_MODEL": "safe-model",
            f"IMG_{safe_name}_SECRET_KEY": "secret-safe",
            "IMAGE_GEN_API": "腾讯混元",
            "IMG_SIZE": "512x512",
        }
        with patch.dict("os.environ", env, clear=False):
            obj._auto_load_image_api_config()

        self.assertEqual(obj.img_api_presets["腾讯混元"]["key"], "k_safe")
        self.assertEqual(obj.img_api_presets["腾讯混元"]["base_url"], "https://safe.example/v1")
        self.assertEqual(obj.img_api_presets["腾讯混元"]["model"], "safe-model")
        self.assertEqual(obj.img_api_presets["腾讯混元"]["secret_key"], "secret-safe")
        self.assertEqual(obj.img_size.get(), "512x512")
        self.assertEqual(obj.img_api_preset.get(), "腾讯混元")


if __name__ == "__main__":
    unittest.main()
