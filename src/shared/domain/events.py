"""Creative event protocol. See v2 plan §3.3 / §7.5 / §14.2.

A single event type is shared by all 3 services; SSE wire format is
`event: creative\\ndata: <json>\\n\\n`.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

EventType = Literal[
    "run_started",
    "node_started",
    "node_finished",
    "token",
    "partial_chapter",
    "human_input_required",
    "warning",
    "failed",
    "succeeded",
    "cancelled",
]


@dataclass
class CreativeEvent:
    type: EventType
    run_id: str
    message: str = ""
    node: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    ts: str = ""  # ISO 8601; filled by `stamp()` if empty

    def stamp(self) -> "CreativeEvent":
        if not self.ts:
            self.ts = datetime.now(timezone.utc).isoformat()
        return self

    def to_json(self) -> str:
        return json.dumps(asdict(self.stamp()), ensure_ascii=False)


def serialize_event(ev: CreativeEvent) -> str:
    """Encode for an SSE `data:` line (no trailing newline)."""
    return ev.to_json()


def deserialize_event(line: str) -> CreativeEvent:
    raw = json.loads(line)
    return CreativeEvent(
        type=raw["type"],
        run_id=raw["run_id"],
        message=raw.get("message", ""),
        node=raw.get("node", ""),
        payload=raw.get("payload") or {},
        ts=raw.get("ts", ""),
    )
