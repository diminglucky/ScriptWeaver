"""ports.json read / write / delete + base_url. See docs/technical_architecture.md.4 / 搂10."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.gui.backend import ports as ports_module
from src.shared.config import paths as paths_module


@pytest.fixture(autouse=True)
def _isolated_repo_root(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("WSF_REPO_ROOT", str(tmp_path))
    paths_module.get_repo_paths.cache_clear()
    yield
    paths_module.get_repo_paths.cache_clear()


def test_write_and_read_roundtrip(tmp_path: Path):
    pf = ports_module.PortsFile(
        token="tok",
        service_token="svc",
        story_port=8102,
        rag_port=8101,
        image_port=8103,
    )
    written = ports_module.write_ports(pf)
    assert written.exists()
    back = ports_module.read_ports()
    assert back.token == "tok"
    assert back.story_port == 8102
    assert back.rag_port == 8101
    assert back.image_port == 8103


def test_base_url_uses_loopback():
    pf = ports_module.PortsFile(
        token="t", service_token="s", story_port=1, rag_port=2, image_port=3
    )
    assert pf.base_url("story") == "http://127.0.0.1:1"
    assert pf.base_url("rag") == "http://127.0.0.1:2"
    assert pf.base_url("image") == "http://127.0.0.1:3"


def test_delete_ports_is_idempotent():
    # No file yet 鈫?no exception.
    ports_module.delete_ports()
    pf = ports_module.PortsFile(
        token="t", service_token="s", story_port=1, rag_port=2, image_port=3
    )
    ports_module.write_ports(pf)
    ports_module.delete_ports()
    ports_module.delete_ports()  # second call should also succeed
