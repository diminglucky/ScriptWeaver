"""Model label utilities extracted from settings mixin."""

import re


class SettingsModelUtilsMixin:
    """Helpers for model value normalization and display decoration."""

    def _strip_model_label(self, model: str) -> str:
        if not model:
            return ""
        value = str(model).strip()
        value = value.replace("\ufe0f", "")
        value = re.sub(r"^(?:[\U0001F300-\U0001FAFF]\s*)+", "", value)
        value = re.sub(r"^[^\w\u4e00-\u9fff]+", "", value)
        value = re.sub(r"^(?:text|image|文本|图像|图片)\s*", "", value, flags=re.IGNORECASE)
        value = re.sub(r"^[\|\-:：·、\s]+", "", value)
        return value.strip()

    def _decorate_model_value(self, model: str, kind: str) -> str:
        raw = self._strip_model_label(model)
        if not raw:
            return ""
        prefix = "🖼️ 图像" if kind == "image" else "🔵 文本"
        return f"{prefix} {raw}"

    def _decorate_model_list(self, models, kind: str):
        if not models:
            return []
        return [self._decorate_model_value(m, kind) for m in models if str(m).strip()]

    def _models_need_refresh(self, models) -> bool:
        if not models:
            return True
        cleaned = []
        for m in models:
            if isinstance(m, str) and m.strip():
                cleaned.append(m.strip())
        if not cleaned:
            return True
        if len(cleaned) == 1 and cleaned[0].lower() == "default":
            return True
        return False
