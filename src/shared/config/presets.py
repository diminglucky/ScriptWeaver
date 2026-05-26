"""Loads `custom_api_presets.json` + `custom_image_api_presets.json`.

See v2 plan §12. Each preset records a base_url plus an api_key alias which
must be resolvable via `KeyVault`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .paths import get_repo_paths


@dataclass
class Preset:
    name: str
    base_url: str
    api_key_alias: str = ""
    extras: dict = field(default_factory=dict)


@dataclass
class PresetsConfig:
    chat: dict[str, Preset] = field(default_factory=dict)
    image: dict[str, Preset] = field(default_factory=dict)

    def get_chat(self, name: str) -> Preset | None:
        return self.chat.get(name)

    def get_image(self, name: str) -> Preset | None:
        return self.image.get(name)


def _load_one(path: Path) -> dict[str, Preset]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, Preset] = {}
    items = raw.get("presets") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        return out
    for entry in items:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name") or entry.get("id")
        if not name:
            continue
        out[name] = Preset(
            name=name,
            base_url=entry.get("base_url", ""),
            api_key_alias=entry.get("api_key_alias") or entry.get("key_alias", ""),
            extras={k: v for k, v in entry.items() if k not in {"name", "id", "base_url", "api_key_alias", "key_alias"}},
        )
    return out


def load_presets(
    *,
    chat_path: Path | None = None,
    image_path: Path | None = None,
) -> PresetsConfig:
    paths = get_repo_paths()
    chat_path = chat_path or (paths.repo_root / "custom_api_presets.json")
    image_path = image_path or (paths.repo_root / "custom_image_api_presets.json")
    return PresetsConfig(chat=_load_one(chat_path), image=_load_one(image_path))
