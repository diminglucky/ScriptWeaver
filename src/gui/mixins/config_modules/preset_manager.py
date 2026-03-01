"""Config preset manager mixin."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from tkinter import messagebox


logger = logging.getLogger(__name__)


class PresetManagerMixin:
    """Preset selection and custom preset CRUD helpers."""

    _CUSTOM_API_FILE = Path("custom_api_presets.json")
    _CUSTOM_IMAGE_API_FILE = Path("custom_image_api_presets.json")

    def _on_api_preset_selected(self, event=None) -> None:
        """Populate story API fields from selected preset."""
        preset_name = self.api_preset.get()
        preset = self.api_presets.get(preset_name)
        if not isinstance(preset, dict):
            return

        if preset.get("base_url"):
            self.base_url.set(preset["base_url"])
        if preset.get("model"):
            self.model.set(preset["model"])
        if preset.get("key"):
            self.api_key.set(preset["key"])

        if hasattr(self, "status"):
            self.status.set(f"Selected preset: {preset_name}")

    def _on_img_api_preset_selected(self, event=None) -> None:
        """Populate image API fields from selected preset."""
        preset_name = self.img_api_preset.get()
        preset = self.img_api_presets.get(preset_name)
        if not isinstance(preset, dict):
            return

        provider = preset.get("provider", "openai")
        if hasattr(self, "img_api_type"):
            self.img_api_type.set(provider)

        if preset.get("base_url"):
            self.img_base_url.set(preset["base_url"])
        if preset.get("model"):
            self.img_model.set(preset["model"])
        if preset.get("key"):
            self.img_api_key.set(preset["key"])
        self.img_secret_key.set(preset.get("secret_key", ""))

    def _load_custom_presets(self) -> None:
        """Load custom story API presets from disk."""
        custom = self._read_json_dict(self._CUSTOM_API_FILE)
        if custom:
            self.api_presets.update(custom)

    def _save_custom_preset(self) -> None:
        """Save current story API config as a custom preset."""
        from tkinter import simpledialog

        preset_name = simpledialog.askstring("Save Preset", "Preset name:", parent=self)
        if not preset_name:
            return

        custom_map = self._read_json_dict(self._CUSTOM_API_FILE)
        builtin_keys = set(self.api_presets.keys()) - set(custom_map.keys())
        if preset_name in builtin_keys:
            messagebox.showwarning("Warning", "Cannot overwrite builtin preset.")
            return

        config = {
            "base_url": self.base_url.get(),
            "model": self.model.get(),
            "key": self.api_key.get(),
        }
        self.api_presets[preset_name] = config
        custom_map[preset_name] = config

        try:
            self._write_json_dict(self._CUSTOM_API_FILE, custom_map)
            self._refresh_story_preset_values()
            self.api_preset.set(preset_name)
            messagebox.showinfo("Success", f"Saved preset: {preset_name}")
            if hasattr(self, "status"):
                self.status.set(f"Saved preset: {preset_name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save preset: {e}")

    def _delete_custom_preset(self) -> None:
        """Delete selected custom story API preset."""
        current = self.api_preset.get()
        if not current:
            messagebox.showwarning("Warning", "No preset selected.")
            return

        custom_map = self._read_json_dict(self._CUSTOM_API_FILE)
        if current not in custom_map:
            messagebox.showwarning("Not allowed", "Builtin preset cannot be deleted.")
            return
        if not messagebox.askyesno("Delete", f"Delete preset '{current}'?"):
            return

        try:
            self.api_presets.pop(current, None)
            custom_map.pop(current, None)
            self._persist_custom_map(self._CUSTOM_API_FILE, custom_map)

            self._refresh_story_preset_values()
            fallback = next(iter(self.api_presets), "")
            self.api_preset.set(fallback)
            self._on_api_preset_selected(None)
            messagebox.showinfo("Success", f"Deleted preset: {current}")
            if hasattr(self, "status"):
                self.status.set(f"Deleted preset: {current}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete preset: {e}")

    def _load_custom_image_presets(self) -> None:
        """Load custom image API presets from disk."""
        custom = self._read_json_dict(self._CUSTOM_IMAGE_API_FILE)
        if custom:
            self.img_api_presets.update(custom)

    def _save_custom_image_preset(self) -> None:
        """Save current image API config as a custom preset."""
        from tkinter import simpledialog

        preset_name = simpledialog.askstring("Save Image Preset", "Preset name:", parent=self)
        if not preset_name:
            return

        custom_map = self._read_json_dict(self._CUSTOM_IMAGE_API_FILE)
        builtin_keys = set(self.img_api_presets.keys()) - set(custom_map.keys())
        if preset_name in builtin_keys:
            messagebox.showwarning("Warning", "Cannot overwrite builtin image preset.")
            return

        provider = self.img_api_type.get() if hasattr(self, "img_api_type") else "openai"
        config = {
            "base_url": self.img_base_url.get(),
            "model": self.img_model.get(),
            "key": self.img_api_key.get(),
            "provider": provider,
            "secret_key": self.img_secret_key.get() if provider == "hunyuan" else "",
        }

        self.img_api_presets[preset_name] = config
        custom_map[preset_name] = config

        try:
            self._write_json_dict(self._CUSTOM_IMAGE_API_FILE, custom_map)
            self._refresh_image_preset_values()
            self.img_api_preset.set(preset_name)
            messagebox.showinfo("Success", f"Saved image preset: {preset_name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save image preset: {e}")

    def _delete_custom_image_preset(self) -> None:
        """Delete selected custom image API preset."""
        current = self.img_api_preset.get()
        if not current:
            messagebox.showwarning("Warning", "No image preset selected.")
            return

        custom_map = self._read_json_dict(self._CUSTOM_IMAGE_API_FILE)
        if current not in custom_map:
            messagebox.showwarning("Not allowed", "Builtin image preset cannot be deleted.")
            return
        if not messagebox.askyesno("Delete", f"Delete image preset '{current}'?"):
            return

        try:
            self.img_api_presets.pop(current, None)
            custom_map.pop(current, None)
            self._persist_custom_map(self._CUSTOM_IMAGE_API_FILE, custom_map)

            self._refresh_image_preset_values()
            fallback = next(iter(self.img_api_presets), "")
            self.img_api_preset.set(fallback)
            self._on_img_api_preset_selected(None)
            messagebox.showinfo("Success", f"Deleted image preset: {current}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete image preset: {e}")

    def _refresh_story_preset_values(self) -> None:
        if hasattr(self, "combo_api_preset"):
            self.combo_api_preset["values"] = list(self.api_presets.keys())

    def _refresh_image_preset_values(self) -> None:
        if hasattr(self, "combo_img_api_preset"):
            self.combo_img_api_preset["values"] = list(self.img_api_presets.keys())

    def _persist_custom_map(self, path: Path, payload: dict) -> None:
        if payload:
            self._write_json_dict(path, payload)
        elif path.exists():
            path.unlink()

    def _read_json_dict(self, path: Path) -> dict:
        """Read a json dict safely from disk."""
        if not path.exists():
            return {}
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
            logger.warning("Preset file %s does not contain a dict", path)
        except Exception as e:
            logger.warning("Failed to read preset file %s: %s", path, e)
        return {}

    @staticmethod
    def _write_json_dict(path: Path, payload: dict) -> None:
        """Write json dict with utf-8 encoding."""
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
