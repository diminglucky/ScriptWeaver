"""Model routing UI helpers extracted from settings mixin."""

from tkinter import END, messagebox

from ..config_modules.model_routing import MODEL_ROUTING_TASKS


class SettingsModelRoutingUIMixin:
    """Sync model routing configs with UI state."""

    def _on_route_provider_change(self, task_key: str) -> None:
        if not hasattr(self, "model_route_vars"):
            return
        route_ui = self.model_route_vars.get(task_key)
        if not route_ui:
            return

        provider = route_ui["provider_var"].get()
        models = []
        provider_cfg = None
        if hasattr(self, "api_providers") and provider in self.api_providers:
            provider_cfg = self.api_providers[provider]
            models = provider_cfg.get("models", [])
        elif hasattr(self, "api_presets") and provider in self.api_presets:
            saved_model = self.api_presets[provider].get("model", "")
            if saved_model:
                models = [saved_model]

        combo_model = route_ui["combo_model"]
        route_task_key = route_ui.get("task_key", "")
        kind = "image" if str(route_task_key).startswith("image_") else "text"
        display_models = self._decorate_model_list(models, kind)
        combo_model["values"] = display_models or [""]

        current_model = route_ui["model_var"].get().strip()
        raw_current = self._strip_model_label(current_model)
        if not raw_current and models:
            if display_models:
                route_ui["model_var"].set(display_models[0])
        elif raw_current in models:
            decorated = self._decorate_model_value(raw_current, kind)
            if current_model != decorated:
                route_ui["model_var"].set(decorated)

        if self._models_need_refresh(models):
            key = ""
            base_url = ""
            if provider_cfg:
                key = provider_cfg.get("key", "")
                base_url = provider_cfg.get("base_url", "")
            if hasattr(self, "settings_api_provider") and self.settings_api_provider.get() == provider:
                key = self.settings_api_key.get().strip() or key
                base_url = self.settings_base_url.get().strip() or base_url
            if key and base_url:
                self._refresh_models_for_provider(provider, key, base_url, log_to_settings=False)

    def _load_model_routing_to_ui(self) -> None:
        if not hasattr(self, "model_route_vars"):
            return
        if hasattr(self, "_ensure_model_routing_loaded"):
            self._ensure_model_routing_loaded()

        for task_key, _label in MODEL_ROUTING_TASKS:
            route = self._get_task_route(task_key) if hasattr(self, "_get_task_route") else {}
            route_ui = self.model_route_vars.get(task_key)
            if not route_ui:
                continue
            provider = route.get("provider", "") or (
                self.settings_api_provider.get() if hasattr(self, "settings_api_provider") else "DeepSeek"
            )
            model = route.get("model", "")
            route_ui["provider_var"].set(provider)
            self._on_route_provider_change(task_key)
            if model:
                kind = "image" if str(task_key).startswith("image_") else "text"
                route_ui["model_var"].set(self._decorate_model_value(model, kind))

    def _save_model_routing_settings(self) -> None:
        if not hasattr(self, "model_route_vars"):
            return
        if not hasattr(self, "model_routing"):
            self.model_routing = {}

        for task_key, _label in MODEL_ROUTING_TASKS:
            route_ui = self.model_route_vars.get(task_key)
            if not route_ui:
                continue
            provider = route_ui["provider_var"].get().strip()
            model = self._strip_model_label(route_ui["model_var"].get().strip())
            self.model_routing[task_key] = {"provider": provider, "model": model}

        self._model_routing_loaded = True
        if hasattr(self, "_save_model_routing_to_file"):
            self._save_model_routing_to_file()
        if hasattr(self, "settings_log"):
            self.settings_log.insert(END, "OK model routing config saved\n")
            self.settings_log.see(END)
        messagebox.showinfo("成功", "模型路由已保存")
