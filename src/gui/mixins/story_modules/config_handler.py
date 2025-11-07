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
		try:
			self.set_busy(True)
			self.status.set("测试故事生成 API 中...")
			
			# 确保使用故事配置页面的日志框
			if not hasattr(self, 'story_test_log'):
				messagebox.showwarning(
					"提示", 
					"请先切换到【故事生成 → 配置】标签页，\n"
					"以便在该页面查看详细的测试日志。"
				)
				return
			
			log_widget = self.story_test_log
			# 清空之前的日志
			log_widget.delete("1.0", END)
			import datetime
			timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			log_widget.insert(END, f"[{timestamp}] 开始测试故事生成API...\n")
			
			from src.utils.text import sanitize as _sanitize, try_chat_api as _try_chat
			
			key = _sanitize(self.api_key.get())
			base = _sanitize(self.base_url.get())
			model = _sanitize(self.model.get()) or "deepseek-chat"
			
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
				
				ok, msg = _try_chat(key, b, model)
				tried_msgs.append(f"base_url={b} -> {'SUCCESS' if ok else 'FAIL'}: {msg}")
				
				if ok:
					log_widget.insert(END, f"✅ 成功: {msg}\n")
				else:
					log_widget.insert(END, f"❌ 失败: {msg}\n")
				
				if ok:
					self.base_url.set(b)
					# 测试成功后，更新当前预设的配置并更新下拉框
					current_preset = self.api_preset.get() if hasattr(self, 'api_preset') else ""
					if current_preset and hasattr(self, 'api_presets') and current_preset in self.api_presets:
						self.api_presets[current_preset]["key"] = key
						self.api_presets[current_preset]["base_url"] = b
						self.api_presets[current_preset]["model"] = model
					
					log_widget.insert(END, f"\n🎉 测试成功！已自动更新Base URL为: {b}\n")
					messagebox.showinfo("测试成功", f"故事生成 API 可用\n{b}")
					self.status.set("故事API可用")
					
					# 更新故事生成API下拉框
					if hasattr(self, '_update_story_api_dropdowns'):
						self._update_story_api_dropdowns()
					
					return
			
			# all failed
			full_msg = "\n".join(tried_msgs)
			log_widget.insert(END, "\n" + "="*60 + "\n")
			log_widget.insert(END, "❌ 故事API测试失败（已尝试所有可能的base_url）\n")
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
			messagebox.showerror("API 错误", "故事API鉴权失败，请检查密钥/额度/网络/模型。\n详情见配置页面的测试日志。")
			self.status.set("故事API测试失败")
		except Exception as e:
			import traceback
			if 'log_widget' not in locals():
				log_widget = getattr(self, 'story_test_log', None)
			if log_widget:
				error_trace = traceback.format_exc()
				log_widget.insert(END, "\n" + "="*60 + "\n")
				log_widget.insert(END, "💥 故事API测试异常\n")
				log_widget.insert(END, "="*60 + "\n")
				log_widget.insert(END, error_trace + "\n")
			
			messagebox.showerror("API 错误", f"测试时发生异常:\n{str(e)}\n\n详情见配置页面的测试日志。")
			self.status.set("故事API测试失败")
		finally:
			self.set_busy(False)
	
	
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
	
	