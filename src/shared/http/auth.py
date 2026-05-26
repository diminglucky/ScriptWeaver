"""Bearer-token auth middleware factory. See v2 plan §8.1."""

from __future__ import annotations

from typing import Callable

from src.shared.domain.errors import AuthError


def bearer_required(token_provider: Callable[[], str], *, allow_empty: bool = False):
    """Return a FastAPI dependency that validates `Authorization: Bearer ...`.

    The dependency function is constructed lazily so this module can be
    imported even before FastAPI is installed.
    """

    def _make_dependency():
        from fastapi import Header

        async def dependency(authorization: str | None = Header(default=None)) -> None:
            expected = token_provider()
            if not expected and allow_empty:
                return
            if not authorization or not authorization.startswith("Bearer "):
                raise AuthError("missing bearer token")
            token = authorization[len("Bearer ") :].strip()
            if token != expected:
                raise AuthError("invalid bearer token")

        return dependency

    return _make_dependency
