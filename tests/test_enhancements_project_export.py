import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.gui.mixins.enhancements_modules.project_export import ProjectExportMixin


class _DummyProjectExport(ProjectExportMixin):
    def __init__(self):
        self.current_project = None
        self.refreshed = False

    def refresh_projects(self):
        self.refreshed = True


class _DummyProjectExportWithProjectList(ProjectExportMixin):
    def __init__(self):
        self.current_project = None
        self.list_refreshed = False
        self.refreshed = False

    def _refresh_project_list(self):
        self.list_refreshed = True

    def refresh_projects(self):
        self.refreshed = True


class ProjectExportMixinTests(unittest.TestCase):
    @patch("src.gui.mixins.enhancements_modules.project_export.messagebox.showwarning")
    def test_export_project_without_current_project(self, mock_warning):
        obj = _DummyProjectExport()
        obj.current_project = None
        obj.export_project()
        mock_warning.assert_called_once()

    @patch("src.gui.mixins.enhancements_modules.project_export.filedialog.askopenfilename", return_value="")
    @patch("src.gui.mixins.enhancements_modules.project_export.messagebox.showerror")
    def test_import_project_cancelled(self, mock_error, _mock_open):
        obj = _DummyProjectExport()
        obj.import_project()
        mock_error.assert_not_called()

    @patch("src.gui.mixins.enhancements_modules.project_export.messagebox.showinfo")
    @patch("src.gui.mixins.enhancements_modules.project_export.messagebox.showerror")
    @patch("src.gui.mixins.enhancements_modules.project_export.filedialog.asksaveasfilename")
    def test_export_project_supports_project_object(self, mock_saveas, mock_error, mock_info):
        obj = _DummyProjectExport()

        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as td:
            os.chdir(td)
            try:
                project_dir = Path("projects") / "demo_20260209"
                project_dir.mkdir(parents=True, exist_ok=True)
                (project_dir / "story.txt").write_text("hello", encoding="utf-8")
                obj.current_project = SimpleNamespace(project_dir=project_dir, metadata={"name": "demo"})

                out_zip = Path(td) / "export.zip"
                mock_saveas.return_value = str(out_zip)

                obj.export_project()

                self.assertTrue(out_zip.exists())
                with zipfile.ZipFile(out_zip, "r") as zf:
                    names = set(zf.namelist())
                    self.assertIn("metadata.json", names)
                    self.assertIn("demo_20260209/story.txt", names)
            finally:
                os.chdir(old_cwd)

        mock_error.assert_not_called()
        mock_info.assert_called_once()

    @patch("src.gui.mixins.enhancements_modules.project_export.messagebox.showinfo")
    @patch("src.gui.mixins.enhancements_modules.project_export.messagebox.showerror")
    @patch("src.gui.mixins.enhancements_modules.project_export.filedialog.askopenfilename")
    def test_import_project_blocks_zip_slip(self, mock_open, mock_error, mock_info):
        obj = _DummyProjectExport()

        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as td:
            os.chdir(td)
            try:
                zip_path = Path(td) / "import.zip"
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr("metadata.json", '{"name": "safeproj"}')
                    zf.writestr("safeproj/story.txt", "ok")
                    zf.writestr("safeproj/../../evil.txt", "bad")
                    zf.writestr("safeproj\\..\\..\\evil2.txt", "bad2")

                mock_open.return_value = str(zip_path)
                obj.import_project()

                self.assertTrue((Path("projects") / "safeproj" / "story.txt").exists())
                self.assertFalse(Path("evil.txt").exists())
                self.assertFalse(Path("evil2.txt").exists())
                self.assertTrue(obj.refreshed)
            finally:
                os.chdir(old_cwd)

        mock_error.assert_not_called()
        mock_info.assert_called_once()

    @patch("src.gui.mixins.enhancements_modules.project_export.messagebox.askyesno", return_value=True)
    @patch("src.gui.mixins.enhancements_modules.project_export.messagebox.showinfo")
    @patch("src.gui.mixins.enhancements_modules.project_export.messagebox.showerror")
    @patch("src.gui.mixins.enhancements_modules.project_export.filedialog.askopenfilename")
    def test_import_project_overwrite_clears_old_files(self, mock_open, mock_error, mock_info, _mock_confirm):
        obj = _DummyProjectExport()

        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as td:
            os.chdir(td)
            try:
                existing_dir = Path("projects") / "safeproj"
                existing_dir.mkdir(parents=True, exist_ok=True)
                (existing_dir / "old.txt").write_text("old", encoding="utf-8")

                zip_path = Path(td) / "import.zip"
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr("metadata.json", '{"name": "safeproj"}')
                    zf.writestr("safeproj/new.txt", "new")

                mock_open.return_value = str(zip_path)
                obj.import_project()

                self.assertTrue((existing_dir / "new.txt").exists())
                self.assertFalse((existing_dir / "old.txt").exists())
            finally:
                os.chdir(old_cwd)

        mock_error.assert_not_called()
        mock_info.assert_called_once()

    @patch("src.gui.mixins.enhancements_modules.project_export.messagebox.showinfo")
    @patch("src.gui.mixins.enhancements_modules.project_export.messagebox.showerror")
    @patch("src.gui.mixins.enhancements_modules.project_export.filedialog.askopenfilename")
    def test_import_project_keeps_structure_without_single_common_root(self, mock_open, mock_error, mock_info):
        obj = _DummyProjectExport()

        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as td:
            os.chdir(td)
            try:
                zip_path = Path(td) / "import_mixed.zip"
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr("metadata.json", '{"name": "safeproj"}')
                    zf.writestr("a/one.txt", "1")
                    zf.writestr("b/two.txt", "2")

                mock_open.return_value = str(zip_path)
                obj.import_project()

                self.assertTrue((Path("projects") / "safeproj" / "a" / "one.txt").exists())
                self.assertTrue((Path("projects") / "safeproj" / "b" / "two.txt").exists())
            finally:
                os.chdir(old_cwd)

        mock_error.assert_not_called()
        mock_info.assert_called_once()

    @patch("src.gui.mixins.enhancements_modules.project_export.messagebox.showinfo")
    @patch("src.gui.mixins.enhancements_modules.project_export.messagebox.showerror")
    @patch("src.gui.mixins.enhancements_modules.project_export.filedialog.askopenfilename")
    def test_import_project_prefers_refresh_project_list(self, mock_open, mock_error, mock_info):
        obj = _DummyProjectExportWithProjectList()

        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as td:
            os.chdir(td)
            try:
                zip_path = Path(td) / "import.zip"
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr("metadata.json", '{"name": "safeproj"}')
                    zf.writestr("safeproj/story.txt", "ok")

                mock_open.return_value = str(zip_path)
                obj.import_project()
            finally:
                os.chdir(old_cwd)

        self.assertTrue(obj.list_refreshed)
        self.assertFalse(obj.refreshed)
        mock_error.assert_not_called()
        mock_info.assert_called_once()


if __name__ == "__main__":
    unittest.main()
