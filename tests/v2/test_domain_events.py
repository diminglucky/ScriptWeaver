"""CreativeEvent encode/decode. See v2 plan §3.3."""

from __future__ import annotations

import json

from src.shared.domain.events import CreativeEvent, deserialize_event, serialize_event


def test_event_to_json_roundtrip_preserves_fields():
    ev = CreativeEvent(
        type="token",
        run_id="r1",
        node="generate_chapter",
        message="ok",
        payload={"text": "你好"},
    )
    raw = serialize_event(ev)
    back = deserialize_event(raw)
    assert back.type == "token"
    assert back.run_id == "r1"
    assert back.node == "generate_chapter"
    assert back.message == "ok"
    assert back.payload == {"text": "你好"}
    assert back.ts != ""  # stamped during to_json


def test_event_stamp_is_idempotent_when_already_set():
    ev = CreativeEvent(type="run_started", run_id="r2", ts="2026-01-01T00:00:00+00:00")
    ev.stamp()
    assert ev.ts == "2026-01-01T00:00:00+00:00"


def test_deserialize_tolerates_missing_optional_fields():
    raw = json.dumps({"type": "succeeded", "run_id": "r3"})
    ev = deserialize_event(raw)
    assert ev.type == "succeeded"
    assert ev.run_id == "r3"
    assert ev.node == ""
    assert ev.payload == {}


def test_serialized_event_is_valid_json_with_unicode():
    ev = CreativeEvent(type="warning", run_id="r4", message="中文消息")
    raw = serialize_event(ev)
    obj = json.loads(raw)
    assert obj["message"] == "中文消息"
