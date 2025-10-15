"""Config功能模块"""

from tkinter import messagebox, filedialog
import tkinter as tk
import json
from pathlib import Path


class PresetManagerMixin:
	"""Config preset_manager 功能"""
	
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
			
			# 设置API类型（根据预设的provider字段）
			provider = preset.get("provider", "openai")
			if hasattr(self, 'img_api_type'):
				self.img_api_type.set(provider)
				print(f"🔧 已设置图片API类型为: {provider} (预设: {preset_name})")
			
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
	

	