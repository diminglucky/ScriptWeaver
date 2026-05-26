"""ProjectStore atomic writes + legacy migration. See v2 plan §5.9 / §11."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.story_service.core.services.project_store import ProjectStore
from src.shared.domain.schemas import ChapterDraft, OutlineSection, StoryBible


def test_save_and_load_storybible_roundtrip(tmp_path: Path):
    store = ProjectStore("p1", projects_root=tmp_path)
    bible = StoryBible(requirement="r", genre="g", outline=[OutlineSection(index=0, title="t")])
    store.save_storybible(bible)
    back = store.load_storybible()
    assert back is not None
    assert back.requirement == "r"
    assert back.outline[0].title == "t"


def test_save_storybible_atomic_no_tmp_left(tmp_path: Path):
    store = ProjectStore("p1", projects_root=tmp_path)
    store.save_storybible(StoryBible(requirement="r"))
    leftovers = list(store.paths.root.glob("*.tmp"))
    assert leftovers == []


def test_save_chapter_uses_zero_padded_filename(tmp_path: Path):
    store = ProjectStore("p1", projects_root=tmp_path)
    store.save_chapter(ChapterDraft(section_index=3, title="三", content="..."))
    assert (tmp_path / "p1" / "chapters" / "003.json").is_file()


def test_list_chapters_returns_sorted(tmp_path: Path):
    store = ProjectStore("p1", projects_root=tmp_path)
    for i in (2, 0, 1):
        store.save_chapter(ChapterDraft(section_index=i, title=str(i), content="x"))
    out = store.list_chapters()
    assert [c.section_index for c in out] == [0, 1, 2]


def test_list_chapters_skips_corrupt_files(tmp_path: Path):
    store = ProjectStore("p1", projects_root=tmp_path)
    store.paths.ensure_dirs()
    store.save_chapter(ChapterDraft(section_index=0, title="ok", content="x"))
    (store.paths.chapters_dir / "999.json").write_text("not json", encoding="utf-8")
    out = store.list_chapters()
    assert len(out) == 1


def test_save_final_story(tmp_path: Path):
    store = ProjectStore("p1", projects_root=tmp_path)
    store.save_final_story("第一章\n\n第二章")
    assert store.load_final_story() == "第一章\n\n第二章"


def test_load_storybible_returns_none_when_missing(tmp_path: Path):
    store = ProjectStore("p1", projects_root=tmp_path)
    assert store.load_storybible() is None


def test_migrate_legacy_creates_minimal_storybible(tmp_path: Path):
    proj = tmp_path / "legacy"
    proj.mkdir()
    (proj / "project.json").write_text(
        json.dumps({"requirement": "原需求", "category": "悬疑", "style": "克制", "target_chars": 4000}),
        encoding="utf-8",
    )

    bible = ProjectStore.migrate_legacy_with_root("legacy", projects_root=tmp_path)
    assert bible.requirement == "原需求"
    assert bible.genre == "悬疑"
    assert bible.style == "克制"
    assert bible.target_chars == 4000


def test_migrate_legacy_does_not_overwrite_existing(tmp_path: Path):
    proj = tmp_path / "legacy"
    proj.mkdir()
    (proj / "project.json").write_text(json.dumps({"requirement": "old"}), encoding="utf-8")
    store = ProjectStore("legacy", projects_root=tmp_path)
    store.save_storybible(StoryBible(requirement="already_v2"))

    bible = ProjectStore.migrate_legacy_with_root("legacy", projects_root=tmp_path)
    assert bible.requirement == "already_v2"
