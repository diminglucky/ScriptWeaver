"""Model list loading helpers for story/character tabs."""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)


class StoryPromptModelLoadingMixin:
    """Load model list from selected provider and set defaults."""
    def _canonical_story_preset_name(self, raw_name: str, cfg: dict) -> str:
        name = str(raw_name or "").strip()
        if not name:
            return "Custom"
        canonical = {
            "DeepSeek",
            "OpenAI",
            "Azure OpenAI",
            "Moonshot (Kimi)",
            "Zhipu AI (GLM)",
            "Baidu ERNIE",
            "Alibaba Qwen",
            "Custom",
        }
        if name in canonical:
            return name

        legacy_alias = {
            "Moonshot (鏈堜箣鏆楅潰)": "Moonshot (Kimi)",
            "Moonshot (月之暗面)": "Moonshot (Kimi)",
            "鏅鸿氨AI (GLM)": "Zhipu AI (GLM)",
            "智谱AI (GLM)": "Zhipu AI (GLM)",
            "鐧惧害鏂囧績": "Baidu ERNIE",
            "百度文心": "Baidu ERNIE",
            "闃块噷閫氫箟": "Alibaba Qwen",
            "阿里通义": "Alibaba Qwen",
            "鑷畾涔?": "Custom",
            "自定义": "Custom",
        }
        if name in legacy_alias:
            return legacy_alias[name]
        return name

    def _normalize_story_preset_names(self):
        presets = getattr(self, "api_presets", None)
        if not isinstance(presets, dict):
            return
        normalized = {}
        for raw_name, cfg in presets.items():
            if not isinstance(cfg, dict):
                continue
            name = self._canonical_story_preset_name(raw_name, cfg)
            if name not in normalized:
                normalized[name] = cfg
            else:
                existing = normalized[name]
                for key in ("key", "base_url", "model"):
                    if not existing.get(key) and cfg.get(key):
                        existing[key] = cfg[key]
        self.api_presets = normalized

    def _resolve_model_fetch_api_config(self):
        presets = getattr(self, "api_presets", None)
        if not isinstance(presets, dict) or not presets:
            return None, "", ""

        selected = ""
        if hasattr(self, "api_preset"):
            try:
                if hasattr(self, "_ui_get"):
                    selected = (self._ui_get(self.api_preset.get) or "").strip()
                else:
                    selected = (self.api_preset.get() or "").strip()
            except Exception as exc:
                logger.debug("Failed to read current api_preset: %s", exc)

        if selected and isinstance(presets.get(selected), dict):
            cfg = presets[selected]
            return selected, cfg.get("key", ""), cfg.get("base_url", "")

        for alias in ("Custom",):
            cfg = presets.get(alias)
            if isinstance(cfg, dict):
                return alias, cfg.get("key", ""), cfg.get("base_url", "")

        for name, cfg in presets.items():
            if isinstance(cfg, dict) and (cfg.get("key") or cfg.get("base_url")):
                return name, cfg.get("key", ""), cfg.get("base_url", "")

        return None, "", ""

    def _load_available_models(self):
        def task():
            try:
                import requests

                preset_name, api_key, base_url = self._resolve_model_fetch_api_config()
                if not api_key or not base_url:
                    logger.warning("Model fetch skipped: incomplete API config (preset=%s)", preset_name)
                    self._set_default_models()
                    return

                base_url = base_url.rstrip("/")
                candidates = [f"{base_url}/models"] if base_url.endswith("/v1") else [f"{base_url}/v1/models", f"{base_url}/models"]
                headers = {"Authorization": f"Bearer {api_key}", "User-Agent": "Mozilla/5.0"}
                last_status = None
                result = None
                for url in candidates:
                    try:
                        response = requests.get(url, headers=headers, timeout=10)
                        last_status = response.status_code
                        if response.status_code == 200:
                            result = response.json()
                            break
                    except Exception as exc:
                        logger.debug("Model list probe failed for %s: %s", url, exc)
                        continue

                if result is not None:
                    models = []
                    if isinstance(result, dict):
                        if isinstance(result.get("data"), list):
                            models = [m.get("id") or m.get("name") for m in result["data"] if isinstance(m, dict)]
                        elif isinstance(result.get("models"), list):
                            models = [m.get("id") or m.get("name") for m in result["models"] if isinstance(m, dict)]
                    elif isinstance(result, list):
                        models = [m.get("id") or m.get("name") for m in result if isinstance(m, dict)]

                    models = [m for m in models if m]
                    if models:
                        if hasattr(self, "combo_story_model"):
                            self._ui(self.combo_story_model.__setitem__, "values", models)
                            current = self._ui_get(self.story_model_var.get) if hasattr(self, "_ui_get") else self.story_model_var.get()
                            if current not in models:
                                self._ui(self.story_model_var.set, models[0])

                        if hasattr(self, "combo_char_model"):
                            self._ui(self.combo_char_model.__setitem__, "values", models)
                            current = self._ui_get(self.char_model_var.get) if hasattr(self, "_ui_get") else self.char_model_var.get()
                            if current not in models:
                                self._ui(self.char_model_var.set, models[0])

                        logger.info("Loaded %d models for story/character tabs (preset=%s)", len(models), preset_name)
                    else:
                        logger.warning("Model fetch returned no model entries; using defaults")
                        self._set_default_models()
                else:
                    logger.warning("Model fetch failed with status=%s; using defaults", last_status)
                    self._set_default_models()

            except Exception as exc:
                logger.warning("Failed to load available model list: %s", exc)
                self._set_default_models()

        threading.Thread(target=task, daemon=True).start()

    def _set_default_models(self):
        def _ui_call(func, *args):
            if hasattr(self, "_ui"):
                return self._ui(func, *args)
            return func(*args)

        default_models = [
            "claude-sonnet-4-5",
            "claude-sonnet-4-5-20250929",
            "claude-sonnet-4",
            "gemini-3-pro-preview",
            "gemini-3-flash-preview",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gpt-4o",
            "gpt-4o-mini",
        ]

        if hasattr(self, "combo_story_model"):
            _ui_call(self.combo_story_model.__setitem__, "values", default_models)
            current = self._ui_get(self.story_model_var.get) if hasattr(self, "_ui_get") else self.story_model_var.get()
            if current not in default_models:
                _ui_call(self.story_model_var.set, default_models[0])

        if hasattr(self, "combo_char_model"):
            _ui_call(self.combo_char_model.__setitem__, "values", default_models)
            current = self._ui_get(self.char_model_var.get) if hasattr(self, "_ui_get") else self.char_model_var.get()
            if current not in default_models:
                _ui_call(self.char_model_var.set, default_models[0])

        logger.info("Using default model list (%d entries)", len(default_models))
