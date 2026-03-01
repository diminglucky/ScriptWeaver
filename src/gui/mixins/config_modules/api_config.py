"""Config功能模块"""

from tkinter import messagebox, filedialog, END
import tkinter as tk
import json
import os
import re
import threading
import hashlib
from pathlib import Path
import logging


logger = logging.getLogger(__name__)


def _safe_preset_env_name(preset_name: str) -> str:
	text = str(preset_name or "").strip()
	if not text:
		return "CUSTOM_DEFAULT"
	if any(ord(c) > 127 for c in text):
		hash_suffix = hashlib.md5(text.encode("utf-8")).hexdigest()[:8]
		return f"CUSTOM_{hash_suffix}"
	return text.replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")


def _legacy_image_preset_env_name(preset_name: str) -> str:
	return str(preset_name or "").replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")


def _first_non_empty_env(keys: list[str]) -> str:
	for key in keys:
		value = (os.getenv(key, "") or "").strip()
		if value:
			return value
	return ""


def _dotenv_escape(value: str) -> str:
	value = str(value)
	if any(ch.isspace() for ch in value) or any(ch in value for ch in ['#', '"']):
		return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
	return value


def _fallback_set_key(dotenv_path: str, key_to_set: str, value_to_set: str) -> bool:
	try:
		path = Path(dotenv_path)
		path.parent.mkdir(parents=True, exist_ok=True)
		if path.exists():
			lines = path.read_text(encoding="utf-8").splitlines()
		else:
			lines = []
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
	from dotenv import find_dotenv, set_key, load_dotenv
	DOTENV_AVAILABLE = True
