import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.utils.text import try_chat_api


class _DummyCompletions:
    def __init__(self, resp):
        self._resp = resp

    def create(self, **_kwargs):
        return self._resp


def _make_client(resp):
    return SimpleNamespace(chat=SimpleNamespace(completions=_DummyCompletions(resp)))


class TryChatAPITests(unittest.TestCase):
    @patch("src.clients.custom_openai_client.create_compatible_client")
    def test_accepts_string_response(self, mock_create_client):
        mock_create_client.return_value = _make_client("pong")
        ok, msg = try_chat_api("k", "https://example.com/v1", "test-model")
        self.assertTrue(ok)
        self.assertIn("pong", msg)

    @patch("src.clients.custom_openai_client.create_compatible_client")
    def test_accepts_dict_choices_response(self, mock_create_client):
        resp = {"choices": [{"message": {"content": "hello"}}]}
        mock_create_client.return_value = _make_client(resp)
        ok, msg = try_chat_api("k", "https://example.com/v1", "test-model")
        self.assertTrue(ok)
        self.assertIn("hello", msg)

    @patch("src.clients.custom_openai_client.create_compatible_client")
    def test_accepts_object_choices_response(self, mock_create_client):
        message = SimpleNamespace(content=[{"text": "ok"}])
        resp = SimpleNamespace(choices=[SimpleNamespace(message=message)])
        mock_create_client.return_value = _make_client(resp)
        ok, msg = try_chat_api("k", "https://example.com/v1", "test-model")
        self.assertTrue(ok)
        self.assertIn("ok", msg)

    @patch("src.clients.custom_openai_client.create_compatible_client")
    def test_normalizes_chat_completions_base_url(self, mock_create_client):
        mock_create_client.return_value = _make_client("pong")
        ok, _ = try_chat_api("k", "https://api.gpt.ge/v1/chat/completions", "test-model")
        self.assertTrue(ok)
        kwargs = mock_create_client.call_args.kwargs
        self.assertEqual(kwargs.get("base_url"), "https://api.gpt.ge/v1")


if __name__ == "__main__":
    unittest.main()
