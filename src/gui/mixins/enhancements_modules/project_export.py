"""Project import/export helpers extracted from enhancements mixin."""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path, PurePosixPath
from tkinter import filedialog, messagebox

logger = logging.getLogger(__name__)


class ProjectExportMixin:
    """Export and import project zip packages."""

    @staticmethod
    def _sanitize_project_name(name: str) -> str:
        raw = (name or "").strip()
        if not raw:
            return "imported_project"
        safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in raw)
        return safe or "imported_project"

    def _resolve_current_project(self):
        """Return (project_name, project_dir) for current project."""
        project = getattr(self, "current_project", None)
        if not project:
            return None, None

        # Runtime primary type from ProjectManager
        if hasattr(project, "project_dir"):
            project_dir = Path(project.project_dir)
            metadata = getattr(project, "metadata", {}) or {}
            project_name = metadata.get("name") if isinstance(metadata, dict) else None
            if not project_name:
                project_name = project_dir.name
            return str(project_name), project_dir

        # Backward compatibility for dict-shaped projects
        if isinstance(project, dict):
            project_name = str(project.get("name") or "unnamed")
            project_path = project.get("path")
            project_dir = Path(project_path) if project_path else (Path("projects") / project_name)
            return project_name, project_dir

        return None, None

    def export_project(self):
        import zipfile

        if not hasattr(self, "current_project") or not self.current_project:
            messagebox.showwarning("提示", "请先选择一个项目")
            return

        project_name, project_dir = self._resolve_current_project()
        if not project_name or not project_dir:
            messagebox.showerror("错误", "当前项目类型不支持导出")
            return

        if not project_dir.exists():
            messagebox.showerror("错误", "项目目录不存在")
            return

        file_path = filedialog.asksaveasfilename(
            title="导出项目",
            defaultextension=".zip",
            filetypes=[("ZIP文件", "*.zip"), ("所有文件", "*.*")],
            initialname=f"{project_name}_{datetime.now().strftime('%Y%m%d')}.zip",
        )
        if not file_path:
            return

        try:
            with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file in project_dir.rglob("*"):
                    if file.is_file():
                        arcname = file.relative_to(project_dir.parent)
                        zipf.write(file, arcname)

                metadata = {
                    "name": project_name,
                    "export_time": datetime.now().isoformat(),
                    "version": "2.0",
                }
                zipf.writestr("metadata.json", json.dumps(metadata, indent=2, ensure_ascii=False))

            messagebox.showinfo("成功", f"项目已导出到:\n{file_path}")
        except Exception as e:
            messagebox.showerror("错误", f"导出项目失败:\n{e}")

    def import_project(self):
        import zipfile

        file_path = filedialog.askopenfilename(
            title="导入项目",
            filetypes=[("ZIP文件", "*.zip"), ("所有文件", "*.*")],
        )
        if not file_path:
            return

        try:
            with zipfile.ZipFile(file_path, "r") as zipf:
                try:
                    metadata = json.loads(zipf.read("metadata.json"))
                    project_name = self._sanitize_project_name(metadata.get("name", "imported_project"))
                except Exception as e:
                    logger.debug("read project metadata failed, fallback to filename: %s", e)
                    project_name = self._sanitize_project_name(Path(file_path).stem)

                target_dir = Path("projects") / project_name
                if target_dir.exists():
                    if not messagebox.askyesno("确认", f"项目 '{project_name}' 已存在，是否覆盖？"):
                        return
                    shutil.rmtree(target_dir)

                target_dir.mkdir(parents=True, exist_ok=True)
                target_dir_resolved = target_dir.resolve()
                skipped_entries = 0
                parsed_members = []

                for file_info in zipf.infolist():
                    if file_info.filename == "metadata.json":
                        continue
                    member = PurePosixPath(file_info.filename.replace("\\", "/"))
                    parts = [p for p in member.parts if p not in ("", ".")]
                    parsed_members.append((file_info, parts))

                top_levels = {parts[0] for _, parts in parsed_members if parts}
                strip_top_level = len(top_levels) == 1

                for file_info, parts in parsed_members:
                    if not parts or any(p == ".." for p in parts):
                        skipped_entries += 1
                        logger.warning("skip unsafe zip entry: %s", file_info.filename)
                        continue

                    relative_parts = parts[1:] if strip_top_level and len(parts) > 1 else parts
                    if not relative_parts:
                        skipped_entries += 1
                        continue

                    new_path = (target_dir / Path(*relative_parts)).resolve()
                    if target_dir_resolved not in new_path.parents and new_path != target_dir_resolved:
                        skipped_entries += 1
                        logger.warning("skip escaping zip entry: %s", file_info.filename)
                        continue

                    if file_info.is_dir():
                        new_path.mkdir(parents=True, exist_ok=True)
                    else:
                        new_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(new_path, "wb") as f:
                            f.write(zipf.read(file_info.filename))

            if skipped_entries:
                logger.warning("import project skipped %d unsafe entries", skipped_entries)
            messagebox.showinfo("成功", f"项目 '{project_name}' 导入成功")
            # Prefer the current project page API while keeping backward compatibility.
            if hasattr(self, "_refresh_project_list"):
                self._refresh_project_list()
            elif hasattr(self, "refresh_projects"):
                self.refresh_projects()
        except Exception as e:
            messagebox.showerror("错误", f"导入项目失败:\n{e}")
