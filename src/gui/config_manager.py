"""配置管理模块"""

import json
import os
import re
from pathlib import Path
from tkinter import messagebox
import logging

from .utils import sanitize


logger = logging.getLogger(__name__)


def _dotenv_escape(value: str) -> str:
	value = str(value)
	if any(ch.isspace() for ch in value) or any(ch in value for ch in ['#', '"']):
		return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
	return value


def _fallback_set_key(dotenv_path: str, key_to_set: str, value_to_set: str) -> bool:
	try:
		path = Path(dotenv_path)
		path.parent.mkdir(parents=True, exist_ok=True)
		lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
		pattern = re.compile(r"^\s*" + re.escape(key_to_set) + r"\s*=")
		new_line = f"{key_to_set}={_dotenv_escape(value_to_set)}"
		replaced = False
		out = []
		for line in lines:
			if pattern.match(line):
				out.append(new_line)
				replaced = True
			else:
				out.append(line)
		if not replaced:
			out.append(new_line)
		path.write_text("\n".join(out) + "\n", encoding="utf-8")
		return True
	except Exception as e:
		logger.debug("Fallback set_key failed for %s in %s: %s", key_to_set, dotenv_path, e)
		return False


try:
	from dotenv import find_dotenv, set_key
except Exception as e:  # pragma: no cover - optional dependency
	logger.debug("python-dotenv unavailable for config_manager: %s", e)

	def find_dotenv(*args, **kwargs):
		return ""

	def set_key(dotenv_path, key_to_set, value_to_set, *args, **kwargs):
		return _fallback_set_key(dotenv_path, key_to_set, value_to_set)


