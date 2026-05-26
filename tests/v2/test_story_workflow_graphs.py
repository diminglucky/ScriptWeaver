from __future__ import annotations

import json
import asyncio
from pathlib import Path

import pytest

from src.services.story_service.core.services.project_store import ProjectStore
from src.services.story_service.core.workflows.character_graph import build_character_graph
from src.services.story_service.core.workflows.novel_graph import build_novel_graph
from src.services.story_service.core.workflows.review_graph import build_review_graph
from src.shared.config import paths as paths_module
from src.shared.domain.schemas import RetrievedContext, SourceRef


@pytest.fixture(autouse=True)
def _repo_root(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("WSF_REPO_ROOT", str(tmp_path))
    paths_module.get_repo_paths.cache_clear()
    yield
    paths_module.get_repo_paths.cache_clear()


class _FakeRegistry:
    def __init__(self):
        self.tasks: list[str] = []

    def chat_model(self, task: str):
        self.tasks.append(task)
        return _FakeLLM(task)


class _FakeLLM:
    def __init__(self, task: str):
        self.task = task

    async def ainvoke(self, prompt):
        if self.task == "story_bible":
            return json.dumps({
                "requirement": prompt["state"]["requirement"],
                "genre": prompt["state"]["genre"],
                "style": prompt["state"]["style"],
                "theme": "代价",
                "premise": "主角在雨夜发现秘密",
                "core_conflict": "真相与安全冲突",
                "target_chars": prompt["state"]["target_chars"],
                "outline": [
                    {"index": 0, "title": "雨夜", "purpose": "发现秘密", "expected_chars": 500},
                    {"index": 1, "title": "抉择", "purpose": "承担代价", "expected_chars": 500},
                ],
            }, ensure_ascii=False)
        if self.task == "character_design":
            return json.dumps({
                "characters": [
                    {"name": "林夏", "role": "主角", "motivation": "查明真相", "visual_anchor": ["黑伞"]}
                ]
            }, ensure_ascii=False)
        if self.task == "chapter":
            section = prompt["section"]
            return json.dumps({
                "section_index": section["index"],
                "title": section["title"],
                "content": f"{section['title']} 正文。{section['purpose']}",
                "summary": section["purpose"],
                "char_count": 20,
            }, ensure_ascii=False)
        if self.task == "review":
            return json.dumps({"score": 0.9, "notes": ["ok"], "suggested_fixes": []}, ensure_ascii=False)
        return "{}"


class _FakeRag:
    def __init__(self):
        self.search_calls: list[tuple[str, str, str | None]] = []
        self.memory_entries: list[tuple[str, list[dict]]] = []

    async def search(self, kb_type: str, query: str, *, project_id=None, top_k=6):
        self.search_calls.append((kb_type, query, project_id))
        return [RetrievedContext(
            text=f"ctx {kb_type}",
            source=SourceRef(source_id=f"s-{kb_type}", path="/tmp/x", chunk_id="c", score=0.8, kb_type=kb_type, project_id=project_id),
        )]

    async def write_memory(self, project_id: str, entries: list[dict]):
        self.memory_entries.append((project_id, entries))
        return {"entries": entries}


def test_novel_graph_fake_llm_generates_and_persists_two_chapters(tmp_path: Path):
    registry = _FakeRegistry()
    rag = _FakeRag()
    graph = build_novel_graph(registry=registry, prompts=None, rag_client=rag, project_id="p1")

    state = asyncio.run(graph.ainvoke({
        "request": {
            "requirement": "写一个雨夜秘密故事",
            "genre": "悬疑",
            "style": "克制",
            "target_chars": 1000,
            "chapter_count": 2,
        }
    }))

    assert graph.nodes[:3] == ["parse_requirement", "retrieve_reference_context", "build_story_bible"]
    assert graph.interrupt_before == ["human_review_outline", "repair_chapter"]
    assert state["story_bible"].characters[0].name == "林夏"
    assert [ch.title for ch in state["chapters"]] == ["雨夜", "抉择"]
    assert "雨夜 正文" in state["final_text"]
    assert any(call[0] == "reference" for call in rag.search_calls)
    assert len(rag.memory_entries) == 2

    store = ProjectStore("p1")
    assert store.load_storybible().theme == "代价"
    assert [c.section_index for c in store.list_chapters()] == [0, 1]
    assert "抉择 正文" in store.load_final_story()


def test_novel_graph_fallback_without_llm(tmp_path: Path):
    graph = build_novel_graph(registry=None, prompts=None, rag_client=None, project_id="p2")
    state = asyncio.run(graph.ainvoke({"requirement": "fallback", "chapter_count": 2}))
    assert len(state["chapters"]) == 2
    assert state["story_bible"].characters[0].name == "主角"
    assert ProjectStore("p2").load_final_story()


def test_character_graph_fake_llm_uses_reference_and_memory_contexts():
    registry = _FakeRegistry()
    rag = _FakeRag()
    graph = build_character_graph(registry=registry, prompts=None, rag_client=rag, project_id="p3")
    state = asyncio.run(graph.ainvoke({"request": {"story_context": "雨夜秘密"}}))
    assert state["characters"][0].name == "林夏"
    assert [c[0] for c in rag.search_calls] == ["reference", "project_memory"]
    assert state["retrieved_contexts"][1].source.project_id == "p3"


def test_review_graph_fake_llm():
    graph = build_review_graph(registry=_FakeRegistry(), prompts=None)
    state = asyncio.run(graph.ainvoke({"draft": "正文"}))
    assert state["review"].score == 0.9
    assert state["review"].notes == ["ok"]
