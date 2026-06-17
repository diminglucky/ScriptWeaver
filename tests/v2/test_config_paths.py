"""RepoPaths resolution + WSF_REPO_ROOT override. See docs/technical_architecture.md."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.shared.config import paths as paths_module


@pytest.fixture(autouse=True)
def _reset_cache():
    paths_module.get_repo_paths.cache_clear()
    yield
    paths_module.get_repo_paths.cache_clear()


def test_default_repo_root_points_at_real_repo():
    p = paths_module.get_repo_paths()
    assert (p.repo_root / "src").is_dir()
    assert p.projects_root == p.repo_root / "projects"
    assert p.index_root == p.repo_root / "index"
    assert p.config_root == p.repo_root / "config"
    assert p.runtime_root == p.repo_root / ".runtime"
    assert p.logs_root == p.repo_root / "logs"


def test_wsf_repo_root_env_override(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("WSF_REPO_ROOT", str(tmp_path))
    paths_module.get_repo_paths.cache_clear()
    p = paths_module.get_repo_paths()
    assert p.repo_root == tmp_path.resolve()
    assert p.projects_root == tmp_path.resolve() / "projects"
    assert p.runtime_root == tmp_path.resolve() / ".runtime"
