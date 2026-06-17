"""RoutingConfig load + merge + resolve. See docs/technical_architecture.md.3 / 搂12.4."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.shared.config.routing import RouteEntry, RoutingConfig, load_routing


def _write(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_load_routing_returns_empty_when_no_files(tmp_path: Path):
    cfg = load_routing(
        routing_path=tmp_path / "missing.json",
        custom_routing_path=tmp_path / "missing2.json",
    )
    assert cfg.by_task == {}


def test_load_routing_parses_basic_entry(tmp_path: Path):
    routing = _write(
        tmp_path / "model_routing.json",
        {
            "story_outline": {
                "provider": "deepseek",
                "model": "deepseek-chat",
                "temperature": 0.6,
                "max_tokens": 4096,
            }
        },
    )
    cfg = load_routing(routing_path=routing, custom_routing_path=tmp_path / "x.json")
    entry = cfg.by_task["story_outline"]
    assert entry.provider == "deepseek"
    assert entry.model == "deepseek-chat"
    assert entry.temperature == 0.6
    assert entry.extras == {"max_tokens": 4096}


def test_custom_routing_overrides_base(tmp_path: Path):
    base = _write(
        tmp_path / "model_routing.json",
        {"story_generate": {"provider": "openai", "model": "gpt-4o-mini"}},
    )
    custom = _write(
        tmp_path / "custom_model_routing.json",
        {"story_generate": {"provider": "deepseek", "model": "deepseek-chat"}},
    )
    cfg = load_routing(routing_path=base, custom_routing_path=custom)
    assert cfg.by_task["story_generate"].provider == "deepseek"
    assert cfg.by_task["story_generate"].model == "deepseek-chat"


def test_resolve_falls_back_when_task_missing():
    cfg = RoutingConfig(by_task={"story_outline": RouteEntry(provider="p", model="m")})
    fallback = cfg.resolve("requirement_parse", fallback="story_outline")
    assert fallback.model == "m"


def test_resolve_raises_when_no_match():
    cfg = RoutingConfig(by_task={})
    with pytest.raises(KeyError):
        cfg.resolve("nope")


def test_load_routing_skips_non_dict_entries(tmp_path: Path):
    routing = _write(
        tmp_path / "model_routing.json",
        {"good": {"provider": "p", "model": "m"}, "bad": "string-value"},
    )
    cfg = load_routing(routing_path=routing, custom_routing_path=tmp_path / "none.json")
    assert "good" in cfg.by_task
    assert "bad" not in cfg.by_task
