"""Story env preference helpers extracted from settings mixin."""

from __future__ import annotations

import os
from pathlib import Path

from ...helpers.story_creativity import (
    DEFAULT_STORY_CREATIVITY_MODE,
    normalize_story_creativity_mode,
)
from ...helpers.story_generation_modes import (
    DEFAULT_STORY_GENERATION_MODE,
    get_story_generation_mode_settings,
    list_story_generation_modes,
    normalize_story_generation_mode,
)
from ...helpers.story_templates import (
    DEFAULT_STORY_TEMPLATE_KEY,
    DEFAULT_STORY_TEMPLATE_STRATEGY,
    normalize_story_template_strategy,
)


class SettingsStoryEnvMixin:
    """Persist and apply story-related environment preferences."""

    _BOOL_MODE_KEYS = {
        "story_quality_review_enabled",
        "story_global_overview_enabled",
        "story_overview_before_generate",
        "story_preview_before_apply",
        "story_outline_alignment_strict",
    }
    _INT_MODE_KEYS = {
        "story_outline_alignment_max_attempts",
    }
    _FLOAT_MODE_KEYS = {
        "story_quality_min_avg",
        "story_quality_min_dim",
    }

    def _save_story_quality_settings(self, env_path: Path) -> None:
        """保存故事质量控制参数到 .env。"""
        from dotenv import set_key

        if hasattr(self, "story_quality_review_enabled"):
            try:
                quality_review_enabled = bool(self.story_quality_review_enabled.get())
            except Exception:
                quality_review_enabled = True
            set_key(str(env_path), "STORY_QUALITY_REVIEW", "1" if quality_review_enabled else "0")
        if hasattr(self, "story_quality_min_avg"):
            try:
                quality_min_avg_value = float(self.story_quality_min_avg.get())
            except Exception:
                quality_min_avg_value = 7.4
            quality_min_avg_value = max(1.0, min(10.0, quality_min_avg_value))
            set_key(str(env_path), "STORY_QUALITY_MIN_AVG", f"{quality_min_avg_value:.1f}")
        if hasattr(self, "story_quality_min_dim"):
            try:
                quality_min_dim_value = float(self.story_quality_min_dim.get())
            except Exception:
                quality_min_dim_value = 6.8
            quality_min_dim_value = max(1.0, min(10.0, quality_min_dim_value))
            set_key(str(env_path), "STORY_QUALITY_MIN_DIM", f"{quality_min_dim_value:.1f}")
        if hasattr(self, "story_outline_alignment_strict"):
            try:
                strict_enabled = bool(self.story_outline_alignment_strict.get())
            except Exception:
                strict_enabled = True
            set_key(str(env_path), "STORY_OUTLINE_ALIGNMENT_STRICT", "1" if strict_enabled else "0")
        if hasattr(self, "story_outline_alignment_max_attempts"):
            try:
                max_attempts = int(self.story_outline_alignment_max_attempts.get())
            except Exception:
                max_attempts = 2
            max_attempts = max(1, min(4, max_attempts))
            set_key(str(env_path), "STORY_OUTLINE_ALIGNMENT_MAX_ATTEMPTS", str(max_attempts))

    def _resolve_env_path(self) -> Path:
        """返回可写的 .env 路径（不存在则创建）。"""
        from dotenv import find_dotenv

        env_path_str = find_dotenv(usecwd=True)
        env_path = Path(env_path_str) if env_path_str else Path.cwd() / ".env"
        env_path.touch(exist_ok=True)
        return env_path

    @staticmethod
    def _parse_bool_env(raw: str | None, default: bool = False) -> bool:
        if raw is None:
            return default
        text = str(raw).strip().lower()
        if not text:
            return default
        return text in {"1", "true", "yes", "on"}

    @staticmethod
    def _clamp_int(value, default: int, min_value: int, max_value: int) -> int:
        try:
            val = int(value)
        except Exception:
            val = default
        return max(min_value, min(max_value, val))

    @staticmethod
    def _clamp_float(value, default: float, min_value: float, max_value: float) -> float:
        try:
            val = float(value)
        except Exception:
            val = default
        return max(min_value, min(max_value, val))

    def _collect_story_env_payload(self) -> dict[str, str]:
        """收敛故事创作偏好为 .env 键值。"""
        payload: dict[str, str] = {}
        current_mode = self._sync_story_generation_mode_marker_from_settings()
        payload["STORY_GENERATION_MODE"] = current_mode
        if hasattr(self, "story_template_key"):
            template_key = self.story_template_key.get().strip() or DEFAULT_STORY_TEMPLATE_KEY
            payload["STORY_TEMPLATE_KEY"] = template_key
        if hasattr(self, "story_template_strategy"):
            template_strategy = normalize_story_template_strategy(self.story_template_strategy.get())
            self.story_template_strategy.set(template_strategy)
            payload["STORY_TEMPLATE_STRATEGY"] = template_strategy
        if hasattr(self, "story_creativity_mode"):
            creativity_mode = normalize_story_creativity_mode(self.story_creativity_mode.get())
            self.story_creativity_mode.set(creativity_mode)
            payload["STORY_CREATIVITY_MODE"] = creativity_mode
        if hasattr(self, "target_chars"):
            chars_value = self._clamp_int(self.target_chars.get(), default=1800, min_value=500, max_value=30000)
            payload["TARGET_CHARS"] = str(chars_value)
        if hasattr(self, "model_only"):
            try:
                model_only_value = bool(self.model_only.get())
            except Exception:
                model_only_value = False
            payload["MODEL_ONLY"] = "1" if model_only_value else "0"
        if hasattr(self, "story_global_overview_enabled"):
            try:
                global_overview_enabled = bool(self.story_global_overview_enabled.get())
            except Exception:
                global_overview_enabled = True
            payload["STORY_GLOBAL_OVERVIEW_ENABLED"] = "1" if global_overview_enabled else "0"
        if hasattr(self, "story_overview_before_generate"):
            try:
                overview_value = bool(self.story_overview_before_generate.get())
            except Exception:
                overview_value = True
            payload["STORY_OVERVIEW_BEFORE_GENERATE"] = "1" if overview_value else "0"
        if hasattr(self, "story_preview_before_apply"):
            try:
                preview_value = bool(self.story_preview_before_apply.get())
            except Exception:
                preview_value = True
            payload["STORY_PREVIEW_BEFORE_APPLY"] = "1" if preview_value else "0"
        if hasattr(self, "rag_min_score"):
            rag_min_score_value = self._clamp_float(self.rag_min_score.get(), default=0.12, min_value=0.0, max_value=1.0)
            payload["RAG_MIN_SCORE"] = f"{rag_min_score_value:.2f}"
        return payload

    def _read_mode_setting_value(self, key: str):
        var = getattr(self, key, None)
        if var is None or not hasattr(var, "get"):
            return None
        try:
            return var.get()
        except Exception:
            return None

    def _set_mode_setting_value(self, key: str, value) -> None:
        var = getattr(self, key, None)
        if var is None or not hasattr(var, "set"):
            return
        try:
            if key in self._BOOL_MODE_KEYS:
                var.set(bool(value))
                return
            if key in self._INT_MODE_KEYS:
                var.set(int(value))
                return
            if key in self._FLOAT_MODE_KEYS:
                var.set(float(value))
                return
            var.set(value)
        except Exception:
            return

    def _infer_story_generation_mode_from_settings(self) -> str:
        fallback = DEFAULT_STORY_GENERATION_MODE
        if hasattr(self, "story_generation_mode") and hasattr(self.story_generation_mode, "get"):
            try:
                fallback = normalize_story_generation_mode(self.story_generation_mode.get())
            except Exception:
                fallback = DEFAULT_STORY_GENERATION_MODE

        any_compared = False
        for mode_key in ("fast", "balanced", "strict"):
            expected = get_story_generation_mode_settings(mode_key)
            if not expected:
                continue
            compared = 0
            matched = True
            for key, expected_val in expected.items():
                current_val = self._read_mode_setting_value(key)
                if current_val is None:
                    continue
                compared += 1
                if key in self._BOOL_MODE_KEYS:
                    if bool(current_val) != bool(expected_val):
                        matched = False
                        break
                elif key in self._INT_MODE_KEYS:
                    try:
                        if int(current_val) != int(expected_val):
                            matched = False
                            break
                    except Exception:
                        matched = False
                        break
                elif key in self._FLOAT_MODE_KEYS:
                    try:
                        if abs(float(current_val) - float(expected_val)) > 1e-6:
                            matched = False
                            break
                    except Exception:
                        matched = False
                        break
                elif str(current_val) != str(expected_val):
                    matched = False
                    break
            if compared > 0:
                any_compared = True
                if matched:
                    return mode_key
        if not any_compared:
            return fallback
        return "custom"

    def _sync_story_generation_mode_marker_from_settings(self) -> str:
        mode_key = self._infer_story_generation_mode_from_settings()
        if hasattr(self, "story_generation_mode") and hasattr(self.story_generation_mode, "set"):
            try:
                self.story_generation_mode.set(mode_key)
            except Exception:
                pass
        if hasattr(self, "story_generation_mode_key_to_label") and hasattr(
            self, "story_generation_mode_select_var"
        ):
            label = self.story_generation_mode_key_to_label.get(mode_key)
            if label:
                try:
                    self.story_generation_mode_select_var.set(label)
                except Exception:
                    pass
        if hasattr(self, "_update_story_generation_mode_desc"):
            self._update_story_generation_mode_desc()
        return mode_key

    def _apply_story_generation_mode(self, mode: str | None, *, persist: bool = False) -> str:
        mode_key = normalize_story_generation_mode(mode)
        mode_settings = get_story_generation_mode_settings(mode_key)
        for key, value in mode_settings.items():
            self._set_mode_setting_value(key, value)

        if hasattr(self, "story_generation_mode") and hasattr(self.story_generation_mode, "set"):
            try:
                self.story_generation_mode.set(mode_key)
            except Exception:
                pass
        if hasattr(self, "story_generation_mode_key_to_label") and hasattr(
            self, "story_generation_mode_select_var"
        ):
            label = self.story_generation_mode_key_to_label.get(mode_key)
            if label:
                try:
                    self.story_generation_mode_select_var.set(label)
                except Exception:
                    pass
        if hasattr(self, "_update_story_generation_mode_desc"):
            self._update_story_generation_mode_desc()

        if persist:
            try:
                env_path = self._resolve_env_path()
                self._save_story_env_payload(env_path)
            except Exception as e:
                import logging
                logging.getLogger(__name__).debug("persist story generation mode failed: %s", e)
        return mode_key

    def _on_story_generation_mode_changed(self, _event=None) -> None:
        mode_key = ""
        if hasattr(self, "story_generation_mode_select_var") and hasattr(
            self, "story_generation_mode_label_to_key"
        ):
            try:
                label = self.story_generation_mode_select_var.get().strip()
                mode_key = self.story_generation_mode_label_to_key.get(label, "")
            except Exception:
                mode_key = ""
        if not mode_key and hasattr(self, "story_generation_mode"):
            try:
                mode_key = str(self.story_generation_mode.get() or "").strip()
            except Exception:
                mode_key = ""
        mode_key = normalize_story_generation_mode(mode_key)
        self._apply_story_generation_mode(mode_key, persist=True)

    def _update_story_generation_mode_desc(self) -> None:
        if not hasattr(self, "story_generation_mode_desc_label"):
            return
        current_mode = DEFAULT_STORY_GENERATION_MODE
        if hasattr(self, "story_generation_mode"):
            try:
                current_mode = normalize_story_generation_mode(self.story_generation_mode.get())
            except Exception:
                current_mode = DEFAULT_STORY_GENERATION_MODE

        for item in list_story_generation_modes():
            if item.get("key") == current_mode:
                label = str(item.get("label", current_mode))
                desc = str(item.get("description", ""))
                self.story_generation_mode_desc_label.config(text=f"{label}: {desc}")
                return
        self.story_generation_mode_desc_label.config(text=current_mode)

    def _save_story_env_payload(self, env_path: Path) -> None:
        """保存统一故事偏好到 .env。"""
        from dotenv import set_key

        for key, value in self._collect_story_env_payload().items():
            set_key(str(env_path), key, value)
        self._save_story_quality_settings(env_path)

    def _apply_story_env_preferences_from_env(self) -> None:
        """从环境变量加载统一故事偏好并同步到 UI 变量。"""
        story_mode_raw = (os.getenv("STORY_GENERATION_MODE", "") or "").strip()
        explicit_story_mode = ""
        if story_mode_raw:
            explicit_story_mode = normalize_story_generation_mode(story_mode_raw)
            if hasattr(self, "story_generation_mode"):
                self.story_generation_mode.set(explicit_story_mode)

        template_key = (os.getenv("STORY_TEMPLATE_KEY", "") or "").strip() or DEFAULT_STORY_TEMPLATE_KEY
        if hasattr(self, "story_template_key"):
            self.story_template_key.set(template_key)
        if hasattr(self, "story_template_key_to_label") and hasattr(self, "story_template_select_var"):
            template_label = self.story_template_key_to_label.get(template_key)
            if template_label:
                self.story_template_select_var.set(template_label)
        if hasattr(self, "_update_story_template_desc"):
            self._update_story_template_desc()

        template_strategy = normalize_story_template_strategy(
            (os.getenv("STORY_TEMPLATE_STRATEGY", "") or "").strip() or DEFAULT_STORY_TEMPLATE_STRATEGY
        )
        if hasattr(self, "story_template_strategy"):
            self.story_template_strategy.set(template_strategy)
        if hasattr(self, "story_template_strategy_key_to_label") and hasattr(
            self, "story_template_strategy_select_var"
        ):
            strategy_label = self.story_template_strategy_key_to_label.get(template_strategy)
            if strategy_label:
                self.story_template_strategy_select_var.set(strategy_label)
        if hasattr(self, "_update_story_template_strategy_desc"):
            self._update_story_template_strategy_desc()

        creativity_fallback = "stable"
        if hasattr(self, "story_creativity_mode"):
            try:
                creativity_fallback = self.story_creativity_mode.get()
            except Exception:
                creativity_fallback = "stable"
        creativity_mode = normalize_story_creativity_mode(
            (os.getenv("STORY_CREATIVITY_MODE", "") or "").strip() or creativity_fallback
        )
        if hasattr(self, "story_creativity_mode"):
            self.story_creativity_mode.set(creativity_mode)
        if hasattr(self, "story_creativity_key_to_label") and hasattr(self, "story_creativity_select_var"):
            creativity_label = self.story_creativity_key_to_label.get(creativity_mode)
            if creativity_label:
                self.story_creativity_select_var.set(creativity_label)
        if hasattr(self, "_update_story_creativity_mode_desc"):
            self._update_story_creativity_mode_desc()

        if hasattr(self, "target_chars"):
            chars_raw = (os.getenv("TARGET_CHARS", "") or "").strip()
            if chars_raw:
                self.target_chars.set(self._clamp_int(chars_raw, default=1800, min_value=500, max_value=30000))
        if hasattr(self, "model_only"):
            model_only_raw = (os.getenv("MODEL_ONLY", "") or "").strip().lower()
            if model_only_raw:
                self.model_only.set(self._parse_bool_env(model_only_raw, default=False))
        if hasattr(self, "story_global_overview_enabled"):
            global_overview_raw = (os.getenv("STORY_GLOBAL_OVERVIEW_ENABLED", "") or "").strip().lower()
            if global_overview_raw:
                self.story_global_overview_enabled.set(self._parse_bool_env(global_overview_raw, default=True))
        if hasattr(self, "story_overview_before_generate"):
            overview_raw = (os.getenv("STORY_OVERVIEW_BEFORE_GENERATE", "") or "").strip().lower()
            if overview_raw:
                self.story_overview_before_generate.set(self._parse_bool_env(overview_raw, default=True))
        if hasattr(self, "story_preview_before_apply"):
            preview_raw = (os.getenv("STORY_PREVIEW_BEFORE_APPLY", "") or "").strip().lower()
            if preview_raw:
                self.story_preview_before_apply.set(self._parse_bool_env(preview_raw, default=True))
        if hasattr(self, "rag_min_score"):
            rag_raw = (os.getenv("RAG_MIN_SCORE", "") or "").strip()
            if rag_raw:
                self.rag_min_score.set(self._clamp_float(rag_raw, default=0.12, min_value=0.0, max_value=1.0))
        if hasattr(self, "story_quality_review_enabled"):
            quality_review_raw = (os.getenv("STORY_QUALITY_REVIEW", "") or "").strip().lower()
            if quality_review_raw:
                self.story_quality_review_enabled.set(self._parse_bool_env(quality_review_raw, default=True))
        if hasattr(self, "story_quality_min_avg"):
            quality_min_avg_raw = (os.getenv("STORY_QUALITY_MIN_AVG", "") or "").strip()
            if quality_min_avg_raw:
                self.story_quality_min_avg.set(
                    self._clamp_float(quality_min_avg_raw, default=7.4, min_value=1.0, max_value=10.0)
                )
        if hasattr(self, "story_quality_min_dim"):
            quality_min_dim_raw = (os.getenv("STORY_QUALITY_MIN_DIM", "") or "").strip()
            if quality_min_dim_raw:
                self.story_quality_min_dim.set(
                    self._clamp_float(quality_min_dim_raw, default=6.8, min_value=1.0, max_value=10.0)
                )
        if hasattr(self, "story_outline_alignment_strict"):
            strict_raw = (os.getenv("STORY_OUTLINE_ALIGNMENT_STRICT", "") or "").strip().lower()
            if strict_raw:
                self.story_outline_alignment_strict.set(self._parse_bool_env(strict_raw, default=True))
        if hasattr(self, "story_outline_alignment_max_attempts"):
            attempts_raw = (os.getenv("STORY_OUTLINE_ALIGNMENT_MAX_ATTEMPTS", "") or "").strip()
            if attempts_raw:
                self.story_outline_alignment_max_attempts.set(
                    self._clamp_int(attempts_raw, default=2, min_value=1, max_value=4)
                )

        if explicit_story_mode in {"fast", "balanced", "strict"}:
            self._apply_story_generation_mode(explicit_story_mode, persist=False)
        else:
            self._sync_story_generation_mode_marker_from_settings()
