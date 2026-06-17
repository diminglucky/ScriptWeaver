"""Prompt library. Merges config/story_*_profile.json and guardrails."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PromptLibrary:
    pipeline_profile: dict = field(default_factory=dict)
    prompt_profile: dict = field(default_factory=dict)
    guardrails: dict = field(default_factory=dict)

    @classmethod
    def from_config(cls) -> "PromptLibrary":
        import json

        from src.shared.config.paths import get_repo_paths

        cfg = get_repo_paths().config_root
        files = {
            "pipeline_profile": cfg / "story_pipeline_profile.json",
            "prompt_profile": cfg / "story_prompt_profile.json",
            "guardrails": cfg / "story_guardrails.json",
        }
        loaded: dict[str, dict] = {}
        for key, path in files.items():
            if path.exists():
                try:
                    loaded[key] = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    loaded[key] = {}
            else:
                loaded[key] = {}
        return cls(**loaded)

    def build_story_bible_prompt(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "task": "story_bible",
            "instruction": "Use the requirement, retrieved context, and constraints to return pure JSON matching StoryBible.",
            "profile": self.prompt_profile.get("outline", {}),
            "guardrails": self.guardrails,
            "state": state,
        }

    def build_character_prompt(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "task": "character_design",
            "instruction": "Return a characters array whose items match CharacterProfile.",
            "profile": self.prompt_profile.get("story", {}),
            "guardrails": self.guardrails,
            "state": state,
        }

    def build_outline_prompt(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "task": "outline",
            "instruction": "Return an outline array whose items match OutlineSection.",
            "profile": self.prompt_profile.get("outline", {}),
            "pipeline": self.pipeline_profile.get("emotion_arc", {}),
            "guardrails": self.guardrails,
            "state": state,
        }

    def build_chapter_prompt(self, state: dict[str, Any], section: dict[str, Any]) -> dict[str, Any]:
        return {
            "task": "chapter",
            "instruction": "Use the StoryBible, section plan, and context to return pure JSON matching ChapterDraft.",
            "profile": self.prompt_profile.get("section", {}),
            "pipeline": self.pipeline_profile,
            "guardrails": self.guardrails,
            "section": section,
            "state": state,
        }

    def build_review_prompt(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "task": "review",
            "instruction": "Score the draft and return actionable revision notes as pure JSON matching ReviewResult.",
            "profile": self.pipeline_profile.get("quality_review", {}),
            "guardrails": self.guardrails,
            "state": state,
        }
