"""Bridge between asyncio worker threads and the Tk main thread.

See docs/technical_architecture.md.4.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any, Awaitable, Callable


def run_in_background(coro_factory: Callable[[], Awaitable[Any]]) -> threading.Thread:
    """Run an async coroutine in a fresh event loop on a daemon thread."""

    def _runner() -> None:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(coro_factory())
        finally:
            loop.close()

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    return thread


def marshal_to_tk(widget: Any, fn: Callable[[], None]) -> None:
    """Schedule `fn` on the Tk main thread via `widget.after(0, ...)`."""
    try:
        widget.after(0, fn)
    except Exception:
        # Widget might already be destroyed; swallow silently.
        pass
