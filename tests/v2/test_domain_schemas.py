"""Pydantic v2 schema contracts. See v2 plan §3.2."""

from __future__ import annotations

from src.shared.domain.schemas import (
    ChapterDraft,
    CharacterProfile,
    ContextBudget,
    OutlineSection,
    RetrievedContext,
    ShotPrompt,
    SourceRef,
    StoryBible,
)


def test_storybible_json_roundtrip_preserves_chinese_role():
    bible = StoryBible(
        requirement="一个关于",
        genre="奇幻",
        style="冷峻",
        characters=[CharacterProfile(name="主角", role="主角")],
        outline=[OutlineSection(index=0, title="起", required_beats=["相遇"])],
    )
    raw = bible.model_dump_json()
    back = StoryBible.model_validate_json(raw)
    assert back.requirement == bible.requirement
    assert back.characters[0].role == "主角"
    assert back.outline[0].required_beats == ["相遇"]


def test_character_profile_role_accepts_any_string():
    cp = CharacterProfile(name="X", role="守护神")
    assert cp.role == "守护神"


def test_character_profile_default_lists_are_independent():
    a = CharacterProfile(name="A")
    b = CharacterProfile(name="B")
    a.visual_anchor.append("red")
    assert b.visual_anchor == []


def test_chapter_draft_minimum_fields():
    cd = ChapterDraft(section_index=2, title="二", content="内容")
    raw = cd.model_dump_json()
    back = ChapterDraft.model_validate_json(raw)
    assert back.section_index == 2 and back.title == "二"
    assert back.token_usage == {}


def test_shot_prompt_default_aspect_ratio():
    s = ShotPrompt(shot_id="s1", scene="森林清晨", prompt="forest morning")
    assert s.aspect_ratio == "16:9"
    assert s.style_tags == []


def test_source_ref_kb_type_validates():
    ref = SourceRef(source_id="s", path="p", chunk_id="c")
    assert ref.kb_type == "reference"
    ref2 = SourceRef(source_id="s", path="p", chunk_id="c", kb_type="project_memory", project_id="proj-1")
    assert ref2.project_id == "proj-1"


def test_retrieved_context_truncated_default_false():
    ctx = RetrievedContext(text="t", source=SourceRef(source_id="s", path="p", chunk_id="c"))
    assert ctx.truncated is False


def test_context_budget_defaults():
    b = ContextBudget()
    assert b.max_total_tokens == 1500
    assert b.max_per_chunk_tokens == 400
