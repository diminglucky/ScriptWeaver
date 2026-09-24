"""ModelRegistry: constructs chat models from routing, presets, and keys."""

from __future__ import annotations

import json
from typing import Any

from src.clients.chat_response import extract_chat_content
from src.shared.domain.errors import DependencyMissing, ModelProviderError


class _DeterministicChatModel:
    def __init__(self, *, task: str, model: str = "deterministic", temperature: float = 0.0):
        self.task = task
        self.model = model
        self.temperature = temperature

    async def ainvoke(self, prompt: Any) -> str:
        state = prompt.get("state", prompt) if isinstance(prompt, dict) else {}
        request = state.get("request", {}) if isinstance(state, dict) else {}
        requirement = state.get("requirement") or request.get("requirement") or request.get("story_context") or ""
        genre = state.get("genre") or request.get("genre") or ""
        style = state.get("style") or request.get("style") or ""
        target_chars = int(state.get("target_chars") or request.get("target_chars") or 0)
        chapter_count = int(state.get("chapter_count") or request.get("chapter_count") or 1)

        if self.task in {"story_bible", "story_outline", "outline"}:
            return json.dumps({
                "requirement": requirement,
                "genre": genre,
                "style": style,
                "theme": "growth and cost",
                "premise": requirement or "The protagonist faces a life-changing choice.",
                "core_conflict": "desire versus consequence",
                "target_chars": target_chars,
                "characters": [{
                    "name": "protagonist",
                    "role": "protagonist",
                    "motivation": requirement,
                }],
                "outline": [
                    {"index": i, "title": f"第{i + 1}章", "purpose": "推进主线", "expected_chars": 1200}
                    for i in range(chapter_count)
                ],
            }, ensure_ascii=False)

        if self.task in {"character_design", "character_extract", "character_description"}:
            return json.dumps({
                "characters": [{
                    "name": "protagonist",
                    "role": "protagonist",
                    "motivation": requirement,
                }]
            }, ensure_ascii=False)

        if self.task in {"chapter", "story_generate"}:
            section = prompt.get("section", {}) if isinstance(prompt, dict) else {}
            title = section.get("title") or "章节"
            purpose = section.get("purpose") or "推进主线"
            content = f"{title}\n\n{requirement or '故事继续发展。'}\n\n{purpose}"
            return json.dumps({
                "section_index": int(section.get("index") or 0),
                "title": title,
                "content": content,
                "summary": purpose,
                "char_count": len(content),
            }, ensure_ascii=False)

        if self.task == "review":
            return json.dumps({"score": 1.0, "notes": [], "suggested_fixes": []}, ensure_ascii=False)

        return "{}"


class _OpenAICompatibleChatModel:
    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str = "",
        temperature: float = 0.0,
        extras: dict | None = None,
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.extras = extras or {}

    async def ainvoke(self, prompt: Any) -> str:
        try:
            from openai import AsyncOpenAI
        except Exception as exc:
            raise DependencyMissing("openai package is required for this model provider") from exc

        client_kwargs: dict[str, Any] = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        client = AsyncOpenAI(**client_kwargs)
        content = prompt if isinstance(prompt, str) else json.dumps(prompt, ensure_ascii=False, default=str)
        try:
            resp = await client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[{"role": "user", "content": content}],
                **self.extras,
            )
        except Exception as exc:
            raise ModelProviderError(str(exc), detail={"model": self.model, "base_url": self.base_url}) from exc
        return extract_chat_content(resp)


_TASK_FALLBACKS = {
    "story_bible": "story_outline",
    "outline": "story_outline",
    "chapter": "story_generate",
    "character_design": "character_description",
    "review": "story_generate",
}


def _is_fake_provider(provider: str) -> bool:
    return provider.lower() in {"", "fake", "local", "mock", "deterministic"}


def _allow_missing_key_fallback(provider: str) -> bool:
    return provider.lower() in {"custom", "自定义"}


class ModelRegistry:
    """Single-source factory for chat LLMs across all workflows."""

    def __init__(self, *, routing, presets, vault):
        self.routing = routing
        self.presets = presets
        self.vault = vault

    @classmethod
    def from_config(cls) -> "ModelRegistry":
        from src.shared.config.keyfile import KeyVault
        from src.shared.config.presets import load_presets
        from src.shared.config.routing import load_routing

        return cls(
            routing=load_routing(),
            presets=load_presets(),
            vault=KeyVault(),
        )

    def chat_model(
        self,
        task: str,
        *,
        provider: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        streaming: bool = False,
        callbacks: list | None = None,
    ) -> Any:
        route = None
        try:
            route = self.routing.resolve(task, fallback=_TASK_FALLBACKS.get(task))
        except Exception:
            route = None

        provider_name = provider or (route.provider if route else "deterministic")
        model_name = model or (route.model if route else "deterministic")
        temp = temperature if temperature is not None else (route.temperature if route else 0.0)
        extras = dict(route.extras) if route else {}
        extras.pop("streaming", None)
        extras.pop("callbacks", None)

        if _is_fake_provider(provider_name):
            return _DeterministicChatModel(task=task, model=model_name, temperature=float(temp or 0.0))

        preset = self.presets.get_chat(provider_name) if self.presets is not None else None
        base_url = extras.pop("base_url", "")
        api_key_alias = extras.pop("api_key_alias", "")
        if preset is not None:
            base_url = preset.base_url or base_url
            api_key_alias = preset.api_key_alias or api_key_alias
            extras = {**preset.extras, **extras}

        api_key = ""
        if self.vault is not None:
            api_key = self.vault.get(api_key_alias or provider_name, "")
        if not api_key:
            if _allow_missing_key_fallback(provider_name):
                return _DeterministicChatModel(task=task, model=model_name, temperature=float(temp or 0.0))
            raise ModelProviderError(
                "missing API key for model provider",
                detail={"provider": provider_name, "api_key_alias": api_key_alias},
            )

        return _OpenAICompatibleChatModel(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=float(temp or 0.0),
            extras=extras,
        )

    def estimate_cost(self, task: str, prompt_tokens: int, completion_tokens: int) -> float:
        return 0.0
