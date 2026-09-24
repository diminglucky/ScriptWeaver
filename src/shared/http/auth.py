"""Bearer-token auth middleware factory. See docs/technical_architecture.md.1."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Callable

from src.shared.domain.errors import AuthError


TokenProvider = Callable[[], str | Iterable[str]]


def bearer_required(token_provider: TokenProvider, *, allow_empty: bool = False):
    """Return a FastAPI dependency that validates `Authorization: Bearer ...`.

    The dependency function is constructed lazily so this module can be
    imported even before FastAPI is installed.
    """

    def _make_dependency():
        from fastapi import Header

        async def dependency(authorization: str | None = Header(default=None)) -> None:
            raw = token_provider()
            if isinstance(raw, str):
                expected = {raw.strip()} if raw.strip() else set()
            else:
                expected = {str(item).strip() for item in raw if str(item).strip()}
            if not expected and allow_empty:
                return
            if not authorization or not authorization.startswith("Bearer "):
                raise AuthError("missing bearer token")
            token = authorization[len("Bearer ") :].strip()
            if token not in expected:
                raise AuthError("invalid bearer token")

        return dependency

    return _make_dependency


def service_auth_dependency():
    """Return the shared auth dependency for the three local services.

    Authentication is enforced whenever a backend or service token is
    configured. With no configured token it stays open for local development
    and tests; `WSF_NO_AUTH=1` explicitly disables token validation.
    """
    from src.shared.config.settings import ServiceSettings

    settings = ServiceSettings()

    def _tokens() -> list[str]:
        if settings.no_auth:
            return []
        return [settings.backend_token, settings.service_token]

    return bearer_required(_tokens, allow_empty=True)()
