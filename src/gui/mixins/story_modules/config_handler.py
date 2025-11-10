"""Story功能模块"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, messagebox, filedialog, scrolledtext
import tkinter as tk
from tkinter import ttk
import threading
import re
from pathlib import Path
from dotenv import load_dotenv

from src.clients.deepseek_client import DeepSeekClient
# 延迟导入：只在使用时才导入，避免启动时加载 sentence_transformers (3.8秒)
# from src.kb.ingest import KnowledgeBaseIngestor, IngestConfig
# from src.kb.search import KnowledgeBaseSearcher, SearchConfig
from src.utils.text import sanitize as _sanitize


class StoryConfigMixin:
	"""Story config_handler 功能"""
	
	def on_save_as(self) -> None:
		content = self.output.get("1.0", END).strip()
		if not content:
			messagebox.showwarning("提示", "当前没有可保存的内容")
			return
		path = filedialog.asksaveasfilename(defaultextension=".md", filetypes=[
			("Markdown", "*.md"),
			("Text", "*.txt"),
			("All Files", "*.*"),
		])
		if not path:
			return
		try:
			with open(path, "w", encoding="utf-8") as f:
				f.write(content)
			messagebox.showinfo("成功", f"已保存到: {path}")
		except Exception as e:
			messagebox.showerror("错误", str(e))

	
	def on_clear_output(self) -> None:
		self.output.delete("1.0", END)
		self.status.set("输出已清空")

	
	def on_copy_output(self) -> None:
		text = self.output.get("1.0", END)
		self.clipboard_clear()
		self.clipboard_append(text)
		self.status.set("内容已复制到剪贴板")
	
	
	def _save_story_assist_api_config(self) -> None:
		"""保存故事创作功能API配置（目录生成和故事生成）"""
		try:
			from pathlib import Path
			from dotenv import find_dotenv, set_key
			from dotenv import load_dotenv
			
			env_path_str = find_dotenv(usecwd=True)
			if not env_path_str:
				env_path = Path.cwd() / ".env"
			else:
				env_path = Path(env_path_str)
			env_path.touch(exist_ok=True)
			
			# 保存目录生成API
			if hasattr(self, 'outline_gen_api'):
				set_key(str(env_path), "STORY_OUTLINE_GEN_API", self.outline_gen_api.get())
			
			# 保存故事生成API
			if hasattr(self, 'story_gen_api'):
				set_key(str(env_path), "STORY_STORY_GEN_API", self.story_gen_api.get())
			
			load_dotenv(override=True)
			messagebox.showinfo("成功", f"已保存故事创作功能API配置\n\n目录生成: {self.outline_gen_api.get()}\n故事生成: {self.story_gen_api.get()}")
		except Exception as e:
			messagebox.showerror("错误", f"保存配置失败: {str(e)}")
	
	
	def on_test_story_api(self) -> None:
		"""测试故事生成API（输出到配置页面的测试日志）"""
		# 确保使用故事配置页面的日志框
		if not hasattr(self, 'story_test_log'):
			messagebox.showwarning(
				"提示", 
				"请先切换到【故事生成 → 配置】标签页，\n"
				"以便在该页面查看详细的测试日志。"
			)
			return
		
		# 获取参数（在主线程中获取，避免线程安全问题）
		from src.utils.text import sanitize as _sanitize
		key = _sanitize(self.api_key.get())
		base = _sanitize(self.base_url.get())
		model_raw = self.model.get() if hasattr(self, 'model') else ""
		model = _sanitize(model_raw) if model_raw else "deepseek-chat"
		
		if not key:
			messagebox.showwarning("警告", "请先填写API Key")
			self.status.set("测试失败：缺少API Key")
			return
		
		# 在后台线程中运行测试，避免阻塞UI
		def test_task():
			try:
				self.after(0, lambda: self.set_busy(True))
				self.after(0, lambda: self.status.set("测试故事生成 API 中..."))
				
				log_widget = self.story_test_log
				# 清空之前的日志（线程安全）
				self.after(0, lambda: log_widget.delete("1.0", END))
				import datetime
				timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
				self.after(0, lambda ts=timestamp: log_widget.insert(END, f"[{ts}] 开始测试故事生成API...\n"))
				
				from src.utils.text import try_chat_api as _try_chat
				
				# 检查是否是 Gemini API（通过模型名称判断，Gemini 不需要 base_url）
				is_gemini = bool(model and "gemini" in model.lower())
				
				# 记录测试参数（线程安全）
				def update_log(text):
					self.after(0, lambda t=text: log_widget.insert(END, t))
				
				update_log(f"\n📋 测试参数:\n")
				update_log(f"  • Model: {model}\n")
				update_log(f"  • API Key: {'*' * (len(key)-8) + key[-8:] if len(key) > 8 else '***'}\n")
				update_log(f"  • 检测到 Gemini API: {'是' if is_gemini else '否'}\n")
				
				if is_gemini:
					update_log(f"  • 注意: Gemini API 不需要 Base URL\n")
				elif not base:
					self.after(0, lambda: messagebox.showwarning("警告", "请先填写Base URL"))
					self.after(0, lambda: self.status.set("测试失败：缺少Base URL"))
					update_log("❌ 错误: 缺少Base URL\n")
					return
				
				# Gemini API 直接测试，不需要尝试不同的 base_url
				if is_gemini:
					update_log(f"\n🔍 测试 Gemini API...\n")
					
					ok, msg = _try_chat(key, "", model)  # Gemini 不需要 base_url
					
					if ok:
						update_log(f"✅ 成功: {msg}\n")
						# 测试成功后，更新当前预设的配置
						current_preset = self.api_preset.get() if hasattr(self, 'api_preset') else ""
						if current_preset and hasattr(self, 'api_presets') and current_preset in self.api_presets:
							self.api_presets[current_preset]["key"] = key
							self.api_presets[current_preset]["base_url"] = ""  # Gemini 不需要 base_url
							self.api_presets[current_preset]["model"] = model
						
						update_log(f"\n🎉 测试成功！\n")
						self.after(0, lambda: messagebox.showinfo("测试成功", f"Gemini API 连接成功\n\n{msg}"))
						self.after(0, lambda: self.status.set("Gemini API 可用"))
						return
					else:
						update_log(f"❌ 失败: {msg}\n")
						# 提供更详细的错误提示
						if "模型不存在" in msg or "404" in msg:
							update_log(f"\n💡 提示: 请检查模型名称是否正确\n")
							update_log(f"   推荐使用: gemini-1.5-flash 或 gemini-1.5-pro\n")
						elif "连接失败" in msg or "代理" in msg:
							update_log(f"\n💡 提示: 如果在中国大陆，可能需要配置代理\n")
							update_log(f"   在 .env 文件中添加: HTTPS_PROXY=http://127.0.0.1:7890\n")
						elif "Missing google-generativeai" in msg or "google-generativeai" in msg.lower():
							update_log(f"\n💡 提示: 缺少 google-generativeai 包\n")
							update_log(f"   请运行: pip install google-generativeai\n")
							update_log(f"   或者在项目根目录运行: pip install -r requirements.txt\n")
						self.after(0, lambda m=msg: messagebox.showerror("测试失败", f"Gemini API 测试失败\n\n{m}"))
						self.after(0, lambda: self.status.set("Gemini API 测试失败"))
						return
			
				# 其他 API 尝试不同的 base_url
				candidates = []
				# try user-provided
				candidates.append(base.rstrip("/"))
				# also try toggling /v1 suffix
				if base.rstrip("/").endswith("/v1"):
					candidates.append(base.rstrip("/")[:-3])
				else:
					candidates.append(base.rstrip("/") + "/v1")
				
				update_log(f"\n🔍 尝试的Base URL:\n")
				
				tried_msgs: list[str] = []
				for i, b in enumerate(candidates, 1):
					update_log(f"\n[{i}/{len(candidates)}] 测试: {b}\n")
					
					ok, msg = _try_chat(key, b, model)
					tried_msgs.append(f"base_url={b} -> {'SUCCESS' if ok else 'FAIL'}: {msg}")
					
					if ok:
						update_log(f"✅ 成功: {msg}\n")
					else:
						update_log(f"❌ 失败: {msg}\n")
					
					if ok:
						self.after(0, lambda url=b: self.base_url.set(url))
						# 测试成功后，更新当前预设的配置并更新下拉框
						current_preset = self.api_preset.get() if hasattr(self, 'api_preset') else ""
						if current_preset and hasattr(self, 'api_presets') and current_preset in self.api_presets:
							self.api_presets[current_preset]["key"] = key
							self.api_presets[current_preset]["base_url"] = b
							self.api_presets[current_preset]["model"] = model
						
						update_log(f"\n🎉 测试成功！已自动更新Base URL为: {b}\n")
						self.after(0, lambda url=b: messagebox.showinfo("测试成功", f"故事生成 API 可用\n{url}"))
						self.after(0, lambda: self.status.set("故事API可用"))
						
						# 更新故事生成API下拉框
						if hasattr(self, '_update_story_api_dropdowns'):
							self.after(0, lambda: self._update_story_api_dropdowns())
						
						return
				
				# all failed
				full_msg = "\n".join(tried_msgs)
				update_log("\n" + "="*60 + "\n")
				update_log("❌ 故事API测试失败（已尝试所有可能的base_url）\n")
				update_log("="*60 + "\n")
				update_log(full_msg + "\n")
				update_log("\n💡 可能的原因:\n")
				update_log("  1. API密钥错误或已过期\n")
				update_log("  2. 账户余额不足\n")
				update_log("  3. Base URL不正确\n")
				update_log("  4. 网络连接问题\n")
				update_log("  5. 模型名称不支持\n")
				update_log("\n建议操作:\n")
				update_log("  • 检查API密钥是否正确\n")
				update_log("  • 登录服务商网站查看账户余额\n")
				update_log("  • 确认Base URL格式正确\n")
				self.after(0, lambda: messagebox.showerror("API 错误", "故事API鉴权失败，请检查密钥/额度/网络/模型。\n详情见配置页面的测试日志。"))
				self.after(0, lambda: self.status.set("故事API测试失败"))
			except Exception as e:
				import traceback
				error_trace = traceback.format_exc()
				log_widget = self.story_test_log
				if log_widget:
					self.after(0, lambda: log_widget.insert(END, "\n" + "="*60 + "\n"))
					self.after(0, lambda: log_widget.insert(END, "💥 故事API测试异常\n"))
					self.after(0, lambda: log_widget.insert(END, "="*60 + "\n"))
					self.after(0, lambda et=error_trace: log_widget.insert(END, et + "\n"))
				
				self.after(0, lambda err=str(e): messagebox.showerror("API 错误", f"测试时发生异常:\n{err}\n\n详情见配置页面的测试日志。"))
				self.after(0, lambda: self.status.set("故事API测试失败"))
			finally:
				self.after(0, lambda: self.set_busy(False))
		
		# 启动后台线程
		threading.Thread(target=test_task, daemon=True).start()
	
	
	def _estimate_chars(self, outline: str) -> int:
		"""根据目录估算字数"""
		lines = [l.strip() for l in outline.splitlines() if l.strip()]
		# Count section-like lines
		count = 0
		for l in lines:
			if l[:2].isdigit() or l[:1] in {"-", "•", "*"} or l.startswith(("一、", "二、", "三、", "四、", "五、")):
				count += 1
		if count <= 0:
			count = max(3, min(8, len(lines)//2 or 4))
		# Rough estimate: ~350 chars per section
		return int(count * 350)
	
	