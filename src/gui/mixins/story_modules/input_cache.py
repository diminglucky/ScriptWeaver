"""
输入缓存模块 - 自动保存和恢复用户输入
避免用户输入的内容在关闭应用后丢失
"""

import json
from pathlib import Path
from tkinter import END

from src.core.logging_config import get_logger

logger = get_logger(__name__)


class InputCacheMixin:
	"""输入缓存功能 - 自动保存和恢复用户输入"""
	
	def _init_input_cache(self):
		"""初始化输入缓存"""
		self.cache_file = Path("data") / "input_cache.json"
		self.cache_file.parent.mkdir(parents=True, exist_ok=True)
		
		# 延迟保存计时器
		self._save_timer = None
	
	def _load_input_cache(self):
		"""加载输入缓存并恢复到UI"""
		try:
			if not hasattr(self, 'cache_file') or not self.cache_file.exists():
				return
			
			with open(self.cache_file, 'r', encoding='utf-8') as f:
				cache = json.load(f)
			
			# 恢复创作需求
			if 'requirement' in cache and cache['requirement']:
				if hasattr(self, 'prompt_text'):
					# 清除占位符
					self.prompt_text.delete("1.0", END)
					self.prompt_text.insert("1.0", cache['requirement'])
					self.prompt_text.tag_remove("placeholder", "1.0", "end")
			
			# 恢复风格（如果和当前不同）
			if 'style' in cache and cache['style']:
				current_style = self.style.get()
				# 只有当前风格是默认值时才恢复
				if current_style == "情感起伏/反转/细节描写/有画面感/口语化":
					if hasattr(self, 'entry_style'):
						self.entry_style.delete(0, END)
						self.entry_style.insert(0, cache['style'])
			
			# 恢复种类
			if 'category' in cache and cache['category']:
				try:
					self.category.set(cache['category'])
				except:
					pass
			
			# 恢复字数
			if 'target_chars' in cache and cache['target_chars']:
				try:
					self.target_chars.set(cache['target_chars'])
				except:
					pass
			
			logger.info("已恢复上次输入内容")
			
		except Exception as e:
			logger.warning(f"加载输入缓存失败: {e}")
	
	def _save_input_cache(self, delay=True):
		"""保存输入缓存
		
		Args:
			delay: 是否延迟保存（避免频繁写文件）
		"""
		if delay:
			# 取消之前的计时器
			if self._save_timer:
				self.after_cancel(self._save_timer)
			# 设置新的延迟保存（2秒后）
			self._save_timer = self.after(2000, lambda: self._save_input_cache(delay=False))
			return
		
		try:
			if not hasattr(self, 'cache_file'):
				return
			
			# 获取当前输入
			cache = {}
			
			# 保存创作需求
			if hasattr(self, 'prompt_text'):
				content = self.prompt_text.get("1.0", "end-1c").strip()
				# 检查是否是占位符（多种占位符格式）
				is_placeholder = False
				if content:
					# 检查是否有placeholder标签
					tags = self.prompt_text.tag_names("1.0")
					if "placeholder" in tags:
						is_placeholder = True
					# 检查常见占位符文本
					placeholder_texts = [
						"例如：",
						"📝 请详细描述你的故事创意",
						"请详细描述你的故事创意",
						"写一个惊悚短篇"
					]
					for placeholder in placeholder_texts:
						if placeholder in content and len(content) < 200:  # 占位符通常较短
							is_placeholder = True
							break
				
				# 只保存非占位符内容
				if content and not is_placeholder:
					cache['requirement'] = content
			
			# 保存风格
			if hasattr(self, 'entry_style'):
				style = self.entry_style.get().strip()
				if style:
					cache['style'] = style
			
			# 保存种类
			if hasattr(self, 'category'):
				cache['category'] = self.category.get()
			
			# 保存字数
			if hasattr(self, 'target_chars'):
				cache['target_chars'] = self.target_chars.get()
			
			# 写入文件（即使cache为空也要写入，用于清空缓存）
			with open(self.cache_file, 'w', encoding='utf-8') as f:
				json.dump(cache, f, ensure_ascii=False, indent=2)
			
			# 调试信息
			if cache.get('requirement'):
				logger.debug(f"已保存创作需求到缓存: {len(cache['requirement'])} 字符")
			
		except Exception as e:
			logger.warning(f"保存输入缓存失败: {e}")
	
	def _bind_input_cache_events(self):
		"""绑定输入事件，自动保存"""
		try:
			# 监听创作需求输入
			if hasattr(self, 'prompt_text'):
				def on_prompt_change(event=None):
					self._save_input_cache(delay=True)
				
				self.prompt_text.bind("<KeyRelease>", on_prompt_change)
			
			# 监听风格输入
			if hasattr(self, 'entry_style'):
				def on_style_change(event=None):
					self._save_input_cache(delay=True)
				
				self.entry_style.bind("<KeyRelease>", on_style_change)
			
			# 监听种类变化
			if hasattr(self, 'category'):
				def on_category_change(*args):
					self._save_input_cache(delay=True)
				
				self.category.trace_add("write", on_category_change)
			
			# 监听字数变化
			if hasattr(self, 'target_chars'):
				def on_chars_change(*args):
					self._save_input_cache(delay=True)
				
				self.target_chars.trace_add("write", on_chars_change)
			
			logger.info("输入自动保存已启用")
			
		except Exception as e:
			logger.warning(f"绑定输入缓存事件失败: {e}")


