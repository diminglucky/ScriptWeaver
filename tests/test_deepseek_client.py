from types import SimpleNamespace

import pytest

from src.clients.deepseek_client import DeepSeekClient


class _Completions:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def create(self, **_kwargs):
        if self.error is not None:
            raise self.error
        return self.response


def _client(response=None, error=None):
    client = DeepSeekClient.__new__(DeepSeekClient)
    client.client = SimpleNamespace(
        chat=SimpleNamespace(completions=_Completions(response, error))
    )
    client.model = "test-model"
    return client


def test_chat_accepts_gateway_returning_plain_text():
    assert _client(response="generated text").chat([]) == "generated text"


def test_chat_accepts_openai_response_object():
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="generated text"))]
    )
    assert _client(response=response).chat([]) == "generated text"


def test_chat_preserves_request_exception():
    error = RuntimeError("upstream failed")
    with pytest.raises(RuntimeError) as raised:
        _client(error=error).chat([])
    assert raised.value is error
