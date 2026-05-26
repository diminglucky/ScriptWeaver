"""Per-service runtime settings. See v2 plan §12.2.

Uses `pydantic-settings` when available; falls back to a plain dataclass-like
reader so the skeleton imports cleanly even before deps are installed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    _HAS_PYDANTIC_SETTINGS = True
except Exception:  # pragma: no cover - optional dependency at scaffold time
    BaseSettings = object  # type: ignore[misc,assignment]
    SettingsConfigDict = dict  # type: ignore[misc,assignment]
    _HAS_PYDANTIC_SETTINGS = False


if _HAS_PYDANTIC_SETTINGS:
    from pydantic import Field

    class ServiceSettings(BaseSettings):  # type: ignore[misc]
        """Env-driven settings; all three services share this class.

        Boolean toggles use explicit env names to match the supervisor
        convention (`WSF_DEV`, `WSF_NO_AUTH`, `WSF_DEBUG`).
        """

        backend_token: str = ""
        service_token: str = ""
        rag_base_url: str = ""
        story_base_url: str = ""
        image_base_url: str = ""
        debug: bool = Field(default=False, validation_alias="WSF_DEBUG")
        no_auth: bool = Field(default=False, validation_alias="WSF_NO_AUTH")
        dev_mode: bool = Field(default=False, validation_alias="WSF_DEV")

        model_config = SettingsConfigDict(
            env_prefix="WSF_",
            env_file=".env",
            extra="ignore",
        )

else:

    @dataclass
    class ServiceSettings:  # type: ignore[no-redef]
        """Fallback settings used when pydantic-settings is unavailable."""

        backend_token: str = ""
        service_token: str = ""
        rag_base_url: str = ""
        story_base_url: str = ""
        image_base_url: str = ""
        debug: bool = False
        no_auth: bool = False
        dev_mode: bool = False

        @classmethod
        def from_env(cls) -> "ServiceSettings":
            def _b(name: str) -> bool:
                v = os.environ.get(name, "").strip().lower()
                return v in {"1", "true", "yes", "on"}

            return cls(
                backend_token=os.environ.get("WSF_BACKEND_TOKEN", ""),
                service_token=os.environ.get("WSF_SERVICE_TOKEN", ""),
                rag_base_url=os.environ.get("WSF_RAG_BASE_URL", ""),
                story_base_url=os.environ.get("WSF_STORY_BASE_URL", ""),
                image_base_url=os.environ.get("WSF_IMAGE_BASE_URL", ""),
                debug=_b("WSF_DEBUG"),
                no_auth=_b("WSF_NO_AUTH"),
                dev_mode=_b("WSF_DEV"),
            )
