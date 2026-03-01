import unittest

from src.gui.mixins.enhancements_modules.history import HistoryManager


class HistoryManagerTests(unittest.TestCase):
    def test_undo_redo_flow(self):
        manager = HistoryManager(max_history=5)
        calls = []

        def undo(data):
            calls.append(("undo", data["v"]))

        def redo(data):
            calls.append(("redo", data["v"]))

        manager.add("a1", {"v": 1}, undo_func=undo, redo_func=redo)
        manager.add("a2", {"v": 2}, undo_func=undo, redo_func=redo)

        self.assertTrue(manager.can_undo())
        record = manager.undo()
        self.assertEqual(record["action"], "a2")
        self.assertEqual(calls[-1], ("undo", 2))

        self.assertTrue(manager.can_redo())
        record = manager.redo()
        self.assertEqual(record["action"], "a2")
        self.assertEqual(calls[-1], ("redo", 2))

    def test_truncate_future_after_new_add(self):
        manager = HistoryManager(max_history=5)
        manager.add("a1", {"v": 1})
        manager.add("a2", {"v": 2})
        manager.undo()
        manager.add("a3", {"v": 3})
        self.assertEqual([x["action"] for x in manager.history], ["a1", "a3"])


if __name__ == "__main__":
    unittest.main()
