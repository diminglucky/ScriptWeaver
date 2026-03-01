import json
import tempfile
import unittest
from pathlib import Path

from src.project_manager import Project
from src.project_manager import ProjectManager


class ProjectManagerMetadataTests(unittest.TestCase):
    def test_load_invalid_metadata_logs_warning_and_falls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "demo_project"
            project_dir.mkdir(parents=True, exist_ok=True)
            (project_dir / "project.json").write_text("{invalid json", encoding="utf-8")

            with self.assertLogs("src.project_manager", level="WARNING") as logs:
                project = Project(project_dir)

            self.assertTrue(any("Failed to load project metadata" in msg for msg in logs.output))
            self.assertEqual(project.metadata.get("name"), "demo_project")
            self.assertIn("created_at", project.metadata)

    def test_load_valid_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "demo_project"
            project_dir.mkdir(parents=True, exist_ok=True)
            payload = {"name": "my story", "target_chars": 2500}
            (project_dir / "project.json").write_text(
                json.dumps(payload, ensure_ascii=False),
                encoding="utf-8",
            )

            project = Project(project_dir)
            self.assertEqual(project.metadata["name"], "my story")
            self.assertEqual(project.metadata["target_chars"], 2500)

    def test_delete_project_rejects_path_outside_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "projects"
            workspace.mkdir(parents=True, exist_ok=True)
            outside = root / "outside_project"
            outside.mkdir(parents=True, exist_ok=True)

            manager = ProjectManager(workspace=workspace)
            with self.assertRaises(ValueError):
                manager.delete_project(outside)

            self.assertTrue(outside.exists())

    def test_delete_project_allows_workspace_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "projects"
            workspace.mkdir(parents=True, exist_ok=True)
            target = workspace / "demo"
            target.mkdir(parents=True, exist_ok=True)
            (target / "story.txt").write_text("x", encoding="utf-8")

            manager = ProjectManager(workspace=workspace)
            manager.delete_project(target)

            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
