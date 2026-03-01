"""Runtime sync helpers extracted from settings mixin."""

import logging
import os

logger = logging.getLogger(__name__)


class SettingsRuntimeSyncMixin:
    """Sync image API settings to runtime variables."""

    def _sync_img_runtime_from_settings(self, provider_name: str | None = None) -> None:
        try:
            name = provider_name or (self.settings_img_provider.get().strip() if hasattr(self, "settings_img_provider") else "")
            key = self.settings_img_api_key.get().strip() if hasattr(self, "settings_img_api_key") else ""
            base_url = self.settings_img_base_url.get().strip() if hasattr(self, "settings_img_base_url") else ""
            model = self._get_current_img_model() if hasattr(self, "_get_current_img_model") else ""

            if hasattr(self, "img_api_key"):
                self.img_api_key.set(key)
            if hasattr(self, "img_base_url"):
                self.img_base_url.set(base_url)
            if hasattr(self, "img_model"):
                self.img_model.set(model)

            if hasattr(self, "img_api_type"):
                api_type = None
                if hasattr(self, "img_api_providers") and name in self.img_api_providers:
                    api_type = self.img_api_providers[name].get("provider")
                if not api_type:
                    lower = name.lower()
                    if "混元" in name or "hunyuan" in lower:
                        api_type = "hunyuan"
                    else:
                        api_type = "openai"
                self.img_api_type.set(api_type)
        except Exception as e:
            logger.debug("sync image runtime from settings failed: %s", e)

    def _sync_img_runtime_from_config(self, provider_name: str | None = None) -> None:
        try:
            name = provider_name or ""
            if not name:
                name = os.getenv("IMAGE_GEN_API", "") or os.getenv("IMG_API_PRESET", "")
            if not name and hasattr(self, "settings_img_provider"):
                name = self.settings_img_provider.get().strip()

            config = None
            if hasattr(self, "img_api_providers") and name in self.img_api_providers:
                config = self.img_api_providers[name]
            elif hasattr(self, "img_api_presets") and name in self.img_api_presets:
                config = self.img_api_presets[name]
            elif hasattr(self, "img_api_providers"):
                for provider_name_iter, cfg in self.img_api_providers.items():
                    if cfg.get("key"):
                        name = provider_name_iter
                        config = cfg
                        break

            if not config:
                return

            key = (config.get("key") or "").strip()
            base_url = (config.get("base_url") or "").strip()
            model = self._strip_model_label(config.get("model", "")) if hasattr(self, "_strip_model_label") else (
                config.get("model", "") or ""
            )

            if hasattr(self, "img_api_key"):
                self.img_api_key.set(key)
            if hasattr(self, "img_base_url"):
                self.img_base_url.set(base_url)
            if hasattr(self, "img_model"):
                self.img_model.set(model)

            if hasattr(self, "img_api_type"):
                api_type = config.get("provider")
                if not api_type:
                    lower = name.lower()
                    if "混元" in name or "hunyuan" in lower:
                        api_type = "hunyuan"
                    else:
                        api_type = "openai"
                self.img_api_type.set(api_type)
        except Exception as e:
            logger.debug("sync image runtime from config failed: %s", e)
