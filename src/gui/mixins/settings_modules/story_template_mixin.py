"""Story template/strategy/creativity helpers extracted from settings mixin."""

from __future__ import annotations

from tkinter import END

from ...helpers.story_creativity import (
    DEFAULT_STORY_CREATIVITY_MODE,
    list_story_creativity_modes,
    normalize_story_creativity_mode,
)
from ...helpers.story_templates import (
    DEFAULT_STORY_TEMPLATE_KEY,
    DEFAULT_STORY_TEMPLATE_STRATEGY,
    get_story_template,
    list_story_template_strategies,
    normalize_story_template_strategy,
)


class SettingsStoryTemplateMixin:
    """Maintain story template/strategy/creativity settings and descriptions."""


    def _on_story_template_changed(self, _event=None):
        label = self.story_template_select_var.get().strip() if hasattr(self, "story_template_select_var") else ""
        key = ""
        if hasattr(self, "story_template_label_to_key"):
            key = self.story_template_label_to_key.get(label, "")
        if not key:
            key = DEFAULT_STORY_TEMPLATE_KEY
        if hasattr(self, "story_template_key"):
            self.story_template_key.set(key)
        self._update_story_template_desc()
        self._persist_story_template_selection()

    def _update_story_template_desc(self):
        if not hasattr(self, "story_template_desc_label"):
            return
        key = self.story_template_key.get().strip() if hasattr(self, "story_template_key") else DEFAULT_STORY_TEMPLATE_KEY
        template = get_story_template(key)
        label = template.get("label", key)
        desc = template.get("description", "")
        self.story_template_desc_label.config(text=f"{label}: {desc}")

    def _persist_story_template_selection(self):
        try:
            from pathlib import Path
            from dotenv import find_dotenv, set_key

            key = self.story_template_key.get().strip() if hasattr(self, "story_template_key") else DEFAULT_STORY_TEMPLATE_KEY
            if not key:
                key = DEFAULT_STORY_TEMPLATE_KEY
            env_path_str = find_dotenv(usecwd=True)
            env_path = Path(env_path_str) if env_path_str else Path.cwd() / ".env"
            env_path.touch(exist_ok=True)
            set_key(str(env_path), "STORY_TEMPLATE_KEY", key)
        except Exception as e:
            if hasattr(self, "settings_log"):
                self.settings_log.insert(END, f"⚠ 保存故事模版失败: {e}\n")

    def _on_story_template_strategy_changed(self, _event=None):
        label = (
            self.story_template_strategy_select_var.get().strip()
            if hasattr(self, "story_template_strategy_select_var")
            else ""
        )
        strategy = ""
        if hasattr(self, "story_template_strategy_label_to_key"):
            strategy = self.story_template_strategy_label_to_key.get(label, "")
        strategy = normalize_story_template_strategy(strategy or DEFAULT_STORY_TEMPLATE_STRATEGY)
        if hasattr(self, "story_template_strategy"):
            self.story_template_strategy.set(strategy)
        self._update_story_template_strategy_desc()
        self._persist_story_template_strategy()

    def _update_story_template_strategy_desc(self):
        if not hasattr(self, "story_template_strategy_desc_label"):
            return
        strategy_key = DEFAULT_STORY_TEMPLATE_STRATEGY
        if hasattr(self, "story_template_strategy"):
            strategy_key = normalize_story_template_strategy(self.story_template_strategy.get())
        for item in list_story_template_strategies():
            if item.get("key") == strategy_key:
                self.story_template_strategy_desc_label.config(
                    text=f"{item.get('label', strategy_key)}: {item.get('description', '')}"
                )
                return
        self.story_template_strategy_desc_label.config(text=strategy_key)

    def _persist_story_template_strategy(self):
        try:
            from pathlib import Path
            from dotenv import find_dotenv, set_key

            strategy = DEFAULT_STORY_TEMPLATE_STRATEGY
            if hasattr(self, "story_template_strategy"):
                strategy = normalize_story_template_strategy(self.story_template_strategy.get())
                self.story_template_strategy.set(strategy)
            env_path_str = find_dotenv(usecwd=True)
            env_path = Path(env_path_str) if env_path_str else Path.cwd() / ".env"
            env_path.touch(exist_ok=True)
            set_key(str(env_path), "STORY_TEMPLATE_STRATEGY", strategy)
        except Exception as e:
            if hasattr(self, "settings_log"):
                self.settings_log.insert(END, f"⚠ 保存模版策略失败: {e}\n")

    def _on_story_creativity_mode_changed(self, _event=None):
        label = self.story_creativity_select_var.get().strip() if hasattr(self, "story_creativity_select_var") else ""
        mode = ""
        if hasattr(self, "story_creativity_label_to_key"):
            mode = self.story_creativity_label_to_key.get(label, "")
        mode = normalize_story_creativity_mode(mode or DEFAULT_STORY_CREATIVITY_MODE)
        if hasattr(self, "story_creativity_mode"):
            self.story_creativity_mode.set(mode)
        self._update_story_creativity_mode_desc()
        self._persist_story_creativity_mode()

    def _update_story_creativity_mode_desc(self):
        if not hasattr(self, "story_creativity_desc_label"):
            return
        mode_key = DEFAULT_STORY_CREATIVITY_MODE
        if hasattr(self, "story_creativity_mode"):
            mode_key = normalize_story_creativity_mode(self.story_creativity_mode.get())
        for item in list_story_creativity_modes():
            if item.get("key") == mode_key:
                self.story_creativity_desc_label.config(
                    text=f"{item.get('label', mode_key)}: {item.get('description', '')}"
                )
                return
        self.story_creativity_desc_label.config(text=mode_key)

    def _persist_story_creativity_mode(self):
        try:
            from pathlib import Path
            from dotenv import find_dotenv, set_key

            mode = DEFAULT_STORY_CREATIVITY_MODE
            if hasattr(self, "story_creativity_mode"):
                mode = normalize_story_creativity_mode(self.story_creativity_mode.get())
                self.story_creativity_mode.set(mode)
            env_path_str = find_dotenv(usecwd=True)
            env_path = Path(env_path_str) if env_path_str else Path.cwd() / ".env"
            env_path.touch(exist_ok=True)
            set_key(str(env_path), "STORY_CREATIVITY_MODE", mode)
        except Exception as e:
            if hasattr(self, "settings_log"):
                self.settings_log.insert(END, f"⚠ 保存创新模式失败: {e}\n")
