"""
知识库增强模块
包含：内容预览、多格式支持、管理界面
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, END
from pathlib import Path
from typing import List, Dict, Optional
import threading


class KBPreviewDialog:
    """知识库内容预览对话框"""
    
    def __init__(self, parent, kb_path: str):
        self.parent = parent
        self.kb_path = Path(kb_path)
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("知识库内容预览")
        self.dialog.geometry("900x600")
        self.dialog.transient(parent)
        
        # 样式
        self.dialog.configure(bg="#1e1e1e")
        
        self._build_ui()
        self._load_content()
    
    def _build_ui(self):
        """构建UI"""
        # 顶部工具栏
        toolbar = tk.Frame(self.dialog, bg="#2b2b2b", height=50)
        toolbar.pack(fill="x", padx=10, pady=10)
        toolbar.pack_propagate(False)
        
        tk.Label(toolbar, text=f"📚 知识库: {self.kb_path}", bg="#2b2b2b", fg="#ffffff",
                 font=("", 12)).pack(side="left", padx=10, pady=10)
        
        # 搜索框
        tk.Label(toolbar, text="搜索:", bg="#2b2b2b", fg="#9CA3AF").pack(side="left", padx=(20, 5))
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(toolbar, textvariable=self.search_var, bg="#1e1e1e", fg="#ffffff",
                                      insertbackground="white", width=30)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<Return>", self._on_search)
        
        tk.Button(toolbar, text="🔍 搜索", command=self._on_search, bg="#3B82F6", fg="#ffffff",
                  relief=tk.FLAT, cursor="hand2").pack(side="left", padx=5)
        
        # 主内容区域
        main_frame = tk.Frame(self.dialog, bg="#1e1e1e")
        main_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # 左侧：文件列表
        left_frame = tk.Frame(main_frame, bg="#2b2b2b", width=250)
        left_frame.pack(side="left", fill="y", padx=(0, 10))
        left_frame.pack_propagate(False)
        
        tk.Label(left_frame, text="文件列表", bg="#2b2b2b", fg="#ffffff",
                 font=("", 11, "bold")).pack(pady=10)
        
        # 文件列表
        list_frame = tk.Frame(left_frame, bg="#1e1e1e")
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        scroll_y = tk.Scrollbar(list_frame, orient="vertical")
        scroll_y.pack(side="right", fill="y")
        
        self.file_listbox = tk.Listbox(list_frame, bg="#1e1e1e", fg="#d4d4d4",
                                        selectbackground="#3B82F6", selectforeground="#ffffff",
                                        yscrollcommand=scroll_y.set, font=("", 10))
        self.file_listbox.pack(fill="both", expand=True)
        scroll_y.config(command=self.file_listbox.yview)
        self.file_listbox.bind("<<ListboxSelect>>", self._on_file_select)
        
        # 文件统计
        self.stats_label = tk.Label(left_frame, text="文件数: 0", bg="#2b2b2b", fg="#6B7280")
        self.stats_label.pack(pady=5)
        
        # 右侧：内容预览
        right_frame = tk.Frame(main_frame, bg="#2b2b2b")
        right_frame.pack(side="right", fill="both", expand=True)
        
        tk.Label(right_frame, text="内容预览", bg="#2b2b2b", fg="#ffffff",
                 font=("", 11, "bold")).pack(pady=10)
        
        # 预览文本框
        preview_frame = tk.Frame(right_frame, bg="#1e1e1e")
        preview_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        scroll_y2 = tk.Scrollbar(preview_frame, orient="vertical")
        scroll_y2.pack(side="right", fill="y")
        
        self.preview_text = tk.Text(preview_frame, wrap="word", bg="#1e1e1e", fg="#d4d4d4",
                                     yscrollcommand=scroll_y2.set, font=("Consolas", 10),
                                     padx=10, pady=10)
        self.preview_text.pack(fill="both", expand=True)
        scroll_y2.config(command=self.preview_text.yview)
        
        # 底部信息
        self.info_label = tk.Label(right_frame, text="选择文件查看内容", bg="#2b2b2b", fg="#6B7280")
        self.info_label.pack(pady=5)
    
    def _load_content(self):
        """加载知识库内容"""
        if not self.kb_path.exists():
            self.preview_text.insert("1.0", "知识库目录不存在")
            return
        
        # 支持的文件格式
        supported_extensions = {'.txt', '.md', '.json', '.csv', '.docx', '.pdf'}
        
        files = []
        for ext in supported_extensions:
            files.extend(self.kb_path.glob(f"**/*{ext}"))
        
        files = sorted(files)
        
        self.files = files
        self.file_listbox.delete(0, END)
        
        for f in files:
            rel_path = f.relative_to(self.kb_path)
            self.file_listbox.insert(END, str(rel_path))
        
        self.stats_label.config(text=f"文件数: {len(files)}")
    
    def _on_file_select(self, event):
        """文件选择事件"""
        selection = self.file_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        if index >= len(self.files):
            return
        
        file_path = self.files[index]
        self._preview_file(file_path)
    
    def _preview_file(self, file_path: Path):
        """预览文件内容"""
        self.preview_text.delete("1.0", END)
        
        try:
            ext = file_path.suffix.lower()
            
            if ext in ['.txt', '.md', '.json', '.csv']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            elif ext == '.docx':
                content = self._read_docx(file_path)
            elif ext == '.pdf':
                content = self._read_pdf(file_path)
            else:
                content = "不支持的文件格式"
            
            # 限制显示长度
            if len(content) > 50000:
                content = content[:50000] + "\n\n... (内容过长，已截断)"
            
            self.preview_text.insert("1.0", content)
            
            # 更新信息
            size = file_path.stat().st_size
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size/1024:.1f} KB"
            else:
                size_str = f"{size/(1024*1024):.1f} MB"
            
            self.info_label.config(text=f"文件: {file_path.name} | 大小: {size_str} | 字符数: {len(content)}")
            
        except Exception as e:
            self.preview_text.insert("1.0", f"读取文件失败: {str(e)}")
    
    def _read_docx(self, file_path: Path) -> str:
        """读取Word文档"""
        try:
            from docx import Document
            doc = Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs]
            return '\n'.join(paragraphs)
        except ImportError:
            return "需要安装 python-docx 库来读取Word文档\npip install python-docx"
        except Exception as e:
            return f"读取Word文档失败: {str(e)}"
    
    def _read_pdf(self, file_path: Path) -> str:
        """读取PDF文档"""
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = []
                for page in reader.pages:
                    text.append(page.extract_text())
                return '\n'.join(text)
        except ImportError:
            return "需要安装 PyPDF2 库来读取PDF文档\npip install PyPDF2"
        except Exception as e:
            return f"读取PDF文档失败: {str(e)}"
    
    def _on_search(self, event=None):
        """搜索知识库内容"""
        query = self.search_var.get().strip()
        if not query:
            return
        
        # 简单的全文搜索
        results = []
        
        for file_path in self.files:
            try:
                ext = file_path.suffix.lower()
                if ext in ['.txt', '.md', '.json', '.csv']:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    if query.lower() in content.lower():
                        # 找到匹配的上下文
                        idx = content.lower().find(query.lower())
                        start = max(0, idx - 100)
                        end = min(len(content), idx + len(query) + 100)
                        context = content[start:end]
                        results.append({
                            'file': file_path.relative_to(self.kb_path),
                            'context': context,
                            'full_path': file_path
                        })
            except Exception:
                pass
        
        # 显示结果
        self.preview_text.delete("1.0", END)
        if results:
            self.preview_text.insert("1.0", f"搜索 '{query}' 找到 {len(results)} 个结果:\n\n")
            for i, result in enumerate(results[:50], 1):  # 限制显示前50个
                self.preview_text.insert(END, f"━━━ {i}. {result['file']} ━━━\n")
                self.preview_text.insert(END, f"...{result['context']}...\n\n")
        else:
            self.preview_text.insert("1.0", f"未找到包含 '{query}' 的内容")


class KBManagerDialog:
    """知识库管理对话框"""
    
    def __init__(self, parent, data_dir: str, index_dir: str, on_rebuild: callable = None):
        self.parent = parent
        self.data_dir = Path(data_dir)
        self.index_dir = Path(index_dir)
        self.on_rebuild = on_rebuild
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("知识库管理")
        self.dialog.geometry("700x500")
        self.dialog.transient(parent)
        
        self.dialog.configure(bg="#1e1e1e")
        
        self._build_ui()
        self._load_stats()
    
    def _build_ui(self):
        """构建UI"""
        # 标题
        tk.Label(self.dialog, text="📚 知识库管理", bg="#1e1e1e", fg="#ffffff",
                 font=("", 16, "bold")).pack(pady=20)
        
        # 信息卡片
        info_frame = tk.Frame(self.dialog, bg="#2b2b2b")
        info_frame.pack(fill="x", padx=20, pady=10)
        
        # 数据目录
        row1 = tk.Frame(info_frame, bg="#2b2b2b")
        row1.pack(fill="x", padx=15, pady=10)
        tk.Label(row1, text="数据目录:", bg="#2b2b2b", fg="#9CA3AF", width=12, anchor="w").pack(side="left")
        tk.Label(row1, text=str(self.data_dir), bg="#2b2b2b", fg="#ffffff").pack(side="left")
        
        # 索引目录
        row2 = tk.Frame(info_frame, bg="#2b2b2b")
        row2.pack(fill="x", padx=15, pady=5)
        tk.Label(row2, text="索引目录:", bg="#2b2b2b", fg="#9CA3AF", width=12, anchor="w").pack(side="left")
        tk.Label(row2, text=str(self.index_dir), bg="#2b2b2b", fg="#ffffff").pack(side="left")
        
        # 统计信息
        stats_frame = tk.Frame(self.dialog, bg="#2b2b2b")
        stats_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(stats_frame, text="统计信息", bg="#2b2b2b", fg="#ffffff",
                 font=("", 12, "bold")).pack(anchor="w", padx=15, pady=10)
        
        self.stats_text = tk.Text(stats_frame, height=8, bg="#1e1e1e", fg="#d4d4d4",
                                   font=("Consolas", 10), padx=10, pady=10)
        self.stats_text.pack(fill="x", padx=15, pady=(0, 10))
        
        # 操作按钮
        btn_frame = tk.Frame(self.dialog, bg="#1e1e1e")
        btn_frame.pack(fill="x", padx=20, pady=20)
        
        tk.Button(btn_frame, text="👁️ 预览内容", command=self._preview_content,
                  bg="#3B82F6", fg="#ffffff", relief=tk.FLAT, cursor="hand2",
                  padx=20, pady=10).pack(side="left", padx=10)
        
        tk.Button(btn_frame, text="🔨 重建索引", command=self._rebuild_index,
                  bg="#10B981", fg="#ffffff", relief=tk.FLAT, cursor="hand2",
                  padx=20, pady=10).pack(side="left", padx=10)
        
        tk.Button(btn_frame, text="📁 添加文档", command=self._add_documents,
                  bg="#6366F1", fg="#ffffff", relief=tk.FLAT, cursor="hand2",
                  padx=20, pady=10).pack(side="left", padx=10)
        
        tk.Button(btn_frame, text="🗑️ 清除索引", command=self._clear_index,
                  bg="#EF4444", fg="#ffffff", relief=tk.FLAT, cursor="hand2",
                  padx=20, pady=10).pack(side="left", padx=10)
        
        # 支持的格式说明
        format_frame = tk.Frame(self.dialog, bg="#2b2b2b")
        format_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(format_frame, text="支持的文档格式:", bg="#2b2b2b", fg="#ffffff",
                 font=("", 11, "bold")).pack(anchor="w", padx=15, pady=10)
        
        formats_text = """• 纯文本: .txt
