"""SSE frame encoder. See v2 plan §7.5."""

from __future__ import annotations

import json

from src.shared.domain.events import CreativeEvent
from src.shared.http.sse import sse_event_line


def test_sse_event_line_has_correct_framing():
    ev = CreativeEvent(type="token", run_id="r1", payload={"text": "hi"})
    frame = sse_event_line(ev)
    assert frame.startswith("event: creative\n")
    assert frame.endswith("\n\n")
    assert "data: " in frame


def test_sse_event_line_payload_is_valid_json():
    ev = CreativeEvent(type="warning", run_id="r1", message="msg")
    frame = sse_event_line(ev)
    data_line = next(line for line in frame.splitlines() if line.startswith("data: "))
    obj = json.loads(data_line[len("data: ") :])
    assert obj["run_id"] == "r1"
    assert obj["type"] == "warning"


def test_sse_custom_event_name():
    ev = CreativeEvent(type="token", run_id="r1")
    frame = sse_event_line(ev, event_name="ping")
    assert frame.startswith("event: ping\n")
