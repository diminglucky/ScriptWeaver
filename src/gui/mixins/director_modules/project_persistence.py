"""
导演项目数据持久化 - 保存和加载项目的所有工作流数据
"""

import json
import os
from typing import Dict, List, Any
from pathlib import Path


class ProjectPersistenceMixin:
	"""项目数据持久化功能"""
	
	def save_director_project(self, project_path: str) -> bool:
		"""
		保存导演项目的所有数据
		
		包含：
		- 剧本
		- 分镜头列表
		- 一致性设定表
		- 生成的图片路径
		- 视频提示词
		- 生成参数
		
		Args:
			project_path: 项目目录路径
			
		Returns:
			是否保存成功
		"""
		
		try:
			# 创建导演数据目录
			director_dir = os.path.join(project_path, "director")
			os.makedirs(director_dir, exist_ok=True)
			
			# 保存剧本
			if hasattr(self, 'current_script') and self.current_script:
				script_file = os.path.join(director_dir, "script.txt")
				with open(script_file, 'w', encoding='utf-8') as f:
					f.write(self.current_script)
				print(f"✅ 剧本已保存: {script_file}")
			
			# 保存分镜头列表
			if hasattr(self, 'current_shots') and self.current_shots:
				shots_file = os.path.join(director_dir, "shots.json")
				with open(shots_file, 'w', encoding='utf-8') as f:
					json.dump(self.current_shots, f, ensure_ascii=False, indent=2)
				print(f"✅ 分镜头已保存: {shots_file}")
			
			# 保存一致性设定表
			if hasattr(self, 'consistency_data') and self.consistency_data:
				consistency_file = os.path.join(director_dir, "consistency.json")
				with open(consistency_file, 'w', encoding='utf-8') as f:
					json.dump(self.consistency_data, f, ensure_ascii=False, indent=2)
				print(f"✅ 一致性设定已保存: {consistency_file}")
			
			# 保存生成参数
			if hasattr(self, 'director_resolution') and hasattr(self, 'director_style'):
				params = {
					"resolution": self.director_resolution.get(),
					"style": self.director_style.get(),
					"video_platform": self.director_video_platform.get() if hasattr(self, 'director_video_platform') else "jimeng"
				}
				params_file = os.path.join(director_dir, "parameters.json")
				with open(params_file, 'w', encoding='utf-8') as f:
					json.dump(params, f, ensure_ascii=False, indent=2)
				print(f"✅ 生成参数已保存: {params_file}")
			
			# 保存视频提示词
			if hasattr(self, 'video_prompt_text'):
				prompt_text = self.video_prompt_text.get("1.0", "end-1c").strip()
				if prompt_text:
					prompt_file = os.path.join(director_dir, "video_prompt.txt")
					with open(prompt_file, 'w', encoding='utf-8') as f:
						f.write(prompt_text)
					print(f"✅ 视频提示词已保存: {prompt_file}")
			
			# 保存项目元数据
			metadata = {
				"version": "1.0",
				"type": "director_project",
				"has_script": bool(hasattr(self, 'current_script') and self.current_script),
				"has_shots": bool(hasattr(self, 'current_shots') and self.current_shots),
				"shots_count": len(self.current_shots) if hasattr(self, 'current_shots') else 0,
				"has_consistency": bool(hasattr(self, 'current_consistency') and self.current_consistency),
				"has_video_prompt": bool(hasattr(self, 'video_prompt_text'))
			}
			metadata_file = os.path.join(director_dir, "metadata.json")
			with open(metadata_file, 'w', encoding='utf-8') as f:
				json.dump(metadata, f, ensure_ascii=False, indent=2)
			
			print(f"\n✅ 导演项目已保存到: {director_dir}")
			return True
		
		except Exception as e:
			print(f"❌ 保存导演项目失败: {str(e)}")
			return False
	
	def load_director_project(self, project_path: str) -> bool:
		"""
		加载导演项目的所有数据
		
		Args:
			project_path: 项目目录路径
			
		Returns:
			是否加载成功
		"""
		
		try:
			director_dir = os.path.join(project_path, "director")
			
			# 检查目录是否存在
			if not os.path.exists(director_dir):
				print(f"⚠️  未找到导演数据: {director_dir}")
				return False
			
			# 加载剧本
			script_file = os.path.join(director_dir, "script.txt")
			if os.path.exists(script_file):
				with open(script_file, 'r', encoding='utf-8') as f:
					self.current_script = f.read()
				if hasattr(self, 'script_text'):
					self.script_text.config(state="normal")
					self.script_text.delete("1.0", "end")
					self.script_text.insert("1.0", self.current_script)
					self.script_text.config(state="disabled")
				print(f"✅ 已加载剧本")
			
			# 加载分镜头列表
			shots_file = os.path.join(director_dir, "shots.json")
			if os.path.exists(shots_file):
				with open(shots_file, 'r', encoding='utf-8') as f:
					self.current_shots = json.load(f)
				if hasattr(self, 'shots_list'):
					self.shots_list.config(state="normal")
					self.shots_list.delete("1.0", "end")
					for shot in self.current_shots:
						shot_num = shot.get('shot_number', 0)
						shot_type = shot.get('shot_type', '')
						description = shot.get('scene_description', '')
						shot_info = f"【镜头 {shot_num}】{shot_type}\n{description}\n\n"
						self.shots_list.insert("end", shot_info)
					self.shots_list.config(state="disabled")
				print(f"✅ 已加载 {len(self.current_shots)} 个分镜头")
			
			# 加载一致性设定表
			consistency_file = os.path.join(director_dir, "consistency.json")
			if os.path.exists(consistency_file):
				with open(consistency_file, 'r', encoding='utf-8') as f:
					self.consistency_data = json.load(f)
				print(f"✅ 已加载一致性设定表")
				
				# 更新UI显示
				char_count = len(self.consistency_data.get("characters", {}))
				if hasattr(self, 'consistency_status_label'):
					self.consistency_status_label.config(
						text=f"已设定 {char_count} 个人物",
						foreground="green"
					)
			
			# 加载生成参数
			params_file = os.path.join(director_dir, "parameters.json")
			if os.path.exists(params_file):
				with open(params_file, 'r', encoding='utf-8') as f:
					params = json.load(f)
				if hasattr(self, 'director_resolution'):
					self.director_resolution.set(params.get("resolution", "768x512"))
				if hasattr(self, 'director_style'):
					self.director_style.set(params.get("style", "photorealistic"))
				if hasattr(self, 'director_video_platform'):
					self.director_video_platform.set(params.get("video_platform", "jimeng"))
				print(f"✅ 已加载生成参数")
			
			# 加载视频提示词
			prompt_file = os.path.join(director_dir, "video_prompt.txt")
			if os.path.exists(prompt_file):
				with open(prompt_file, 'r', encoding='utf-8') as f:
					prompt_text = f.read()
				if hasattr(self, 'video_prompt_text'):
					self.video_prompt_text.config(state="normal")
					self.video_prompt_text.delete("1.0", "end")
					self.video_prompt_text.insert("1.0", prompt_text)
					self.video_prompt_text.config(state="disabled")
				print(f"✅ 已加载视频提示词")
			
			print(f"\n✅ 导演项目已加载: {director_dir}")
			return True
		
		except Exception as e:
			print(f"❌ 加载导演项目失败: {str(e)}")
			return False
	
	def export_director_project(self, project_path: str, export_format: str = "markdown") -> bool:
		"""
		导出导演项目为文档格式
		
		Args:
			project_path: 项目目录路径
			export_format: 导出格式 ("markdown" 或 "html")
			
		Returns:
			是否导出成功
		"""
		
		try:
			export_dir = os.path.join(project_path, "director", "exports")
			os.makedirs(export_dir, exist_ok=True)
			
			# 生成导出内容
			content = self._generate_export_content()
			
			if export_format == "markdown":
				export_file = os.path.join(export_dir, "project_export.md")
				with open(export_file, 'w', encoding='utf-8') as f:
					f.write(content)
			elif export_format == "html":
				# 简单的HTML转换
				html_content = f"""
<!DOCTYPE html>
<html>
<head>
	<meta charset="UTF-8">
	<title>导演项目</title>
	<style>
		body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; }}
		h1 {{ color: #333; }}
		h2 {{ color: #666; margin-top: 30px; }}
		pre {{ background: #f5f5f5; padding: 10px; border-radius: 5px; overflow-x: auto; }}
	</style>
</head>
<body>
{content.replace(chr(10), '<br>')}
</body>
</html>
"""
				export_file = os.path.join(export_dir, "project_export.html")
				with open(export_file, 'w', encoding='utf-8') as f:
					f.write(html_content)
			
			print(f"✅ 项目已导出: {export_file}")
			return True
		
		except Exception as e:
			print(f"❌ 导出项目失败: {str(e)}")
			return False
	
	def _generate_export_content(self) -> str:
		"""生成导出内容"""
		
		content = "# 🎬 导演项目导出\n\n"
		
		# 剧本
		if hasattr(self, 'current_script') and self.current_script:
			content += "## 📝 剧本\n\n"
			content += self.current_script + "\n\n"
		
		# 分镜头
		if hasattr(self, 'current_shots') and self.current_shots:
			content += "## 🎬 分镜头列表\n\n"
			for shot in self.current_shots:
				shot_num = shot.get('shot_number', 0)
				shot_type = shot.get('shot_type', 'Unknown')
				description = shot.get('scene_description', '')
				characters = shot.get('characters', [])
				action = shot.get('action', '')
				lighting = shot.get('lighting', '')
				atmosphere = shot.get('atmosphere', '')
				
				content += f"### 镜头 {shot_num}: {shot_type}\n\n"
				content += f"**场景**: {description}\n\n"
				if characters:
					content += f"**人物**: {', '.join(characters)}\n\n"
				if action:
					content += f"**动作**: {action}\n\n"
				if lighting:
					content += f"**光线**: {lighting}\n\n"
				if atmosphere:
					content += f"**氛围**: {atmosphere}\n\n"
				content += "---\n\n"
		
		# 视频提示词
		if hasattr(self, 'video_prompt_text'):
			prompt_text = self.video_prompt_text.get("1.0", "end-1c").strip()
			if prompt_text:
				content += "## 🎥 视频提示词\n\n"
				content += prompt_text + "\n\n"
		
		return content
	
	def get_project_status(self, project_path: str) -> Dict[str, Any]:
		"""
		获取项目状态信息
		
		Returns:
			项目状态字典
		"""
		
		try:
			director_dir = os.path.join(project_path, "director")
			metadata_file = os.path.join(director_dir, "metadata.json")
			
			if os.path.exists(metadata_file):
				with open(metadata_file, 'r', encoding='utf-8') as f:
					metadata = json.load(f)
				return metadata
			else:
				return {
					"version": "1.0",
					"type": "director_project",
					"has_script": False,
					"has_shots": False,
					"shots_count": 0,
					"has_consistency": False,
					"has_video_prompt": False
				}
		
		except Exception as e:
			print(f"❌ 获取项目状态失败: {str(e)}")
			return {}



