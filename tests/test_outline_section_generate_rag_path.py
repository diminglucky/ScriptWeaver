from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.gui.mixins.story_modules.outline_section_generate_mixin import OutlineSectionGenerateMixin


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


class _DummyApp(OutlineSectionGenerateMixin):
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


def test_generate_section_rag_uses_existing_index(tmp_path: Path):
    idx_dir = tmp_path / "idx"
    idx_dir.mkdir(parents=True, exist_ok=True)
    (idx_dir / "kb.index").write_bytes(b"ok")

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
