import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.gui.mixins.config_modules.preset_manager import PresetManagerMixin


class _Var:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _DummyPreset(PresetManagerMixin):
    def __init__(self, root: Path):
        self._CUSTOM_API_FILE = root / "custom_api_presets.json"
        self._CUSTOM_IMAGE_API_FILE = root / "custom_image_api_presets.json"

        self.status = _Var("")
        self.api_preset = _Var("DeepSeek")
        self.img_api_preset = _Var("ProviderImage")

        self.base_url = _Var("https://story.example/v1")
        self.model = _Var("story-model")
        self.api_key = _Var("story-key")

        self.img_base_url = _Var("https://image.example/v1")
        self.img_model = _Var("image-model")
        self.img_api_key = _Var("image-key")
        self.img_api_type = _Var("openai")
        self.img_secret_key = _Var("")

        self.api_presets = {
            "DeepSeek": {"base_url": "builtin", "model": "builtin", "key": ""},
            "ProviderStory": {"base_url": "builtin-2", "model": "builtin-2", "key": ""},
        }
        self.img_api_presets = {
            "ProviderImage": {"base_url": "builtin", "model": "builtin", "key": "", "provider": "openai"},
        }

        self.combo_api_preset = {}
        self.combo_img_api_preset = {}


class PresetManagerTests(unittest.TestCase):
    def test_save_custom_story_preset_updates_file_and_values(self):
        with tempfile.TemporaryDirectory() as td:
            obj = _DummyPreset(Path(td))
            with patch(
                "tkinter.simpledialog.askstring",
                return_value="MyStory",
            ):
                with patch("src.gui.mixins.config_modules.preset_manager.messagebox.showinfo"):
                    obj._save_custom_preset()

            self.assertIn("MyStory", obj.api_presets)
            self.assertIn("MyStory", obj.combo_api_preset.get("values", []))
            data = json.loads(obj._CUSTOM_API_FILE.read_text(encoding="utf-8"))
            self.assertIn("MyStory", data)

    def test_save_story_builtin_name_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            obj = _DummyPreset(Path(td))
            with patch(
                "tkinter.simpledialog.askstring",
                return_value="ProviderStory",
            ):
                with patch("src.gui.mixins.config_modules.preset_manager.messagebox.showwarning") as warn:
                    obj._save_custom_preset()

            self.assertTrue(warn.called)
            self.assertFalse(obj._CUSTOM_API_FILE.exists())

    def test_delete_story_custom_removes_from_memory_and_file(self):
        with tempfile.TemporaryDirectory() as td:
            obj = _DummyPreset(Path(td))
            custom = {"MyStory": {"base_url": "x", "model": "m", "key": "k"}}
            obj._CUSTOM_API_FILE.write_text(json.dumps(custom), encoding="utf-8")
            obj.api_presets.update(custom)
            obj.api_preset.set("MyStory")

            with patch("src.gui.mixins.config_modules.preset_manager.messagebox.askyesno", return_value=True):
                with patch("src.gui.mixins.config_modules.preset_manager.messagebox.showinfo"):
                    obj._delete_custom_preset()

            self.assertNotIn("MyStory", obj.api_presets)
            self.assertFalse(obj._CUSTOM_API_FILE.exists())

    def test_save_image_builtin_name_is_blocked_by_dynamic_detection(self):
        with tempfile.TemporaryDirectory() as td:
            obj = _DummyPreset(Path(td))
            with patch(
                "tkinter.simpledialog.askstring",
                return_value="ProviderImage",
            ):
                with patch("src.gui.mixins.config_modules.preset_manager.messagebox.showwarning") as warn:
                    obj._save_custom_image_preset()

            self.assertTrue(warn.called)
            self.assertFalse(obj._CUSTOM_IMAGE_API_FILE.exists())


if __name__ == "__main__":
    unittest.main()
