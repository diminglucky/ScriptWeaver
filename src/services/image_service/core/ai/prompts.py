"""Image-side prompts: shot extract / shot prompt / translate / character desc."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ImagePromptLibrary:
    @classmethod
    def from_config(cls) -> "ImagePromptLibrary":
        return cls()

    # Concrete builders implemented in Phase 6.
