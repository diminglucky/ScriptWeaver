"""Tests for GUI backend ServiceSupervisor."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.gui.backend import ports as ports_module
from src.gui.backend.supervisor import ServiceSupervisor
from src.shared.config import paths as paths_module


@pytest.fixture(autouse=True)
def _isolated_repo_root(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("WSF_REPO_ROOT", str(tmp_path))
    paths_module.get_repo_paths.cache_clear()
    yield
    paths_module.get_repo_paths.cache_clear()


class _FakeProc:
    _next_pid = 1000

    def __init__(self, *args, **kwargs):
        type(self)._next_pid += 1
        self.pid = type(self)._next_pid
        self.args = args
        self.kwargs = kwargs
        self.returncode = None
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = 0

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self, timeout=None):
        if self.returncode is None:
            self.returncode = 0
        return self.returncode


def test_module_for_known_services(tmp_path: Path):
    sup = ServiceSupervisor(tmp_path)
    assert sup._module_for("rag") == "src.services.rag_service.runtime"
    assert sup._module_for("story") == "src.services.story_service.runtime"
    assert sup._module_for("image") == "src.services.image_service.runtime"


def test_health_requires_started_service(tmp_path: Path):
    sup = ServiceSupervisor(tmp_path)
    with pytest.raises(RuntimeError):
        sup.health("rag")
    with pytest.raises(KeyError):
        sup.health("bad")


def test_start_all_writes_ports_and_spawns(monkeypatch, tmp_path: Path):
    created: list[_FakeProc] = []

    def fake_popen(*args, **kwargs):
        proc = _FakeProc(*args, **kwargs)
        created.append(proc)
        return proc

    monkeypatch.setattr("src.gui.backend.supervisor.subprocess.Popen", fake_popen)
    monkeypatch.setattr("src.gui.backend.supervisor.ServiceSupervisor._wait_healthy", lambda self, name, timeout: None)
    monkeypatch.setattr("src.gui.backend.supervisor.ServiceSupervisor._free_port", staticmethod(lambda: 18080 + len(created)))

    sup = ServiceSupervisor(tmp_path)
    base_urls = sup.start_all(dev_mode=True)

    assert set(base_urls) == {"rag", "story", "image"}
    assert len(created) == 3
    # Command uses python -m uvicorn <module>:app --host 127.0.0.1 --port <port>.
    first_cmd = created[0].args[0]
    assert first_cmd[1:4] == ["-m", "uvicorn", "src.services.rag_service.runtime:app"]
    assert created[0].kwargs["cwd"] == tmp_path.resolve()
    assert created[0].kwargs["env"]["WSF_DEV"] == "1"

    pf = ports_module.read_ports()
    assert pf.rag_port == sup.ports["rag"]
    assert pf.story_port == sup.ports["story"]
    assert pf.image_port == sup.ports["image"]
    assert pf.pid_rag == created[0].pid
    assert pf.pid_story == created[1].pid
    assert pf.pid_image == created[2].pid

    # Calling start_all again is idempotent and does not spawn new processes.
    again = sup.start_all()
    assert again == base_urls
    assert len(created) == 3

    sup.shutdown(timeout=1)
    assert all(p.terminated for p in created)
    with pytest.raises(FileNotFoundError):
        ports_module.read_ports()


def test_shutdown_is_idempotent(tmp_path: Path):
    sup = ServiceSupervisor(tmp_path)
    sup.shutdown(timeout=1)
    sup.shutdown(timeout=1)


def test_restart_validates_name_and_stops_existing(tmp_path: Path):
    sup = ServiceSupervisor(tmp_path)
    proc = _FakeProc()
    sup.processes["rag"] = proc
    sup.ports["rag"] = 12345

    with pytest.raises(KeyError):
        sup.restart("bad")

    sup.restart("rag")
    assert proc.terminated is True
    assert "rag" not in sup.processes
    assert sup.ports["rag"] == 12345
