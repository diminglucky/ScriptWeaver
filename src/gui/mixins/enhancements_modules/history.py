"""History helpers extracted from enhancements mixin."""

from datetime import datetime
from typing import Callable, Dict, List, Optional


class HistoryManager:
    """Simple undo/redo history stack."""

    def __init__(self, max_history: int = 50):
        self.max_history = max_history
        self.history: List[Dict] = []
        self.current_index = -1

    def add(self, action: str, data: Dict, undo_func: Callable = None, redo_func: Callable = None):
        if self.current_index < len(self.history) - 1:
            self.history = self.history[: self.current_index + 1]

        record = {
            "action": action,
            "data": data,
            "undo": undo_func,
            "redo": redo_func,
            "timestamp": datetime.now().isoformat(),
        }

        self.history.append(record)
        self.current_index = len(self.history) - 1

        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history :]
            self.current_index = len(self.history) - 1

    def undo(self) -> Optional[Dict]:
        if self.current_index >= 0:
            record = self.history[self.current_index]
            if record.get("undo"):
                record["undo"](record["data"])
            self.current_index -= 1
            return record
        return None

    def redo(self) -> Optional[Dict]:
        if self.current_index < len(self.history) - 1:
            self.current_index += 1
            record = self.history[self.current_index]
            if record.get("redo"):
                record["redo"](record["data"])
            return record
        return None

    def can_undo(self) -> bool:
        return self.current_index >= 0

    def can_redo(self) -> bool:
        return self.current_index < len(self.history) - 1

    def clear(self):
        self.history = []
        self.current_index = -1

    def get_history_list(self) -> List[Dict]:
        return self.history[: self.current_index + 1]


class HistoryMixin:
    """History mixin APIs used by the UI."""

    def _init_history(self):
        self.history_manager = HistoryManager()

    def add_to_history(self, action: str, data: Dict, undo_func: Callable = None, redo_func: Callable = None):
        if hasattr(self, "history_manager"):
            self.history_manager.add(action, data, undo_func, redo_func)

    def undo_action(self):
        if hasattr(self, "history_manager") and self.history_manager.can_undo():
            record = self.history_manager.undo()
            if record:
                self.update_status(f"已撤销: {record['action']}")

    def redo_action(self):
        if hasattr(self, "history_manager") and self.history_manager.can_redo():
            record = self.history_manager.redo()
            if record:
                self.update_status(f"已重做: {record['action']}")

    def update_status(self, message: str):
        if hasattr(self, "status"):
            self.status.set(message)
