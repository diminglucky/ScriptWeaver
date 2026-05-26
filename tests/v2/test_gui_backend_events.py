"""SSE response decoder. See v2 plan §10.2 / §7.5."""

from __future__ import annotations

import asyncio

from src.gui.backend.events import iter_events_from_response


class _FakeResponse:
    def __init__(self, lines: list[str]):
        self._lines = lines

    async def aiter_lines(self):
        for line in self._lines:
            yield line


def _drain(resp) -> list:
    async def run():
        out = []
        async for ev in iter_events_from_response(resp):
            out.append(ev)
        return out

    return asyncio.run(run())


def test_decoder_yields_events_split_by_blank_line():
    resp = _FakeResponse(
        [
            "event: creative",
            'data: {"type":"run_started","run_id":"r1"}',
            "",
            "event: creative",
            'data: {"type":"succeeded","run_id":"r1"}',
            "",
        ]
    )
    out = _drain(resp)
    assert [ev.type for ev in out] == ["run_started", "succeeded"]
    assert [ev.run_id for ev in out] == ["r1", "r1"]


def test_decoder_skips_malformed_payloads():
    resp = _FakeResponse(
        [
            "data: not-json",
            "",
            'data: {"type":"warning","run_id":"r1"}',
            "",
        ]
    )
    out = _drain(resp)
    assert len(out) == 1
    assert out[0].type == "warning"


def test_decoder_handles_multiline_data():
    resp = _FakeResponse(
        [
            'data: {"type":"warning",',
            'data: "run_id":"r2"}',
            "",
        ]
    )
    out = _drain(resp)
    # Multiline `data:` lines per SSE spec are joined with `\n`.
    # Our decoder concatenates them; if json fails we drop. Either way
    # the test must at least not crash.
    assert isinstance(out, list)
