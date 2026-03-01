"""Provider UI handlers extracted from settings mixin."""

from tkinter import END


class SettingsProviderUIMixin:
    """Handle provider/model selection updates on settings page."""

    @staticmethod
    def _is_custom_provider(provider_name: str) -> bool:
        name = (provider_name or "").strip()
        if not name:
            return False
        text = name.lower()
        if "custom" in text:
            return True
        # Backward-compat for mojibake aliases that may degrade to "?????"
        if set(name) == {"?"}:
            return True
        return any(
            token in name
            for token in (
                "自定义",
                "自訂",
                "用户自定义",
                "\u95bc\u5949\u4e9c\u9423\u70ac\u7a0a?",
                "\u95c1\u714e\ue68e\u6d5c\u6ec8\u60be\u9410\ue102\u2595?",
            )
        )

    def _on_settings_provider_change(self, event=None):
        provider_name = self.settings_api_provider.get()
        if not (hasattr(self, "api_providers") and provider_name in self.api_providers):
            return

        provider = self.api_providers[provider_name]
        models = provider.get("models", ["default"])
        display_models = self._decorate_model_list(models, "text")
        self.settings_combo_model["values"] = display_models or [""]

        if event is not None and self._models_need_refresh(models):
            key = provider.get("key", "")
            base_url = provider.get("base_url", "")
            if key and base_url:
                self._refresh_models_for_provider(provider_name, key, base_url, log_to_settings=False)

        saved_model = None
        if hasattr(self, "api_presets") and provider_name in self.api_presets:
            saved_model = self.api_presets[provider_name].get("model", "")

        if saved_model:
            raw_saved = self._strip_model_label(saved_model)
            self.settings_model_var.set(self._decorate_model_value(raw_saved, "text"))
        else:
            default_model = models[0] if models else ""
            self.settings_model_var.set(self._decorate_model_value(default_model, "text"))

        if self._is_custom_provider(provider_name) and hasattr(self, "settings_custom_model"):
            current_custom = self.settings_custom_model.get().strip()
            if not current_custom and saved_model:
                self.settings_custom_model.delete(0, END)
                self.settings_custom_model.insert(0, saved_model)

        if hasattr(self, "settings_combo_model"):
            self.settings_combo_model.update()

        self.settings_base_url.delete(0, END)
        self.settings_base_url.insert(0, provider.get("base_url", ""))
        self.settings_api_key.delete(0, END)
        self.settings_api_key.insert(0, provider.get("key", ""))

    def _on_settings_img_provider_change(self, event=None):
        provider_name = self.settings_img_provider.get()
        if not (hasattr(self, "img_api_providers") and provider_name in self.img_api_providers):
            return

        provider = self.img_api_providers[provider_name]
        models = provider.get("models", ["default"])
        display_models = self._decorate_model_list(models, "image")
        self.settings_combo_img_model["values"] = display_models or [""]

        saved_model = None
        if hasattr(self, "img_api_presets") and provider_name in self.img_api_presets:
            saved_model = self.img_api_presets[provider_name].get("model", "")

        if saved_model:
            raw_saved = self._strip_model_label(saved_model)
            self.settings_img_model_var.set(self._decorate_model_value(raw_saved, "image"))
        else:
            default_model = models[0] if models else ""
            self.settings_img_model_var.set(self._decorate_model_value(default_model, "image"))

        if self._is_custom_provider(provider_name) and hasattr(self, "settings_img_custom_model"):
            current_custom = self.settings_img_custom_model.get().strip()
            if not current_custom and saved_model:
                self.settings_img_custom_model.delete(0, END)
                self.settings_img_custom_model.insert(0, saved_model)

        self.settings_img_base_url.delete(0, END)
        self.settings_img_base_url.insert(0, provider.get("base_url", ""))
        self.settings_img_api_key.delete(0, END)
        self.settings_img_api_key.insert(0, provider.get("key", ""))

        self._sync_img_runtime_from_settings(provider_name)

    def _toggle_key_visibility(self):
        if self.show_key_var.get():
            self.settings_api_key.config(show="")
        else:
            self.settings_api_key.config(show="*")

    def _toggle_img_key_visibility(self):
        if self.show_img_key_var.get():
            self.settings_img_api_key.config(show="")
        else:
            self.settings_img_api_key.config(show="*")

    def _get_current_story_model(self):
        model = self._strip_model_label(self.settings_model_var.get().strip())
        custom_model = ""
        if hasattr(self, "settings_custom_model"):
            custom_model = self._strip_model_label(self.settings_custom_model.get().strip())
        provider = self.settings_api_provider.get().strip() if hasattr(self, "settings_api_provider") else ""
        if self._is_custom_provider(provider):
            return custom_model or model or "gpt-3.5-turbo"
        return model or custom_model or "gpt-3.5-turbo"

    def _get_current_img_model(self):
        model = self._strip_model_label(self.settings_img_model_var.get().strip())
        custom_model = ""
        if hasattr(self, "settings_img_custom_model"):
            custom_model = self._strip_model_label(self.settings_img_custom_model.get().strip())
        provider = self.settings_img_provider.get().strip() if hasattr(self, "settings_img_provider") else ""
        if self._is_custom_provider(provider):
            return custom_model or model or "dall-e-3"
        return model or custom_model or "dall-e-3"
