"""Read/write `.runtime/ports.json`. See docs/technical_architecture.md.4."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from src.shared.config.paths import get_repo_paths


@dataclass
class PortsFile:
    token: str
    service_token: str
    story_port: int
    rag_port: int
    image_port: int
    pid_story: int = 0
    pid_rag: int = 0
    pid_image: int = 0

    def base_url(self, name: str) -> str:
        port = getattr(self, f"{name}_port")
        return f"http://127.0.0.1:{port}"


def _ports_path() -> Path:
    return get_repo_paths().runtime_root / "ports.json"


def write_ports(data: PortsFile) -> Path:
    path = _ports_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(asdict(data), indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return path


def read_ports() -> PortsFile:
    raw = json.loads(_ports_path().read_text(encoding="utf-8"))
    return PortsFile(**raw)


def delete_ports() -> None:
    try:
        _ports_path().unlink()
    except FileNotFoundError:
        pass
