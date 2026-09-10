from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.gui.mixins.story_modules.outline_generate_mixin import OutlineGenerateMixin


class _Var:
    def __init__(self, value=""):
        self.value = value

    def set(self, value):
        self.value = value


class _Output:
    def __init__(self):
        self.text = ""

    def insert(self, *_args):
        self.text += str(_args[-1])

    def see(self, *_args):
        return None


class _App(OutlineGenerateMixin):
    def __init__(self):
        self.status = _Var()
        self.output = _Output()

    def _ui(self, fn, *args, **kwargs):
        return fn(*args, **kwargs)


class _ChatClient:
    def __init__(self, failures=0, error="Upstream request failed"):
        self.failures = failures
        self.error = error
        self.calls = 0

    def chat(self, *_args, **_kwargs):
        self.calls += 1
        if self.failures:
            self.failures -= 1
            raise RuntimeError(self.error)
        return "1. 雨夜来电 | 主角发现关键线索"


def test_outline_chat_retries_upstream_failure(monkeypatch):
    app = _App()
    client = _ChatClient(failures=2)
    delays = []
    monkeypatch.setattr(
        "src.gui.mixins.story_modules.outline_generate_mixin.time.sleep",
        lambda delay: delays.append(delay),
    )

    result = app._chat_with_connection_retry(client, [], temperature=0.7, max_tokens=300)

    assert result.startswith("1.")
    assert client.calls == 3
    assert delays == [1.0, 2.0]


def test_outline_chat_honors_retry_after_header(monkeypatch):
    app = _App()
    client = _ChatClient(failures=1, error="429 Too Many Requests")
    delays = []
    error = RuntimeError("429 Too Many Requests")
    error.response = SimpleNamespace(headers={"Retry-After": "7"})

    def chat(*_args, **_kwargs):
        client.calls += 1
        if client.calls == 1:
            raise error
        return "outline"

    client.chat = chat
    monkeypatch.setattr(
        "src.gui.mixins.story_modules.outline_generate_mixin.time.sleep",
        lambda delay: delays.append(delay),
    )

    assert app._chat_with_connection_retry(client, [], temperature=0.7) == "outline"
    assert delays == [7.0]


def test_outline_stream_falls_back_to_chat_after_upstream_failure(monkeypatch):
    app = _App()
    client = _ChatClient()

    def stream(*_args, **_kwargs):
        raise RuntimeError("Upstream request failed")
        yield "never"

    client.stream = stream
    monkeypatch.setattr(
        "src.gui.mixins.story_modules.outline_generate_mixin.time.sleep",
        lambda _delay: None,
    )

    result = app._stream_outline_generation(
        client, [], temperature=0.7, max_tokens=300
    )

    assert result.startswith("1.")
    assert client.calls == 1


def test_outline_chat_does_not_retry_invalid_request(monkeypatch):
    app = _App()
    client = _ChatClient(failures=1, error="invalid request parameters")
    sleeps = []
    monkeypatch.setattr(
        "src.gui.mixins.story_modules.outline_generate_mixin.time.sleep",
        lambda delay: sleeps.append(delay),
    )

    with pytest.raises(RuntimeError, match="invalid request"):
        app._chat_with_connection_retry(client, [], temperature=0.7)

    assert client.calls == 1
    assert sleeps == []
