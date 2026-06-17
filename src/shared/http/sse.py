"""SSE encoding helpers. See docs/technical_architecture.md.5."""

from __future__ import annotations

from src.shared.domain.events import CreativeEvent, serialize_event


def sse_event_line(ev: CreativeEvent, *, event_name: str = "creative") -> str:
    """Encode a CreativeEvent as a complete SSE frame (incl. trailing blank line)."""
    return f"event: {event_name}\ndata: {serialize_event(ev)}\n\n"
