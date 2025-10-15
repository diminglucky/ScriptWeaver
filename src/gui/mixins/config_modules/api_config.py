"""Config功能模块"""

from tkinter import messagebox, filedialog, END
import tkinter as tk
import json
import os
from pathlib import Path
from dotenv import find_dotenv, set_key, load_dotenv
from src.utils.text import sanitize as _sanitize, try_image_api as _try_image


class APIConfigMixin:
	"""Config api_config 功能"""
	
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
				
				# 设置API类型（根据预设的provider字段）
				provider = preset_config.get("provider", "openai")
				if hasattr(self, 'img_api_type'):
					self.img_api_type.set(provider)
					print(f"🔧 启动时已设置图片API类型为: {provider} (预设: {last_preset})")
				
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
			
			# 加载辅助功能API配置
			shot_api = os.getenv("ASSIST_SHOT_GEN_API", "DeepSeek")
			if hasattr(self, 'shot_gen_api'):
				self.shot_gen_api.set(shot_api)
			
			desc_api = os.getenv("ASSIST_DESC_GEN_API", "DeepSeek")
			if hasattr(self, 'desc_gen_api'):
				self.desc_gen_api.set(desc_api)
		except Exception as e:
			print(f"加载图片API配置时出错: {e}")
			
			# 更新辅助功能API下拉框的选项（从story api_presets）
			if hasattr(self, 'api_presets') and hasattr(self, 'combo_shot_gen_api'):
				api_list = list(self.api_presets.keys())
				self.combo_shot_gen_api['values'] = api_list
				self.combo_desc_gen_api['values'] = api_list
			
			# 加载故事创作功能API配置
			outline_api = os.getenv("STORY_OUTLINE_GEN_API", "DeepSeek")
			if hasattr(self, 'outline_gen_api'):
				self.outline_gen_api.set(outline_api)
			
			story_api = os.getenv("STORY_STORY_GEN_API", "DeepSeek")
			if hasattr(self, 'story_gen_api'):
				self.story_gen_api.set(story_api)
			
			# 更新故事创作功能API下拉框的选项
			if hasattr(self, 'api_presets') and hasattr(self, 'combo_outline_gen_api'):
				api_list = list(self.api_presets.keys())
				self.combo_outline_gen_api['values'] = api_list
				self.combo_story_gen_api['values'] = api_list
			
			print(f"已自动加载图片API配置: {last_preset or 'OpenAI (DALL-E)'}")
		except Exception as e:
			print(f"加载图片API配置失败: {e}")
	
	
	def _save_assist_api_config(self) -> None:
		"""保存辅助功能API配置（分镜头生成和图片描述生成）"""
		try:
			env_path_str = find_dotenv(usecwd=True)
			if not env_path_str:
				env_path = Path.cwd() / ".env"
			else:
				env_path = Path(env_path_str)
			env_path.touch(exist_ok=True)
			
			# 保存分镜头生成API
			if hasattr(self, 'shot_gen_api'):
				set_key(str(env_path), "ASSIST_SHOT_GEN_API", self.shot_gen_api.get())
			
			# 保存图片描述生成API
			if hasattr(self, 'desc_gen_api'):
				set_key(str(env_path), "ASSIST_DESC_GEN_API", self.desc_gen_api.get())
			
			load_dotenv(override=True)
			messagebox.showinfo("成功", f"已保存辅助功能API配置\n\n分镜头生成: {self.shot_gen_api.get()}\n图片描述生成: {self.desc_gen_api.get()}")
		except Exception as e:
			messagebox.showerror("错误", f"保存配置失败: {str(e)}")
	
	
	def on_test_image_api(self) -> None:
		"""测试图片生成API"""
		try:
			self.set_busy(True)
			self.status.set("测试图片生成 API 中...")
			
			# 确保使用图片配置页面的日志框（如果不存在则提示用户）
			if not hasattr(self, 'img_test_log'):
				messagebox.showwarning(
					"提示", 
					"请先切换到【图片生成 → 配置】标签页，\n"
					"以便在该页面查看详细的测试日志。\n\n"
					"点击确定后将在故事生成页面显示简要日志。"
				)
				log_widget = self.output
			else:
				log_widget = self.img_test_log
				# 清空之前的日志
				self.img_test_log.delete("1.0", END)
				import datetime
				timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
				self.img_test_log.insert(END, f"[{timestamp}] 开始测试图片生成API...\n")
			
			# 检查API类型
			api_type = self.img_api_type.get() if hasattr(self, 'img_api_type') else "openai"
			log_widget.insert(END, f"  • API类型: {api_type}\n")
			
			# 根据API类型进行不同的测试
			if api_type == "hunyuan":
				# 腾讯混元API测试
				self._test_hunyuan_api(log_widget)
			else:
				# OpenAI兼容API测试
				self._test_openai_compatible_api(log_widget)
				
		except Exception as e:
			import traceback
			# 使用已经确定的 log_widget，如果不存在则使用 output
			if 'log_widget' not in locals():
				log_widget = getattr(self, 'img_test_log', self.output)
			error_trace = traceback.format_exc()
			log_widget.insert(END, "\n" + "="*60 + "\n")
			log_widget.insert(END, "💥 图片API测试异常\n")
			log_widget.insert(END, "="*60 + "\n")
			log_widget.insert(END, error_trace + "\n")
			
			error_location = "配置页面的测试日志" if hasattr(self, 'img_test_log') and log_widget == self.img_test_log else "故事生成页面的输出日志"
			messagebox.showerror("API 错误", f"测试时发生异常:\n{str(e)}\n\n详情见{error_location}。")
			self.status.set("图片API测试失败")
		finally:
			self.set_busy(False)
	
	
	def _test_hunyuan_api(self, log_widget) -> None:
		"""测试腾讯混元API"""
		secret_id = _sanitize(self.img_api_key.get())
		secret_key = _sanitize(self.img_secret_key.get()) if hasattr(self, 'img_secret_key') else ""
		
		if not secret_id:
			messagebox.showwarning("警告", "请先填写SecretId (API Key)")
			self.status.set("测试失败：缺少SecretId")
			log_widget.insert(END, "❌ 错误: 缺少SecretId\n")
			return
		
		if not secret_key:
			messagebox.showwarning("警告", "请先填写SecretKey")
			self.status.set("测试失败：缺少SecretKey")
			log_widget.insert(END, "❌ 错误: 缺少SecretKey\n")
			return
		
		# 记录测试参数
		log_widget.insert(END, f"\n📋 腾讯混元测试参数:\n")
		log_widget.insert(END, f"  • SecretId: {'*' * (len(secret_id)-8) + secret_id[-8:] if len(secret_id) > 8 else '***'}\n")
		log_widget.insert(END, f"  • SecretKey: {'*' * 20}\n")
		log_widget.insert(END, f"\n🔍 测试腾讯混元图片生成API...\n")
		log_widget.update()
		
		try:
			from src.clients.hunyuan_image_client import HunyuanImageClient
			
			log_widget.insert(END, "  • 创建HunyuanImageClient...\n")
			client = HunyuanImageClient(secret_id=secret_id, secret_key=secret_key)
			
			log_widget.insert(END, "  • 发送测试请求（生成简单测试图片）...\n")
			log_widget.update()
			
			# 使用简单的提示词测试
			result = client.generate(prompt="a simple test image", resolution="1024:1024")
			
			if result and hasattr(result, 'image'):
				log_widget.insert(END, f"✅ 成功生成测试图片！\n")
				log_widget.insert(END, f"  • 图片尺寸: {result.image.size}\n")
				log_widget.insert(END, f"  • 提供商: {result.provider}\n")
				log_widget.insert(END, f"  • 模型: {result.model}\n")
				messagebox.showinfo("测试成功", "腾讯混元图片API可用！\n\n已成功生成测试图片。\n\n注意：已消耗少量API配额。")
				self.status.set("腾讯混元API可用")
			else:
				raise RuntimeError("API返回空结果或格式错误")
				
		except Exception as e:
			error_msg = str(e)
			log_widget.insert(END, f"❌ 测试失败: {error_msg}\n")
			log_widget.insert(END, "\n💡 可能的原因:\n")
			log_widget.insert(END, "  1. SecretId或SecretKey错误\n")
			log_widget.insert(END, "  2. 账户余额不足\n")
			log_widget.insert(END, "  3. 网络连接问题\n")
			log_widget.insert(END, "  4. API权限未开通\n")
			messagebox.showerror("API 错误", f"腾讯混元API测试失败\n\n{error_msg}\n\n详情见测试日志。")
			self.status.set("腾讯混元API测试失败")
	
	
	def _test_openai_compatible_api(self, log_widget) -> None:
		"""测试OpenAI兼容API"""
		key = _sanitize(self.img_api_key.get())
		base = _sanitize(self.img_base_url.get())
		model = _sanitize(self.img_model.get()) or "dall-e-3"
		
		if not key:
			messagebox.showwarning("警告", "请先填写API Key")
			self.status.set("测试失败：缺少API Key")
			log_widget.insert(END, "❌ 错误: 缺少API Key\n")
			return
		
		if not base:
			messagebox.showwarning("警告", "请先填写Base URL")
			self.status.set("测试失败：缺少Base URL")
			log_widget.insert(END, "❌ 错误: 缺少Base URL\n")
			return
		
		# 记录测试参数
		log_widget.insert(END, f"\n📋 测试参数:\n")
		log_widget.insert(END, f"  • Model: {model}\n")
		log_widget.insert(END, f"  • API Key: {'*' * (len(key)-8) + key[-8:] if len(key) > 8 else '***'}\n")
		
		candidates = []
		# try user-provided
		candidates.append(base.rstrip("/"))
		# also try toggling /v1 suffix
		if base.rstrip("/").endswith("/v1"):
			candidates.append(base.rstrip("/")[:-3])
		else:
			candidates.append(base.rstrip("/") + "/v1")
		
		log_widget.insert(END, f"\n🔍 尝试的Base URL:\n")
		
		tried_msgs: list[str] = []
		for i, b in enumerate(candidates, 1):
			log_widget.insert(END, f"\n[{i}/{len(candidates)}] 测试: {b}\n")
			log_widget.update()
			
			ok, msg = _try_image(key, b, model)
			tried_msgs.append(f"base_url={b} -> {'SUCCESS' if ok else 'FAIL'}: {msg}")
			
			if ok:
				log_widget.insert(END, f"✅ 成功: {msg}\n")
			else:
				log_widget.insert(END, f"❌ 失败: {msg}\n")
			
			if ok:
				self.img_base_url.set(b)
				log_widget.insert(END, f"\n🎉 测试成功！已自动更新Base URL为: {b}\n")
				messagebox.showinfo("测试成功", f"图片生成 API 可用\n{b}\n\n{msg}\n\n注意：实际生成了一张测试图片，可能会消耗少量费用")
				self.status.set("图片API可用")
				return
		
		# all failed
		full_msg = "\n".join(tried_msgs)
		log_widget.insert(END, "\n" + "="*60 + "\n")
		log_widget.insert(END, "❌ 图片API测试失败（已尝试所有可能的base_url）\n")
		log_widget.insert(END, "="*60 + "\n")
		log_widget.insert(END, full_msg + "\n")
		log_widget.insert(END, "\n💡 可能的原因:\n")
		log_widget.insert(END, "  1. API密钥错误或已过期\n")
		log_widget.insert(END, "  2. 账户余额不足\n")
		log_widget.insert(END, "  3. Base URL不正确\n")
		log_widget.insert(END, "  4. 网络连接问题\n")
		log_widget.insert(END, "  5. 模型名称不支持\n")
		log_widget.insert(END, "\n建议操作:\n")
		log_widget.insert(END, "  • 检查API密钥是否正确\n")
		log_widget.insert(END, "  • 登录服务商网站查看账户余额\n")
		log_widget.insert(END, "  • 确认Base URL格式正确\n")
		messagebox.showerror("API 错误", "图片API鉴权失败，请检查密钥/额度/网络/模型。\n详情见配置页面的测试日志。")
		self.status.set("图片API测试失败")

	
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
	
	