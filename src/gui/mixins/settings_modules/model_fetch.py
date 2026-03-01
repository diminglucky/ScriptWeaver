"""Model fetch/refresh helpers extracted from settings mixin."""

import logging
import threading
from tkinter import END

logger = logging.getLogger(__name__)


class SettingsModelFetchMixin:
    """Fetch model lists from provider APIs and refresh related UI."""

    def _fetch_models_from_api(self, api_key: str, base_url: str):
        try:
            import requests

            base = (base_url or "").strip().rstrip("/")
            if not base:
                return [], "Base URL is empty"

            candidates = [f"{base}/models"] if base.endswith("/v1") else [f"{base}/v1/models", f"{base}/models"]
            headers = {"Authorization": f"Bearer {api_key}", "User-Agent": "Mozilla/5.0"}

            last_error = None
            for url in candidates:
                try:
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code != 200:
                        last_error = f"{resp.status_code}"
                        continue
                    result = resp.json()

                    def _extract(items):
                        out = []
                        for item in items:
                            if isinstance(item, dict):
                                mid = item.get("id") or item.get("name")
                            elif isinstance(item, str):
                                mid = item
                            else:
                                mid = None
                            if mid:
                                out.append(str(mid))
                        return out

                    models = []
                    if isinstance(result, dict):
                        if isinstance(result.get("data"), list):
                            models = _extract(result.get("data", []))
                        elif isinstance(result.get("models"), list):
                            models = _extract(result.get("models", []))
                        elif isinstance(result.get("result"), list):
                            models = _extract(result.get("result", []))
                    elif isinstance(result, list):
                        models = _extract(result)

                    seen = set()
                    unique = []
                    for model in models:
                        if model not in seen:
                            seen.add(model)
                            unique.append(model)

                    if unique:
                        return unique, None
                    last_error = "response has no models"
                except Exception as e:
                    last_error = str(e)
                    continue
            return [], last_error or "request failed"
        except Exception as e:
            return [], str(e)

    def _refresh_models_for_provider(
        self,
        provider: str,
        api_key: str,
        base_url: str,
        log_to_settings: bool = False,
    ) -> None:
        if not provider or not api_key or not base_url:
            return
        if not hasattr(self, "_model_fetching"):
            self._model_fetching = set()
        if provider in self._model_fetching:
            return
        self._model_fetching.add(provider)

        def ui_call(func, *args, **kwargs):
            if hasattr(self, "_ui"):
                return self._ui(func, *args, **kwargs)
            return func(*args, **kwargs)

        def task():
            try:
                models, err = self._fetch_models_from_api(api_key, base_url)
                if models:
                    def apply_models():
                        if hasattr(self, "api_providers") and provider in self.api_providers:
                            self.api_providers[provider]["models"] = models
                            self.api_providers[provider]["key"] = api_key
                            self.api_providers[provider]["base_url"] = base_url

                        if (
                            hasattr(self, "settings_api_provider")
                            and self.settings_api_provider.get() == provider
                            and hasattr(self, "settings_combo_model")
                        ):
                            display_models = self._decorate_model_list(models, "text")
                            self.settings_combo_model["values"] = display_models or [""]
                            current = self.settings_model_var.get().strip()
                            raw_current = self._strip_model_label(current)
                            if not raw_current and models:
                                if display_models:
                                    self.settings_model_var.set(display_models[0])
                            elif raw_current in models:
                                decorated = self._decorate_model_value(raw_current, "text")
                                if current != decorated:
                                    self.settings_model_var.set(decorated)

                        if hasattr(self, "model_route_vars"):
                            for _task_key, route_ui in self.model_route_vars.items():
                                if route_ui["provider_var"].get() == provider:
                                    task_key = route_ui.get("task_key", "")
                                    kind = "image" if str(task_key).startswith("image_") else "text"
                                    display_models = self._decorate_model_list(models, kind)
                                    route_ui["combo_model"]["values"] = display_models or [""]
                                    current = route_ui["model_var"].get().strip()
                                    raw_current = self._strip_model_label(current)
                                    if not raw_current and models:
                                        if display_models:
                                            route_ui["model_var"].set(display_models[0])
                                    elif raw_current in models:
                                        decorated = self._decorate_model_value(raw_current, kind)
                                        if current != decorated:
                                            route_ui["model_var"].set(decorated)

                        if log_to_settings and hasattr(self, "settings_log"):
                            self.settings_log.insert(END, f"OK loaded {len(models)} models\n")
                            self.settings_log.see(END)

                    ui_call(apply_models)
                else:
                    if log_to_settings and hasattr(self, "settings_log"):
                        ui_call(self.settings_log.insert, END, f"WARN model fetch failed: {err or 'unknown'}\n")
                        ui_call(self.settings_log.see, END)
            finally:
                try:
                    self._model_fetching.discard(provider)
                except Exception as e:
                    logger.debug("clear model fetching flag failed: %s", e)

        threading.Thread(target=task, daemon=True).start()
