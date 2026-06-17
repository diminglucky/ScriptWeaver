"""KeyVault bridge to existing `config/.keyfile` encryption.

Wraps the legacy `SecureKeyStorage` so services don't depend on the GUI
mixin path. See docs/technical_architecture.md.3 / 搂12.2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .paths import get_repo_paths


@dataclass
class KeyVault:
    """In-memory secrets store; never logged, never serialized."""

    by_alias: dict[str, str] = field(default_factory=dict)

    def get(self, alias: str, default: str = "") -> str:
        return self.by_alias.get(alias, default)

    def set(self, alias: str, value: str) -> None:
        self.by_alias[alias] = value

    def has(self, alias: str) -> bool:
        return bool(self.by_alias.get(alias))


def load_keyfile(*, key_file: Path | None = None) -> "Any":
    """Return the legacy `SecureKeyStorage` instance for encrypt/decrypt use.

    Services should pass the returned storage to higher-level loaders that
    populate a `KeyVault`. Kept as a thin bridge so we don't duplicate the
    encryption logic during v2 build-out.
    """
    from src.gui.mixins.enhancements_modules.secure_config import SecureKeyStorage

    target = key_file or (get_repo_paths().config_root / ".keyfile")
    return SecureKeyStorage(str(target))
