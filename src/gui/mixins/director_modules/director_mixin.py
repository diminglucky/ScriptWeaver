"""
导演页面混入类 - 故事到视频的完整工作流UI
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog, END, DISABLED, NORMAL
from tkinter.scrolledtext import ScrolledText
import threading
import os
import subprocess

from .script_generator import ScriptGeneratorMixin
from .shot_list_generator import ShotListGeneratorMixin
from .video_prompt_builder import VideoPromptBuilderMixin
from .scene_image_generator import SceneImageGeneratorMixin
from .project_persistence import ProjectPersistenceMixin
from .sd_consistency_generator import SDConsistencyMixin
from .shot_viewer import ShotViewerMixin


class DirectorMixin(ScriptGeneratorMixin, ShotListGeneratorMixin, VideoPromptBuilderMixin, 
				   SceneImageGeneratorMixin, ProjectPersistenceMixin, SDConsistencyMixin, ShotViewerMixin):
	"""导演页面 - 整合所有视频制作功能"""
	
	def _build_director_page(self) -> None:
		"""构建导演页面UI"""
		
		# 初始化人物种子映射表，确保同一人物在所有分镜中使用相同种子
		if not hasattr(self, 'character_seed_map'):
			self.character_seed_map = {}
		
		# 创建主容器
		director_frame = ttk.Frame(self.notebook)
		self.notebook.add(director_frame, text="🎬 导演")
		
		# 创建主布局 - 三列设计
		# 左列：工作流面板 | 中列：内容展示 | 右列：设置面板
		
		# ===== 左侧工作流面板（可滚动） =====
		left_outer_frame = ttk.Frame(director_frame, width=270)
		left_outer_frame.pack(side="left", fill="y", expand=False, padx=10, pady=10)
		left_outer_frame.pack_propagate(False)
		
		# 创建Canvas和Scrollbar
		left_canvas = tk.Canvas(left_outer_frame, bg="#2b2b2b", highlightthickness=0, width=250)
		left_scrollbar = ttk.Scrollbar(left_outer_frame, orient="vertical", command=left_canvas.yview)
		left_panel = ttk.Frame(left_canvas)
		
		# 配置滚动
		left_panel.bind(
			"<Configure>",
			lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all"))
		)
		left_canvas.create_window((0, 0), window=left_panel, anchor="nw", width=250)
		left_canvas.configure(yscrollcommand=left_scrollbar.set)
		
		# 鼠标滚轮支持 - 直接绑定到canvas避免冲突
		def _on_left_mousewheel(event):
			left_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
		
		# 绑定滚轮事件到canvas
		left_canvas.bind("<MouseWheel>", _on_left_mousewheel)
		left_panel.bind("<MouseWheel>", _on_left_mousewheel)
		
		# 递归绑定所有子控件，确保无论鼠标在哪里都能滚动
		def bind_mousewheel_recursive(widget):
			widget.bind("<MouseWheel>", _on_left_mousewheel)
			for child in widget.winfo_children():
				bind_mousewheel_recursive(child)
		
		# 延迟绑定，确保所有控件都已创建
		def bind_all_children():
			bind_mousewheel_recursive(left_panel)
		self.after(100, bind_all_children)
		
		left_canvas.pack(side="left", fill="both", expand=True)
		left_scrollbar.pack(side="right", fill="y")
		
		workflow_label = ttk.Label(left_panel, text="🎬 工作流", font=("Microsoft YaHei", 12, "bold"))
		workflow_label.pack(pady=(0, 10))
		
		# 步骤1：故事转剧本
		step1_frame = ttk.LabelFrame(left_panel, text="【步骤1】故事转剧本", padding=10)
		step1_frame.pack(fill="x", pady=5)
		ttk.Button(step1_frame, text="📝 生成剧本", command=self._on_story_to_script).pack(fill="x")
		
		# 步骤2：剧本转分镜
		step2_frame = ttk.LabelFrame(left_panel, text="【步骤2】剧本转分镜", padding=10)
		step2_frame.pack(fill="x", pady=5)
		
		def _debug_shot_button():
			print("🎬 【按钮点击】生成分镜按钮被点击")
			self._on_script_to_shots()
		
		ttk.Button(step2_frame, text="🎬 生成分镜", command=_debug_shot_button).pack(fill="x", pady=(0, 5))
		ttk.Button(step2_frame, text="📋 查看所有分镜", command=self.open_shot_viewer).pack(fill="x")
		
		# 步骤3：一致性设定
		step3_frame = ttk.LabelFrame(left_panel, text="【步骤3】一致性设定", padding=10)
		step3_frame.pack(fill="x", pady=5)
		ttk.Button(step3_frame, text="👥 编辑设定表", command=self._on_edit_consistency).pack(fill="x")
		
		# 添加SD参考图片生成按钮（仅在使用本地SD时显示）
		self.sd_ref_button = ttk.Button(
			step3_frame, 
			text="🎨 生成SD参考图片", 
			command=self._generate_character_references
		)
		# 检查是否使用本地SD
		if hasattr(self, 'img_api_preset') and self.img_api_preset.get() == "本地 Stable Diffusion":
			self.sd_ref_button.pack(fill="x", pady=(5, 0))
		
		self.consistency_status_label = ttk.Label(step3_frame, text="未设定", foreground="gray")
		self.consistency_status_label.pack(pady=(5, 0))
		
		# 步骤4：生成分镜图片
		step4_frame = ttk.LabelFrame(left_panel, text="【步骤4】生成图片", padding=10)
		step4_frame.pack(fill="x", pady=5)
		
		# 选择分镜下拉框
		ttk.Label(step4_frame, text="选择分镜:").pack(anchor="w", pady=(0, 2))
		self.shot_select_var = tk.StringVar()
		self.shot_select_combo = ttk.Combobox(
			step4_frame,
			textvariable=self.shot_select_var,
			state="readonly",
			width=18
		)
		self.shot_select_combo.pack(fill="x", pady=(0, 5))
		self.shot_select_combo['values'] = ["全部分镜"]
		self.shot_select_combo.current(0)
		
		# 生成按钮 - 改为垂直布局避免遮挡
		ttk.Button(step4_frame, text="🖼️  生成图片", command=self._on_generate_selected_shot).pack(fill="x", pady=(0, 5))
		ttk.Button(step4_frame, text="🗑️  管理图片", command=self._on_manage_images).pack(fill="x", pady=(0, 5))
		
		# 刷新按钮（调试用）
		ttk.Button(step4_frame, text="🔄 刷新列表", command=self._refresh_shot_combo).pack(fill="x", pady=(0, 0))
		
		# 步骤5：生成视频提示词
		step5_frame = ttk.LabelFrame(left_panel, text="【步骤5】视频提示词", padding=10)
		step5_frame.pack(fill="x", pady=5)
		ttk.Button(step5_frame, text="🎥 生成提示词", command=self._on_generate_video_prompt).pack(fill="x")
		
		# 步骤6：导出指南
		step6_frame = ttk.LabelFrame(left_panel, text="【步骤6】视频制作", padding=10)
		step6_frame.pack(fill="x", pady=5)
		ttk.Button(step6_frame, text="📤 导出指南", command=self._on_export_video_guide).pack(fill="x")
		
		# ===== 中间内容展示区 =====
		middle_panel = ttk.Frame(director_frame)
		middle_panel.pack(side="left", fill="both", expand=True, padx=10, pady=10)
		
		# 使用Notebook来切换显示不同的内容
		self.director_content_notebook = ttk.Notebook(middle_panel)
		self.director_content_notebook.pack(fill="both", expand=True)
		
		# Tab1：剧本显示
		script_frame = ttk.Frame(self.director_content_notebook)
		self.director_content_notebook.add(script_frame, text="📝 剧本")
		self.script_text = ScrolledText(script_frame, height=25, width=80, wrap="word", font=("Consolas", 10))
		self.script_text.pack(fill="both", expand=True, padx=5, pady=5)
		
		# Tab2：分镜头显示
		shots_frame = ttk.Frame(self.director_content_notebook)
		self.director_content_notebook.add(shots_frame, text="🎬 分镜头")
		
		# 添加工具栏
		shots_toolbar = ttk.Frame(shots_frame)
		shots_toolbar.pack(fill="x", padx=5, pady=5)
		ttk.Button(
			shots_toolbar, 
			text="📋 查看详细分镜", 
			command=self.open_shot_viewer
		).pack(side="left", padx=5)
		
		self.shots_list = ScrolledText(shots_frame, height=25, width=80, wrap="word", font=("Microsoft YaHei", 11))
		self.shots_list.pack(fill="both", expand=True, padx=5, pady=5)
		
		# Tab3：图片预览
		images_frame = ttk.Frame(self.director_content_notebook)
		self.director_content_notebook.add(images_frame, text="🖼️  图片预览")
		
		# 创建可滚动的图片网格
		self.director_images_canvas = tk.Canvas(images_frame, bg="#1e1e1e", highlightthickness=0)
		scrollbar = ttk.Scrollbar(images_frame, orient="vertical", command=self.director_images_canvas.yview)
		self.director_images_scrollable = ttk.Frame(self.director_images_canvas)
		self.director_images_scrollable.bind(
			"<Configure>",
			lambda e: self.director_images_canvas.configure(scrollregion=self.director_images_canvas.bbox("all"))
		)
		self.director_images_canvas.create_window((0, 0), window=self.director_images_scrollable, anchor="nw")
		self.director_images_canvas.configure(yscrollcommand=scrollbar.set)
		
		self.director_images_canvas.pack(side="left", fill="both", expand=True)
		scrollbar.pack(side="right", fill="y")
		
		# Tab4：视频提示词
		prompt_frame = ttk.Frame(self.director_content_notebook)
		self.director_content_notebook.add(prompt_frame, text="🎥 视频提示词")
		self.video_prompt_text = ScrolledText(prompt_frame, height=25, width=80, wrap="word", font=("Consolas", 10))
		self.video_prompt_text.pack(fill="both", expand=True, padx=5, pady=5)
		
		# ===== 右侧设置面板 =====
		right_panel = ttk.Frame(director_frame, width=250)
		right_panel.pack(side="right", fill="both", expand=False, padx=10, pady=10)
		right_panel.pack_propagate(False)
		
		settings_label = ttk.Label(right_panel, text="⚙️  设置", font=("Microsoft YaHei", 12, "bold"))
		settings_label.pack(pady=(0, 10))
		
		# 视频平台选择
		platform_frame = ttk.LabelFrame(right_panel, text="📹 视频平台", padding=10)
		platform_frame.pack(fill="x", pady=5)
		
		self.director_video_platform = tk.StringVar(value="jimeng")
		platforms = [
			("即梦AI (推荐)", "jimeng"),
			("Runway ML", "runway"),
			("剪映/CapCut", "capcut"),
		]
		for text, value in platforms:
			ttk.Radiobutton(platform_frame, text=text, variable=self.director_video_platform, value=value).pack(anchor="w", pady=2)
		
		# 一致性设置
		consistency_frame = ttk.LabelFrame(right_panel, text="👥 一致性设置", padding=10)
		consistency_frame.pack(fill="x", pady=5)
		
		ttk.Label(consistency_frame, text="参考人物:").pack(anchor="w")
		self.director_reference_char = tk.StringVar()
		char_dropdown = ttk.Combobox(
			consistency_frame,
			textvariable=self.director_reference_char,
			values=["不使用参考"],
			state="readonly",
			width=18
		)
		char_dropdown.pack(fill="x", pady=5)
		char_dropdown.current(0)
		
		# 提示词参数
		params_frame = ttk.LabelFrame(right_panel, text="🎨 生成参数", padding=10)
		params_frame.pack(fill="x", pady=5)
		
		ttk.Label(params_frame, text="分辨率:").pack(anchor="w")
		self.director_resolution = tk.StringVar(value="768x512")
		res_dropdown = ttk.Combobox(
			params_frame,
			textvariable=self.director_resolution,
			values=["512x512", "768x512", "1024x768"],
			state="readonly",
			width=18
		)
		res_dropdown.pack(fill="x", pady=5)
		
		ttk.Label(params_frame, text="图片风格:").pack(anchor="w")
		self.director_style = tk.StringVar(value="photorealistic")
		style_dropdown = ttk.Combobox(
			params_frame,
			textvariable=self.director_style,
			values=["photorealistic", "cinematic", "artistic"],
			state="readonly",
			width=18
		)
		style_dropdown.pack(fill="x", pady=5)
		
		# 导出和保存
		export_frame = ttk.LabelFrame(right_panel, text="📤 导出", padding=10)
		export_frame.pack(fill="x", pady=5)
		
		ttk.Button(export_frame, text="💾 保存项目", command=self._on_save_director_project).pack(fill="x", pady=2)
		ttk.Button(export_frame, text="📋 复制提示词", command=self._on_copy_video_prompt).pack(fill="x", pady=2)
		ttk.Button(export_frame, text="📁 打开输出目录", command=self._on_open_output_folder).pack(fill="x", pady=2)
		
		# 保存对象引用，以便其他地方使用
		self.current_shots = []
		self.current_script = ""
		
	def _refresh_shot_combo(self) -> None:
		"""手动刷新分镜下拉框"""
		if not hasattr(self, 'current_shots') or not self.current_shots:
			messagebox.showinfo("提示", "还没有生成分镜")
			return
		
		if not hasattr(self, 'shot_select_combo'):
			messagebox.showerror("错误", "未找到分镜选择下拉框")
			return
		
		shot_options = ["全部分镜"] + [
			f"分镜{s.get('shot_number', i+1)} - {s.get('scene_id', '场景')} - {s.get('shot_type', '未知')}"
			for i, s in enumerate(self.current_shots)
		]
		
		self.shot_select_combo['values'] = shot_options
		self.shot_select_combo.current(0)
		self.shot_select_combo.update_idletasks()
		
		messagebox.showinfo("成功", f"已刷新！共 {len(self.current_shots)} 个分镜\n\n请点击下拉框查看")
		print(f"✅ 手动刷新下拉框成功")
		print(f"选项列表: {shot_options}")
	
	def _on_edit_consistency(self) -> None:
		"""编辑一致性设定表"""
		from .consistency_dialog import ConsistencyDialog
		
		# 获取当前人物列表
		characters = []
		if hasattr(self, 'current_shots') and self.current_shots:
			# 从分镜中提取人物
			for shot in self.current_shots:
				chars = shot.get('characters', [])
				for char in chars:
					if char and char not in characters:
						characters.append(char)
		
		# 如果没有从分镜中获取到人物，尝试从剧本中提取
		if not characters and hasattr(self, 'current_script'):
			# 简单的人物名称提取（可以后续优化）
			import re
			# 查找常见的人物名称模式
			names = re.findall(r'([李王张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾萧田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤][一-龥]{1,2})', self.current_script)
			characters = list(set(names))[:10]  # 最多取10个
		
		# 获取当前的一致性设定
		consistency_data = getattr(self, 'consistency_data', None)
		
		# 打开对话框（非模态）
		dialog = ConsistencyDialog(self, consistency_data, characters)
		
		# 存储对话框引用以便后续访问
		self._consistency_dialog = dialog
		
		# 不需要绑定关闭事件，对话框自己处理
		# 但需要在对话框关闭后获取结果
		def check_dialog_result():
			"""定期检查对话框是否关闭并获取结果"""
			if dialog.winfo_exists():
				# 对话框还在，继续检查
				self.after(100, check_dialog_result)
			else:
				# 对话框已关闭，获取结果
				result = dialog.result
				if result is not None:
					self.consistency_data = result
					self.status.set("✅ 一致性设定已保存")
					
					# 更新UI显示
					char_count = len(result.get("characters", {}))
					if hasattr(self, 'consistency_status_label'):
						self.consistency_status_label.config(
							text=f"已设定 {char_count} 个人物",
							foreground="green"
						)
					
					# 自动保存项目
					if hasattr(self, 'save_complete_project'):
						self.save_complete_project()
						print("✅ 一致性设定已自动保存到项目")
				else:
					self.status.set("❌ 未保存一致性设定")
		
		# 开始检查
		self.after(100, check_dialog_result)
		
	def _on_generate_selected_shot(self) -> None:
		"""生成选中的分镜图片"""
		if not self.current_shots:
			messagebox.showwarning("提示", "请先生成分镜头")
			return
		
		selected = self.shot_select_var.get()
		
		if selected == "全部分镜":
			# 生成所有分镜
			self._on_generate_shot_images()
		else:
			# 生成单个分镜
			# 从选项中提取分镜编号
			import re
			match = re.match(r"分镜(\d+)", selected)
			if match:
				shot_num = int(match.group(1))
				self._generate_single_shot(shot_num)
			else:
				messagebox.showwarning("提示", "无法识别选中的分镜")
	
	def _generate_single_shot(self, shot_num: int) -> None:
		"""生成单个分镜的图片"""
		# 找到对应的分镜
		shot = None
		for s in self.current_shots:
			if s.get('shot_number') == shot_num:
				shot = s
				break
		
		if not shot:
			messagebox.showwarning("提示", f"未找到分镜 {shot_num}")
			return
		
		# 询问生成多少张
		num_images = simpledialog.askinteger(
			"生成设置",
			f"为分镜{shot_num}生成多少张候选图片？",
			initialvalue=3,
			minvalue=1,
			maxvalue=10
		)
		
		if not num_images:
			return
		
		def task():
			try:
				self.status.set(f"🖼️  正在生成分镜 {shot_num}...")
				
				# 获取项目路径
				if hasattr(self.current_project, 'project_dir'):
					project_path = str(self.current_project.project_dir)
				elif isinstance(self.current_project, dict):
					project_path = self.current_project.get('path', '')
				else:
					project_path = str(self.current_project)
				
				output_dir = os.path.join(project_path, 'director', 'shots')
				os.makedirs(output_dir, exist_ok=True)
				
				# 构建描述
				description = self._build_shot_description(shot, shot_num)
				
				# 生成多张图片
				generated = []
				for i in range(num_images):
					self.status.set(f"🖼️  分镜 {shot_num} - 图片 {i+1}/{num_images}")
					
					try:
						image_path = self._generate_single_shot_image(
							shot_num=shot_num,
							shot_variant=i+1,
							description=description,
							output_dir=output_dir,
							seed_offset=i
						)
						
						if image_path and os.path.exists(image_path):
							generated.append(image_path)
							print(f"✅ 生成分镜 {shot_num} 变体 {i+1}: {os.path.basename(image_path)}")
					except Exception as e:
						print(f"❌ 生成失败: {str(e)}")
				
				self.after(0, lambda: messagebox.showinfo(
					"完成",
					f"分镜 {shot_num} 生成完成\n成功: {len(generated)}/{num_images} 张"
				))
				self.status.set("✅ 图片生成完成")
				
			except Exception as e:
				self.after(0, lambda: messagebox.showerror("错误", f"生成失败: {str(e)}"))
				self.status.set("❌ 生成失败")
		
		import threading
		threading.Thread(target=task, daemon=True).start()
	
	def _on_manage_images(self) -> None:
		"""管理已生成的图片"""
		if not self.current_project:
			messagebox.showwarning("提示", "请先创建或加载项目")
			return
		
		# 获取项目路径
		if hasattr(self.current_project, 'project_dir'):
			project_path = str(self.current_project.project_dir)
		elif isinstance(self.current_project, dict):
			project_path = self.current_project.get('path', '')
		else:
			project_path = str(self.current_project)
		
		shots_dir = os.path.join(project_path, 'director', 'shots')
		
		if not os.path.exists(shots_dir):
			messagebox.showinfo("提示", "还没有生成任何图片")
			return
		
		# 打开图片管理对话框
		self._open_image_manager_dialog(shots_dir)
	
	def _open_image_manager_dialog(self, shots_dir: str) -> None:
		"""打开图片管理对话框"""
		import tkinter as tk
		from tkinter import ttk
		from PIL import Image, ImageTk
		
		dialog = tk.Toplevel(self)
		dialog.title("🖼️  图片管理")
		dialog.geometry("900x700")
		dialog.transient(self)
		
		# 获取所有图片
		image_files = [f for f in os.listdir(shots_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
		image_files.sort()
		
		if not image_files:
			ttk.Label(dialog, text="没有找到图片", font=("Arial", 14)).pack(pady=50)
			ttk.Button(dialog, text="关闭", command=dialog.destroy).pack()
			return
		
		# 创建滚动区域
		canvas = tk.Canvas(dialog)
		scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
		scrollable_frame = ttk.Frame(canvas)
		
		scrollable_frame.bind(
			"<Configure>",
			lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
		)
		
		canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
		canvas.configure(yscrollcommand=scrollbar.set)
		
		# 存储选中的图片
		selected_images = {}
		
		# 显示图片网格
		cols = 3
		for idx, img_file in enumerate(image_files):
			row = idx // cols
			col = idx % cols
			
			img_path = os.path.join(shots_dir, img_file)
			
			# 创建图片框
			frame = ttk.LabelFrame(scrollable_frame, text=img_file, padding=5)
			frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
			
			try:
				# 加载并缩放图片
				img = Image.open(img_path)
				img.thumbnail((250, 200))
				photo = ImageTk.PhotoImage(img)
				
				label = ttk.Label(frame, image=photo)
				label.image = photo  # 保持引用
				label.pack()
			except:
				ttk.Label(frame, text="无法加载图片").pack()
			
			# 复选框
			var = tk.BooleanVar(value=True)  # 默认保留
			selected_images[img_file] = var
			ttk.Checkbutton(
				frame,
				text="保留此图片",
				variable=var
			).pack()
		
		canvas.pack(side="left", fill="both", expand=True)
		scrollbar.pack(side="right", fill="y")
		
		# 底部按钮
		btn_frame = ttk.Frame(dialog)
		btn_frame.pack(side="bottom", fill="x", padx=10, pady=10)
		
		ttk.Label(btn_frame, text=f"共 {len(image_files)} 张图片").pack(side="left")
		
		def delete_unselected():
			to_delete = [f for f, var in selected_images.items() if not var.get()]
			if not to_delete:
				messagebox.showinfo("提示", "没有要删除的图片")
				return
			
			if messagebox.askyesno("确认", f"确定要删除 {len(to_delete)} 张图片吗？"):
				for f in to_delete:
					try:
						os.remove(os.path.join(shots_dir, f))
						print(f"🗑️  删除图片: {f}")
					except Exception as e:
						print(f"删除失败 {f}: {e}")
				
				messagebox.showinfo("完成", f"已删除 {len(to_delete)} 张图片")
				dialog.destroy()
		
		ttk.Button(btn_frame, text="🗑️  删除未选中", command=delete_unselected).pack(side="right", padx=5)
		ttk.Button(btn_frame, text="✅ 全选", command=lambda: [v.set(True) for v in selected_images.values()]).pack(side="right", padx=5)
		ttk.Button(btn_frame, text="❌ 全不选", command=lambda: [v.set(False) for v in selected_images.values()]).pack(side="right", padx=5)
	
	def _on_generate_shot_images(self) -> None:
		"""生成所有分镜头图片"""
		if not self.current_shots:
			messagebox.showwarning("提示", "请先生成分镜头")
			return
		
		def task():
			try:
				self.status.set("🖼️  正在生成分镜头图片...")
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("生成分镜图片中...", "🖼️"))
				
				generated_count = 0
				failed_shots = []
				
				# 确保有输出目录 - 兼容不同项目对象类型
				if hasattr(self.current_project, 'project_dir'):
					project_path = str(self.current_project.project_dir)
				elif isinstance(self.current_project, dict):
					project_path = self.current_project.get('path', '')
				else:
					project_path = str(self.current_project)
				
				output_dir = os.path.join(project_path, 'director', 'shots')
				os.makedirs(output_dir, exist_ok=True)
				
				# 询问每个分镜生成多少张图片
				num_images_per_shot = simpledialog.askinteger(
					"生成设置",
					"每个分镜生成多少张候选图片？\n（建议3-5张，方便选择最佳效果）",
					initialvalue=3,
					minvalue=1,
					maxvalue=10
				)
				
				if not num_images_per_shot:
					num_images_per_shot = 3  # 默认3张
				
				total_images = len(self.current_shots) * num_images_per_shot
				current_image = 0
				
				for i, shot in enumerate(self.current_shots, 1):
					try:
						# 调用图片生成逻辑
						self.status.set(f"🖼️  正在生成分镜 {i}/{len(self.current_shots)}...")
						
						# 构建图片描述
						description = self._build_shot_description(shot, i)
						
						# 为每个分镜生成多张图片
						shot_images = []
						for j in range(num_images_per_shot):
							current_image += 1
							self.status.set(f"🖼️  分镜 {i}/{len(self.current_shots)} - 图片 {j+1}/{num_images_per_shot} (总进度: {current_image}/{total_images})")
							
							try:
								# 生成图片（每次略微调整种子以产生变化）
								image_path = self._generate_single_shot_image(
									shot_num=i,
									shot_variant=j+1,
									description=description,
									output_dir=output_dir,
									seed_offset=j  # 添加种子偏移以产生变化
								)
								
								if image_path and os.path.exists(image_path):
									shot_images.append(image_path)
									print(f"✅ 生成分镜 {i} 变体 {j+1}: {os.path.basename(image_path)}")
								else:
									print(f"⚠️  生成分镜 {i} 变体 {j+1} 失败")
							except Exception as e:
								print(f"❌ 生成分镜 {i} 变体 {j+1} 失败: {str(e)}")
						
						if shot_images:
							generated_count += 1
							print(f"✅ 分镜 {i} 完成，共生成 {len(shot_images)} 张图片")
						else:
							failed_shots.append(i)
							print(f"❌ 分镜 {i} 所有变体都失败")
						
					except Exception as e:
						failed_shots.append(i)
						print(f"生成分镜 {i} 失败: {str(e)}")
						continue
				
				self.after(0, lambda: messagebox.showinfo(
					"完成",
					f"成功生成 {generated_count}/{len(self.current_shots)} 张分镜头图片"
				))
				
			except Exception as e:
				self.after(0, lambda: messagebox.showerror("错误", f"生成分镜图片失败: {str(e)}"))
			finally:
				self.status.set("✅ 分镜图片生成完成")
				if hasattr(self, 'update_header_status'):
					self.after(0, lambda: self.update_header_status("完成", "✅"))
		
		threading.Thread(target=task, daemon=True).start()
	
	def _on_generate_video_prompt(self) -> None:
		"""生成视频提示词"""
		if not self.current_shots:
			messagebox.showwarning("提示", "请先生成分镜头")
			return
		
		platform = self.director_video_platform.get()
		
		if platform == "jimeng":
			prompt = self.build_jimeng_ai_prompt(self.current_shots)
		elif platform == "runway":
			prompt = self.build_runway_ml_guide(self.current_shots)
		else:  # capcut
			prompt = self.build_capcut_template(self.current_shots)
		
		# 显示提示词
		self.director_content_notebook.select(3)  # 切换到视频提示词标签
		self.video_prompt_text.config(state="normal")
		self.video_prompt_text.delete("1.0", END)
		self.video_prompt_text.insert(END, prompt)
		self.video_prompt_text.config(state="disabled")
		
		messagebox.showinfo("成功", "视频提示词已生成")
	
	def _on_export_video_guide(self) -> None:
		"""导出视频制作指南"""
		if not self.current_shots:
			messagebox.showwarning("提示", "请先生成分镜头")
			return
		
		# 生成完整的视频制作指南
		guide = self.build_image_to_video_guide(self.current_shots)
		
		# 显示在新窗口中
		guide_window = tk.Toplevel(self)
		guide_window.title("视频制作指南")
		guide_window.geometry("900x700")
		
		guide_text = ScrolledText(guide_window, font=("Consolas", 10), wrap="word")
		guide_text.pack(fill="both", expand=True, padx=10, pady=10)
		guide_text.insert(END, guide)
		guide_text.config(state="disabled")
		
		# 导出按钮
		button_frame = ttk.Frame(guide_window)
		button_frame.pack(fill="x", padx=10, pady=10)
		
		def save_guide():
			file_path = filedialog.asksaveasfilename(
				defaultextension=".md",
				filetypes=[("Markdown", "*.md"), ("Text", "*.txt")]
			)
			if file_path:
				with open(file_path, 'w', encoding='utf-8') as f:
					f.write(guide)
				messagebox.showinfo("成功", f"指南已保存到: {file_path}")
		
		ttk.Button(button_frame, text="💾 保存指南", command=save_guide).pack(side="left", padx=5)
		ttk.Button(button_frame, text="复制全部", command=lambda: self._copy_text(guide)).pack(side="left", padx=5)
	
	def _on_save_director_project(self) -> None:
		"""保存导演项目"""
		try:
			# 获取当前项目路径
			if not hasattr(self, 'current_project') or not self.current_project:
				messagebox.showwarning("提示", "请先打开一个项目")
				return
			
			project_path = self.current_project.path if hasattr(self.current_project, 'path') else str(self.current_project)
			
			# 保存项目
			success = self.save_director_project(project_path)
			
			if success:
				messagebox.showinfo("成功", "导演项目已保存完成！\n\n已保存内容：\n- 剧本\n- 分镜头列表\n- 一致性设定\n- 生成参数\n- 视频提示词")
			else:
				messagebox.showerror("错误", "项目保存失败，请检查权限")
		
		except Exception as e:
			messagebox.showerror("错误", f"保存项目失败: {str(e)}")
	
	def _on_copy_video_prompt(self) -> None:
		"""复制视频提示词到剪贴板"""
		prompt = self.video_prompt_text.get("1.0", END)
		if prompt.strip():
			self.clipboard_clear()
			self.clipboard_append(prompt)
			messagebox.showinfo("成功", "视频提示词已复制到剪贴板")
		else:
			messagebox.showwarning("提示", "请先生成视频提示词")
	
	def _on_open_output_folder(self) -> None:
		"""打开输出文件夹"""
		import os
		import subprocess
		
		output_dir = os.path.join(os.getcwd(), "director_output")
		os.makedirs(output_dir, exist_ok=True)
		
		if os.path.exists(output_dir):
			subprocess.Popen(f'explorer "{output_dir}"')
			messagebox.showinfo("打开成功", f"输出文件夹: {output_dir}")
		else:
			messagebox.showwarning("错误", "无法打开文件夹")
	
	def _copy_text(self, text: str) -> None:
		"""复制文本到剪贴板"""
		self.clipboard_clear()
		self.clipboard_append(text)
		messagebox.showinfo("成功", "文本已复制")
	
	def build_runway_ml_guide(self, shots: list) -> str:
		"""为Runway ML生成指南"""
		guide = "【Runway ML 图片序列转视频指南】\n\n"
		guide += "1. 访问 https://runwayml.com\n"
		guide += "2. 创建新项目\n"
		guide += "3. 使用 Motion Brush 工具\n"
		guide += "4. 逐张上传分镜头图片\n"
		guide += "5. 在关键部位画出运动轨迹\n"
		guide += "6. 设置参数\n"
		guide += "7. 生成视频\n\n"
		
		guide += "【参数建议】\n"
		guide += "- Motion Intensity: medium\n"
		guide += "- Camera Motion: subtle zoom in\n"
		guide += "- Duration: 1.0 seconds per shot\n"
		guide += "- Frame Rate: 30fps\n\n"
		
		guide += "【镜头列表】\n"
		for i, shot in enumerate(shots, 1):
			guide += f"{i}. {shot.get('shot_type', 'Medium Shot')}\n"
			guide += f"   {shot.get('scene_description', '')[:80]}...\n"
		
		return guide
	
	def _build_shot_description(self, shot: dict, shot_num: int) -> str:
		"""为分镜构建SD优化的超详细提示词，确保人物和场景一致性"""
		
		# 检查是否使用SD
		use_sd = False
		if hasattr(self, 'img_api_preset') and hasattr(self, 'img_api_presets'):
			preset_name = self.img_api_preset.get()
			if preset_name in self.img_api_presets:
				provider = self.img_api_presets[preset_name].get("provider", "")
				use_sd = (provider == "sd")
		
		if use_sd:
			# 使用SD优化器生成英文提示词
			return self._build_sd_optimized_prompt(shot, shot_num)
		else:
			# 普通中文描述
			return self._build_chinese_description(shot, shot_num)
	
	def _build_chinese_description(self, shot: dict, shot_num: int) -> str:
		"""构建中文描述（用于非SD API）"""
		parts = []
		
		# 1. 场景ID和位置
		scene_id = shot.get('scene_id', '')
		location = shot.get('location', '')
		if scene_id or location:
			parts.append(f"【{scene_id}】{location}")
		
		# 2. 详细的视觉描述
		visual_desc = shot.get('visual_description', '')
		if visual_desc:
			parts.append(f"环境：{visual_desc}")
		
		# 3. 光线和氛围
		lighting = shot.get('lighting', '')
		atmosphere = shot.get('atmosphere', '')
		if lighting or atmosphere:
			parts.append(f"光线：{lighting}，氛围：{atmosphere}")
		
		# 4. 人物详细信息
		characters = shot.get('characters', [])
		character_details = shot.get('character_details', {})
		
		if characters:
			char_descriptions = []
			
			for char_name in characters:
				char_parts = []
				
				# 从分镜中获取的详细信息
				if isinstance(character_details, dict) and char_name in character_details:
					detail = character_details[char_name]
					
					if isinstance(detail, dict):
						# 外貌
						if detail.get('appearance'):
							char_parts.append(f"外貌：{detail['appearance']}")
						
						# 服装
						if detail.get('clothing'):
							char_parts.append(f"服装：{detail['clothing']}")
						
						# 表情
						if detail.get('expression'):
							char_parts.append(f"表情：{detail['expression']}")
						
						# 姿势
						if detail.get('posture'):
							char_parts.append(f"姿势：{detail['posture']}")
					elif isinstance(detail, str):
						char_parts.append(detail)
				
				# 补充一致性设定中的信息
				if hasattr(self, 'consistency_data') and self.consistency_data:
					consistency_chars = self.consistency_data.get('characters', {})
					if char_name in consistency_chars:
						char_data = consistency_chars[char_name]
						
						# 只添加分镜中没有的信息
						if not any('外貌' in p for p in char_parts):
							# 添加外貌
							appearance = char_data.get('appearance', {})
							face = appearance.get('face', {})
							hair = appearance.get('hair', {})
							
							app_parts = []
							if face.get('face_shape'):
								app_parts.append(face['face_shape'])
							if face.get('skin_tone'):
								app_parts.append(f"{face['skin_tone']}肤色")
							if face.get('eyes'):
								app_parts.append(face['eyes'])
							
							if hair.get('color') and hair.get('style'):
								hair_desc = f"{hair['color']}{hair.get('length', '')}{hair['style']}"
								if hair.get('bangs'):
									hair_desc += f"，{hair['bangs']}"
								app_parts.append(hair_desc)
							
							if app_parts:
								char_parts.append(f"外貌：{'，'.join(app_parts)}")
						
						if not any('服装' in p for p in char_parts):
							# 添加服装
							outfits = char_data.get('outfits', {})
							outfit = outfits.get('default', {})
							
							outfit_parts = []
							if outfit.get('top'):
								outfit_parts.append(outfit['top'])
							if outfit.get('bottom'):
								outfit_parts.append(outfit['bottom'])
							if outfit.get('shoes'):
								outfit_parts.append(outfit['shoes'])
							
							if outfit_parts:
								char_parts.append(f"服装：{'，'.join(outfit_parts)}")
				
				# 组合人物描述
				if char_parts:
					char_desc = f"【{char_name}】{' | '.join(char_parts)}"
					char_descriptions.append(char_desc)
			
			if char_descriptions:
				parts.append("人物：" + " || ".join(char_descriptions))
		
		# 5. 动作描述
		action = shot.get('action', '')
		if action:
			parts.append(f"动作：{action}")
		
		# 6. 情绪
		emotion = shot.get('emotion', '')
		if emotion:
			parts.append(f"情绪：{emotion}")
		
		# 7. 道具
		props = shot.get('props', [])
		if props:
			props_str = '，'.join(props) if isinstance(props, list) else props
			parts.append(f"道具：{props_str}")
		
		# 8. 镜头信息
		camera = shot.get('camera', {})
		if camera:
			cam_parts = []
			if camera.get('movement'):
				cam_parts.append(f"运动：{camera['movement']}")
			if camera.get('angle'):
				cam_parts.append(f"角度：{camera['angle']}")
			if camera.get('lens'):
				cam_parts.append(f"镜头：{camera['lens']}")
			
			if cam_parts:
				parts.append(f"摄影：{' | '.join(cam_parts)}")
		
		# 9. 连贯性提示
		continuity = shot.get('continuity', '')
		if continuity:
			parts.append(f"连贯：{continuity}")
		
		# 10. 镜头类型作为风格指导
		shot_type = shot.get('shot_type', '')
		if shot_type:
			parts.append(f"镜头类型：{shot_type}")
		
		# 组合所有部分，用换行分隔以提高可读性
		description = "\n".join(parts)
		
		# 添加质量标签
		description += "\n\n【质量要求】高质量，专业摄影，电影级，细节丰富，清晰锐利"
		
		return description
	
	def _build_sd_optimized_prompt(self, shot: dict, shot_num: int) -> str:
		"""为SD构建优化的英文提示词，确保人物和场景一致性"""
		from .sd_prompt_optimizer import SDPromptOptimizer
		
		# === 第一部分：质量和风格标签（最前面，权重最高） ===
		quality_tags = [
			"masterpiece", "best quality", "ultra detailed", "8k", "photorealistic",
			"cinematic lighting", "professional photography", "sharp focus",
			"highly detailed", "intricate details",
			"character consistency", "consistent character design", "same person"  # 添加一致性关键词
		]
		
		# === 第二部分：人物一致性描述（核心！） ===
		character_prompts = []
		characters = shot.get('characters', [])
		character_details = shot.get('character_details', {})
		
		for char_name in characters:
			char_parts = []
			
			# 从分镜获取详细信息
			if isinstance(character_details, dict) and char_name in character_details:
				detail = character_details[char_name]
				
				if isinstance(detail, dict):
					# 外貌特征（最重要！）
					if detail.get('appearance'):
						appearance = detail['appearance']
						# 提取关键特征
						char_parts.append(f"1person")
						
						# 年龄和性别
						if "岁" in appearance:
							import re
							age_match = re.search(r'(\d+)岁', appearance)
							if age_match:
								age = int(age_match.group(1))
								if age < 18:
									char_parts.append("teenage")
								elif age < 30:
									char_parts.append("young adult")
								elif age < 50:
									char_parts.append("middle-aged")
								else:
									char_parts.append("elderly")
						
						if "男" in appearance:
							char_parts.append("male")
						elif "女" in appearance:
							char_parts.append("female")
						
						# 发型
						if "黑发" in appearance or "黑色" in appearance:
							char_parts.append("black hair")
						if "短发" in appearance or "短寸" in appearance:
							char_parts.append("short hair")
						elif "长发" in appearance:
							char_parts.append("long hair")
						
						# 脸型
						if "国字脸" in appearance:
							char_parts.append("square jaw")
						elif "瓜子脸" in appearance:
							char_parts.append("oval face")
						
						# 眼睛
						if "大眼" in appearance:
							char_parts.append("large eyes")
						if "眼镜" in appearance or "黑框眼镜" in appearance:
							char_parts.append("wearing glasses, black frame glasses")
					
					# 服装（必须详细！）
					if detail.get('clothing'):
						clothing = detail['clothing']
						
						# 颜色
						if "白色" in clothing:
							char_parts.append("white")
						elif "黑色" in clothing:
							char_parts.append("black")
						elif "蓝色" in clothing:
							char_parts.append("blue")
						elif "红色" in clothing:
							char_parts.append("red")
						
						# 服装类型
						if "校服" in clothing:
							char_parts.append("school uniform")
						if "衬衫" in clothing:
							char_parts.append("shirt")
						if "T恤" in clothing:
							char_parts.append("t-shirt")
						if "裤" in clothing:
							char_parts.append("pants")
						if "背包" in clothing or "双肩包" in clothing:
							char_parts.append("backpack")
					
					# 表情（重要！）
					if detail.get('expression'):
						expression = detail['expression']
						
						if "疲惫" in expression or "疲倦" in expression:
							char_parts.append("tired expression, exhausted face")
						if "微笑" in expression:
							char_parts.append("smiling, gentle smile")
						if "严肃" in expression:
							char_parts.append("serious expression")
						if "空洞" in expression or "迷茫" in expression:
							char_parts.append("empty eyes, blank stare")
						if "紧闭" in expression and "嘴" in expression:
							char_parts.append("lips pressed together")
						if "皱眉" in expression or "眉头" in expression:
							char_parts.append("frowning, furrowed brows")
					
					# 姿势和动作
					if detail.get('posture'):
						posture = detail['posture']
						
						if "站" in posture:
							char_parts.append("standing")
						elif "坐" in posture:
							char_parts.append("sitting")
						elif "蹲" in posture:
							char_parts.append("crouching")
						
						if "前倾" in posture:
							char_parts.append("leaning forward")
						if "耷拉" in posture or "下垂" in posture:
							char_parts.append("slouched shoulders")
			
			# ★★★ 优先使用一致性设定中的完整信息 ★★★
			if hasattr(self, 'consistency_data') and self.consistency_data:
				consistency_chars = self.consistency_data.get('characters', {})
				if char_name in consistency_chars:
					char_data = consistency_chars[char_name]
					
					# 在最开始添加"固定人物"标记
					if not char_parts:
						char_parts.append("1person")
					
					# 外貌
					appearance = char_data.get('appearance', {})
					face = appearance.get('face', {})
					hair = appearance.get('hair', {})
					body = appearance.get('body', {})
					
					# 性别（优先级最高）
					gender = char_data.get('gender', '')
					if gender and 'male' not in ' '.join(char_parts) and 'female' not in ' '.join(char_parts):
						if "男" in gender:
							char_parts.insert(1, "male")
						elif "女" in gender:
							char_parts.insert(1, "female")
					
					# 年龄
					age = char_data.get('age', '')
					if age and 'teenage' not in ' '.join(char_parts):
						if "16" in str(age) or "17" in str(age) or "18" in str(age):
							char_parts.insert(2, "teenage, high school student")
						elif "20" in str(age) or "25" in str(age):
							char_parts.insert(2, "young adult")
					
					# 发型（一致性设定中的最优先）
					if hair:
						hair_desc = []
						color = hair.get('color', '')
						length = hair.get('length', '')
						style = hair.get('style', '')
						
						if "黑" in color:
							hair_desc.append("black")
						elif "棕" in color:
							hair_desc.append("brown")
						elif "金" in color:
							hair_desc.append("blonde")
						
						if "短" in length:
							hair_desc.append("short")
						elif "长" in length:
							hair_desc.append("long")
						elif "中" in length:
							hair_desc.append("medium")
						
						if "直" in style:
							hair_desc.append("straight")
						elif "卷" in style:
							hair_desc.append("wavy")
						
						if hair_desc:
							hair_desc.append("hair")
							char_parts.append(" ".join(hair_desc))
					
					# 脸部特征
					if face:
						if face.get('skin_tone'):
							skin = face['skin_tone']
							if "白" in skin or "苍白" in skin:
								char_parts.append("pale skin, fair skin")
							elif "小麦" in skin:
								char_parts.append("tan skin, healthy complexion")
						
						if face.get('face_shape'):
							face_shape = face['face_shape']
							if "国字" in face_shape:
								char_parts.append("square face, strong jawline")
							elif "瓜子" in face_shape or "鹅蛋" in face_shape:
								char_parts.append("oval face, delicate features")
						
						if face.get('eyes'):
							char_parts.append(face['eyes'])
					
					# 体型
					if body.get('body_type'):
						body_type = body['body_type']
						if "苗条" in body_type or "瘦" in body_type:
							char_parts.append("slim build, slender body")
						elif "健壮" in body_type or "强壮" in body_type:
							char_parts.append("athletic build, fit body")
						elif "中等" in body_type:
							char_parts.append("average build")
					
					if body.get('height'):
						height = body['height']
						if "高" in height:
							char_parts.append("tall")
						elif "矮" in height:
							char_parts.append("short")
					
					# 服装（从一致性设定）
					outfits = char_data.get('outfits', {})
					outfit = outfits.get('default', {})
					
					if outfit:
						outfit_parts = []
						if outfit.get('top'):
							top = outfit['top']
							if "白" in top:
								outfit_parts.append("white")
							if "衬衫" in top:
								outfit_parts.append("dress shirt")
							elif "T恤" in top:
								outfit_parts.append("t-shirt")
							elif "校服" in top:
								outfit_parts.append("school uniform shirt")
						
						if outfit.get('bottom'):
							bottom = outfit['bottom']
							if "裤" in bottom:
								outfit_parts.append("pants")
							if "牛仔" in bottom:
								outfit_parts.append("jeans")
							if "校服" in bottom:
								outfit_parts.append("school uniform pants")
						
						if outfit.get('shoes'):
							shoes = outfit['shoes']
							if "运动鞋" in shoes:
								outfit_parts.append("sneakers")
							elif "皮鞋" in shoes:
								outfit_parts.append("dress shoes")
						
						if outfit_parts:
							char_parts.append("wearing " + ", ".join(outfit_parts))
			
			if char_parts:
				# 去重并组合
				char_prompt = ", ".join(dict.fromkeys(char_parts))
				character_prompts.append(char_prompt)
		
		# === 第三部分：场景和环境 ===
		scene_parts = []
		
		# 视觉描述
		visual_desc = shot.get('visual_description', '')
		if visual_desc:
			# 提取关键环境元素
			if "教室" in visual_desc:
				scene_parts.append("classroom")
			if "办公室" in visual_desc:
				scene_parts.append("office")
			if "阳光" in visual_desc or "太阳" in visual_desc:
				scene_parts.append("sunlight, natural lighting")
			if "窗" in visual_desc:
				scene_parts.append("window")
			if "桌" in visual_desc:
				scene_parts.append("desk")
			if "清晨" in visual_desc or "早晨" in visual_desc:
				scene_parts.append("morning")
			if "黄昏" in visual_desc or "傍晚" in visual_desc:
				scene_parts.append("evening, sunset")
			
			# 添加原始详细描述的翻译版本
			scene_parts.append("detailed environment")
		
		# 光线
		lighting = shot.get('lighting', '')
		if lighting:
			if "自然光" in lighting:
				scene_parts.append("natural light")
			if "柔和" in lighting:
				scene_parts.append("soft lighting")
			if "高对比" in lighting:
				scene_parts.append("high contrast")
			if "暖色" in lighting or "warm" in lighting:
				scene_parts.append("warm color temperature")
		
		# 氛围
		atmosphere = shot.get('atmosphere', '')
		if atmosphere:
			if "寂静" in atmosphere or "安静" in atmosphere:
				scene_parts.append("quiet atmosphere, serene")
			if "紧张" in atmosphere:
				scene_parts.append("tense atmosphere")
			if "温馨" in atmosphere:
				scene_parts.append("warm atmosphere, cozy")
		
		# === 第四部分：动作和表情 ===
		action_parts = []
		
		action = shot.get('action', '')
		if action:
			# 提取动作关键词
			if "推门" in action or "打开" in action:
				action_parts.append("opening door")
			if "走" in action or "迈步" in action:
				action_parts.append("walking")
			if "站立" in action or "站在" in action:
				action_parts.append("standing")
			if "坐" in action:
				action_parts.append("sitting")
			if "看" in action or "注视" in action:
				action_parts.append("looking")
			if "微笑" in action:
				action_parts.append("smiling")
		
		# === 第五部分：镜头类型 ===
		shot_type = shot.get('shot_type', '')
		shot_type_en = ""
		
		if "Wide" in shot_type or "全景" in shot_type:
			shot_type_en = "wide shot, full scene"
		elif "Medium" in shot_type or "中景" in shot_type:
			shot_type_en = "medium shot"
		elif "Close" in shot_type or "特写" in shot_type:
			shot_type_en = "close-up shot"
		
		# === 组合最终提示词 ===
		# SD提示词格式：质量标签, 人物（优先级最高）, 动作, 场景, 镜头类型, 光线
		final_prompt = ", ".join(quality_tags)
		
		# ★ 人物描述放在最前面，权重最高 ★
		if character_prompts:
			final_prompt += ", " + ", ".join(character_prompts)
		
		# 添加动作和表情（体现故事情节）
		if action_parts:
			final_prompt += ", " + ", ".join(action_parts)
		
		# 场景环境
		if scene_parts:
			final_prompt += ", " + ", ".join(scene_parts)
		
		# 镜头类型
		if shot_type_en:
			final_prompt += ", " + shot_type_en
		
		# 添加具体的环境描述（更详细）
		location = shot.get('location', '')
		if location:
			if "教室" in location:
				final_prompt += ", classroom interior, desks and chairs, school setting"
			elif "办公室" in location:
				final_prompt += ", office interior, desk, professional environment"
			elif "走廊" in location:
				final_prompt += ", hallway, corridor"
			elif "操场" in location or "outdoor" in location.lower():
				final_prompt += ", outdoor, playground"
		
		# ★★★ 添加故事连贯性描述 ★★★
		continuity = shot.get('continuity', '')
		scene_id = shot.get('scene_id', '')
		if continuity or scene_id:
			final_prompt += ", story scene, narrative sequence, cinematic storytelling"
		
		# 添加情绪氛围（体现故事情节）
		emotion = shot.get('emotion', '')
		if emotion:
			if "孤独" in emotion or "lonely" in emotion.lower():
				final_prompt += ", lonely atmosphere, solitary"
			if "疲惫" in emotion or "tired" in emotion.lower():
				final_prompt += ", tired expression, exhausted"
			if "紧张" in emotion:
				final_prompt += ", tense mood"
			if "开心" in emotion or "happy" in emotion.lower():
				final_prompt += ", happy, cheerful"
		
		# 打印提示词用于调试
		print(f"\n=== SD提示词 (分镜{shot_num}) ===")
		print(f"人物: {', '.join(characters) if characters else '无'}")
		print(f"正向提示词 ({len(final_prompt)}字符):")
		print(f"  {final_prompt[:300]}...")
		
		return final_prompt
	
	def _build_sd_negative_prompt(self, shot: dict) -> str:
		"""构建SD负面提示词 - 加强人物一致性约束"""
		negative_tags = [
			# 质量相关
			"low quality", "worst quality", "normal quality", "lowres", "blurry", "fuzzy",
			"bad anatomy", "bad hands", "bad proportions", "bad perspective",
			"ugly", "deformed", "disfigured", "mutation", "mutated",
			
			# ★★★ 人物一致性相关（加强）★★★
			"multiple people", "crowd", "different person", "changing appearance",
			"inconsistent clothing", "inconsistent hair", "inconsistent face",
			"different hairstyle", "hair color change", "different outfit",
			"face inconsistency", "character inconsistency",
			"multiple identities", "changing features",
			
			# 构图相关
			"cropped", "cut off", "out of frame", "watermark", "signature", "text",
			"username", "logo", "copyright", "border",
			
			# 风格相关
			"cartoon", "anime", "illustration", "painting", "drawing",
			"3d render", "cg", "unrealistic", "artistic style",
			
			# 其他
			"duplicate", "repeating", "extra limbs", "missing limbs",
			"bad lighting", "overexposed", "underexposed",
			"distorted", "weird", "strange"
		]
		
		# 如果是人物镜头，添加更多限制
		if shot.get('characters'):
			negative_tags.extend([
				"multiple heads", "two faces", "deformed face",
				"asymmetric eyes", "cross-eyed", "wrong anatomy",
				"extra fingers", "missing fingers", "fused fingers",
				"different face", "face change"
			])
		
		return ", ".join(negative_tags)
	
	def _generate_single_shot_image(self, shot_num: int, description: str, output_dir: str, 
									  shot_variant: int = 1, seed_offset: int = 0) -> str:
		"""生成单个分镜图片
		
		Args:
			shot_num: 分镜编号
			description: 图片描述
			output_dir: 输出目录
			shot_variant: 变体编号（用于文件命名）
			seed_offset: 种子偏移量（用于产生不同变体）
		"""
		try:
			print(f"\n=== 生成分镜 {shot_num} 变体 {shot_variant} ===")
			print(f"描述: {description[:200]}...")
			print(f"种子偏移: {seed_offset}")
			
			# 获取图片生成设置
			img_type = getattr(self, 'director_img_type', tk.StringVar(value="写实照片")).get()
			
			# 获取API配置
			if not hasattr(self, 'img_api_preset'):
				print("❌ 错误：未找到 img_api_preset 属性")
				raise Exception("请先在图片生成页面配置API")
			
			if not hasattr(self, 'img_api_presets'):
				print("❌ 错误：未找到 img_api_presets 属性")
				raise Exception("系统初始化失败，请重启应用")
			
			preset_name = self.img_api_preset.get()
			print(f"📌 当前选择的图片API预设: {preset_name}")
			
			if preset_name not in self.img_api_presets:
				print(f"❌ 错误：预设 '{preset_name}' 不在可用列表中")
				print(f"可用预设: {list(self.img_api_presets.keys())}")
				raise Exception(f"未找到预设配置：{preset_name}")
			
			api_config = self.img_api_presets[preset_name]
			provider = api_config.get("provider", "openai")
			print(f"📌 API提供商: {provider}")
			print(f"📌 配置信息: base_url={api_config.get('base_url', '未配置')}")
			
			# 调用实际的图片生成
			if provider == "sd":
				# 使用SD一致性生成器
				# 获取当前分镜信息
				current_shot = None
				if hasattr(self, 'current_shots') and shot_num <= len(self.current_shots):
					current_shot = self.current_shots[shot_num - 1]
				
				if current_shot and hasattr(self, 'consistency_data') and self.consistency_data:
					# 使用一致性生成器
					print("尝试使用SD一致性生成器...")
					image_path = self._generate_shot_with_sd_consistency(
						current_shot, shot_num, output_dir, shot_variant
					)
					if image_path:
						return image_path
					else:
						print("⚠️ SD一致性生成器失败，回退到普通SD生成")
				
				# 如果一致性生成失败或未配置，使用优化的普通SD生成
				from src.clients.sd_client import StableDiffusionClient
				
				sd_base_url = api_config.get("base_url", "http://localhost:7860")
				print(f"连接到SD: {sd_base_url}")
				
				try:
					client = StableDiffusionClient(base_url=sd_base_url)
				except Exception as e:
					print(f"❌ SD客户端初始化失败: {str(e)}")
					raise Exception(f"无法连接SD服务器 {sd_base_url}，请确认SD WebUI已启动并开启--api参数")
				
				# 获取负面提示词
				negative_prompt = self._build_sd_negative_prompt(current_shot) if current_shot else self._build_sd_negative_prompt({})
				
				# 为保持人物一致性，使用全局固定种子
				# 确保同一人物在所有分镜中使用相同的基础种子
				base_seed = 42  # 默认种子
				
				if current_shot and current_shot.get('characters'):
					# 获取主要人物
					main_char = current_shot['characters'][0]
					
					# 如果这个人物还没有分配种子，为其分配一个固定种子
					if main_char not in self.character_seed_map:
						# 使用人物名hash生成唯一且固定的种子
						self.character_seed_map[main_char] = abs(hash(main_char)) % 1000000
						print(f"🎨 为人物 '{main_char}' 分配固定种子: {self.character_seed_map[main_char]}")
					
					base_seed = self.character_seed_map[main_char]
				
				# 只在同一分镜的不同变体间使用小偏移
				seed = base_seed + seed_offset * 10  # 减小偏移量，增强一致性
				
				print(f"负向: {negative_prompt[:100]}...")
				print(f"种子: {seed} (基础:{base_seed} + 偏移:{seed_offset}*100)")
				
				try:
					images = client.txt2img(
						prompt=description,
						negative_prompt=negative_prompt,
						width=768,
						height=512,
						steps=35,  # 增加步数提高质量和一致性
						cfg_scale=8.5,  # 提高CFG增强提示词遵循度（重要！）
						sampler_name="DPM++ 2M Karras",  # 高质量采样器
						seed=seed,
						# denoising_strength=0.7  # 如果使用img2img可以用这个参数
					)
				except ConnectionError as e:
					print(f"❌ SD连接错误: {str(e)}")
					raise Exception(f"无法连接到SD服务器，请确认:\n1. SD WebUI已启动\n2. 启动时添加了 --api 参数\n3. 访问地址是 {sd_base_url}")
				except Exception as e:
					print(f"❌ SD生成错误: {str(e)}")
					raise
				
				if images:
					# 文件名包含变体编号
					image_path = os.path.join(output_dir, f"shot_{shot_num:03d}_v{shot_variant}.png")
					# 保存图片
					images[0].save(image_path)
					print(f"✅ 已保存: {image_path}")
					return image_path
				else:
					print(f"❌ SD未返回图片")
					raise Exception("SD生成失败，未返回图片数据")
			else:
				# OpenAI兼容API
				from src.clients.image_client import OpenAIImageClient
				client = OpenAIImageClient(
					api_key=api_config.get("key", ""),
					base_url=api_config.get("base_url", ""),
					model=api_config.get("model", "")
				)
				
				# 生成图片
				image_data = client.generate(
					prompt=description,
					size="1024x1024"
				)
				
				if image_data:
					# 文件名包含变体编号
					image_path = os.path.join(output_dir, f"shot_{shot_num:03d}_v{shot_variant}.png")
					# 保存图片
					import requests
					if isinstance(image_data, str) and image_data.startswith("http"):
						# URL形式
						response = requests.get(image_data)
						with open(image_path, 'wb') as f:
							f.write(response.content)
					else:
						# Base64形式
						import base64
						with open(image_path, 'wb') as f:
							f.write(base64.b64decode(image_data))
					print(f"✅ 已保存: {image_path}")
					return image_path
			
			# 如果没有配置，使用默认的图片生成页面的方法
			print("警告：未找到图片API配置，尝试使用默认方法")
			
			# 创建占位文件
			image_path = os.path.join(output_dir, f"shot_{shot_num:03d}.png")
			with open(image_path, 'w') as f:
				f.write(f"Shot {shot_num} - 请配置图片生成API")
			
			return image_path
			
		except Exception as e:
			print(f"生成图片失败: {str(e)}")
			import traceback
			traceback.print_exc()
			return None
