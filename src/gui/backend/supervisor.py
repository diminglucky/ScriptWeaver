"""ServiceSupervisor: spawn + health-check + shutdown the 3 backend services.

See v2 plan §9.
"""

from __future__ import annotations

import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

from .ports import PortsFile, delete_ports, write_ports


_SERVICES: tuple[str, ...] = ("rag", "story", "image")
_MODULE_BY_NAME = {
    "rag": "src.services.rag_service.runtime",
    "story": "src.services.story_service.runtime",
    "image": "src.services.image_service.runtime",
}


class ServiceSupervisor:
    """Owns subprocess.Popen handles for the 3 services."""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()
        self.processes: dict[str, subprocess.Popen[Any]] = {}
        self.token: str = secrets.token_urlsafe(32)
        self.service_token: str = secrets.token_urlsafe(32)
        self.ports: dict[str, int] = {}

    # ── lifecycle ─────────────────────────────────────────────────────────
    def start_all(self, *, dev_mode: bool = False) -> dict[str, str]:
        """Spawn services in order (rag → story → image). Returns base_url map."""
        if self.processes:
            return {name: f"http://127.0.0.1:{port}" for name, port in self.ports.items()}

        self.ports = {name: self._free_port() for name in _SERVICES}
        base_urls = {name: f"http://127.0.0.1:{self.ports[name]}" for name in _SERVICES}

        env = os.environ.copy()
        env.update({
            "WSF_BACKEND_TOKEN": self.token,
            "WSF_SERVICE_TOKEN": self.service_token,
            "WSF_RAG_BASE_URL": base_urls["rag"],
            "WSF_STORY_BASE_URL": base_urls["story"],
            "WSF_IMAGE_BASE_URL": base_urls["image"],
            "WSF_REPO_ROOT": str(self.project_root),
            "WSF_DEV": "1" if dev_mode else "0",
            "TRANSFORMERS_NO_TF": "1",
        })

        logs_dir = self.project_root / ".runtime" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        try:
            for name in _SERVICES:
                log = (logs_dir / f"{name}.log").open("ab")
                cmd = [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    f"{self._module_for(name)}:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(self.ports[name]),
                ]
                proc = subprocess.Popen(
                    cmd,
                    cwd=self.project_root,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    close_fds=True,
                )
                self.processes[name] = proc

            write_ports(PortsFile(
                token=self.token,
                service_token=self.service_token,
                story_port=self.ports["story"],
                rag_port=self.ports["rag"],
                image_port=self.ports["image"],
                pid_story=self.processes["story"].pid,
                pid_rag=self.processes["rag"].pid,
                pid_image=self.processes["image"].pid,
            ))

            for name in _SERVICES:
                self._wait_healthy(name, timeout=15.0)
            return base_urls
        except Exception:
            self.shutdown(timeout=2)
            raise

    def shutdown(self, *, timeout: int = 10) -> None:
        """Reverse-order SIGTERM, SIGKILL on timeout."""
        for name in reversed(_SERVICES):
            proc = self.processes.get(name)
            if proc is not None and proc.poll() is None:
                proc.terminate()
        deadline = time.time() + timeout
        for name in reversed(_SERVICES):
            proc = self.processes.get(name)
            if proc is None:
                continue
            remaining = max(0.0, deadline - time.time())
            try:
                proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)
        self.processes.clear()
        self.ports.clear()
        delete_ports()

    def restart(self, name: str) -> None:
        if name not in _SERVICES:
            raise KeyError(name)
        proc = self.processes.get(name)
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)
        self.processes.pop(name, None)
        port = self.ports.get(name) or self._free_port()
        self.ports[name] = port

    # ── helpers ───────────────────────────────────────────────────────────
    def health(self, name: str, *, timeout: float = 2.0) -> dict:
        if name not in _SERVICES:
            raise KeyError(name)
        port = self.ports.get(name)
        if not port:
            raise RuntimeError(f"service not started: {name}")
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/health", timeout=timeout) as resp:
            import json

            return json.loads(resp.read().decode("utf-8"))

    def _module_for(self, name: str) -> str:
        return _MODULE_BY_NAME[name]

    def _wait_healthy(self, name: str, *, timeout: float) -> None:
        end = time.time() + timeout
        last_error: Exception | None = None
        while time.time() < end:
            proc = self.processes.get(name)
            if proc is not None and proc.poll() is not None:
                raise RuntimeError(f"{name} exited during startup with code {proc.returncode}")
            try:
                self.health(name, timeout=1.0)
                return
            except Exception as exc:
                last_error = exc
                time.sleep(0.2)
        raise TimeoutError(f"{name} did not become healthy: {last_error}")

    @staticmethod
    def _free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])
