from __future__ import annotations

from unittest.mock import patch

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
        self.text = ""

    def delete(self, *_args):
        self.text = ""

    def insert(self, *_args):
        if _args:
            self.text += str(_args[-1])

    def see(self, *_args):
        return None


class _ImmediateThread:
    def __init__(self, target=None, daemon=None, args=(), kwargs=None):
        self._target = target
        self._args = args or ()
        self._kwargs = kwargs or {}

    def start(self):
        if self._target:
            self._target(*self._args, **self._kwargs)


class _DummyClient:
    def __init__(self, *args, **kwargs):
        _ = (args, kwargs)

    def stream(self, *_args, **_kwargs):
        if False:
            yield ""


class _DummyStoryGenerator(StoryInfraMixin, StoryGeneratorMixin):
    def __init__(self):
        self.target_chars = _Var(9000)
        self.category = _Var("校园")
        self.current_outline = "1. 第一章\n2. 第二章"
        self.model_only = _Var(True)
        self.story_gen_api = _Var("Custom")
        self.story_model_var = _Var("mock-model")
        self.temperature = _Var(0.7)
        self.output = _Output()
        self.status = _Var("")
        self._busy = False
        self._saved = False
        self.header_updates: list[tuple[str, str]] = []

    def _ui(self, fn, *args, **kwargs):
        return fn(*args, **kwargs)

    def _resolve_task_api(self, *_args, **_kwargs):
        return {"provider": "Custom", "key": "k", "base_url": "https://api.example.com/v1", "model": "mock-model"}

    def _parse_outline_sections(self, _outline):
        return [{"title": "第一章"}, {"title": "第二章"}]

    def _generate_in_sections(self, *_args, **_kwargs):
        return False

    def set_busy(self, busy: bool):
        self._busy = busy

    def update_header_status(self, text: str, icon: str = "🔄", color=None):
        _ = color
        self.header_updates.append((text, icon))

    def _header_status(self, text: str, icon: str = "🔄", color: str | None = None):
        self.update_header_status(text, icon, color)

    def _auto_save_to_project(self):
        self._saved = True


class _DummyStoryGeneratorSingleShot(StoryInfraMixin, StoryGeneratorMixin):
    def __init__(self, preview_action=("accept", "预览确认后的正文")):
        self.target_chars = _Var(1800)
        self.category = _Var("校园")
        self.current_outline = ""
        self.model_only = _Var(True)
        self.story_gen_api = _Var("Custom")
        self.story_model_var = _Var("mock-model")
        self.temperature = _Var(0.7)
        self.output = _Output()
        self.status = _Var("")
        self._busy = False
        self._saved = False
        self.preview_action = preview_action
        self.header_updates: list[tuple[str, str]] = []

    def _ui(self, fn, *args, **kwargs):
        return fn(*args, **kwargs)

    def _resolve_task_api(self, *_args, **_kwargs):
        return {"provider": "Custom", "key": "k", "base_url": "https://api.example.com/v1", "model": "mock-model"}

    def _parse_outline_sections(self, _outline):
        return []

    def _build_prompt(self, *_args, **_kwargs):
        return "PROMPT"

    def _stream_story_with_retry(self, *_args, **_kwargs):
        return "原始整篇故事"

    def _preview_generated_section_before_apply(self, **_kwargs):
        return self.preview_action

    def set_busy(self, busy: bool):
        self._busy = busy

    def update_header_status(self, text: str, icon: str = "🔄", color=None):
        _ = color
        self.header_updates.append((text, icon))

    def _header_status(self, text: str, icon: str = "🔄", color: str | None = None):
        self.update_header_status(text, icon, color)

    def _auto_save_to_project(self):
        self._saved = True


class _QualityLoopHarness(StoryGeneratorMixin):
    def __init__(self):
        self.reviews = [
            {"scores": {"realism": 5, "detail": 5, "coherence": 5, "continuity": 5, "escalation": 5, "hook_density": 5, "naturalness": 5}, "verdict": "rewrite", "issues": ["结构空泛"]},
            {"scores": {"realism": 8, "detail": 8, "coherence": 8, "continuity": 8, "escalation": 8, "hook_density": 8, "naturalness": 8}, "verdict": "pass", "issues": []},
        ]
        self.report = None
        self.polish_calls = 0

    def _post_stream_quality_review(self, **_kwargs):
        return self.reviews.pop(0)

    def _is_auto_polish_enabled(self):
        return True

    def _get_story_quality_thresholds(self):
        return 7.4, 6.8

    def _update_chapter_quality_report(self, _index, _title, review):
        self.report = review

    def _polish_section_text(self, *_args, **_kwargs):
        self.polish_calls += 1
        return "精修后的正文"


def test_full_story_quality_review_polishes_and_rescores_output():
    app = _QualityLoopHarness()
    result = app._review_and_polish_full_story(None, "原始正文", "悬疑故事", "悬疑", 1200)

    assert result == "精修后的正文"
    assert app.polish_calls == 1
    assert app.report["verdict"] == "pass"


def test_model_only_segmented_generation_cancelled_by_preview_sets_stopped_status():
    app = _DummyStoryGenerator()

    with patch("src.gui.mixins.story_modules.story_generator.threading.Thread", _ImmediateThread), patch(
        "src.gui.mixins.story_modules.story_generator.DeepSeekClient", _DummyClient
    ):
        app._generate_model_only("测试需求")

    assert app.status.get() == "已停止（预览取消）"
    assert app._saved is True
    assert ("生成已停止", "⏹️") in app.header_updates


def test_model_only_single_shot_uses_preview_content_before_save():
    app = _DummyStoryGeneratorSingleShot(preview_action=("accept", "最终采用版正文"))

    with patch("src.gui.mixins.story_modules.story_generator.threading.Thread", _ImmediateThread), patch(
        "src.gui.mixins.story_modules.story_generator.DeepSeekClient", _DummyClient
    ):
        app._generate_model_only("测试需求")

    assert app.status.get() == "生成完成"
    assert app._saved is True
    assert "最终采用版正文" in app.output.text


def test_model_only_single_shot_discard_preview_stops_without_save():
    app = _DummyStoryGeneratorSingleShot(preview_action=("discard", ""))

    with patch("src.gui.mixins.story_modules.story_generator.threading.Thread", _ImmediateThread), patch(
        "src.gui.mixins.story_modules.story_generator.DeepSeekClient", _DummyClient
    ):
        app._generate_model_only("测试需求")

    assert app.status.get() == "已取消（预览未采用）"
    assert app._saved is False
