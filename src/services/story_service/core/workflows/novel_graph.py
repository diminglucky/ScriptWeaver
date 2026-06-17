"""Novel-generation workflow graph."""

from __future__ import annotations

import inspect
from typing import Any

from pydantic import BaseModel, Field

from src.services.story_service.core.ai.structured import invoke_structured
from src.services.story_service.core.services.project_store import ProjectStore
from src.services.story_service.core.workflows.simple_graph import SimpleCompiledGraph
from src.shared.domain.schemas import (
    ChapterDraft,
    CharacterProfile,
    OutlineSection,
    RetrievedContext,
    StoryBible,
)


class OutlinePlan(BaseModel):
    outline: list[OutlineSection] = Field(default_factory=list)


class CharacterPlan(BaseModel):
    characters: list[CharacterProfile] = Field(default_factory=list)


def _chat_model(registry: Any, task: str) -> Any | None:
    if registry is None:
        return None
    if hasattr(registry, "chat_model"):
        return registry.chat_model(task)
    if hasattr(registry, "ainvoke"):
        return registry
    return None


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _search(rag_client: Any, kb_type: str, query: str, *, project_id: str | None = None) -> list[RetrievedContext]:
    if rag_client is None or not hasattr(rag_client, "search"):
        return []
    res = await _maybe_await(rag_client.search(kb_type, query, project_id=project_id, top_k=6))
    if isinstance(res, dict):
        res = res.get("results", [])
    return [x if isinstance(x, RetrievedContext) else RetrievedContext.model_validate(x) for x in (res or [])]


async def _write_memory(rag_client: Any, project_id: str, entries: list[dict]) -> None:
    if not entries or rag_client is None or not hasattr(rag_client, "write_memory"):
        return
    await _maybe_await(rag_client.write_memory(project_id, entries))


def _context_lines(contexts: list[RetrievedContext], *, limit: int = 8) -> list[str]:
    lines: list[str] = []
    for idx, ctx in enumerate(contexts[:limit], 1):
        src = ctx.source
        label = src.kb_type
        if src.project_id:
            label = f"{label}:{src.project_id}"
        text = " ".join(str(ctx.text or "").split())
        if len(text) > 500:
            text = text[:500].rstrip() + "..."
        lines.append(f"[{idx}] {label} {src.source_id} score={src.score:.3f}: {text}")
    return lines


def _default_outline(chapter_count: int) -> list[OutlineSection]:
    return [
        OutlineSection(index=i, title=f"第{i + 1}章", purpose="推进主线", expected_chars=1200)
        for i in range(chapter_count)
    ]


def _fallback_bible(state: dict[str, Any]) -> StoryBible:
    return StoryBible(
        requirement=state.get("requirement", ""),
        genre=state.get("genre", ""),
        style=state.get("style", ""),
        target_chars=int(state.get("target_chars") or 0),
        premise=state.get("requirement", ""),
        outline=_default_outline(int(state.get("chapter_count") or 1)),
    )