class ConfigManager:
	"""配置管理器"""
	
	def __init__(self, config_file: str = "custom_api_presets.json"):
		self.config_file = config_file
		self.custom_presets = {}
		self.custom_image_presets = {}
	
	def load_custom_presets(self) -> dict:
		"""加载自定义API预设"""
		if not Path(self.config_file).exists():
			return {}
		
		try:
			with open(self.config_file, 'r', encoding='utf-8') as f:
				data = json.load(f)
				self.custom_presets = data.get('custom_presets', {})
				return self.custom_presets
		except Exception as e:
			logger.warning("Failed to load custom presets from %s: %s", self.config_file, e)
			return {}
	
	def save_custom_preset(self, name: str, api_key: str, base_url: str, model: str) -> bool:
		"""保存自定义API预设"""
		try:
			# 读取现有配置
			data = {}
			if Path(self.config_file).exists():
				with open(self.config_file, 'r', encoding='utf-8') as f:
					data = json.load(f)
			
			# 更新预设
			if 'custom_presets' not in data:
				data['custom_presets'] = {}
			
			data['custom_presets'][name] = {
				'api_key': api_key,
				'base_url': base_url,
				'model': model
			}
			
			# 保存
			with open(self.config_file, 'w', encoding='utf-8') as f:
				json.dump(data, f, indent=2, ensure_ascii=False)
			
			self.custom_presets = data['custom_presets']
			return True
		except Exception as e:
			messagebox.showerror("错误", f"保存预设失败: {e}")
			return False
	
	def delete_custom_preset(self, name: str) -> bool:
		"""删除自定义API预设"""
		try:
			if not Path(self.config_file).exists():
				return False
			
			with open(self.config_file, 'r', encoding='utf-8') as f:
				data = json.load(f)
			
			if 'custom_presets' in data and name in data['custom_presets']:
				del data['custom_presets'][name]
				
				with open(self.config_file, 'w', encoding='utf-8') as f:
					json.dump(data, f, indent=2, ensure_ascii=False)
				
				self.custom_presets = data.get('custom_presets', {})
				return True
			
			return False
		except Exception as e:
			messagebox.showerror("错误", f"删除预设失败: {e}")
			return False
	
	def load_custom_image_presets(self) -> dict:
		"""加载自定义图片API预设"""
		if not Path(self.config_file).exists():
			return {}
		
		try:
			with open(self.config_file, 'r', encoding='utf-8') as f:
				data = json.load(f)
				self.custom_image_presets = data.get('custom_image_presets', {})
				return self.custom_image_presets
		except Exception as e:
			logger.warning("Failed to load custom image presets from %s: %s", self.config_file, e)
			return {}
	
	def save_custom_image_preset(self, name: str, provider: str, api_key: str, 
								  base_url: str, model: str, secret_key: str = "") -> bool:
		"""保存自定义图片API预设"""
		try:
			# 读取现有配置
			data = {}
			if Path(self.config_file).exists():
				with open(self.config_file, 'r', encoding='utf-8') as f:
					data = json.load(f)
			
			# 更新预设
			if 'custom_image_presets' not in data:
				data['custom_image_presets'] = {}
			
			preset_data = {
				'provider': provider,
				'api_key': api_key,
				'base_url': base_url,
				'model': model
			}
			
			if secret_key:
				preset_data['secret_key'] = secret_key
			
			data['custom_image_presets'][name] = preset_data
			
			# 保存
			with open(self.config_file, 'w', encoding='utf-8') as f:
				json.dump(data, f, indent=2, ensure_ascii=False)
			
			self.custom_image_presets = data['custom_image_presets']
			return True
		except Exception as e:
			messagebox.showerror("错误", f"保存图片预设失败: {e}")
			return False
	
	def delete_custom_image_preset(self, name: str) -> bool:
		"""删除自定义图片API预设"""
		try:
			if not Path(self.config_file).exists():
				return False
			
			with open(self.config_file, 'r', encoding='utf-8') as f:
				data = json.load(f)
			
			if 'custom_image_presets' in data and name in data['custom_image_presets']:
				del data['custom_image_presets'][name]
				
				with open(self.config_file, 'w', encoding='utf-8') as f:
					json.dump(data, f, indent=2, ensure_ascii=False)
				
				self.custom_image_presets = data.get('custom_image_presets', {})
				return True
			
			return False
		except Exception as e:
			messagebox.showerror("错误", f"删除图片预设失败: {e}")
			return False
	
	def save_api_config_to_env(self, api_key: str, base_url: str, model: str) -> None:
		"""保存API配置到.env文件"""
		env_file = find_dotenv() or ".env"
		
		api_key = sanitize(api_key)
		base_url = sanitize(base_url)
		model = sanitize(model)
		
		set_key(env_file, "API_KEY", api_key)
		set_key(env_file, "BASE_URL", base_url)
		set_key(env_file, "MODEL", model)
	
	def save_image_api_config_to_env(self, api_key: str, base_url: str, 
									  model: str, secret_key: str = "") -> None:
		"""保存图片API配置到.env文件"""
		env_file = find_dotenv() or ".env"
		
		api_key = sanitize(api_key)
		base_url = sanitize(base_url)
		model = sanitize(model)
		secret_key = sanitize(secret_key)
		
		set_key(env_file, "IMAGE_API_KEY", api_key)
		set_key(env_file, "IMAGE_BASE_URL", base_url)
		set_key(env_file, "IMAGE_MODEL", model)
		
		if secret_key:
			set_key(env_file, "HUNYUAN_SECRET_KEY", secret_key)
	
	def load_api_config_from_env(self) -> tuple[str, str, str]:
		"""从环境变量加载API配置"""
		return (
			os.getenv("API_KEY", ""),
			os.getenv("BASE_URL", ""),
			os.getenv("MODEL", "")
		)
	
	def load_image_api_config_from_env(self) -> tuple[str, str, str, str]:
		"""从环境变量加载图片API配置"""
		return (
			os.getenv("IMAGE_API_KEY", ""),
			os.getenv("IMAGE_BASE_URL", ""),
			os.getenv("IMAGE_MODEL", ""),
			os.getenv("HUNYUAN_SECRET_KEY", "")
		)

