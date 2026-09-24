"""Bearer-token dependency factory. See docs/technical_architecture.md.1."""

from __future__ import annotations

import asyncio

import pytest

from src.shared.domain.errors import AuthError
from src.shared.http.auth import bearer_required, service_auth_dependency

fastapi = pytest.importorskip("fastapi")


def _make_dep(token, *, allow_empty: bool = False):
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


def test_bearer_dep_accepts_any_configured_token():
    dep = _make_dep(["backend", "service"])
    asyncio.run(dep("Bearer backend"))
    asyncio.run(dep("Bearer service"))


def test_service_app_enforces_configured_backend_token(monkeypatch):
    from fastapi.testclient import TestClient
    from src.services.rag_service.main import create_app

    monkeypatch.setenv("WSF_BACKEND_TOKEN", "backend-token")
    monkeypatch.delenv("WSF_SERVICE_TOKEN", raising=False)
    monkeypatch.delenv("WSF_NO_AUTH", raising=False)
    client = TestClient(create_app())

    assert client.get("/v1/health").status_code == 401
    assert client.get(
        "/v1/health",
        headers={"Authorization": "Bearer backend-token"},
    ).status_code == 200


def test_service_app_accepts_service_token(monkeypatch):
    from fastapi.testclient import TestClient
    from src.services.rag_service.main import create_app

    monkeypatch.delenv("WSF_BACKEND_TOKEN", raising=False)
    monkeypatch.setenv("WSF_SERVICE_TOKEN", "service-token")
    monkeypatch.delenv("WSF_NO_AUTH", raising=False)
    client = TestClient(create_app())

    assert client.get(
        "/v1/health",
        headers={"Authorization": "Bearer service-token"},
    ).status_code == 200


def test_service_auth_dependency_allows_empty_configuration(monkeypatch):
    monkeypatch.delenv("WSF_BACKEND_TOKEN", raising=False)
    monkeypatch.delenv("WSF_SERVICE_TOKEN", raising=False)
    monkeypatch.delenv("WSF_NO_AUTH", raising=False)
    dep = service_auth_dependency()

    asyncio.run(dep(None))
