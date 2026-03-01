import json
import tempfile
import unittest
from unittest.mock import patch

from src.gui.mixins.enhancements_modules.config_export import ConfigExportMixin


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _DummyConfigExport(ConfigExportMixin):
    def __init__(self):
        self.temperature = _Var(0.9)
        self.top_k = _Var(7)
        self.target_chars = _Var(2100)
        self.api_providers = {"DeepSeek": {"base_url": "u1", "models": ["m1"], "key": "k1"}}
        self.img_api_providers = {"Img": {"base_url": "u2", "models": ["im1"], "provider": "openai", "key": "k2"}}
        self.loaded_called = False

    def _load_settings_values(self):
        self.loaded_called = True


class ConfigExportMixinTests(unittest.TestCase):
    @patch("src.gui.mixins.enhancements_modules.config_export.messagebox.showinfo")
    def test_export_config(self, _mock_info):
        obj = _DummyConfigExport()
        with tempfile.TemporaryDirectory() as tmp:
            out = f"{tmp}/out.json"
            with patch(
                "src.gui.mixins.enhancements_modules.config_export.filedialog.asksaveasfilename",
                return_value=out,
            ):
                obj.export_config(include_keys=True)

            with open(out, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertEqual(data["settings"]["temperature"], 0.9)
            self.assertEqual(data["settings"]["top_k"], 7)
            self.assertEqual(data["settings"]["target_chars"], 2100)
            self.assertEqual(data["api_providers"]["DeepSeek"]["key"], "k1")
            self.assertEqual(data["img_api_providers"]["Img"]["key"], "k2")
            self.assertEqual(data["img_api_providers"]["Img"]["provider"], "openai")

    @patch("src.gui.mixins.enhancements_modules.config_export.messagebox.showwarning")
    @patch("src.gui.mixins.enhancements_modules.config_export.messagebox.showerror")
    @patch("src.gui.mixins.enhancements_modules.config_export.messagebox.showinfo")
    def test_import_config(self, _mock_info, _mock_error, _mock_warn):
        obj = _DummyConfigExport()
        with tempfile.TemporaryDirectory() as tmp:
            src = f"{tmp}/in.json"
            payload = {
                "version": "2.0",
                "settings": {"temperature": 0.6, "top_k": 5, "target_chars": 1600},
                "api_providers": {"DeepSeek": {"base_url": "nu1", "models": ["nm1", "nm2"], "key": "nk1"}},
                "img_api_providers": {"Img": {"base_url": "nu2", "models": ["nim1"], "provider": "hunyuan", "key": "nk2"}},
            }
            with open(src, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)

            with patch(
                "src.gui.mixins.enhancements_modules.config_export.filedialog.askopenfilename",
                return_value=src,
            ):
                obj.import_config()

            self.assertEqual(obj.temperature.get(), 0.6)
            self.assertEqual(obj.top_k.get(), 5)
            self.assertEqual(obj.target_chars.get(), 1600)
            self.assertEqual(obj.api_providers["DeepSeek"]["base_url"], "nu1")
            self.assertEqual(obj.api_providers["DeepSeek"]["models"], ["nm1", "nm2"])
            self.assertEqual(obj.api_providers["DeepSeek"]["key"], "nk1")
            self.assertEqual(obj.img_api_providers["Img"]["base_url"], "nu2")
            self.assertEqual(obj.img_api_providers["Img"]["models"], ["nim1"])
            self.assertEqual(obj.img_api_providers["Img"]["provider"], "hunyuan")
            self.assertEqual(obj.img_api_providers["Img"]["key"], "nk2")
            self.assertTrue(obj.loaded_called)

    @patch("src.gui.mixins.enhancements_modules.config_export.messagebox.showwarning")
    @patch("src.gui.mixins.enhancements_modules.config_export.messagebox.showerror")
    @patch("src.gui.mixins.enhancements_modules.config_export.messagebox.showinfo")
    def test_import_newer_version_does_not_warn(self, _mock_info, _mock_error, mock_warn):
        obj = _DummyConfigExport()
        with tempfile.TemporaryDirectory() as tmp:
            src = f"{tmp}/in.json"
            payload = {"version": "10.0", "settings": {}}
            with open(src, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)

            with patch(
                "src.gui.mixins.enhancements_modules.config_export.filedialog.askopenfilename",
                return_value=src,
            ):
                obj.import_config()

        mock_warn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
