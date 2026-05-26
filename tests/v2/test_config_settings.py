"""ServiceSettings env-driven defaults. See v2 plan §12.2."""

from __future__ import annotations

from src.shared.config.settings import ServiceSettings, _HAS_PYDANTIC_SETTINGS


def test_settings_defaults_are_empty(monkeypatch):
    for key in ("WSF_BACKEND_TOKEN", "WSF_RAG_BASE_URL", "WSF_DEBUG", "WSF_NO_AUTH", "WSF_DEV"):
        monkeypatch.delenv(key, raising=False)

    if _HAS_PYDANTIC_SETTINGS:
        s = ServiceSettings()
    else:
        s = ServiceSettings.from_env()

    assert s.backend_token == ""
    assert s.rag_base_url == ""
    assert s.debug is False
    assert s.no_auth is False
    assert s.dev_mode is False


def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("WSF_BACKEND_TOKEN", "tok-1")
    monkeypatch.setenv("WSF_RAG_BASE_URL", "http://127.0.0.1:1234")
    monkeypatch.setenv("WSF_DEV", "1")
    monkeypatch.setenv("WSF_NO_AUTH", "true")
    monkeypatch.setenv("WSF_DEBUG", "yes")

    if _HAS_PYDANTIC_SETTINGS:
        s = ServiceSettings()
    else:
        s = ServiceSettings.from_env()

    assert s.backend_token == "tok-1"
    assert s.rag_base_url == "http://127.0.0.1:1234"
    assert s.dev_mode is True
    assert s.no_auth is True
    assert s.debug is True
