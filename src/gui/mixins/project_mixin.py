"""
Project相关功能模块
"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, messagebox, filedialog
import tkinter as tk
from tkinter import ttk


class ProjectMixin:
	"""Project管理功能"""
	
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
		# 弹出对话框让用户输入项目名称
		from tkinter import simpledialog
		project_name = simpledialog.askstring("新建项目", "请输入项目名称:")
		if not project_name or not project_name.strip():
			return
		
		try:
			self.current_project = self.project_manager.create_project(project_name.strip())
			self.lbl_current_project.config(text=f"当前项目: {project_name}", fg="#4CAF50")
			self.btn_save_story.config(state=NORMAL)
			
			# 创建人物照片文件夹
			if self.current_project:
				from pathlib import Path
				characters_dir = self.current_project.project_dir / "characters"
				characters_dir.mkdir(parents=True, exist_ok=True)
				print(f"📁 已创建人物照片文件夹：{characters_dir}")
			
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
					print(f"📁 自动创建人物照片文件夹：{characters_dir}")
			
			# 加载项目的人物照片
			if hasattr(self, '_load_project_characters'):
				self._load_project_characters()
			
			# 恢复创作参数
			meta = self.current_project.metadata
			if meta.get("category"):
				self.category.set(meta["category"])
			if meta.get("requirement"):
				self.prompt_text.delete("1.0", END)
				self.prompt_text.insert("1.0", meta["requirement"])
				self.prompt_text.tag_remove("placeholder", "1.0", "end")
			if meta.get("style"):
				self.style.set(meta["style"])
			if meta.get("target_chars"):
				self.target_chars.set(meta["target_chars"])
			
			messagebox.showinfo("成功", f"项目已加载: {project_name}\n\n故事内容已恢复到输出区域")
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
			self._refresh_project_list()
			if hasattr(self, 'status'):
				self.status.set(f"故事已保存到项目: {self.current_project.metadata['name']}")
			messagebox.showinfo("成功", f"故事已保存到项目\n\n字数: {len(story_content)}")
		except Exception as e:
			messagebox.showerror("错误", f"保存故事失败: {e}")
	
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
		self.btn_new_project = ttk.Button(btn_row, text="➕ 新建项目", command=self._on_new_project)
		self.btn_new_project.pack(side=LEFT, padx=(0, 6))
		self.btn_save_story = ttk.Button(btn_row, text="💾 保存当前故事", command=self._on_save_story, state=DISABLED)
		self.btn_save_story.pack(side=LEFT, padx=6)
		
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
		
		self.btn_load_project = ttk.Button(btn_frame, text="📖 加载选中项目", command=self._on_load_project)
		self.btn_load_project.pack(side=LEFT, padx=(0, 6))
		self.btn_refresh_list = ttk.Button(btn_frame, text="🔄 刷新列表", command=self._refresh_project_list)
		self.btn_refresh_list.pack(side=LEFT, padx=6)
		self.btn_delete_project = ttk.Button(btn_frame, text="🗑️ 删除选中项目", command=self._on_delete_project)
		self.btn_delete_project.pack(side=LEFT, padx=6)
		
		# 初始加载项目列表
		self._refresh_project_list()
	

