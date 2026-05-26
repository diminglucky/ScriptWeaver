"""ProjectPaths layout + ensure_dirs. See v2 plan §3.6."""

from __future__ import annotations

from pathlib import Path

from src.shared.domain.project_paths import ProjectPaths


def test_chapter_file_zero_pads_to_three_digits(tmp_path: Path):
    p = ProjectPaths(tmp_path, "demo")
    assert p.chapter_file(0).name == "000.json"
    assert p.chapter_file(7).name == "007.json"
    assert p.chapter_file(123).name == "123.json"


def test_ensure_dirs_creates_all_v2_directories(tmp_path: Path):
    p = ProjectPaths(tmp_path, "demo")
    p.ensure_dirs()

    expected = [
        tmp_path / "demo",
        tmp_path / "demo/images",
        tmp_path / "demo/characters",
        tmp_path / "demo/chapters",
        tmp_path / "demo/shots",
        tmp_path / "demo/runs",
        tmp_path / "demo/director",
    ]
    for path in expected:
        assert path.is_dir(), f"missing directory: {path}"


def test_ensure_dirs_idempotent(tmp_path: Path):
    p = ProjectPaths(tmp_path, "demo")
    p.ensure_dirs()
    (tmp_path / "demo/chapters/keep.txt").write_text("hi")
    p.ensure_dirs()
    assert (tmp_path / "demo/chapters/keep.txt").read_text() == "hi"


def test_run_file_uses_runs_dir(tmp_path: Path):
    p = ProjectPaths(tmp_path, "demo")
    assert p.run_file("abc123") == tmp_path / "demo/runs/abc123.jsonl"


def test_storybible_path_under_root(tmp_path: Path):
    p = ProjectPaths(tmp_path, "demo")
    assert p.storybible_json == tmp_path / "demo/storybible.json"
