"""GUI-side backend integration: supervisor, HTTP clients, and threading bridge.

The GUI must not import workflow, vector backend, or model SDK internals
directly; every backend interaction goes through this package.
"""

from .ports import PortsFile, read_ports, write_ports
from .errors import error_from_payload
from .events import iter_events_from_response
from .threading_bridge import marshal_to_tk, run_in_background

__all__ = [
    "PortsFile",
    "read_ports",
    "write_ports",
    "error_from_payload",
    "iter_events_from_response",
    "marshal_to_tk",
    "run_in_background",
]
