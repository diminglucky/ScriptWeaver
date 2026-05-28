from __future__ import annotations

import unittest

from src.gui.utils import parse_outline_sections


class StoryOutlineEventPromiseTests(unittest.TestCase):
    def test_parse_outline_sections_extracts_event_promise(self):
        sections = parse_outline_sections(
            "1. 空降基层 | 主角发现证据后被总部反咬，失去调查权限\n"
            "2. 暗流涌动（1500字）｜盟友交出假资料，真正账本被转移"
        )
        self.assertEqual(sections[0]["title"], "空降基层")
        self.assertEqual(sections[0]["event_promise"], "主角发现证据后被总部反咬，失去调查权限")
        self.assertEqual(sections[1]["title"], "暗流涌动")
        self.assertEqual(sections[1]["chars"], 1500)
        self.assertEqual(sections[1]["event_promise"], "盟友交出假资料，真正账本被转移")


if __name__ == "__main__":
    unittest.main()
