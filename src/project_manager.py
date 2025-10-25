"""
项目管理模块：负责保存和加载创作项目
每个项目包含：故事内容、生成参数、图片等
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any


class Project:
	"""单个创作项目"""
	
	def __init__(self, project_dir: Path):
		self.project_dir = Path(project_dir)
		self.project_dir.mkdir(parents=True, exist_ok=True)
		
		self.meta_file = self.project_dir / "project.json"
		self.story_file = self.project_dir / "story.txt"
		self.images_dir = self.project_dir / "images"
		self.images_dir.mkdir(exist_ok=True)
		
		self.metadata: dict[str, Any] = self._load_metadata()
	
	def _load_metadata(self) -> dict[str, Any]:
		"""加载项目元数据"""
		if self.meta_file.exists():
			try:
				with open(self.meta_file, "r", encoding="utf-8") as f:
					return json.load(f)
			except Exception:
				pass
		return {
			"name": self.project_dir.name,
			"created_at": datetime.now().isoformat(),
			"updated_at": datetime.now().isoformat(),
			"category": "",
			"requirement": "",
			"style": "",
			"target_chars": 1800,
		}
	
	def _save_metadata(self) -> None:
		"""保存项目元数据"""
		self.metadata["updated_at"] = datetime.now().isoformat()
		with open(self.meta_file, "w", encoding="utf-8") as f:
			json.dump(self.metadata, f, ensure_ascii=False, indent=2)
	
	def save_story(self, content: str, **params) -> None:
		"""保存故事内容"""
		with open(self.story_file, "w", encoding="utf-8") as f:
			f.write(content)
		
		# 更新元数据
		for key, value in params.items():
			self.metadata[key] = value
		self._save_metadata()
	
	def load_story(self) -> str:
		"""加载故事内容"""
		if self.story_file.exists():
			with open(self.story_file, "r", encoding="utf-8") as f:
				return f.read()
		return ""
	
	def save_image(self, image_path: Path | str, name: str | None = None) -> Path:
		"""保存图片到项目"""
		src = Path(image_path)
		if not src.exists():
			raise FileNotFoundError(f"图片不存在: {src}")
		
		if name is None:
			timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
			name = f"img_{timestamp}{src.suffix}"
		
		dst = self.images_dir / name
		shutil.copy2(src, dst)
		return dst
	
	def list_images(self) -> list[Path]:
		"""列出项目中的所有图片"""
		if not self.images_dir.exists():
			return []
		# Path.glob 不支持大括号扩展，需逐个模式匹配
		images: list[Path] = []
		for pattern in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
			images.extend(self.images_dir.glob(pattern))
		return sorted(images)
	
	def get_info(self) -> dict[str, Any]:
		"""获取项目信息摘要"""
		story_length = len(self.load_story())
		image_count = len(list(self.images_dir.glob("*.*"))) if self.images_dir.exists() else 0
		
		return {
			"name": self.metadata.get("name", self.project_dir.name),
			"created_at": self.metadata.get("created_at", ""),
			"updated_at": self.metadata.get("updated_at", ""),
			"category": self.metadata.get("category", ""),
			"story_length": story_length,
			"image_count": image_count,
		}


class ProjectManager:
	"""项目管理器：管理多个项目"""
	
	def __init__(self, workspace: Path | str = "projects"):
		self.workspace = Path(workspace)
		self.workspace.mkdir(parents=True, exist_ok=True)
	
	def create_project(self, name: str) -> Project:
		"""创建新项目"""
		# 生成安全的文件夹名
		safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		project_dir = self.workspace / f"{safe_name}_{timestamp}"
		
		project = Project(project_dir)
		project.metadata["name"] = name
		project._save_metadata()
		return project
	
	def load_project(self, project_dir: Path | str) -> Project:
		"""加载已有项目"""
		return Project(project_dir)
	
	def list_projects(self) -> list[dict[str, Any]]:
		"""列出所有项目"""
		projects = []
		for item in self.workspace.iterdir():
			if item.is_dir() and (item / "project.json").exists():
				try:
					project = Project(item)
					info = project.get_info()
					info["path"] = str(item)
					projects.append(info)
				except Exception:
					continue
		
		# 按更新时间倒序排列
		projects.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
		return projects
	
	def delete_project(self, project_dir: Path | str) -> None:
		"""删除项目"""
		project_path = Path(project_dir)
		if project_path.exists() and project_path.is_dir():
			shutil.rmtree(project_path)

