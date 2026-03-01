"""Keyboard shortcuts extracted from enhancements.py."""

import json
import logging
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from typing import Callable, List

logger = logging.getLogger(__name__)


class KeyboardShortcuts:
    """Shortcut registry and binding helper."""

    DEFAULT_SHORTCUTS = {
        "<Control-n>": ("new_project", "New Project"),
        "<Control-o>": ("open_project", "Open Project"),
        "<Control-s>": ("save_project", "Save Project"),
        "<Control-Shift-s>": ("save_as", "Save As"),
        "<Control-e>": ("export_project", "Export Project"),
        "<Control-i>": ("import_project", "Import Project"),
        "<Control-z>": ("undo", "Undo"),
        "<Control-Shift-z>": ("redo", "Redo"),
        "<Control-y>": ("redo", "Redo"),
        "<Control-g>": ("generate_outline", "Generate Outline"),
        "<Control-Shift-g>": ("generate_story", "Generate Story"),
        "<F5>": ("generate_selected", "Generate Selected Chapter"),
        "<Control-1>": ("goto_project", "Go Project Tab"),
        "<Control-2>": ("goto_story", "Go Story Tab"),
        "<Control-3>": ("goto_image", "Go Image Tab"),
        "<Control-4>": ("goto_settings", "Go Settings Tab"),
        "<Control-t>": ("toggle_theme", "Toggle Theme"),
        "<F1>": ("show_help", "Show Help"),
        "<Control-comma>": ("open_settings", "Open Settings"),
    }

    def __init__(self, root: tk.Tk):
        self.root = root
        self.shortcuts = {}
        self.handlers = {}
        self._load_shortcuts()

    @classmethod
    def _normalize_shortcuts_config(cls, config) -> dict:
        normalized = dict(cls.DEFAULT_SHORTCUTS)
        if not isinstance(config, dict):
            return normalized

        for key, value in config.items():
            if not isinstance(key, str):
                continue
            if (
                isinstance(value, (list, tuple))
                and len(value) == 2
                and isinstance(value[0], str)
                and isinstance(value[1], str)
            ):
                normalized[key] = (value[0], value[1])
        return normalized

    def _load_shortcuts(self):
        config_path = Path("config/shortcuts.json")
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self.shortcuts = self._normalize_shortcuts_config(loaded)
            except Exception as e:
                logger.debug("load shortcuts config failed, using defaults: %s", e)
                self.shortcuts = dict(self.DEFAULT_SHORTCUTS)
        else:
            self.shortcuts = dict(self.DEFAULT_SHORTCUTS)

    def save_shortcuts(self):
        config_path = Path("config/shortcuts.json")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(self.shortcuts, f, indent=2, ensure_ascii=False)

    def register(self, action: str, handler: Callable):
        self.handlers[action] = handler

    def bind_all(self):
        for key, (action, _) in self.shortcuts.items():
            self._bind_key(key, action)

    def _bind_key(self, key: str, action: str):
        def handler(_event):
            if action in self.handlers:
                try:
                    self.handlers[action]()
                except Exception as e:
                    logger.warning("shortcut handler error [%s]: %s", action, e)
            return "break"

        try:
            self.root.bind_all(key, handler)
        except Exception as e:
            logger.debug("bind shortcut failed [%s -> %s]: %s", key, action, e)

    def get_shortcut_list(self) -> List[tuple]:
        return [(key, action, desc) for key, (action, desc) in self.shortcuts.items()]


class ShortcutsMixin:
    """UI shortcut commands."""

    def _setup_shortcuts(self):
        self.shortcuts = KeyboardShortcuts(self)
        self.shortcuts.register("new_project", self._shortcut_new_project)
        self.shortcuts.register("open_project", self._shortcut_open_project)
        self.shortcuts.register("save_project", self._shortcut_save_project)
        self.shortcuts.register("export_project", self._shortcut_export)
        self.shortcuts.register("import_project", self._shortcut_import)
        self.shortcuts.register("generate_outline", self._shortcut_generate_outline)
        self.shortcuts.register("generate_story", self._shortcut_generate_story)
        self.shortcuts.register("goto_project", lambda: self._goto_tab(0))
        self.shortcuts.register("goto_story", lambda: self._goto_tab(1))
        self.shortcuts.register("goto_image", lambda: self._goto_tab(2))
        self.shortcuts.register("goto_settings", lambda: self._goto_tab(3))
        self.shortcuts.register("toggle_theme", self._toggle_theme)
        self.shortcuts.register("show_help", self._show_shortcuts_help)
        self.shortcuts.bind_all()

    def _goto_tab(self, index: int):
        if hasattr(self, "notebook"):
            tabs = self.notebook.tabs()
            if index < len(tabs):
                self.notebook.select(tabs[index])

    def _shortcut_new_project(self):
        if hasattr(self, "_on_new_project"):
            self._on_new_project()

    def _shortcut_open_project(self):
        if hasattr(self, "_on_load_project"):
            self._on_load_project()

    def _shortcut_save_project(self):
        if hasattr(self, "_auto_save_to_project"):
            self._auto_save_to_project()
        elif hasattr(self, "_on_save_story"):
            self._on_save_story()

    def _shortcut_export(self):
        if hasattr(self, "export_project"):
            self.export_project()

    def _shortcut_import(self):
        if hasattr(self, "import_project"):
            self.import_project()

    def _shortcut_generate_outline(self):
        if hasattr(self, "on_generate_outline"):
            self.on_generate_outline()

    def _shortcut_generate_story(self):
        if hasattr(self, "on_auto_generate_all"):
            self.on_auto_generate_all()
        elif hasattr(self, "on_generate"):
            self.on_generate()

    def _toggle_theme(self):
        from ...theme import theme_manager
        theme_manager.toggle()
        if hasattr(self, "_refresh_theme"):
            self._refresh_theme()

    def _show_shortcuts_help(self):
        help_text = "Shortcut List:\n\n"
        for key, _action, desc in self.shortcuts.get_shortcut_list():
            key_display = key.replace("<", "").replace(">", "").replace("Control", "Ctrl")
            help_text += f"  {key_display}: {desc}\n"
        messagebox.showinfo("Shortcuts", help_text)