def build_novel_graph(*, registry, prompts, rag_client, project_id: str) -> Any:
    """Construct and compile the workflow app for a single novel run."""
    store = ProjectStore(project_id)

    async def parse_requirement(state: dict[str, Any]) -> dict[str, Any]:
        request = state.get("request") or {}
        return {
            "project_id": project_id,
            "requirement": state.get("requirement") or request.get("requirement") or "",
            "genre": state.get("genre") or request.get("genre") or "",
            "style": state.get("style") or request.get("style") or "",
            "target_chars": int(state.get("target_chars") or request.get("target_chars") or 0),
            "use_rag": bool(state.get("use_rag", request.get("use_rag", True))),
            "chapter_count": int(state.get("chapter_count") or request.get("chapter_count") or 1),
        }

    async def retrieve_reference_context(state: dict[str, Any]) -> dict[str, Any]:
        if not state.get("use_rag", True):
            return {"retrieved_contexts": []}
        contexts = await _search(rag_client, "reference", state.get("requirement", ""), project_id=None)
        return {"retrieved_contexts": contexts}

    async def build_story_bible(state: dict[str, Any]) -> dict[str, Any]:
        llm = _chat_model(registry, "story_bible")
        if llm is None:
            bible = _fallback_bible(state)
        else:
            prompt = prompts.build_story_bible_prompt(state) if prompts is not None else {"task": "story_bible", "state": state}
            bible, _ = await invoke_structured(llm, prompt, StoryBible)
            if not bible.outline:
                bible.outline = _default_outline(int(state.get("chapter_count") or 1))
        return {"story_bible": bible}

    async def save_storybible(state: dict[str, Any]) -> dict[str, Any]:
        store.save_storybible(state["story_bible"])
        return {}

    async def design_characters(state: dict[str, Any]) -> dict[str, Any]:
        bible: StoryBible = state["story_bible"]
        if bible.characters:
            return {"story_bible": bible}
        llm = _chat_model(registry, "character_design")
        if llm is not None:
            prompt = prompts.build_character_prompt(state) if prompts is not None else {"task": "character_design", "state": state}
            plan, _ = await invoke_structured(llm, prompt, CharacterPlan)
            bible.characters = plan.characters
        if not bible.characters:
            bible.characters = [CharacterProfile(name="主角", role="protagonist", motivation=bible.premise)]
        return {"story_bible": bible}

    async def generate_outline(state: dict[str, Any]) -> dict[str, Any]:
        bible: StoryBible = state["story_bible"]
        if bible.outline:
            return {"story_bible": bible}
        llm = _chat_model(registry, "outline")
        if llm is not None:
            prompt = prompts.build_outline_prompt(state) if prompts is not None else {"task": "outline", "state": state}
            plan, _ = await invoke_structured(llm, prompt, OutlinePlan)
            bible.outline = plan.outline
        if not bible.outline:
            bible.outline = _default_outline(int(state.get("chapter_count") or 1))
        return {"story_bible": bible}

    async def review_outline(state: dict[str, Any]) -> dict[str, Any]:
        llm = _chat_model(registry, "review")
        if llm is None:
            return {"outline_review": {"score": 1.0, "notes": []}}
        prompt = prompts.build_review_prompt(state) if prompts is not None else {"task": "review_outline", "state": state}
        raw = await _maybe_await(llm.ainvoke(prompt))
        return {"outline_review": raw}

    async def chapter_loop(state: dict[str, Any]) -> dict[str, Any]:
        bible: StoryBible = state["story_bible"]
        chapters: list[ChapterDraft] = []
        llm = _chat_model(registry, "chapter")
        previous_summaries: list[str] = []
        for section in bible.outline:
            query = " ".join([
                bible.premise,
                section.title,
                section.purpose,
                section.conflict,
                " ".join(section.required_beats),
                " ".join(previous_summaries[-3:]),
            ]).strip()
            if state.get("use_rag", True):
                reference_contexts = await _search(rag_client, "reference", query, project_id=None)
                memory_contexts = await _search(rag_client, "project_memory", query, project_id=project_id)
            else:
                reference_contexts = []
                memory_contexts = []
            chapter_contexts = reference_contexts + memory_contexts
            chapter_state = {
                **state,
                "current_section": section.model_dump(),
                "previous_chapter_summaries": previous_summaries[-5:],
                "chapter_contexts": chapter_contexts,
                "chapter_context_text": "\n".join(_context_lines(chapter_contexts)),
            }
            if llm is None:
                context_text = chapter_state.get("chapter_context_text", "")
                content = f"{section.title}\n\n{bible.premise or bible.requirement}\n\n{section.purpose}"
                if context_text:
                    content += f"\n\n{context_text}"
                draft = ChapterDraft(
                    section_index=section.index,
                    title=section.title,
                    content=content,
                    summary=section.purpose,
                    char_count=len(content),
                    citations=[c.source for c in chapter_contexts],
                )
            else:
                prompt = (
                    prompts.build_chapter_prompt(chapter_state, section.model_dump())
                    if prompts is not None
                    else {"task": "chapter", "section": section.model_dump(), "state": chapter_state}
                )
                draft, _ = await invoke_structured(llm, prompt, ChapterDraft)
                if not draft.citations:
                    draft.citations = [c.source for c in chapter_contexts]
            chapters.append(draft)
            store.save_chapter(draft)
            memory_text = "\n".join(
                part for part in [
                    f"chapter={draft.section_index}",
                    f"title={draft.title}",
                    f"summary={draft.summary or draft.content[:300]}",
                    "continuity=" + "; ".join(draft.continuity_updates) if draft.continuity_updates else "",
                ]
                if part
            )
            await _write_memory(rag_client, project_id, [{
                "source_id": f"chapter-{draft.section_index}",
                "text": memory_text,
                "tags": ["chapter_summary", "continuity"],
            }])
            previous_summaries.append(draft.summary or draft.content[:300])
        return {"chapters": chapters}

    async def assemble_final_story(state: dict[str, Any]) -> dict[str, Any]:
        chapters: list[ChapterDraft] = state.get("chapters") or []
        final_text = "\n\n".join(ch.content for ch in chapters)
        return {"final_text": final_text}

    async def save_project(state: dict[str, Any]) -> dict[str, Any]:
        store.save_storybible(state["story_bible"])
        store.save_final_story(state.get("final_text", ""))
        return {}

    return SimpleCompiledGraph(
        steps=[
            ("parse_requirement", parse_requirement),
            ("retrieve_reference_context", retrieve_reference_context),
            ("build_story_bible", build_story_bible),
            ("save_storybible", save_storybible),
            ("design_characters", design_characters),
            ("generate_outline", generate_outline),
            ("review_outline", review_outline),
            ("chapter_loop", chapter_loop),
            ("assemble_final_story", assemble_final_story),
            ("save_project", save_project),
        ],
        interrupt_before=["human_review_outline", "repair_chapter"],
    )
