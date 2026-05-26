"""BackendClient: single GUI-facing facade over the 3 services.

See v2 plan §10.1.
"""

from __future__ import annotations

from .image_client import ImageClient
from .ports import PortsFile, read_ports
from .rag_client import RagClient
from .story_client import StoryClient


class BackendClient:
    def __init__(self, ports: PortsFile):
        self.ports = ports
        self.story = StoryClient(base_url=ports.base_url("story"), token=ports.token)
        self.rag = RagClient(base_url=ports.base_url("rag"), token=ports.token)
        self.image = ImageClient(base_url=ports.base_url("image"), token=ports.token)

    @classmethod
    def from_runtime(cls) -> "BackendClient":
        return cls(read_ports())
