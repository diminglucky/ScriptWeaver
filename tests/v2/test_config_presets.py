"""PresetsConfig loaders. See v2 plan §12."""

from __future__ import annotations

import json
from pathlib import Path

from src.shared.config.presets import load_presets


def _write(path: Path, payload) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_load_presets_returns_empty_when_files_missing(tmp_path: Path):
    cfg = load_presets(chat_path=tmp_path / "x.json", image_path=tmp_path / "y.json")
    assert cfg.chat == {}
    assert cfg.image == {}


def test_load_presets_handles_list_root(tmp_path: Path):
    chat = _write(
        tmp_path / "custom_api_presets.json",
        [
            {"name": "deepseek-prod", "base_url": "https://api.deepseek.com", "api_key_alias": "deepseek_main"},
            {"name": "openai-edge", "base_url": "https://api.openai.com", "api_key_alias": "openai_edge"},
        ],
    )
    cfg = load_presets(chat_path=chat, image_path=tmp_path / "none.json")
    assert "deepseek-prod" in cfg.chat
    assert cfg.chat["deepseek-prod"].base_url == "https://api.deepseek.com"
    assert cfg.chat["deepseek-prod"].api_key_alias == "deepseek_main"


def test_load_presets_handles_dict_with_presets_key(tmp_path: Path):
    image = _write(
        tmp_path / "custom_image_api_presets.json",
        {
            "presets": [
                {"id": "hunyuan", "base_url": "https://h.example", "key_alias": "hunyuan_key"},
            ]
        },
    )
    cfg = load_presets(chat_path=tmp_path / "none.json", image_path=image)
    assert "hunyuan" in cfg.image
    assert cfg.image["hunyuan"].api_key_alias == "hunyuan_key"


def test_load_presets_skips_invalid_entries(tmp_path: Path):
    chat = _write(
        tmp_path / "c.json",
        [
            "string-not-dict",
            {"name": "ok", "base_url": "u"},
            {"base_url": "no-name"},  # missing name
        ],
    )
    cfg = load_presets(chat_path=chat, image_path=tmp_path / "none.json")
    assert list(cfg.chat.keys()) == ["ok"]


def test_get_chat_returns_none_for_missing(tmp_path: Path):
    cfg = load_presets(chat_path=tmp_path / "x.json", image_path=tmp_path / "y.json")
    assert cfg.get_chat("nope") is None
    assert cfg.get_image("nope") is None
