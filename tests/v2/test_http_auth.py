"""Bearer-token dependency factory. See docs/technical_architecture.md.1."""

from __future__ import annotations

import asyncio

import pytest

from src.shared.domain.errors import AuthError
from src.shared.http.auth import bearer_required

fastapi = pytest.importorskip("fastapi")


def _make_dep(token: str, *, allow_empty: bool = False):
    return bearer_required(lambda: token, allow_empty=allow_empty)()


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_bearer_dep_accepts_correct_token():
    dep = _make_dep("secret")
    asyncio.run(dep("Bearer secret"))


def test_bearer_dep_rejects_missing_header():
    dep = _make_dep("secret")
    with pytest.raises(AuthError):
        asyncio.run(dep(None))


def test_bearer_dep_rejects_wrong_token():
    dep = _make_dep("secret")
    with pytest.raises(AuthError):
        asyncio.run(dep("Bearer nope"))


def test_bearer_dep_rejects_non_bearer_scheme():
    dep = _make_dep("secret")
    with pytest.raises(AuthError):
        asyncio.run(dep("Basic abc"))


def test_bearer_dep_allow_empty_skips_when_no_expected_token():
    dep = _make_dep("", allow_empty=True)
    asyncio.run(dep(None))
    asyncio.run(dep("Bearer whatever"))
