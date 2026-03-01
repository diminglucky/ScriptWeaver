import unittest

from src.gui.mixins import enhancements


class EnhancementsLegacyImportTests(unittest.TestCase):
    def test_legacy_symbols_exist(self):
        required = [
            "ProgressDialog",
            "ProgressMixin",
            "KeyboardShortcuts",
            "ShortcutsMixin",
            "HistoryManager",
            "HistoryMixin",
            "SecureKeyStorage",
            "SecureConfigMixin",
            "APIStatusMonitor",
            "APIMonitorMixin",
            "ConfigExportMixin",
            "CacheManager",
            "CacheMixin",
            "ProjectExportMixin",
            "EnhancementsMixin",
        ]
        for name in required:
            self.assertTrue(hasattr(enhancements, name), msg=f"missing legacy symbol: {name}")


if __name__ == "__main__":
    unittest.main()
