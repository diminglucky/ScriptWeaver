"""
Kb相关功能模块
"""

from tkinter import BOTH, LEFT, RIGHT, DISABLED, NORMAL, END, messagebox, filedialog
import tkinter as tk
from tkinter import ttk
import threading
from pathlib import Path

from src.core.logging_config import get_logger

logger = get_logger(__name__)


class KbMixin:
	"""Kb管理功能"""
	
	def on_ingest(self) -> None:
		"""构建知识库索引"""
		# Preflight检查
		data_dir_path = Path(self.data_dir.get())
		if not data_dir_path.exists():
			messagebox.showwarning("提示", "数据目录不存在，请先选择有效的数据目录")
			return
		
		# 检查是否有文本文件
		txt_files = list(data_dir_path.rglob("*.txt"))
		md_files = list(data_dir_path.rglob("*.md"))
		markdown_files = list(data_dir_path.rglob("*.markdown"))
		
		if not txt_files and not md_files and not markdown_files:
			messagebox.showwarning(
				"提示",
				"数据目录下未发现 .txt/.md/.markdown 文件\n\n"
				"💡 提示：你可以点击「快速添加故事文件」按钮来添加故事文件。"
			)
			return
		
		total_files = len(txt_files) + len(md_files) + len(markdown_files)
		
		# 确认构建
		if not messagebox.askyesno(
			"确认构建",
			f"准备构建知识库索引\n\n"
			f"数据目录: {data_dir_path}\n"
			f"找到 {total_files} 个文件\n"
			f"索引目录: {self.index_dir.get()}\n\n"
			f"是否继续？"
		):
			return
		
		def task():
			try:
				# 更新UI状态（在主线程）
				self.after(0, lambda: self.set_busy(True))
				self.after(0, lambda: self.status.set(f"正在构建知识库索引（{total_files}个文件）..."))
				
				# 延迟导入（可能较慢）
				self.after(0, lambda: self.status.set("正在加载知识库模块..."))
				try:
					from src.kb.ingest import KnowledgeBaseIngestor, IngestConfig
				except ImportError as e:
					raise RuntimeError(f"导入知识库模块失败，请确保已安装所需依赖：sentence-transformers, faiss-cpu\n\n错误详情：{e}")
				
				# 构建索引
				self.after(0, lambda: self.status.set("正在读取和分块文本文件..."))
				cfg = IngestConfig(
					data_root=data_dir_path,
					index_dir=Path(self.index_dir.get())
				)
				ingestor = KnowledgeBaseIngestor(cfg)
				
				self.after(0, lambda: self.status.set("正在生成向量索引（这可能需要一些时间）..."))
				ingestor.build()
				
				# 更新UI
				self.after(0, lambda: self.status.set("✅ 索引构建完成"))
				if hasattr(self, 'output'):
					self.after(0, lambda: self.output.insert(END, f"✅ 知识库索引构建完成！\n"))
					self.after(0, lambda: self.output.insert(END, f"   数据目录: {data_dir_path}\n"))
					self.after(0, lambda: self.output.insert(END, f"   索引目录: {self.index_dir.get()}\n"))
					self.after(0, lambda: self.output.insert(END, f"   文件数量: {total_files}\n\n"))
					self.after(0, lambda: self.output.see(END))
				
				self.after(0, lambda: messagebox.showinfo(
					"成功",
					f"知识库索引构建完成！\n\n"
					f"数据目录: {data_dir_path}\n"
					f"索引目录: {self.index_dir.get()}\n"
					f"文件数量: {total_files}\n\n"
					f"现在可以使用RAG增强创作功能了！"
				))
			except Exception as e:
				import traceback
				error_msg = f"构建索引出错:\n{str(e)}\n\n{traceback.format_exc()}"
				logger.error(error_msg, exc_info=True)
				self.after(0, lambda msg=error_msg: self.output.insert(END, f"❌ {msg}\n\n") if hasattr(self, 'output') else None)
				self.after(0, lambda: self.output.see(END) if hasattr(self, 'output') else None)
				self.after(0, lambda err=str(e): messagebox.showerror("错误", f"构建索引失败\n\n{err}"))
				self.after(0, lambda: self.status.set("构建索引失败"))
			finally:
				self.after(0, lambda: self.set_busy(False))
		
		threading.Thread(target=task, daemon=True).start()

	def locate_existing_index(self) -> None:
		"""If current index_dir is a parent, find first child that contains kb.index and switch to it."""
		base = Path(self.index_dir.get())
		if base.is_file():
			base = base.parent
		candidates = list(base.rglob("kb.index"))
		if not candidates:
			messagebox.showinfo("提示", "未在当前索引目录下找到任何 kb.index")
			return
		chosen = candidates[0].parent
		self.index_dir.set(str(chosen))
		self.output.insert(END, f"已定位到索引目录: {chosen}\n")
		self.status.set("已定位到现有索引")

	def choose_data(self) -> None:
		path = filedialog.askdirectory(initialdir=self.data_dir.get())
		if path:
			self.data_dir.set(path)
			self.status.set("已选择数据目录")

	def choose_library_quick(self) -> None:
		"""一键选择库：自动设置数据目录和索引目录"""
		path = filedialog.askdirectory(initialdir=self.data_dir.get())
		if not path:
			return
		self.data_dir.set(path)
		base = Path(path).name
		auto_index = Path.cwd() / "index" / base
		auto_index.mkdir(parents=True, exist_ok=True)
		self.index_dir.set(str(auto_index))
		# 统计文件数量
		try:
			txt_files = list(Path(path).rglob("*.txt"))
			md_files = list(Path(path).rglob("*.md"))
			markdown_files = list(Path(path).rglob("*.markdown"))
			total_files = len(txt_files) + len(md_files) + len(markdown_files)
			if hasattr(self, 'output'):
				self.output.insert(END, f"✅ 已选择资料库: {path}\n")
				self.output.insert(END, f"   找到 {total_files} 个故事文件（.txt/.md/.markdown）\n")
				self.output.insert(END, f"   索引目录: {auto_index}\n\n")
				self.output.see(END)
		except Exception as e:
			logger.warning(f"统计文件失败: {e}")
		self.status.set(f"已选择资料库并设置索引目录（找到 {total_files if 'total_files' in locals() else '?'} 个文件）")
	
	def on_quick_add_stories(self) -> None:
		"""快速添加故事文件到知识库数据目录"""
		# 选择多个txt/md文件
		files = filedialog.askopenfilenames(
			title="选择故事文件（可多选）",
			filetypes=[
				("文本文件", "*.txt"),
				("Markdown文件", "*.md"),
				("Markdown文件", "*.markdown"),
				("所有文件", "*.*")
			],
			initialdir=self.data_dir.get() if Path(self.data_dir.get()).exists() else "."
		)
		
		if not files:
			return
		
		# 确保数据目录存在
		data_dir_path = Path(self.data_dir.get())
		data_dir_path.mkdir(parents=True, exist_ok=True)
		
		# 复制文件到数据目录
		import shutil
		copied_count = 0
		failed_count = 0
		
		for file_path in files:
			try:
				source = Path(file_path)
				dest = data_dir_path / source.name
				# 如果目标文件已存在，添加序号
				if dest.exists():
					stem = source.stem
					suffix = source.suffix
					counter = 1
					while dest.exists():
						dest = data_dir_path / f"{stem}_{counter}{suffix}"
						counter += 1
				shutil.copy2(source, dest)
				copied_count += 1
			except Exception as e:
				print(f"[WARN] 复制文件失败: {file_path} -> {e}")
				failed_count += 1
				continue
		
		if copied_count > 0:
			if hasattr(self, 'output'):
				self.output.insert(END, f"✅ 成功添加 {copied_count} 个故事文件到知识库\n")
				if failed_count > 0:
					self.output.insert(END, f"⚠️ {failed_count} 个文件添加失败\n")
				self.output.insert(END, f"   数据目录: {data_dir_path}\n\n")
				self.output.see(END)
			self.status.set(f"✅ 已添加 {copied_count} 个故事文件到知识库")
			if copied_count > 0:
				messagebox.showinfo(
					"成功",
					f"成功添加 {copied_count} 个故事文件到知识库！\n\n"
					f"数据目录: {data_dir_path}\n\n"
					f"现在可以点击「构建索引」按钮来构建知识库索引。"
				)
		else:
			messagebox.showwarning("提示", "没有成功添加任何文件")
	
	def on_view_kb_info(self) -> None:
		"""查看知识库信息"""
		index_dir = Path(self.index_dir.get())
		index_path = index_dir / "kb.index"
		chunks_path = index_dir / "chunks.npy"
		meta_path = index_dir / "meta.npy"
		
		if not index_path.exists():
			messagebox.showinfo(
				"知识库信息",
				f"❌ 知识库未构建\n\n"
				f"索引目录: {index_dir}\n\n"
				f"请先选择数据目录并构建索引。"
			)
			return
		
		try:
			import numpy as np
			import faiss
			
			# 加载索引
			index = faiss.read_index(str(index_path))
			chunks = np.load(chunks_path, allow_pickle=True)
			metas = np.load(meta_path, allow_pickle=True)
			
			# 统计信息
			total_chunks = len(chunks)
			total_files = len(set(m[0] for m in metas))
			
			# 计算平均chunk长度
			avg_chunk_len = sum(len(str(c)) for c in chunks) / total_chunks if total_chunks > 0 else 0
			
			# 获取文件列表
			file_list = list(set(m[0] for m in metas))[:10]  # 最多显示10个文件
			file_list_str = "\n".join(f"  • {Path(f).name}" for f in file_list)
			if total_files > 10:
				file_list_str += f"\n  ... 还有 {total_files - 10} 个文件"
			
			info_msg = (
				f"✅ 知识库已构建\n\n"
				f"📊 统计信息：\n"
				f"  • 索引目录: {index_dir}\n"
				f"  • 文件数量: {total_files}\n"
				f"  • 文本片段数: {total_chunks}\n"
				f"  • 平均片段长度: {int(avg_chunk_len)} 字符\n\n"
				f"📁 文件列表（前10个）：\n{file_list_str}\n\n"
				f"💡 提示：你可以随时重新构建索引以更新知识库。"
			)
			
			messagebox.showinfo("知识库信息", info_msg)
			
		except Exception as e:
			import traceback
			messagebox.showerror(
				"错误",
				f"读取知识库信息失败：\n\n{str(e)}\n\n{traceback.format_exc()}"
			)

	def choose_index(self) -> None:
		path = filedialog.askdirectory(initialdir=self.index_dir.get())
		if path:
			self.index_dir.set(path)
			self.status.set("已选择索引目录")
	
	def _on_project_stories_toggle(self) -> None:
		"""当用户切换'使用项目故事作为知识库'选项时"""
		if self.use_project_stories.get():
			# 启用项目故事库时，自动禁用"仅用模型"选项（因为需要使用RAG）
			if hasattr(self, 'model_only'):
				self.model_only.set(False)
			
			# 启用项目故事库时，自动设置路径
			projects_dir = Path("projects")
			if projects_dir.exists():
				# 设置数据目录为projects目录（会搜索story.txt）
				# 但实际构建时会从projects/*/story.txt读取
				project_kb_index = Path("index") / "project_stories"
				self.index_dir.set(str(project_kb_index))
				self.status.set("已启用项目故事知识库模式（已自动启用RAG检索）")
			else:
				messagebox.showwarning("提示", "未找到projects目录，请先创建项目")
				self.use_project_stories.set(False)
		else:
			# 禁用项目故事库时，恢复状态
			self.status.set("已禁用项目故事知识库模式")
	
	def on_build_project_stories_kb(self) -> None:
		"""构建项目故事知识库"""
		# 检查按钮是否已禁用（防止重复点击）
		if hasattr(self, 'btn_build_project_kb'):
			if self.btn_build_project_kb.cget("state") == DISABLED:
				return  # 已经在处理中，忽略重复点击
			# 立即禁用按钮，防止重复点击
			self.btn_build_project_kb.config(state=DISABLED)
		
		projects_dir = Path("projects")
		if not projects_dir.exists():
			if hasattr(self, 'btn_build_project_kb'):
				self.btn_build_project_kb.config(state=NORMAL)
			messagebox.showwarning("提示", "未找到projects目录")
			return
		
		# 查找所有story.txt文件（在主线程中执行，快速）
		try:
			story_files = list(projects_dir.rglob("story.txt"))
		except Exception as e:
			if hasattr(self, 'btn_build_project_kb'):
				self.btn_build_project_kb.config(state=NORMAL)
			messagebox.showerror("错误", f"扫描项目目录失败: {e}")
			return
		
		if not story_files:
			if hasattr(self, 'btn_build_project_kb'):
				self.btn_build_project_kb.config(state=NORMAL)
			messagebox.showwarning("提示", "在projects目录下未找到任何story.txt文件")
			return
		
		# 排除备份文件
		story_files = [f for f in story_files if not f.name.endswith(".bak")]
		
		if not story_files:
			if hasattr(self, 'btn_build_project_kb'):
				self.btn_build_project_kb.config(state=NORMAL)
			messagebox.showwarning("提示", "未找到有效的story.txt文件（已排除备份文件）")
			return
		
		# 显示进度提示
		if hasattr(self, 'status'):
			self.status.set(f"正在扫描项目故事文件...找到 {len(story_files)} 个文件")
		
		def task():
			try:
				# 更新UI状态（在主线程）
				self.after(0, lambda: self.set_busy(True))
				self.after(0, lambda: self.status.set(f"正在构建项目故事知识库（{len(story_files)}个文件）..."))
				
				# 延迟导入避免启动时加载（可能较慢，需要3-5秒）
				# 注意：导入sentence_transformers会下载模型，首次使用可能较慢
				self.after(0, lambda: self.status.set("正在加载知识库模块（首次使用可能需要下载模型，请稍候）..."))
				
				# 在后台线程中导入，避免阻塞UI
				print("[INFO] 开始导入知识库模块...")
				try:
					from src.kb.ingest import KnowledgeBaseIngestor, IngestConfig
					print("[INFO] 知识库模块导入完成")
					self.after(0, lambda: self.status.set("知识库模块加载完成，开始构建索引..."))
				except ImportError as e:
					raise RuntimeError(f"导入知识库模块失败，请确保已安装所需依赖：sentence-transformers, faiss-cpu\n\n错误详情：{e}")
				except Exception as e:
					raise RuntimeError(f"加载知识库模块时出错：{e}")
				
				# 创建临时目录来存储项目故事
				import tempfile
				import shutil
				self.after(0, lambda: self.status.set("正在准备临时目录..."))
				temp_stories_dir = Path(tempfile.mkdtemp(prefix="project_stories_"))
				
				try:
					# 将项目故事复制到临时目录
					self.after(0, lambda: self.status.set("正在复制故事文件..."))
					copied_count = 0
					for story_file in story_files:
						try:
							# 获取项目名称
							project_name = story_file.parent.name
							# 创建目标文件，文件名包含项目名以便追踪
							target_file = temp_stories_dir / f"{project_name}_story.txt"
							shutil.copy2(story_file, target_file)
							copied_count += 1
						except Exception as e:
							print(f"[WARN] 复制文件失败: {story_file} -> {e}")
							continue
					
					if copied_count == 0:
						raise RuntimeError("没有成功复制任何故事文件")
					
					# 设置索引目录
					index_dir = Path("index") / "project_stories"
					index_dir.mkdir(parents=True, exist_ok=True)
					
					# 构建索引
					self.after(0, lambda: self.status.set("正在构建向量索引（这可能需要一些时间）..."))
					cfg = IngestConfig(
						data_root=temp_stories_dir,
						index_dir=index_dir
					)
					ingestor = KnowledgeBaseIngestor(cfg)
					ingestor.build()
					
					# 更新UI（在主线程中执行）
					self.after(0, lambda: self.index_dir.set(str(index_dir)))
					
					# 输出信息到故事输出区（如果存在）
					if hasattr(self, 'output'):
						self.after(0, lambda: self.output.insert(END, f"✅ 项目故事知识库构建完成！\n"))
						self.after(0, lambda: self.output.insert(END, f"   找到 {len(story_files)} 个故事文件\n"))
						self.after(0, lambda: self.output.insert(END, f"   成功索引 {copied_count} 个文件\n"))
						self.after(0, lambda: self.output.insert(END, f"   索引目录: {index_dir}\n\n"))
						self.after(0, lambda: self.output.see(END))
					
					# 更新状态栏
					self.after(0, lambda: self.status.set(f"✅ 已构建项目故事库（{copied_count}个故事）"))
					
					# 显示成功消息
					self.after(0, lambda: messagebox.showinfo(
						"成功", 
						f"项目故事知识库构建完成！\n\n"
						f"找到 {len(story_files)} 个故事文件\n"
						f"成功索引 {copied_count} 个文件\n"
						f"索引目录: {index_dir}"
					))
				finally:
					# 清理临时目录
					try:
						if temp_stories_dir.exists():
							shutil.rmtree(temp_stories_dir, ignore_errors=True)
					except Exception as e:
						print(f"[WARN] 清理临时目录失败: {e}")
			except Exception as e:
				import traceback
				error_msg = f"构建项目故事知识库出错:\n{str(e)}\n\n{traceback.format_exc()}"
				print(f"[ERROR] {error_msg}")
				
				# 在主线程中显示错误
				if hasattr(self, 'output'):
					self.after(0, lambda msg=error_msg: self.output.insert(END, f"❌ {msg}\n\n"))
					self.after(0, lambda: self.output.see(END))
				
				self.after(0, lambda err=str(e): messagebox.showerror("错误", f"构建项目故事知识库失败\n\n{err}"))
				self.after(0, lambda: self.status.set("构建失败"))
			finally:
				# 恢复按钮状态（在主线程中执行）
				self.after(0, lambda: self.set_busy(False))
				if hasattr(self, 'btn_build_project_kb'):
					self.after(0, lambda: self.btn_build_project_kb.config(state=NORMAL))
		
		# 在后台线程中执行
		threading.Thread(target=task, daemon=True).start()

	def set_busy(self, busy: bool) -> None:
		state = DISABLED if busy else NORMAL
		self.btn_ingest.configure(state=state)
		self.btn_generate.configure(state=state)
		self.btn_outline.configure(state=state)
		# 添加构建项目故事库按钮
		if hasattr(self, 'btn_build_project_kb'):
			self.btn_build_project_kb.configure(state=state)
		if hasattr(self, 'btn_test_api'):
			self.btn_test_api.configure(state=state)
		if hasattr(self, 'btn_test_img_api'):
			self.btn_test_img_api.configure(state=state)
		if hasattr(self, 'btn_clear'):
			self.btn_clear.configure(state=state)
		if hasattr(self, 'btn_copy'):
			self.btn_copy.configure(state=state)
		# 章节生成按钮
		if hasattr(self, 'btn_generate_section'):
			# 只在有章节数据时才启用
			if busy or not self.parsed_sections:
				self.btn_generate_section.configure(state=DISABLED)
				self.btn_continue_next.configure(state=DISABLED)
				if hasattr(self, 'btn_auto_generate'):
					self.btn_auto_generate.configure(state=DISABLED)
			else:
				self.btn_generate_section.configure(state=NORMAL)
				self.btn_continue_next.configure(state=NORMAL)
				if hasattr(self, 'btn_auto_generate'):
					self.btn_auto_generate.configure(state=NORMAL)
		# Image page controls
		for name in (
			'img_btn_build', 'img_btn_gen', 'img_btn_save', 'img_btn_browse',
			'img_btn_extract', 'img_btn_build_from_shots', 'img_btn_copy', 'img_btn_clear',
			'img_btn_copy_shots', 'img_btn_clear_shots'
		):
			if hasattr(self, name):
				getattr(self, name).configure(state=state)