• Markdown: .md  
• JSON: .json
• CSV: .csv
• Word文档: .docx (需安装 python-docx)
• PDF文档: .pdf (需安装 PyPDF2)"""
        
        tk.Label(format_frame, text=formats_text, bg="#2b2b2b", fg="#9CA3AF",
                 justify="left").pack(anchor="w", padx=15, pady=(0, 10))
    
    def _load_stats(self):
        """加载统计信息"""
        self.stats_text.delete("1.0", END)
        
        stats = []
        
        # 数据目录统计
        if self.data_dir.exists():
            file_counts = {}
            total_size = 0
            for f in self.data_dir.rglob('*'):
                if f.is_file():
                    ext = f.suffix.lower() or 'no_ext'
                    file_counts[ext] = file_counts.get(ext, 0) + 1
                    total_size += f.stat().st_size
            
            stats.append(f"数据目录文件统计:")
            for ext, count in sorted(file_counts.items()):
                stats.append(f"  {ext}: {count} 个文件")
            
            if total_size < 1024:
                size_str = f"{total_size} B"
            elif total_size < 1024 * 1024:
                size_str = f"{total_size/1024:.1f} KB"
            else:
                size_str = f"{total_size/(1024*1024):.1f} MB"
            stats.append(f"  总大小: {size_str}")
        else:
            stats.append("数据目录不存在")
        
        stats.append("")
        
        # 索引目录统计
        if self.index_dir.exists():
            index_files = list(self.index_dir.glob('*'))
            index_size = sum(f.stat().st_size for f in index_files if f.is_file())
            
            if index_size < 1024:
                size_str = f"{index_size} B"
            elif index_size < 1024 * 1024:
                size_str = f"{index_size/1024:.1f} KB"
            else:
                size_str = f"{index_size/(1024*1024):.1f} MB"
            
            stats.append(f"索引文件: {len(index_files)} 个")
            stats.append(f"索引大小: {size_str}")
            
            # 检查索引是否有效
            if (self.index_dir / "faiss.index").exists():
                stats.append("索引状态: ✅ 有效")
            else:
                stats.append("索引状态: ❌ 未构建")
        else:
            stats.append("索引目录不存在")
        
        self.stats_text.insert("1.0", "\n".join(stats))
    
    def _preview_content(self):
        """预览知识库内容"""
        if not self.data_dir.exists():
            messagebox.showwarning("提示", "数据目录不存在")
            return
        
        KBPreviewDialog(self.dialog, str(self.data_dir))
    
    def _rebuild_index(self):
        """重建索引"""
        if self.on_rebuild:
            self.on_rebuild()
            self.after(1000, self._load_stats)
    
    def _add_documents(self):
        """添加文档"""
        files = filedialog.askopenfilenames(
            title="选择要添加的文档",
            filetypes=[
                ("所有支持的格式", "*.txt;*.md;*.json;*.csv;*.docx;*.pdf"),
                ("文本文件", "*.txt"),
                ("Markdown", "*.md"),
                ("JSON", "*.json"),
                ("CSV", "*.csv"),
                ("Word文档", "*.docx"),
                ("PDF文档", "*.pdf"),
                ("所有文件", "*.*")
            ]
        )
        
        if not files:
            return
        
        # 确保数据目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        import shutil
        copied = 0
        for file_path in files:
            try:
                src = Path(file_path)
                dst = self.data_dir / src.name
                
                # 如果文件已存在，添加数字后缀
                if dst.exists():
                    base = dst.stem
                    ext = dst.suffix
                    counter = 1
                    while dst.exists():
                        dst = self.data_dir / f"{base}_{counter}{ext}"
                        counter += 1
                
                shutil.copy2(src, dst)
                copied += 1
            except Exception as e:
                print(f"复制文件失败: {e}")
        
        messagebox.showinfo("完成", f"已添加 {copied} 个文档到知识库")
        self._load_stats()
    
    def _clear_index(self):
        """清除索引"""
        if not messagebox.askyesno("确认", "确定要清除所有索引吗？\n这不会删除原始文档。"):
            return
        
        try:
            import shutil
            if self.index_dir.exists():
                shutil.rmtree(self.index_dir)
                self.index_dir.mkdir(parents=True, exist_ok=True)
            messagebox.showinfo("完成", "索引已清除")
            self._load_stats()
        except Exception as e:
            messagebox.showerror("错误", f"清除索引失败: {str(e)}")
    
    def after(self, ms, func):
        """延迟执行"""
        self.dialog.after(ms, func)


class KBEnhancementsMixin:
    """知识库增强Mixin"""
    
    def open_kb_preview(self):
        """打开知识库预览"""
        if hasattr(self, 'data_dir'):
            data_path = self.data_dir.get() if hasattr(self.data_dir, 'get') else str(self.data_dir)
            KBPreviewDialog(self, data_path)
        else:
            messagebox.showwarning("提示", "请先配置知识库路径")
    
    def open_kb_manager(self):
        """打开知识库管理"""
        if hasattr(self, 'data_dir') and hasattr(self, 'index_dir'):
            data_path = self.data_dir.get() if hasattr(self.data_dir, 'get') else str(self.data_dir)
            index_path = self.index_dir.get() if hasattr(self.index_dir, 'get') else str(self.index_dir)
            
            rebuild_func = self.on_ingest if hasattr(self, 'on_ingest') else None
            KBManagerDialog(self, data_path, index_path, rebuild_func)
        else:
            messagebox.showwarning("提示", "请先配置知识库路径")
