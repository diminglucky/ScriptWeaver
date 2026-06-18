from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.gui.mixins.story_modules.outline_section_generate_mixin import OutlineSectionGenerateMixin
from src.gui.mixins.story_modules.story_infra import StoryInfraMixin


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _Selector:
    def __init__(self, idx: int = 0):
        self._idx = idx

    def current(self, idx=None):
        if idx is None:
            return self._idx
        self._idx = idx
        return self._idx


class _Output:
    def __init__(self):
        self.text = ""

    def insert(self, *_args):
        self.text += str(_args[-1]) if _args else ""

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


class _DummySearcher:
    def __init__(self, *_args, **_kwargs):
        pass

    def search(self, query, top_k):
        return [("ctx:" + str(query), 0.99, ("dummy.txt", 0))]


class _DummySearchConfig:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _DummyIngestor:
    def __init__(self, *_args, **_kwargs):
        pass

    def build(self):
        return None


class _DummyIngestConfig:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _DummyApp(StoryInfraMixin, OutlineSectionGenerateMixin):
    def __init__(self, index_dir: Path):
        self.parsed_sections = [{"title": "第一章"}]
        self.section_selector = _Selector(0)
        self.model_only = _Var(False)
        self.index_dir = _Var(str(index_dir))
        self.data_dir = _Var(str(index_dir))
        self.top_k = _Var(3)
        self.story_gen_api = _Var("Custom")
        self.story_model_var = _Var("mock-model")
        self.output = _Output()
        self.called = None
        self._busy = False

    def _get_prompt_content(self):
        return "测试需求"

    def _resolve_task_api(self, *_args, **_kwargs):
        return {"provider": "Custom", "key": "k", "base_url": "", "model": "mock-model"}

    def _ui(self, fn, *args, **kwargs):
        return fn(*args, **kwargs)

    def _ui_get(self, fn, *args, **kwargs):
        return fn(*args, **kwargs)

    def set_busy(self, busy: bool):
        self._busy = busy

    def _generate_single_section_with_contexts(self, query, contexts, selected_index):
        self.called = (query, contexts, selected_index)


class _AutoDummyApp(OutlineSectionGenerateMixin):
    def __init__(self):
        self.parsed_sections = [
            {"title": "第一章", "purpose": "开局", "conflict": "秘密出现", "required_beats": ["发现线索"]},
            {"title": "第二章", "purpose": "追问", "conflict": "关系错位", "required_beats": ["前文回响"]},
        ]
        self.section_selector = _Selector(0)
        self.output = _Output()
        self.generated_content = ""
        self.story_memory_ledger = [{"summary": "第一章旧记忆"}]
        self.calls = []
        self.provider_calls = []
        self.status = _Var("")

    def _ui(self, fn, *args, **kwargs):
        return fn(*args, **kwargs)

    def _resolve_generation_api_config_safe(self, *_args, **_kwargs):
        return {"provider": "Custom", "key": "k", "model": "mock-model"}

    def _create_generation_client(self, _api_config):
        return object()

    def set_busy(self, _busy: bool):
        return None

    def _get_output_text_snapshot(self):
        return self.generated_content

    def _rebuild_generated_content_from_output(self, text: str) -> str:
        return text

    def _build_story_memory_context(self, section_index: int, max_items: int = 4):
        return f"memory before {section_index}: 第一章旧记忆"

    def _do_generate_section(self, _client, query, contexts, idx, **_kwargs):
        self.calls.append((idx, list(contexts)))
        self.generated_content += f"\nchapter {idx + 1} done"
        return "replace"

    def _auto_save_to_project(self):
        return None


def test_generate_section_rag_uses_existing_index(tmp_path: Path):
    idx_dir = tmp_path / "idx"
    idx_dir.mkdir(parents=True, exist_ok=True)
    (idx_dir / "v2").mkdir()
    (idx_dir / "v2" / "manifest.json").write_text("{}", encoding="utf-8")

    app = _DummyApp(index_dir=idx_dir)

    dummy_search_module = SimpleNamespace(
        SearchConfig=_DummySearchConfig,
        KnowledgeBaseSearcher=_DummySearcher,
    )
    dummy_ingest_module = SimpleNamespace(
        IngestConfig=_DummyIngestConfig,
        KnowledgeBaseIngestor=_DummyIngestor,
    )

    with patch("src.gui.mixins.story_modules.outline_section_generate_mixin.threading.Thread", _ImmediateThread), \
         patch("tkinter.messagebox.showwarning", lambda *a, **k: None), \
         patch("tkinter.messagebox.showerror", lambda *a, **k: None), \
         patch.dict(sys.modules, {"src.kb.search": dummy_search_module, "src.kb.ingest": dummy_ingest_module}):
        app.on_generate_section()

    assert app.called is not None
    query, contexts, selected_index = app.called
    assert query == "测试需求"
    assert selected_index == 0
    assert contexts and contexts[0].startswith("ctx:")


def test_auto_generate_all_sections_uses_dynamic_context_provider():
    app = _AutoDummyApp()

    def provider(idx):
        app.provider_calls.append((idx, app._build_section_rag_query("总需求", idx)))
        return [f"ctx-{idx}"]

    with patch("src.gui.mixins.story_modules.outline_section_generate_mixin.threading.Thread", _ImmediateThread):
        app._auto_generate_all_sections("总需求", ["initial"], start_index=0, context_provider=provider)

    assert app.calls == [(0, ["ctx-0"]), (1, ["ctx-1"])]
    assert [idx for idx, _query in app.provider_calls] == [0, 1]
    assert "第一章" in app.provider_calls[0][1]
    assert "第二章" in app.provider_calls[1][1]
    assert "第一章旧记忆" in app.provider_calls[1][1]


def test_auto_generate_all_sections_keeps_static_contexts_without_provider():
    app = _AutoDummyApp()

    with patch("src.gui.mixins.story_modules.outline_section_generate_mixin.threading.Thread", _ImmediateThread):
        app._auto_generate_all_sections("总需求", ["static"], start_index=0)

    assert app.calls == [(0, ["static"]), (1, ["static"])]
    assert app.provider_calls == []
