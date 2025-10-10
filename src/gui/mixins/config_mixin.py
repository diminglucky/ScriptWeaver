"""
Config相关功能模块
"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, messagebox, filedialog
import tkinter as tk
from tkinter import ttk


class ConfigMixin:
	"""Config管理功能"""
	
	def save_api_config(self) -> None:
		"""保存故事API配置，每个预设保存各自的API Key"""
		try:
			# Determine .env path
			env_path_str = find_dotenv(usecwd=True)
			if not env_path_str:
				env_path = Path.cwd() / ".env"
			else:
				env_path = Path(env_path_str)
			env_path.touch(exist_ok=True)
			
			# 获取当前预设
			current_preset = self.api_preset.get().strip()
			# 将中文和特殊字符转换为安全的环境变量名
			import hashlib
			# 对于中文或特殊字符，使用哈希值
			if any(ord(c) > 127 for c in current_preset):
				# 包含非ASCII字符，使用短哈希
				hash_suffix = hashlib.md5(current_preset.encode()).hexdigest()[:8]
				safe_preset_name = f"CUSTOM_{hash_suffix}"
			else:
				safe_preset_name = current_preset.replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")
			
			# 保存当前预设的配置到预设字典
			if current_preset in self.api_presets:
				self.api_presets[current_preset]["key"] = self.api_key.get().strip()
				self.api_presets[current_preset]["base_url"] = self.base_url.get().strip()
				self.api_presets[current_preset]["model"] = self.model.get().strip()
			
			# 保存到.env文件（使用安全的环境变量名）
			set_key(str(env_path), f"STORY_{safe_preset_name}_KEY", self.api_key.get().strip())
			set_key(str(env_path), f"STORY_{safe_preset_name}_BASE_URL", self.base_url.get().strip())
			set_key(str(env_path), f"STORY_{safe_preset_name}_MODEL", self.model.get().strip())
			set_key(str(env_path), "API_PRESET", current_preset)
			
			load_dotenv(override=True)
			messagebox.showinfo("成功", f"已保存 {current_preset} 的配置到: {env_path}")
		except Exception as e:
			messagebox.showerror("错误", str(e))

	def load_api_config(self) -> None:
		try:
			load_dotenv(override=True)
			self.api_key.set(os.getenv("DEEPSEEK_API_KEY", ""))
			self.base_url.set(os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"))
			self.model.set(os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
			preset = os.getenv("API_PRESET", "DeepSeek")
			if preset in self.api_presets:
				self.api_preset.set(preset)
			messagebox.showinfo("成功", "已从 .env 加载配置")
		except Exception as e:
			messagebox.showerror("错误", str(e))
	
	def _auto_load_api_config(self) -> None:
		"""启动时自动加载所有预设的API配置"""
		try:
			load_dotenv(override=True)
			import hashlib
			
			# 加载所有预设的API配置
			for preset_name in self.api_presets.keys():
				# 生成安全的环境变量名（与保存时保持一致）
				if any(ord(c) > 127 for c in preset_name):
					hash_suffix = hashlib.md5(preset_name.encode()).hexdigest()[:8]
					safe_preset_name = f"CUSTOM_{hash_suffix}"
				else:
					safe_preset_name = preset_name.replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")
				
				# 加载该预设的配置
				key = os.getenv(f"STORY_{safe_preset_name}_KEY")
				if key:
					self.api_presets[preset_name]["key"] = key
				
				base_url = os.getenv(f"STORY_{safe_preset_name}_BASE_URL")
				if base_url:
					self.api_presets[preset_name]["base_url"] = base_url
				
				model = os.getenv(f"STORY_{safe_preset_name}_MODEL")
				if model:
					self.api_presets[preset_name]["model"] = model
			
			# 加载上次使用的预设
			preset = os.getenv("API_PRESET", "DeepSeek")
			# 如果preset不在现有列表中，添加它（可能是自定义的）
			if preset not in self.api_presets and preset:
				# 生成安全名称并加载配置
				if any(ord(c) > 127 for c in preset):
					hash_suffix = hashlib.md5(preset.encode()).hexdigest()[:8]
					safe_preset_name = f"CUSTOM_{hash_suffix}"
				else:
					safe_preset_name = preset.replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")
				
				key = os.getenv(f"STORY_{safe_preset_name}_KEY", "")
				base_url = os.getenv(f"STORY_{safe_preset_name}_BASE_URL", "")
				model = os.getenv(f"STORY_{safe_preset_name}_MODEL", "")
				
				self.api_presets[preset] = {
					"key": key,
					"base_url": base_url,
					"model": model
				}
			
			if preset in self.api_presets:
				self.api_preset.set(preset)
				# 自动填充该预设的配置
				preset_config = self.api_presets[preset]
				self.api_key.set(preset_config.get("key", ""))
				self.base_url.set(preset_config.get("base_url", ""))
				self.model.set(preset_config.get("model", ""))
			
			if hasattr(self, 'status'):
				self.status.set(f"已自动加载配置: {preset}")
		except Exception as e:
			print(f"加载配置失败: {e}")
			pass  # 静默失败，使用默认值

	def save_img_api_config(self) -> None:
		"""保存图片API配置（公开方法，供按钮调用）"""
		self._save_image_api_config()
	
	def load_img_api_config(self) -> None:
		"""加载图片API配置（公开方法，供按钮调用）"""
		try:
			load_dotenv(override=True)
			# 加载上次使用的预设
			last_preset = os.getenv("IMG_API_PRESET", "OpenAI (DALL-E)")
			if last_preset in self.img_api_presets:
				self.img_api_preset.set(last_preset)
				self._on_img_api_preset_selected(None)
			
			# 加载图片尺寸
			img_size = os.getenv("IMG_SIZE", "1024x1024")
			self.img_size.set(img_size)
			
			messagebox.showinfo("成功", "已从 .env 加载图片API配置")
		except Exception as e:
			messagebox.showerror("错误", str(e))
	
	def _auto_load_image_api_config(self) -> None:
		"""自动加载所有预设的图片API配置"""
		try:
			load_dotenv()
			
			# 加载所有预设的API配置
			for preset_name in self.img_api_presets.keys():
				safe_preset_name = preset_name.replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")
				
				# 加载该预设的API Key
				key = os.getenv(f"IMG_{safe_preset_name}_KEY")
				if key:
					self.img_api_presets[preset_name]["key"] = key
				
				# 加载该预设的Base URL
				base_url = os.getenv(f"IMG_{safe_preset_name}_BASE_URL")
				if base_url:
					self.img_api_presets[preset_name]["base_url"] = base_url
				
				# 加载该预设的Model
				model = os.getenv(f"IMG_{safe_preset_name}_MODEL")
				if model:
					self.img_api_presets[preset_name]["model"] = model
				
				# 加载该预设的SecretKey（仅腾讯混元）
				if preset_name == "腾讯混元":
					secret_key = os.getenv(f"IMG_{safe_preset_name}_SECRET_KEY")
					if secret_key:
						self.img_api_presets[preset_name]["secret_key"] = secret_key
			
			# 加载上次使用的预设
			last_preset = os.getenv("IMG_API_PRESET")
			if last_preset and last_preset in self.img_api_presets:
				self.img_api_preset.set(last_preset)
				# 自动填充该预设的配置
				preset_config = self.img_api_presets[last_preset]
				if preset_config.get("key"):
					self.img_api_key.set(preset_config["key"])
				if preset_config.get("base_url"):
					self.img_base_url.set(preset_config["base_url"])
				if preset_config.get("model"):
					self.img_model.set(preset_config["model"])
				# 填充SecretKey（仅腾讯混元）
				if preset_config.get("secret_key"):
					self.img_secret_key.set(preset_config["secret_key"])
			
			# 加载尺寸
			size = os.getenv("IMG_SIZE")
			if size:
				self.img_size.set(size)
			
			print(f"已自动加载图片API配置: {last_preset or 'OpenAI (DALL-E)'}")
		except Exception as e:
			print(f"加载图片API配置失败: {e}")
	
	def on_test_api(self) -> None:
		try:
			self.set_busy(True)
			self.status.set("测试 API 中...")
			key = _sanitize(self.api_key.get())
			base = _sanitize(self.base_url.get())
			model = _sanitize(self.model.get()) or "deepseek-chat"
			candidates = []
			# try user-provided
			candidates.append(base.rstrip("/"))
			# also try toggling /v1 suffix
			if base.rstrip("/").endswith("/v1"):
				candidates.append(base.rstrip("/")[:-3])
			else:
				candidates.append(base.rstrip("/") + "/v1")
			tried_msgs: list[str] = []
			for b in candidates:
				ok, msg = _try_chat(key, b, model)
				tried_msgs.append(f"base_url={b} -> {'SUCCESS' if ok else 'FAIL'}: {msg}")
				if ok:
					self.base_url.set(b)
					messagebox.showinfo("测试成功", f"API 可用\n{b}")
					self.status.set("API 可用")
					return
			# all failed
			full_msg = "\n".join(tried_msgs)
			self.output.insert(END, "API 测试失败（已尝试多种 base_url）:\n" + full_msg + "\n")
			messagebox.showerror("API 错误", "鉴权失败，请检查密钥/额度/网络/模型。详情见下方输出日志。")
			self.status.set("API 测试失败")
		except Exception as e:
			import traceback
			self.output.insert(END, "API 测试异常:\n" + traceback.format_exc() + "\n")
			messagebox.showerror("API 错误", str(e))
			self.status.set("API 测试失败")
		finally:
			self.set_busy(False)

	def on_test_image_api(self) -> None:
		"""测试图片生成API"""
		try:
			self.set_busy(True)
			self.status.set("测试图片生成 API 中...")
			
			key = _sanitize(self.img_api_key.get())
			base = _sanitize(self.img_base_url.get())
			model = _sanitize(self.img_model.get()) or "dall-e-3"
			
			if not key:
				messagebox.showwarning("警告", "请先填写API Key")
				self.status.set("测试失败：缺少API Key")
				return
			
			if not base:
				messagebox.showwarning("警告", "请先填写Base URL")
				self.status.set("测试失败：缺少Base URL")
				return
			
			candidates = []
			# try user-provided
			candidates.append(base.rstrip("/"))
			# also try toggling /v1 suffix
			if base.rstrip("/").endswith("/v1"):
				candidates.append(base.rstrip("/")[:-3])
			else:
				candidates.append(base.rstrip("/") + "/v1")
			
			tried_msgs: list[str] = []
			for b in candidates:
				ok, msg = _try_image(key, b, model)
				tried_msgs.append(f"base_url={b} -> {'SUCCESS' if ok else 'FAIL'}: {msg}")
				if ok:
					self.img_base_url.set(b)
					messagebox.showinfo("测试成功", f"图片生成 API 可用\n{b}\n\n注意：实际生成了一张测试图片，可能会消耗少量费用")
					self.status.set("图片API可用")
					return
			
			# all failed
			full_msg = "\n".join(tried_msgs)
			self.output.insert(END, "图片API测试失败（已尝试多种 base_url）:\n" + full_msg + "\n")
			messagebox.showerror("API 错误", "图片API鉴权失败，请检查密钥/额度/网络/模型。详情见下方输出日志。")
			self.status.set("图片API测试失败")
		except Exception as e:
			import traceback
			self.output.insert(END, "图片API测试异常:\n" + traceback.format_exc() + "\n")
			messagebox.showerror("API 错误", str(e))
			self.status.set("图片API测试失败")
		finally:
			self.set_busy(False)

	def _on_api_preset_selected(self, event=None) -> None:
		"""当选择API预设时，自动填充配置（包括已保存的API Key）"""
		preset_name = self.api_preset.get()
		if preset_name in self.api_presets:
			preset = self.api_presets[preset_name]
			
			# 填充Base URL（如果预设有配置或已保存）
			if preset.get("base_url"):
				self.base_url.set(preset["base_url"])
			
			# 填充Model（如果预设有配置或已保存）
			if preset.get("model"):
				self.model.set(preset["model"])
			
			# 填充API Key（如果已保存）
			if preset.get("key"):
				self.api_key.set(preset["key"])
			
			if hasattr(self, 'status'):
				self.status.set(f"已选择 {preset_name} API预设")
	
	def _on_img_api_preset_selected(self, event=None) -> None:
		"""当选择图片API预设时，自动填充配置（包括已保存的API Key）"""
		preset_name = self.img_api_preset.get()
		if preset_name in self.img_api_presets:
			preset = self.img_api_presets[preset_name]
			
			# 填充Base URL（如果预设有配置或已保存）
			if preset.get("base_url"):
				self.img_base_url.set(preset["base_url"])
			
			# 填充Model（如果预设有配置或已保存）
			if preset.get("model"):
				self.img_model.set(preset["model"])
			
			# 填充API Key（如果已保存）
			if preset.get("key"):
				self.img_api_key.set(preset["key"])
			
			# 填充SecretKey（仅腾讯混元）
			if preset.get("secret_key"):
				self.img_secret_key.set(preset["secret_key"])
			else:
				self.img_secret_key.set("")  # 清空SecretKey字段
	
	def _save_image_api_config(self) -> None:
		"""保存图片API配置到.env文件，包括当前预设的API Key"""
		try:
			load_dotenv()
			env_path = Path(".env")
			
			# 读取现有配置
			if env_path.exists():
				with open(env_path, 'r', encoding='utf-8') as f:
					lines = f.readlines()
			else:
				lines = []
			
			# 获取当前预设名称，用于保存该预设的API Key
			current_preset = self.img_api_preset.get()
			# 将预设名称转换为安全的环境变量名（移除特殊字符和空格）
			safe_preset_name = current_preset.replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")
			
			# 保存当前预设的API配置到预设字典中
			if current_preset in self.img_api_presets:
				self.img_api_presets[current_preset]["key"] = self.img_api_key.get()
				self.img_api_presets[current_preset]["base_url"] = self.img_base_url.get()
				self.img_api_presets[current_preset]["model"] = self.img_model.get()
				# 保存SecretKey（仅腾讯混元）
				if current_preset == "腾讯混元":
					self.img_api_presets[current_preset]["secret_key"] = self.img_secret_key.get()
			
			# 准备要保存的配置
			config_keys = {
				'IMG_API_PRESET': current_preset,
				'IMG_SIZE': self.img_size.get(),
				f'IMG_{safe_preset_name}_KEY': self.img_api_key.get(),
				f'IMG_{safe_preset_name}_BASE_URL': self.img_base_url.get(),
				f'IMG_{safe_preset_name}_MODEL': self.img_model.get()
			}
			
			# 如果是腾讯混元，还要保存SecretKey
			if current_preset == "腾讯混元":
				config_keys[f'IMG_{safe_preset_name}_SECRET_KEY'] = self.img_secret_key.get()
			
			# 更新配置
			new_lines = []
			keys_found = set()
			
			for line in lines:
				stripped_line = line.strip()
				if not stripped_line or stripped_line.startswith('#'):
					new_lines.append(line)
					continue
				
				if '=' in line:
					key = line.split('=')[0].strip()
					if key in config_keys:
						new_lines.append(f"{key}={config_keys[key]}\n")
						keys_found.add(key)
					else:
						new_lines.append(line)
				else:
					new_lines.append(line)
			
			# 添加未找到的配置
			for key, value in config_keys.items():
				if key not in keys_found:
					new_lines.append(f"{key}={value}\n")
			
			# 写入文件
			with open(env_path, 'w', encoding='utf-8') as f:
				f.writelines(new_lines)
			
			messagebox.showinfo("成功", f"已保存 {current_preset} 的API配置")
			self.status.set(f"已保存 {current_preset} 的API配置")
		except Exception as e:
			messagebox.showerror("错误", f"保存失败: {str(e)}")
	
	def _load_custom_presets(self) -> None:
		"""加载用户自定义的API预设"""
		custom_presets_file = Path("custom_api_presets.json")
		if custom_presets_file.exists():
			try:
				import json
				with open(custom_presets_file, 'r', encoding='utf-8') as f:
					custom_presets = json.load(f)
					self.api_presets.update(custom_presets)
			except Exception:
				pass  # 加载失败则跳过
	
	def _save_custom_preset(self) -> None:
		"""保存当前配置为自定义预设"""
		from tkinter import simpledialog
		preset_name = simpledialog.askstring(
			"保存自定义预设",
			"请输入预设名称（例如：我的DeepSeek、公司API等）：",
			parent=self
		)
		
		if not preset_name:
			return
		
		# 检查是否覆盖内置预设
		built_in_presets = ["DeepSeek", "OpenAI", "Azure OpenAI", "Moonshot (月之暗面)", 
						"智谱AI (GLM)", "百度文心", "阿里通义", "自定义"]
		if preset_name in built_in_presets:
			messagebox.showwarning("警告", "不能覆盖内置预设，请使用其他名称")
			return
		
		# 保存当前配置
		self.api_presets[preset_name] = {
			"base_url": self.base_url.get(),
			"model": self.model.get(),
			"key": self.api_key.get()
		}
		
		# 保存到文件
		try:
			import json
			custom_presets_file = Path("custom_api_presets.json")
			# 只保存自定义预设，不保存内置的
			custom_presets = {k: v for k, v in self.api_presets.items() if k not in built_in_presets}
			with open(custom_presets_file, 'w', encoding='utf-8') as f:
				json.dump(custom_presets, f, ensure_ascii=False, indent=2)
			
			# 更新下拉框
			self.combo_api_preset['values'] = list(self.api_presets.keys())
			self.api_preset.set(preset_name)
			
			messagebox.showinfo("成功", f"已保存自定义预设: {preset_name}")
			if hasattr(self, 'status'):
				self.status.set(f"已保存自定义预设: {preset_name}")
		except Exception as e:
			messagebox.showerror("错误", f"保存失败: {str(e)}")
	
	def _delete_custom_preset(self) -> None:
		"""删除自定义API预设"""
		current_preset = self.api_preset.get()
		
		# 检查是否是内置预设
		built_in_presets = ["DeepSeek", "OpenAI", "Azure OpenAI", "Moonshot (月之暗面)", 
						"智谱AI (GLM)", "百度文心", "阿里通义", "自定义"]
		
		if current_preset in built_in_presets:
			messagebox.showwarning("无法删除", "不能删除内置预设，只能删除自定义预设")
			return
		
		if not current_preset:
			messagebox.showwarning("提示", "请先选择要删除的自定义预设")
			return
		
		# 确认删除
		result = messagebox.askyesno("确认删除", f"确定要删除自定义预设 '{current_preset}' 吗？")
		if not result:
			return
		
		try:
			import json
			# 从内存中删除
			if current_preset in self.api_presets:
				del self.api_presets[current_preset]
			
			# 更新文件
			custom_presets_file = Path("custom_api_presets.json")
			custom_presets = {k: v for k, v in self.api_presets.items() if k not in built_in_presets}
			
			if custom_presets:
				with open(custom_presets_file, 'w', encoding='utf-8') as f:
					json.dump(custom_presets, f, ensure_ascii=False, indent=2)
			else:
				# 如果没有自定义预设了，删除文件
				if custom_presets_file.exists():
					custom_presets_file.unlink()
			
			# 更新下拉框
			self.combo_api_preset['values'] = list(self.api_presets.keys())
			# 切换到自定义预设
			self.api_preset.set("自定义")
			self._on_api_preset_selected(None)
			
			messagebox.showinfo("成功", f"已删除自定义预设: {current_preset}")
			if hasattr(self, 'status'):
				self.status.set(f"已删除自定义预设: {current_preset}")
		except Exception as e:
			messagebox.showerror("错误", f"删除失败: {str(e)}")
	
	def _load_custom_image_presets(self) -> None:
		"""加载用户自定义的图片API预设"""
		custom_presets_file = Path("custom_image_api_presets.json")
		if custom_presets_file.exists():
			try:
				import json
				with open(custom_presets_file, 'r', encoding='utf-8') as f:
					custom_presets = json.load(f)
					self.img_api_presets.update(custom_presets)
			except Exception:
				pass  # 加载失败则跳过
	
	def _save_custom_image_preset(self) -> None:
		"""保存当前图片API配置为自定义预设"""
		from tkinter import simpledialog
		preset_name = simpledialog.askstring(
			"保存自定义图片API预设",
			"请输入预设名称（例如：我的DALL-E、公司图片API等）：",
			parent=self
		)
		
		if not preset_name:
			return
		
		# 检查是否覆盖内置预设
		built_in_presets = ["OpenAI (DALL-E)", "腾讯混元", "Azure OpenAI", "Stability AI", "Midjourney API", "自定义"]
		if preset_name in built_in_presets:
			messagebox.showwarning("警告", "不能覆盖内置预设，请使用其他名称")
			return
		
		# 保存当前配置
		self.img_api_presets[preset_name] = {
			"base_url": self.img_base_url.get(),
			"model": self.img_model.get(),
			"key": self.img_api_key.get()
		}
		
		# 保存到文件
		try:
			import json
			custom_presets_file = Path("custom_image_api_presets.json")
			# 只保存自定义预设，不保存内置的
			custom_presets = {k: v for k, v in self.img_api_presets.items() if k not in built_in_presets}
			with open(custom_presets_file, 'w', encoding='utf-8') as f:
				json.dump(custom_presets, f, ensure_ascii=False, indent=2)
			
			# 更新下拉框
			self.combo_img_api_preset['values'] = list(self.img_api_presets.keys())
			self.img_api_preset.set(preset_name)
			
			messagebox.showinfo("成功", f"已保存自定义图片API预设: {preset_name}")
		except Exception as e:
			messagebox.showerror("错误", f"保存失败: {str(e)}")
	
	def _delete_custom_image_preset(self) -> None:
		"""删除自定义图片API预设"""
		current_preset = self.img_api_preset.get()
		
		# 检查是否是内置预设
		built_in_presets = ["OpenAI (DALL-E)", "腾讯混元", "Azure OpenAI", "Stability AI", "Midjourney API", "自定义"]
		
		if current_preset in built_in_presets:
			messagebox.showwarning("无法删除", "不能删除内置预设，只能删除自定义预设")
			return
		
		if not current_preset:
			messagebox.showwarning("提示", "请先选择要删除的自定义预设")
			return
		
		# 确认删除
		result = messagebox.askyesno("确认删除", f"确定要删除自定义图片API预设 '{current_preset}' 吗？")
		if not result:
			return
		
		try:
			import json
			# 从内存中删除
			if current_preset in self.img_api_presets:
				del self.img_api_presets[current_preset]
			
			# 更新文件
			custom_presets_file = Path("custom_image_api_presets.json")
			custom_presets = {k: v for k, v in self.img_api_presets.items() if k not in built_in_presets}
			
			if custom_presets:
				with open(custom_presets_file, 'w', encoding='utf-8') as f:
					json.dump(custom_presets, f, ensure_ascii=False, indent=2)
			else:
				# 如果没有自定义预设了，删除文件
				if custom_presets_file.exists():
					custom_presets_file.unlink()
			
			# 更新下拉框
			self.combo_img_api_preset['values'] = list(self.img_api_presets.keys())
			# 切换到自定义预设
			self.img_api_preset.set("自定义")
			self._on_img_api_preset_selected(None)
			
			messagebox.showinfo("成功", f"已删除自定义图片API预设: {current_preset}")
		except Exception as e:
			messagebox.showerror("错误", f"删除失败: {str(e)}")
	