except Exception as e:  # pragma: no cover - fallback for minimal environments
	DOTENV_AVAILABLE = False
	logger.debug("python-dotenv unavailable, using fallback .env writer: %s", e)

	def find_dotenv(*args, **kwargs):
		return ""

	def set_key(dotenv_path, key_to_set, value_to_set, *args, **kwargs):
		return _fallback_set_key(dotenv_path, key_to_set, value_to_set)

	def load_dotenv(*args, **kwargs):
		return False
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
			safe_preset_name = _safe_preset_env_name(current_preset)
			
			# 保存当前预设的配置到预设字典
			if current_preset in self.api_presets:
				self.api_presets[current_preset]["key"] = self.api_key.get().strip()
				self.api_presets[current_preset]["base_url"] = self.base_url.get().strip()
				self.api_presets[current_preset]["model"] = self.model.get().strip()
			
			# 保存到.env文件（使用安全的环境变量名）
			ok_results = [
				set_key(str(env_path), f"STORY_{safe_preset_name}_KEY", self.api_key.get().strip()),
				set_key(str(env_path), f"STORY_{safe_preset_name}_BASE_URL", self.base_url.get().strip()),
				set_key(str(env_path), f"STORY_{safe_preset_name}_MODEL", self.model.get().strip()),
				set_key(str(env_path), "API_PRESET", current_preset),
			]
			
			load_dotenv(override=True)
			if all(bool(x) for x in ok_results):
				messagebox.showinfo("成功", f"已保存 {current_preset} 的配置到: {env_path}")
			else:
				messagebox.showwarning("警告", f"配置文件可能未完整写入: {env_path}")
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
			# 加载所有预设的API配置
			for preset_name in self.api_presets.keys():
				# 生成安全的环境变量名（与保存时保持一致）
				safe_preset_name = _safe_preset_env_name(preset_name)
				
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
				safe_preset_name = _safe_preset_env_name(preset)
				
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

			# 同步加载图片API相关配置，避免重启后图片配置丢失
			if hasattr(self, "_auto_load_image_api_config"):
				self._auto_load_image_api_config()
			
			if hasattr(self, 'status'):
				self.status.set(f"已自动加载配置: {preset}")
		except Exception as e:
			logger.warning("Failed to load API config from .env: %s", e)
			pass  # 静默失败，使用默认值

	
	def save_img_api_config(self) -> None:
		"""保存图片API配置（公开方法，供按钮调用）"""
		if hasattr(self, "_save_img_api_settings"):
			self._save_img_api_settings()
			return
		self._save_image_api_config()
	
	
	def load_img_api_config(self) -> None:
		"""加载图片API配置（公开方法，供按钮调用）"""
		if hasattr(self, "_load_quick_api_switch"):
			self._load_quick_api_switch()
			messagebox.showinfo("成功", "已加载图片API配置")
			return
		try:
			load_dotenv(override=True)
			# 加载上次使用的预设
			last_preset = os.getenv("IMAGE_GEN_API", "") or os.getenv("IMG_API_PRESET", "OpenAI (DALL-E)")
			if last_preset in self.img_api_presets:
				if hasattr(self, 'img_api_preset'):
					self.img_api_preset.set(last_preset)
				if hasattr(self, '_on_img_api_preset_selected'):
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
				safe_preset_name = _safe_preset_env_name(preset_name)
				legacy_safe_name = _legacy_image_preset_env_name(preset_name)
				safe_names = [safe_preset_name]
				if legacy_safe_name and legacy_safe_name not in safe_names:
					safe_names.append(legacy_safe_name)
				
				# 加载该预设的API Key
				key = _first_non_empty_env([f"IMG_{name}_KEY" for name in safe_names])
				if key:
					self.img_api_presets[preset_name]["key"] = key
				
				# 加载该预设的Base URL
				base_url = _first_non_empty_env([f"IMG_{name}_BASE_URL" for name in safe_names])
				if base_url:
					self.img_api_presets[preset_name]["base_url"] = base_url
				
				# 加载该预设的Model
				model = _first_non_empty_env([f"IMG_{name}_MODEL" for name in safe_names])
				if model:
					self.img_api_presets[preset_name]["model"] = model
				
				# 加载该预设的SecretKey（仅腾讯混元）
				if preset_name == "腾讯混元":
					secret_key = _first_non_empty_env([f"IMG_{name}_SECRET_KEY" for name in safe_names])
					if secret_key:
						self.img_api_presets[preset_name]["secret_key"] = secret_key
			
			# 加载上次使用的预设
			last_preset = os.getenv("IMAGE_GEN_API", "") or os.getenv("IMG_API_PRESET")
			if last_preset and last_preset in self.img_api_presets:
				if hasattr(self, 'img_api_preset'):
					self.img_api_preset.set(last_preset)
				# 自动填充该预设的配置
				preset_config = self.img_api_presets[last_preset]
				
				# 设置API类型（根据预设的provider字段）
				provider = preset_config.get("provider", "openai")
				if hasattr(self, 'img_api_type'):
					self.img_api_type.set(provider)
					logger.info("Initialized image API type on startup: provider=%s preset=%s", provider, last_preset)
				
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
			
			logger.info("Auto-loaded image API preset: %s", last_preset or "OpenAI (DALL-E)")
		except Exception as e:
			logger.warning("Failed to load image API config from .env: %s", e)
	
	
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
			ok_results = []
			if hasattr(self, 'shot_gen_api'):
				ok_results.append(set_key(str(env_path), "ASSIST_SHOT_GEN_API", self.shot_gen_api.get()))
			
			# 保存图片描述生成API
			if hasattr(self, 'desc_gen_api'):
				ok_results.append(set_key(str(env_path), "ASSIST_DESC_GEN_API", self.desc_gen_api.get()))
			
			load_dotenv(override=True)
			if all(bool(x) for x in ok_results):
				messagebox.showinfo("成功", f"已保存辅助功能API配置\n\n分镜头生成: {self.shot_gen_api.get()}\n图片描述生成: {self.desc_gen_api.get()}")
			else:
				messagebox.showwarning("警告", f"配置可能未完整写入: {env_path}")
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
			
			# 根据API类型进行不同的测试（后台线程执行，避免阻塞UI）
			if api_type == "hunyuan":
				secret_id = _sanitize(self.img_api_key.get())
				secret_key = _sanitize(self.img_secret_key.get()) if hasattr(self, 'img_secret_key') else ""
				if not secret_id:
					messagebox.showwarning("警告", "请先填写SecretId (API Key)")
					self.status.set("测试失败：缺少SecretId")
					log_widget.insert(END, "❌ 错误: 缺少SecretId\n")
					self.set_busy(False)
					return
				if not secret_key:
					messagebox.showwarning("警告", "请先填写SecretKey")
					self.status.set("测试失败：缺少SecretKey")
					log_widget.insert(END, "❌ 错误: 缺少SecretKey\n")
					self.set_busy(False)
					return
				threading.Thread(
					target=self._run_hunyuan_test_worker,
					args=(log_widget, secret_id, secret_key),
					daemon=True
				).start()
			else:
				key = _sanitize(self.img_api_key.get())
				base = _sanitize(self.img_base_url.get())
				model = _sanitize(self.img_model.get()) or "dall-e-3"
				if not key:
					messagebox.showwarning("警告", "请先填写API Key")
					self.status.set("测试失败：缺少API Key")
					log_widget.insert(END, "❌ 错误: 缺少API Key\n")
					self.set_busy(False)
					return
				if not base:
					messagebox.showwarning("警告", "请先填写Base URL")
					self.status.set("测试失败：缺少Base URL")
					log_widget.insert(END, "❌ 错误: 缺少Base URL\n")
					self.set_busy(False)
					return
				threading.Thread(
					target=self._run_openai_test_worker,
					args=(log_widget, key, base, model),
					daemon=True
				).start()
			return

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
			# 后台线程模式下，结束状态由 worker 回调处理
			pass

	def _append_test_log(self, log_widget, text: str) -> None:
		try:
			log_widget.insert(END, text)
			log_widget.see(END)
		except Exception as e:
			logger.debug("append_test_log failed: %s", e)

	def _finish_image_test(self, ok: bool, status_text: str, title: str, message: str) -> None:
		self.status.set(status_text)
		if ok:
			messagebox.showinfo(title, message)
		else:
			messagebox.showerror(title, message)
		self.set_busy(False)

	def _run_hunyuan_test_worker(self, log_widget, secret_id: str, secret_key: str) -> None:
		lines = [
			"\n📋 腾讯混元测试参数:\n",
			f"  • SecretId: {'*' * (len(secret_id)-8) + secret_id[-8:] if len(secret_id) > 8 else '***'}\n",
			"  • SecretKey: ********************\n",
			"\n🔍 测试腾讯混元图片生成API...\n",
		]
		for line in lines:
			self.after(0, lambda t=line: self._append_test_log(log_widget, t))
		try:
			from src.clients.hunyuan_image_client import HunyuanImageClient
			client = HunyuanImageClient(secret_id=secret_id, secret_key=secret_key)
			result = client.generate(prompt="a simple test image", resolution="1024:1024")
			if result and hasattr(result, 'image'):
				self.after(0, lambda: self._append_test_log(log_widget, "✅ 成功生成测试图片！\n"))
				self.after(0, lambda: self._finish_image_test(
					True,
					"腾讯混元API可用",
					"测试成功",
					"腾讯混元图片API可用！\n\n已成功生成测试图片。\n\n注意：已消耗少量API配额。"
				))
			else:
				raise RuntimeError("API返回空结果或格式错误")
		except Exception as e:
			error_msg = str(e)
			self.after(0, lambda: self._append_test_log(log_widget, f"❌ 测试失败: {error_msg}\n"))
			self.after(0, lambda: self._finish_image_test(
				False,
				"腾讯混元API测试失败",
				"API 错误",
				f"腾讯混元API测试失败\n\n{error_msg}\n\n详情见测试日志。"
			))

	def _run_openai_test_worker(self, log_widget, key: str, base: str, model: str) -> None:
		self.after(0, lambda: self._append_test_log(log_widget, f"\n📋 测试参数:\n  • Model: {model}\n"))
		self.after(0, lambda: self._append_test_log(
			log_widget,
			f"  • API Key: {'*' * (len(key)-8) + key[-8:] if len(key) > 8 else '***'}\n"
		))
		candidates = [base.rstrip("/")]
		if base.rstrip("/").endswith("/v1"):
			candidates.append(base.rstrip("/")[:-3])
		else:
			candidates.append(base.rstrip("/") + "/v1")
		self.after(0, lambda: self._append_test_log(log_widget, "\n🔍 尝试的Base URL:\n"))

		tried_msgs: list[str] = []
		for i, b in enumerate(candidates, 1):
			self.after(0, lambda idx=i, total=len(candidates), url=b: self._append_test_log(
				log_widget, f"\n[{idx}/{total}] 测试: {url}\n"
			))
			ok, msg = _try_image(key, b, model)
			tried_msgs.append(f"base_url={b} -> {'SUCCESS' if ok else 'FAIL'}: {msg}")
			self.after(0, lambda success=ok, m=msg: self._append_test_log(
				log_widget, f"{'✅ 成功' if success else '❌ 失败'}: {m}\n"
			))
			if ok:
				self.after(0, lambda url=b: self.img_base_url.set(url))
				self.after(0, lambda url=b: self._append_test_log(
					log_widget, f"\n🎉 测试成功！已自动更新Base URL为: {url}\n"
				))
				self.after(0, lambda url=b, m=msg: self._finish_image_test(
					True,
					"图片API可用",
					"测试成功",
					f"图片生成 API 可用\n{url}\n\n{m}\n\n注意：实际生成了一张测试图片，可能会消耗少量费用"
				))
				return

		full_msg = "\n".join(tried_msgs)
		self.after(0, lambda: self._append_test_log(log_widget, "\n" + "="*60 + "\n"))
		self.after(0, lambda: self._append_test_log(log_widget, "❌ 图片API测试失败（已尝试所有可能的base_url）\n"))
		self.after(0, lambda: self._append_test_log(log_widget, "="*60 + "\n"))
		self.after(0, lambda: self._append_test_log(log_widget, full_msg + "\n"))
		self.after(0, lambda: self._finish_image_test(
			False,
			"图片API测试失败",
			"API 错误",
			"图片API鉴权失败，请检查密钥/额度/网络/模型。\n详情见配置页面的测试日志。"
		))
	
	
	def _save_image_api_config(self) -> None:
		"""保存图片API配置到.env文件，包括当前预设的API Key"""
		try:
			env_path_str = find_dotenv(usecwd=True)
			env_path = Path(env_path_str) if env_path_str else (Path.cwd() / ".env")
			env_path.parent.mkdir(parents=True, exist_ok=True)
			env_path.touch(exist_ok=True)
			
			# 获取当前预设名称，用于保存该预设的API Key
			current_preset = self.img_api_preset.get().strip()
			safe_preset_name = _safe_preset_env_name(current_preset)
			image_key = self.img_api_key.get()
			image_base_url = self.img_base_url.get()
			image_model = self.img_model.get()
			image_size = self.img_size.get()
			
			# 保存当前预设的API配置到预设字典中
			if current_preset in self.img_api_presets:
				self.img_api_presets[current_preset]["key"] = image_key
				self.img_api_presets[current_preset]["base_url"] = image_base_url
				self.img_api_presets[current_preset]["model"] = image_model
				# 保存SecretKey（仅腾讯混元）
				if current_preset == "腾讯混元":
					self.img_api_presets[current_preset]["secret_key"] = self.img_secret_key.get()
			
			ok_results = [
				set_key(str(env_path), "IMAGE_GEN_API", current_preset),
				set_key(str(env_path), "IMG_API_PRESET", current_preset),
				set_key(str(env_path), "IMG_SIZE", image_size),
				set_key(str(env_path), f"IMG_{safe_preset_name}_KEY", image_key),
				set_key(str(env_path), f"IMG_{safe_preset_name}_BASE_URL", image_base_url),
				set_key(str(env_path), f"IMG_{safe_preset_name}_MODEL", image_model),
			]

			# 如果是腾讯混元，还要保存 SecretKey
			if current_preset == "腾讯混元":
				ok_results.append(set_key(str(env_path), f"IMG_{safe_preset_name}_SECRET_KEY", self.img_secret_key.get()))
			load_dotenv(override=True)
			
			if all(bool(x) for x in ok_results):
				messagebox.showinfo("成功", f"已保存 {current_preset} 的API配置")
				self.status.set(f"已保存 {current_preset} 的API配置")
			else:
				messagebox.showwarning("警告", f"配置可能未完整写入: {env_path}")
		except Exception as e:
			messagebox.showerror("错误", f"保存失败: {str(e)}")
	
	
