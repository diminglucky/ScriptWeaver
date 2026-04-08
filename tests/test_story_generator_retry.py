import unittest

from src.gui.mixins.story_modules.story_generator import StoryGeneratorMixin
from src.gui.mixins.story_modules.story_infra import StoryInfraMixin


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _Output:
    def __init__(self):
        self.buffer = ""

    def insert(self, _pos, text):
        self.buffer += text

    def see(self, _pos):
        return None


class _DummyStoryGenerator(StoryInfraMixin, StoryGeneratorMixin):
    def __init__(self):
        self.temperature = _Var(0.7)
        self.output = _Output()
        self.status = _Var("")

    def _ui(self, func, *args, **kwargs):
        return func(*args, **kwargs)


class _FakeClient:
    def __init__(self, rounds):
        self.rounds = rounds
        self.calls = 0

    def stream(self, _messages, temperature, max_tokens):
        _ = (temperature, max_tokens)
        idx = self.calls
        self.calls += 1
        for chunk in self.rounds[idx]:
            yield chunk


class StoryGeneratorRetryTests(unittest.TestCase):
    def test_no_retry_when_first_round_reaches_min_chars(self):
        obj = _DummyStoryGenerator()
        client = _FakeClient([["a" * 100]])

        result = obj._stream_story_with_retry(client, "prompt", target_chars=100, min_ratio=0.9, max_rounds=2)

        self.assertEqual(client.calls, 1)
        self.assertEqual(len(result), 100)
        self.assertNotIn("[Auto-continue]", obj.output.buffer)

    def test_retry_when_first_round_too_short(self):
        obj = _DummyStoryGenerator()
        client = _FakeClient([["a" * 20], ["b" * 80]])

        result = obj._stream_story_with_retry(client, "prompt", target_chars=100, min_ratio=0.9, max_rounds=2)

        self.assertEqual(client.calls, 2)
        self.assertGreaterEqual(len(result.strip()), 90)
        self.assertNotIn("[Auto-continue]", obj.output.buffer)


if __name__ == "__main__":
    unittest.main()
