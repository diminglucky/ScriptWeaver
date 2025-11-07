"""
Project相关功能模块
"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, messagebox, filedialog
import tkinter as tk
from tkinter import ttk
from .project_modules import EnhancedProjectManager
from ..theme import Theme
from src.core.logging_config import get_logger

logger = get_logger(__name__)


class ProjectMixin(EnhancedProjectManager):
	"""Project管理功能"""
	
	def _clear_all_ui_data(self) -> None:
		"""清理所有UI界面上的数据缓存"""
		try:
			# 1. 清空故事输出区
			if hasattr(self, 'output'):
				self.output.delete("1.0", END)
			
			# 2. 清空提示词输入区（恢复占位符）
			if hasattr(self, 'prompt_text'):
				self.prompt_text.delete("1.0", END)
				placeholder_text = "📝 请详细描述你的故事创意...\n\n💡 提示：你可以输入：\n· 故事主题和关键情节\n· 人物设定和性格特点\n· 故事背景和时代环境\n· 特殊的叙事要求或风格\n\n✨ 越详细的描述，生成的故事越符合你的期望！"
				self.prompt_text.insert("1.0", placeholder_text)
				self.prompt_text.tag_add("placeholder", "1.0", "end")
				self.prompt_text.config(fg=Theme.TEXT_HINT)  # 使用主题的提示文本颜色
				# 保存空状态到缓存（新建项目时清除缓存）
				if hasattr(self, '_save_input_cache'):
					self.after(100, lambda: self._save_input_cache(delay=False))
			
			# 3. 重置下拉框选项到默认值
			if hasattr(self, 'category'):
				self.category.set("悬疑推理")
			if hasattr(self, 'style'):
				self.style.set("电影化叙事")
			if hasattr(self, 'target_chars'):
				self.target_chars.set(3000)
			
			# 4. 清空导演页面的数据
			if hasattr(self, 'script_text'):
				self.script_text.delete("1.0", END)
			
			if hasattr(self, 'shots_text'):
				self.shots_text.delete("1.0", END)
			
			if hasattr(self, 'jimeng_prompts_text'):
				self.jimeng_prompts_text.delete("1.0", END)
			
			# 5. 清空分镜选择下拉框
			if hasattr(self, 'shot_select_combo'):
				self.shot_select_combo['values'] = ["全部分镜"]
				self.shot_select_combo.current(0)
			
			# 6. 清空图片预览区域
			if hasattr(self, 'director_images_canvas'):
				# 删除canvas上的所有项目
				self.director_images_canvas.delete("all")
				# 如果canvas有内部frame，也需要清理其子控件
				if hasattr(self, 'director_images_container'):
					for widget in self.director_images_container.winfo_children():
						widget.destroy()
			
			# 7. 清空图片管理页面
			if hasattr(self, 'image_gallery_frame'):
				for widget in self.image_gallery_frame.winfo_children():
					widget.destroy()
			
			# 8. 清空人物列表
			if hasattr(self, 'character_listbox'):
				self.character_listbox.delete(0, END)
			
			if hasattr(self, 'ref_character_listbox'):
				self.ref_character_listbox.delete(0, END)
			
			# 9. 清空人物描述文本框
			if hasattr(self, 'character_desc_text'):
				self.character_desc_text.delete("1.0", END)
			
			# 10. 重置进度条
			if hasattr(self, 'image_progress_var'):
				self.image_progress_var.set(0)
			
			if hasattr(self, 'image_progress_label'):
				self.image_progress_label.config(text="")
			
			# 11. 清空内部数据缓存
			if hasattr(self, 'character_seed_map'):
				self.character_seed_map = {}
			
			if hasattr(self, '_current_negative_prompt'):
				self._current_negative_prompt = {}
			
			# 12. 清空分镜数据
			if hasattr(self, 'shots_data'):
				self.shots_data = []
			
			# 13. 清空人物信息缓存
			if hasattr(self, 'characters_info'):
				self.characters_info = {}
			
			from src.core.logging_config import get_logger
			logger = get_logger(__name__)
			logger.info("已清理所有UI界面缓存数据")
			
		except Exception as e:
			from src.core.logging_config import get_logger
			logger = get_logger(__name__)
			logger.warning(f"清理UI数据时出现错误: {e}", exc_info=True)
	
	def _refresh_project_list(self) -> None:
		"""刷新项目列表"""
		try:
			# 清空列表
			for item in self.project_tree.get_children():
				self.project_tree.delete(item)
			
			# 加载项目
			projects = self.project_manager.list_projects()
			for proj in projects:
				self.project_tree.insert("", "end", values=(
					proj["name"],
					proj.get("category", ""),
					proj.get("story_length", 0),
					proj.get("image_count", 0),
					proj.get("updated_at", "")[:19].replace("T", " "),  # 格式化时间
				), tags=(proj["path"],))
			
			if hasattr(self, 'status'):
				self.status.set(f"已加载 {len(projects)} 个项目")
		except Exception as e:
			messagebox.showerror("错误", f"刷新项目列表失败: {e}")
	
	def _on_new_project(self) -> None:
		"""创建新项目"""
		# 弹出自定义对话框让用户输入项目名称
		from ..helpers.dialogs import show_input_dialog
		project_name = show_input_dialog(self, "新建项目", "请输入项目名称:", width=400)
		if not project_name or not project_name.strip():
			return
		
		try:
			# ★★★ 清理所有UI界面缓存数据 ★★★
			self._clear_all_ui_data()
			
			self.current_project = self.project_manager.create_project(project_name.strip())
			self.lbl_current_project.config(text=f"当前项目: {project_name}", fg="#4CAF50")
			self.btn_save_story.config(state=NORMAL)
			self.btn_save_all.config(state=NORMAL)
			
			# 创建人物照片文件夹
			if self.current_project:
				from pathlib import Path
				characters_dir = self.current_project.project_dir / "characters"
				characters_dir.mkdir(parents=True, exist_ok=True)
				logger.info(f"已创建人物照片文件夹：{characters_dir}")
			
			self._refresh_project_list()
			if hasattr(self, 'status'):
				self.status.set(f"已创建项目: {project_name}")
			messagebox.showinfo("成功", f"项目已创建: {project_name}\n\n现在可以前往'故事生成'页面创作内容")
			# 切换到故事生成页面
			self.notebook.select(self.page_story)
		except Exception as e:
			messagebox.showerror("错误", f"创建项目失败: {e}")
	
	def _on_load_project(self) -> None:
		"""加载选中的项目"""
		selection = self.project_tree.selection()
		if not selection:
			messagebox.showwarning("提示", "请先选择一个项目")
			return
		
		try:
			# 获取项目路径
			item = selection[0]
			tags = self.project_tree.item(item, "tags")
			if not tags:
				return
			project_path = tags[0]
			
			# 加载项目
			self.current_project = self.project_manager.load_project(project_path)
			project_name = self.current_project.metadata.get("name", "")
			self.lbl_current_project.config(text=f"当前项目: {project_name}", fg="#4CAF50")
			self.btn_save_story.config(state=NORMAL)
			self.btn_save_all.config(state=NORMAL)
			
			# 恢复故事内容到输出框
			story_content = self.current_project.load_story()
			if story_content:
				self.output.delete("1.0", END)
				self.output.insert(END, story_content)
				if hasattr(self, 'status'):
					self.status.set(f"已加载项目: {project_name} ({len(story_content)} 字)")
			else:
				if hasattr(self, 'status'):
					self.status.set(f"已加载项目: {project_name} (无故事内容)")
			
			# 确保项目有 characters 文件夹（兼容旧项目）
			if self.current_project:
				from pathlib import Path
				characters_dir = self.current_project.project_dir / "characters"
				if not characters_dir.exists():
					characters_dir.mkdir(parents=True, exist_ok=True)
					logger.info(f"自动创建人物照片文件夹：{characters_dir}")
			
			# 使用增强的加载功能（会加载人物数据）
			enhanced_load_success = False
			try:
				enhanced_load_success = self.load_complete_project()
				if enhanced_load_success:
					logger.info("使用增强加载功能成功加载项目")
			except Exception as e:
				logger.warning(f"增强加载失败，使用传统方式: {e}")
			
			# 如果增强加载没有加载人物，再单独加载
			# 注意：load_complete_project中已经会调用_load_project_characters，所以这里不需要重复调用
			# 但如果load_complete_project失败或没有执行人物加载，这里作为后备
			if not enhanced_load_success or (hasattr(self, 'character_list') and len(self.character_list) == 0):
				if hasattr(self, '_load_project_characters'):
					logger.info("后备：单独加载人物数据")
					self._load_project_characters()
			
			# 如果增强加载失败，使用传统方式
			if not enhanced_load_success:
				# 加载导演项目数据（如果存在）
				if hasattr(self, 'load_director_project'):
					logger.info("正在加载导演项目数据...")
					self.load_director_project(project_path)
				
			# 恢复创作参数
			meta = self.current_project.metadata
			if meta.get("category"):
				self.category.set(meta["category"])
			if meta.get("requirement"):
				if hasattr(self, 'prompt_text'):
					self.prompt_text.delete("1.0", END)
					self.prompt_text.insert("1.0", meta["requirement"])
					self.prompt_text.tag_remove("placeholder", "1.0", "end")
					self.prompt_text.config(fg=Theme.TEXT_PRIMARY)  # 使用主题的主文本颜色
			if meta.get("style"):
				self.style.set(meta["style"])
			if meta.get("target_chars"):
				self.target_chars.set(meta["target_chars"])
			
			messagebox.showinfo("成功", f"项目已加载: {project_name}\n\n所有内容已恢复")
			# 切换到故事生成页面
			self.notebook.select(self.page_story)
		except Exception as e:
			messagebox.showerror("错误", f"加载项目失败: {e}")
	
	def _on_save_story(self) -> None:
		"""保存当前故事到项目"""
		if not self.current_project:
			messagebox.showwarning("提示", "请先创建或加载一个项目")
			return
		
		story_content = self.output.get("1.0", END).strip()
		if not story_content:
			messagebox.showwarning("提示", "输出区域没有内容可保存")
			return
		
		try:
			# 保存故事和参数
			self.current_project.save_story(
				story_content,
				category=self.category.get(),
				requirement=self._get_prompt_content(),
				style=self.style.get(),
				target_chars=self.target_chars.get(),
			)
			
			# 使用增强的保存功能保存完整项目
			if self.save_complete_project():
				logger.info("完整项目数据已保存")
			
			self._refresh_project_list()
			if hasattr(self, 'status'):
				project_name = self.current_project.metadata.get('name', '未命名项目')
				self.status.set(f"项目已完整保存: {project_name}")
			messagebox.showinfo("成功", f"项目已完整保存\n\n字数: {len(story_content)}")
		except Exception as e:
			messagebox.showerror("错误", f"保存故事失败: {e}")
	
	def _on_save_all(self) -> None:
		"""完整保存项目的所有内容"""
		if not self.current_project:
			messagebox.showwarning("提示", "请先创建或加载一个项目")
			return
		
		try:
			# 调用增强的保存功能
			if self.save_complete_project():
				messagebox.showinfo("成功", 
					f"项目已完整保存！\n\n"
					f"包含内容：\n"
					f"✓ 故事内容和参数\n"
					f"✓ 剧本和分镜\n"
					f"✓ 人物设定表\n"
					f"✓ 生成的图片\n"
					f"✓ 所有配置信息"
				)
			else:
				messagebox.showwarning("警告", "项目保存不完整，请检查错误信息")
		except Exception as e:
			messagebox.showerror("错误", f"完整保存失败: {e}")
	
	def _on_delete_project(self) -> None:
		"""删除选中的项目"""
		selection = self.project_tree.selection()
		if not selection:
			messagebox.showwarning("提示", "请先选择一个项目")
			return
		
		# 获取项目信息
		item = selection[0]
		values = self.project_tree.item(item, "values")
		project_name = values[0] if values else "未知项目"
		tags = self.project_tree.item(item, "tags")
		if not tags:
			return
		project_path = tags[0]
		
		# 确认删除
		confirm = messagebox.askyesno(
			"确认删除",
			f"确定要删除项目 '{project_name}' 吗？\n\n这将永久删除项目文件夹及其所有内容（故事、图片等）。\n\n此操作不可恢复！",
			icon="warning"
		)
		if not confirm:
			return
		
		try:
			# 如果删除的是当前项目，清空当前项目
			if self.current_project and str(self.current_project.project_dir) == project_path:
				self.current_project = None
				self.lbl_current_project.config(text="未选择项目", fg="#888888")
				self.btn_save_story.config(state=DISABLED)
				self.btn_save_all.config(state=DISABLED)
			
			self.project_manager.delete_project(project_path)
			self._refresh_project_list()
			if hasattr(self, 'status'):
				self.status.set(f"已删除项目: {project_name}")
			messagebox.showinfo("成功", f"项目已删除: {project_name}")
		except Exception as e:
			messagebox.showerror("错误", f"删除项目失败: {e}")
	
	# ==================== 章节管理功能 ====================
	
	def _build_project_page(self) -> None:
		"""构建项目管理页面"""
		# 顶部：当前项目信息
		top_frame = ttk.LabelFrame(self.page_project, text="📂 当前项目", padding=(10, 8))
		top_frame.pack(fill="x", padx=10, pady=(10, 8))
		
		self.lbl_current_project = tk.Label(top_frame, text="未选择项目", font=("", 12, "bold"), fg="#888888", anchor="w")
		self.lbl_current_project.pack(fill="x", pady=(0, 4))
		
		btn_row = ttk.Frame(top_frame)
		btn_row.pack(fill="x")
		self.btn_new_project = ttk.Button(btn_row, text="➕ 新建项目", command=self._on_new_project, style="Accent.TButton")
		self.btn_new_project.pack(side=LEFT, padx=(0, 6))
		self.btn_save_story = ttk.Button(btn_row, text="💾 保存当前故事", command=self._on_save_story, state=DISABLED, style="TButton")
		self.btn_save_story.pack(side=LEFT, padx=6)
		self.btn_save_all = ttk.Button(btn_row, text="💯 完整保存项目", command=self._on_save_all, state=DISABLED, style="Accent.TButton")
		self.btn_save_all.pack(side=LEFT, padx=6)
		
		# 中间：项目列表
		mid_frame = ttk.LabelFrame(self.page_project, text="📚 我的项目", padding=(10, 8))
		mid_frame.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))
		
		# 创建表格
		columns = ("name", "category", "story_len", "images", "updated")
		self.project_tree = ttk.Treeview(mid_frame, columns=columns, show="headings", height=15)
		self.project_tree.heading("name", text="项目名称")
		self.project_tree.heading("category", text="类别")
		self.project_tree.heading("story_len", text="故事字数")
		self.project_tree.heading("images", text="图片数")
		self.project_tree.heading("updated", text="更新时间")
		
		self.project_tree.column("name", width=250)
		self.project_tree.column("category", width=100)
		self.project_tree.column("story_len", width=100)
		self.project_tree.column("images", width=80)
		self.project_tree.column("updated", width=180)
		
		scrollbar = ttk.Scrollbar(mid_frame, orient="vertical", command=self.project_tree.yview)
		self.project_tree.configure(yscrollcommand=scrollbar.set)
		
		self.project_tree.pack(side=LEFT, fill=BOTH, expand=True)
		scrollbar.pack(side=RIGHT, fill="y")
		
		# 底部：操作按钮
		btn_frame = ttk.Frame(mid_frame)
		btn_frame.pack(fill="x", pady=(8, 0))
		self.btn_load_project = ttk.Button(btn_frame, text="📖 加载选中项目", command=self._on_load_project, style="Accent.TButton")
		self.btn_load_project.pack(side=LEFT, padx=(0, 6))
		self.btn_refresh_list = ttk.Button(btn_frame, text="🔄 刷新列表", command=self._refresh_project_list, style="TButton")
		self.btn_refresh_list.pack(side=LEFT, padx=6)
		self.btn_delete_project = ttk.Button(btn_frame, text="🗑️ 删除选中项目", command=self._on_delete_project, style="Ghost.TButton")
		self.btn_delete_project.pack(side=LEFT, padx=6)
		
		# 初始加载项目列表
		self._refresh_project_list()
	

