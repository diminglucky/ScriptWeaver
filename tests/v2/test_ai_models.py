from __future__ import annotations

import asyncio
import json

import pytest

from src.services.story_service.core.ai.models import ModelRegistry
from src.shared.config.keyfile import KeyVault
from src.shared.config.presets import Preset, PresetsConfig
from src.shared.config.routing import RouteEntry, RoutingConfig
from src.shared.domain.errors import ModelProviderError


def test_chat_model_returns_deterministic_model_when_no_route():
    registry = ModelRegistry(routing=RoutingConfig(), presets=PresetsConfig(), vault=KeyVault())
    llm = registry.chat_model("story_bible")
    raw = asyncio.run(llm.ainvoke({"state": {"requirement": "雨夜", "chapter_count": 2}}))
    payload = json.loads(raw)
    assert payload["premise"] == "雨夜"
    assert [x["title"] for x in payload["outline"]] == ["第1章", "第2章"]


def test_chat_model_resolves_fake_route_aliases():
    registry = ModelRegistry(
        routing=RoutingConfig(by_task={"story_outline": RouteEntry(provider="fake", model="fake-chat")}),
        presets=PresetsConfig(),
        vault=KeyVault(),
    )
    llm = registry.chat_model("story_bible")
    assert llm.model == "fake-chat"
    assert json.loads(asyncio.run(llm.ainvoke({"state": {"requirement": "x"}})))["requirement"] == "x"


def test_chat_model_requires_key_for_real_provider():
    registry = ModelRegistry(
        routing=RoutingConfig(by_task={"story_generate": RouteEntry(provider="openai", model="gpt")}),
        presets=PresetsConfig(),
        vault=KeyVault(),
    )
    with pytest.raises(ModelProviderError):
        registry.chat_model("chapter")


def test_chat_model_custom_provider_falls_back_without_key():
    registry = ModelRegistry(
        routing=RoutingConfig(by_task={"story_generate": RouteEntry(provider="自定义", model="m")}),
        presets=PresetsConfig(),
        vault=KeyVault(),
    )
    llm = registry.chat_model("chapter")
    assert llm.model == "m"


def test_chat_model_builds_openai_compatible_wrapper_with_preset_and_key():
    registry = ModelRegistry(
        routing=RoutingConfig(by_task={"story_generate": RouteEntry(provider="custom", model="m", temperature=0.7)}),
        presets=PresetsConfig(chat={"custom": Preset(name="custom", base_url="https://example.test/v1", api_key_alias="k")}),
        vault=KeyVault(by_alias={"k": "secret"}),
    )
    llm = registry.chat_model("chapter")
    assert llm.model == "m"
    assert llm.base_url == "https://example.test/v1"
    assert llm.temperature == 0.7
