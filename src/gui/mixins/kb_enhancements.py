"""
知识库增强模块
包含：内容预览、多格式支持、管理界面
"""

import os
import json
import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, END
from pathlib import Path
from typing import List, Dict, Optional
import threading
import logging
from src.utils.text import read_file_text
from src.gui.theme import Theme


logger = logging.getLogger(__name__)

SUPPORTED_KB_EXTENSIONS = (".txt", ".md", ".markdown", ".json", ".csv", ".docx", ".pdf")
SEARCHABLE_KB_EXTENSIONS = {".txt", ".md", ".markdown", ".json", ".csv", ".docx", ".pdf"}
INDEX_ARTIFACT_NAMES = {"manifest.json", "meta.sqlite"}


def _kb_colors() -> dict[str, str]:
    return {
        "bg": Theme.BG_PRIMARY,
        "panel": Theme.BG_SECONDARY,
        "surface": Theme.SURFACE,
        "border": Theme.BORDER,
        "text": Theme.TEXT_PRIMARY,
        "muted": Theme.TEXT_SECONDARY,
        "disabled": Theme.TEXT_DISABLED,
        "primary": Theme.PRIMARY,
        "success": Theme.SUCCESS,
        "info": Theme.INFO,
        "danger": Theme.ERROR,
        "accent": Theme.ACCENT,
        "selected": Theme.PRIMARY,
        "selected_text": "#FFFFFF",
    }


def _contrasting_text(hex_color: str) -> str:
    value = (hex_color or "").strip().lstrip("#")
    if len(value) != 6:
        return Theme.TEXT_PRIMARY
    try:
        red, green, blue = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return Theme.TEXT_PRIMARY
    luminance = (0.299 * red + 0.587 * green + 0.114 * blue) / 255
    return Theme.TEXT_PRIMARY if luminance > 0.68 else "#FFFFFF"


def _kb_button(parent, *, text: str, command, color: str | None = None, padx: int = 20, pady: int = 10):
    c = _kb_colors()
    bg = color or c["primary"]
    fg = _contrasting_text(bg)
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=fg,
        activebackground=Theme.PRIMARY_LIGHT,
        activeforeground=_contrasting_text(Theme.PRIMARY_LIGHT),
        relief=tk.FLAT,
        cursor="hand2",
        bd=0,
        highlightthickness=0,
        padx=padx,
        pady=pady,
    )


def _discover_supported_files(kb_path: Path) -> list[Path]:
    files: list[Path] = []
    for ext in SUPPORTED_KB_EXTENSIONS:
        files.extend(kb_path.glob(f"**/*{ext}"))
    return sorted(files)


def _search_text_matches(
    files: list[Path],
    kb_path: Path,
    query: str,
    max_results: int = 50,
    context_chars: int = 100,
) -> list[dict]:
    results: list[dict] = []
    query_lower = (query or "").lower()
    if not query_lower:
        return results

    for file_path in files:
        try:
            if file_path.suffix.lower() not in SEARCHABLE_KB_EXTENSIONS:
                continue
            content = read_file_text(file_path)
            content_lower = content.lower()
            if query_lower not in content_lower:
                continue

            idx = content_lower.find(query_lower)
            start = max(0, idx - context_chars)
            end = min(len(content), idx + len(query) + context_chars)
            results.append(
                {
                    "file": file_path.relative_to(kb_path),
                    "context": content[start:end],
                    "full_path": file_path,
                }
            )
            if len(results) >= max_results:
                break
        except Exception as e:
            logger.debug("Search skipped unreadable file %s: %s", file_path, e)
    return results


def _clear_known_index_artifacts(index_dir: Path) -> tuple[int, int]:
    removed = 0
    kept = 0
    if not index_dir.exists():
        return removed, kept
    v2_dir = index_dir / "v2"
    if v2_dir.exists():
        import shutil

        shutil.rmtree(v2_dir)
        return 1, 0

    for path in index_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.name in INDEX_ARTIFACT_NAMES:
            try:
                path.unlink()
                removed += 1
            except Exception as e:
                logger.debug("failed to remove index artifact %s: %s", path, e)
        else:
            kept += 1
    return removed, kept


def _has_valid_index_artifacts(index_dir: Path) -> bool:
    if not index_dir.exists():
        return False
    return (index_dir / "v2" / "manifest.json").exists() or any(index_dir.glob("v2/**/chroma"))


def _discover_index_shards(index_dir: Path) -> list[dict]:
    """Return readable v2 shard metadata stores under an index directory."""
    root = Path(index_dir)
    shards: list[dict] = []
    for db_path in sorted(root.glob("v2/**/meta.sqlite")):
        rel = db_path.relative_to(root)
        parts = rel.parts
        kb_type = parts[1] if len(parts) >= 4 else ""
        project_id = parts[2] if len(parts) >= 4 else ""
        count = 0
        try:
            conn = sqlite3.connect(db_path)
            try:
                count = int(conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
            finally:
                conn.close()
        except Exception as e:
            logger.debug("failed to count shard %s: %s", db_path, e)
        shards.append(
            {
                "label": f"{kb_type}/{project_id}",
                "kb_type": kb_type,
                "project_id": None if project_id == "_global" else project_id,
                "db_path": db_path,
                "count": count,
            }
        )
    return shards


def _load_index_chunks(db_path: Path, *, limit: int = 1000) -> list[dict]:
    """Load chunk text and metadata from a shard meta.sqlite file."""
    if not Path(db_path).exists():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT chunk_id, source_id, path, position, text, kb_type, project_id, tags_json, ordinal
            FROM chunks
            ORDER BY ordinal ASC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    finally:
        conn.close()

    chunks: list[dict] = []
    for row in rows:
        item = dict(row)
        raw_tags = item.pop("tags_json", "[]")
        try:
            item["tags"] = json.loads(raw_tags) if raw_tags else []
        except Exception:
            item["tags"] = []
        chunks.append(item)
    return chunks


def _load_index_documents(db_path: Path) -> list[dict]:
    """Load source document manifest rows from a shard meta.sqlite file."""
    if not Path(db_path).exists():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='documents'"
        ).fetchone()
        if not table:
            return []
        rows = conn.execute("SELECT * FROM documents ORDER BY path ASC").fetchall()
    finally:
        conn.close()

    documents: list[dict] = []
    for row in rows:
        item = dict(row)
        raw_settings = item.pop("chunk_settings_json", "{}")
        try:
            item["chunk_settings"] = json.loads(raw_settings) if raw_settings else {}
        except Exception:
            item["chunk_settings"] = {}
        documents.append(item)
    return documents


class KBPreviewDialog:
    """知识库内容预览对话框"""
    
    def __init__(self, parent, kb_path: str):
        self.parent = parent
        self.kb_path = Path(kb_path)
        self.files: list[Path] = []
        self._search_in_progress = False
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("知识库内容预览")
        self.dialog.geometry("900x600")
        self.dialog.transient(parent)
        
        self.colors = _kb_colors()
        self.dialog.configure(bg=self.colors["bg"])
        
        self._build_ui()
        self._load_content()

    def _safe_after(self, ms: int, callback):
        try:
            if self.dialog.winfo_exists():
                self.dialog.after(ms, callback)
        except Exception as e:
            logger.debug("skip ui callback for closed KB preview dialog: %s", e)
    
    def _build_ui(self):
        """构建UI"""
        # 顶部工具栏
        c = self.colors
        toolbar = tk.Frame(self.dialog, bg=c["panel"], height=50)
        toolbar.pack(fill="x", padx=10, pady=10)
        toolbar.pack_propagate(False)
        
        tk.Label(toolbar, text=f"📚 知识库: {self.kb_path}", bg=c["panel"], fg=c["text"],
                 font=("", 12)).pack(side="left", padx=10, pady=10)
        
        # 搜索框
        tk.Label(toolbar, text="搜索:", bg=c["panel"], fg=c["muted"]).pack(side="left", padx=(20, 5))
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(toolbar, textvariable=self.search_var, bg=c["surface"], fg=c["text"],
                                      insertbackground=c["text"], highlightbackground=c["border"],
                                      highlightcolor=c["primary"], relief=tk.FLAT, width=30)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<Return>", self._on_search)
        
        self.search_btn = _kb_button(
            toolbar,
            text="🔍 搜索",
            command=self._on_search,
            color=c["primary"],
            padx=12,
            pady=4,
        )
        self.search_btn.pack(side="left", padx=5)
        
        # 主内容区域
        main_frame = tk.Frame(self.dialog, bg=c["bg"])
        main_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # 左侧：文件列表
        left_frame = tk.Frame(main_frame, bg=c["panel"], width=250)
        left_frame.pack(side="left", fill="y", padx=(0, 10))
        left_frame.pack_propagate(False)
        
        tk.Label(left_frame, text="文件列表", bg=c["panel"], fg=c["text"],
                 font=("", 11, "bold")).pack(pady=10)
        
        # 文件列表
        list_frame = tk.Frame(left_frame, bg=c["surface"])
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        scroll_y = tk.Scrollbar(list_frame, orient="vertical")
        scroll_y.pack(side="right", fill="y")
        
        self.file_listbox = tk.Listbox(list_frame, bg=c["surface"], fg=c["text"],
                                        selectbackground=c["selected"], selectforeground=c["selected_text"],
                                        highlightbackground=c["border"], highlightcolor=c["primary"],
                                        relief=tk.FLAT, yscrollcommand=scroll_y.set, font=("", 10))
        self.file_listbox.pack(fill="both", expand=True)
        scroll_y.config(command=self.file_listbox.yview)
        self.file_listbox.bind("<<ListboxSelect>>", self._on_file_select)
        
        # 文件统计
        self.stats_label = tk.Label(left_frame, text="文件数: 0", bg=c["panel"], fg=c["muted"])
        self.stats_label.pack(pady=5)
        
        # 右侧：内容预览
        right_frame = tk.Frame(main_frame, bg=c["panel"])
        right_frame.pack(side="right", fill="both", expand=True)
        
        tk.Label(right_frame, text="内容预览", bg=c["panel"], fg=c["text"],
                 font=("", 11, "bold")).pack(pady=10)
        
        # 预览文本框
        preview_frame = tk.Frame(right_frame, bg=c["surface"])
        preview_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        scroll_y2 = tk.Scrollbar(preview_frame, orient="vertical")
        scroll_y2.pack(side="right", fill="y")
        
        self.preview_text = tk.Text(preview_frame, wrap="word", bg=c["surface"], fg=c["text"],
                                     yscrollcommand=scroll_y2.set, font=("Consolas", 10),
                                     insertbackground=c["text"], selectbackground=c["selected"],
                                     selectforeground=c["selected_text"], highlightbackground=c["border"],
                                     highlightcolor=c["primary"], relief=tk.FLAT, padx=10, pady=10)
        self.preview_text.pack(fill="both", expand=True)
        scroll_y2.config(command=self.preview_text.yview)
        
        # 底部信息
        self.info_label = tk.Label(right_frame, text="选择文件查看内容", bg=c["panel"], fg=c["muted"])
        self.info_label.pack(pady=5)
    
    def _load_content(self):
        """加载知识库内容"""
        self.files = []
        self.file_listbox.delete(0, END)
        if not self.kb_path.exists():
            self.preview_text.delete("1.0", END)
            self.preview_text.insert("1.0", "知识库目录不存在")
            self.stats_label.config(text="文件数: 0")
            return

        self.preview_text.delete("1.0", END)
        self.preview_text.insert("1.0", "正在扫描知识库文件，请稍候...")
        self.stats_label.config(text="文件数: 扫描中...")

        def task():
            try:
                files = _discover_supported_files(self.kb_path)
                error = None
            except Exception as e:
                files = []
                error = str(e)

            def apply():
                if not self.dialog.winfo_exists():
                    return
                self.files = files
                self.file_listbox.delete(0, END)
                for f in files:
                    rel_path = f.relative_to(self.kb_path)
                    self.file_listbox.insert(END, str(rel_path))
                self.stats_label.config(text=f"文件数: {len(files)}")
                if error:
                    self.preview_text.delete("1.0", END)
                    self.preview_text.insert("1.0", f"扫描知识库失败: {error}")
                elif files:
                    self.preview_text.delete("1.0", END)
                    self.preview_text.insert("1.0", "请选择左侧文件查看内容")
                else:
                    self.preview_text.delete("1.0", END)
                    self.preview_text.insert("1.0", "未发现支持的文件类型")

            self._safe_after(0, apply)

        threading.Thread(target=task, daemon=True).start()
    
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
            
            if ext in SUPPORTED_KB_EXTENSIONS:
                content = read_file_text(file_path)
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
    
    def _on_search(self, event=None):
        """搜索知识库内容"""
        query = self.search_var.get().strip()
        if not query:
            return
        if not self.files:
            self.preview_text.delete("1.0", END)
            self.preview_text.insert("1.0", "暂无可搜索的文件")
            return
        if self._search_in_progress:
            return

        self._search_in_progress = True
        self.search_btn.config(state=tk.DISABLED)
        self.preview_text.delete("1.0", END)
        self.preview_text.insert("1.0", f"正在搜索 '{query}'，请稍候...")

        def task():
            results = _search_text_matches(self.files, self.kb_path, query)

            def apply():
                if not self.dialog.winfo_exists():
                    return
                self.preview_text.delete("1.0", END)
                if results:
                    self.preview_text.insert("1.0", f"搜索 '{query}' 找到 {len(results)} 个结果:\n\n")
                    for i, result in enumerate(results, 1):
                        self.preview_text.insert(END, f"━━━ {i}. {result['file']} ━━━\n")
                        self.preview_text.insert(END, f"...{result['context']}...\n\n")
                else:
                    self.preview_text.insert("1.0", f"未找到包含 '{query}' 的内容")

                self._search_in_progress = False
                self.search_btn.config(state=tk.NORMAL)

            self._safe_after(0, apply)

        threading.Thread(target=task, daemon=True).start()


class KBChunkPreviewDialog:
    """Preview indexed chunks from meta.sqlite, not raw source documents."""

    def __init__(self, parent, index_dir: str):
        self.parent = parent
        self.index_dir = Path(index_dir)
        self.shards: list[dict] = []
        self.chunks: list[dict] = []
        self.colors = _kb_colors()

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("索引 Chunk 预览")
        self.dialog.geometry("1050x680")
        self.dialog.transient(parent)
        self.dialog.configure(bg=self.colors["bg"])

        self._build_ui()
        self._load_shards()

    def _build_ui(self):
        c = self.colors
        toolbar = tk.Frame(self.dialog, bg=c["panel"], height=52)
        toolbar.pack(fill="x", padx=10, pady=10)
        toolbar.pack_propagate(False)

        tk.Label(
            toolbar,
            text=f"索引目录: {self.index_dir}",
            bg=c["panel"],
            fg=c["text"],
            font=("", 11, "bold"),
        ).pack(side="left", padx=10)

        tk.Label(toolbar, text="Shard:", bg=c["panel"], fg=c["muted"]).pack(side="left", padx=(20, 5))
        self.shard_var = tk.StringVar()
        self.shard_combo = ttk.Combobox(toolbar, textvariable=self.shard_var, state="readonly", width=32)
        self.shard_combo.pack(side="left", padx=5)
        self.shard_combo.bind("<<ComboboxSelected>>", self._on_shard_selected)

        _kb_button(
            toolbar,
            text="刷新",
            command=self._load_shards,
            color=Theme.SURFACE_DARK,
            padx=12,
            pady=4,
        ).pack(side="left", padx=8)

        main = tk.Frame(self.dialog, bg=c["bg"])
        main.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        left = tk.Frame(main, bg=c["panel"], width=360)
        left.pack(side="left", fill="both", padx=(0, 10))
        left.pack_propagate(False)

        tk.Label(left, text="Chunk 列表", bg=c["panel"], fg=c["text"], font=("", 11, "bold")).pack(pady=(10, 4))
        self.chunk_count_label = tk.Label(left, text="0 chunks", bg=c["panel"], fg=c["muted"])
        self.chunk_count_label.pack(pady=(0, 6))

        list_frame = tk.Frame(left, bg=c["surface"])
        list_frame.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        scroll = tk.Scrollbar(list_frame, orient="vertical")
        scroll.pack(side="right", fill="y")
        self.chunk_listbox = tk.Listbox(
            list_frame,
            bg=c["surface"],
            fg=c["text"],
            selectbackground=c["selected"],
            selectforeground=c["selected_text"],
            highlightbackground=c["border"],
            highlightcolor=c["primary"],
            relief=tk.FLAT,
            yscrollcommand=scroll.set,
            font=("Consolas", 9),
        )
        self.chunk_listbox.pack(fill="both", expand=True)
        scroll.config(command=self.chunk_listbox.yview)
        self.chunk_listbox.bind("<<ListboxSelect>>", self._on_chunk_selected)

        right = tk.Frame(main, bg=c["panel"])
        right.pack(side="right", fill="both", expand=True)
        tk.Label(right, text="Chunk 内容", bg=c["panel"], fg=c["text"], font=("", 11, "bold")).pack(pady=(10, 4))
        self.meta_label = tk.Label(right, text="请选择一个 chunk", bg=c["panel"], fg=c["muted"], anchor="w", justify="left")
        self.meta_label.pack(fill="x", padx=10, pady=(0, 6))

        text_frame = tk.Frame(right, bg=c["surface"])
        text_frame.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        text_scroll = tk.Scrollbar(text_frame, orient="vertical")
        text_scroll.pack(side="right", fill="y")
        self.chunk_text = tk.Text(
            text_frame,
            wrap="word",
            bg=c["surface"],
            fg=c["text"],
            yscrollcommand=text_scroll.set,
            font=("Consolas", 10),
            insertbackground=c["text"],
            selectbackground=c["selected"],
            selectforeground=c["selected_text"],
            highlightbackground=c["border"],
            highlightcolor=c["primary"],
            relief=tk.FLAT,
            padx=10,
            pady=10,
        )
        self.chunk_text.pack(fill="both", expand=True)
        text_scroll.config(command=self.chunk_text.yview)

    def _load_shards(self):
        self.shards = _discover_index_shards(self.index_dir)
        labels = [f"{s['label']} ({s['count']} chunks)" for s in self.shards]
        self.shard_combo["values"] = labels
        self.chunk_listbox.delete(0, END)
        self.chunk_text.delete("1.0", END)
        if not self.shards:
            self.shard_var.set("")
            self.chunk_count_label.config(text="未找到 meta.sqlite")
            self.chunk_text.insert("1.0", "没有找到已构建的 chunk 索引。请先构建索引。")
            return
        self.shard_var.set(labels[0])
        self._load_chunks_for_shard(0)

    def _selected_shard_index(self) -> int:
        label = self.shard_var.get()
        labels = [f"{s['label']} ({s['count']} chunks)" for s in self.shards]
        try:
            return labels.index(label)
        except ValueError:
            return 0

    def _on_shard_selected(self, _event=None):
        self._load_chunks_for_shard(self._selected_shard_index())

    def _load_chunks_for_shard(self, shard_index: int):
        if not self.shards:
            return
        shard = self.shards[max(0, min(shard_index, len(self.shards) - 1))]
        try:
            self.chunks = _load_index_chunks(shard["db_path"])
        except Exception as e:
            self.chunks = []
            self.chunk_text.delete("1.0", END)
            self.chunk_text.insert("1.0", f"读取 chunk 失败: {e}")
        self.chunk_listbox.delete(0, END)
        for row in self.chunks:
            source = Path(str(row.get("path") or row.get("source_id") or "")).name
            preview = " ".join(str(row.get("text", "")).split())[:42]
            self.chunk_listbox.insert(END, f"#{row.get('ordinal', 0):04d} p{row.get('position', 0)} {source} | {preview}")
        self.chunk_count_label.config(text=f"{len(self.chunks)} chunks")
        self.meta_label.config(text=f"Shard: {shard['label']} | SQLite: {shard['db_path']}")
        self.chunk_text.delete("1.0", END)
        if self.chunks:
            self.chunk_listbox.selection_set(0)
            self._show_chunk(0)
        else:
            self.chunk_text.insert("1.0", "这个 shard 暂无 chunk。")

    def _on_chunk_selected(self, _event=None):
        selection = self.chunk_listbox.curselection()
        if not selection:
            return
        self._show_chunk(selection[0])

    def _show_chunk(self, index: int):
        if index < 0 or index >= len(self.chunks):
            return
        row = self.chunks[index]
        tags = ", ".join(str(x) for x in row.get("tags") or [])
        meta = (
            f"chunk_id: {row.get('chunk_id', '')}\n"
            f"source: {row.get('source_id', '')}\n"
            f"path: {row.get('path', '')}\n"
            f"kb_type: {row.get('kb_type', '')} | project_id: {row.get('project_id') or '-'} | "
            f"position: {row.get('position', 0)} | ordinal: {row.get('ordinal', 0)} | tags: {tags or '-'}"
        )
        self.meta_label.config(text=meta)
        self.chunk_text.delete("1.0", END)
        self.chunk_text.insert("1.0", str(row.get("text", "")))


class KBManagerDialog:
    """知识库管理对话框"""
    
    def __init__(
        self,
        parent,
        data_dir: str,
        index_dir: str,
        on_rebuild: callable = None,
        on_incremental: callable = None,
    ):
        self.parent = parent
        self.data_dir = Path(data_dir)
        self.index_dir = Path(index_dir)
        self.on_rebuild = on_rebuild
        self.on_incremental = on_incremental
        self.colors = _kb_colors()
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("知识库管理")
        self.dialog.geometry("700x500")
        self.dialog.transient(parent)
        
        self.dialog.configure(bg=self.colors["bg"])
        
        self._build_ui()
        self._load_stats()
    
    def _build_ui(self):
        """构建UI"""
        c = self.colors
        # 标题
        tk.Label(self.dialog, text="📚 知识库管理", bg=c["bg"], fg=c["text"],
                 font=("", 16, "bold")).pack(pady=20)
        
        # 信息卡片
        info_frame = tk.Frame(self.dialog, bg=c["panel"])
        info_frame.pack(fill="x", padx=20, pady=10)
        
        # 数据目录
        row1 = tk.Frame(info_frame, bg=c["panel"])
        row1.pack(fill="x", padx=15, pady=10)
        tk.Label(row1, text="数据目录:", bg=c["panel"], fg=c["muted"], width=12, anchor="w").pack(side="left")
        tk.Label(row1, text=str(self.data_dir), bg=c["panel"], fg=c["text"]).pack(side="left")
        
        # 索引目录
        row2 = tk.Frame(info_frame, bg=c["panel"])
        row2.pack(fill="x", padx=15, pady=5)
        tk.Label(row2, text="索引目录:", bg=c["panel"], fg=c["muted"], width=12, anchor="w").pack(side="left")
        tk.Label(row2, text=str(self.index_dir), bg=c["panel"], fg=c["text"]).pack(side="left")
        
        # 统计信息
        stats_frame = tk.Frame(self.dialog, bg=c["panel"])
        stats_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(stats_frame, text="统计信息", bg=c["panel"], fg=c["text"],
                 font=("", 12, "bold")).pack(anchor="w", padx=15, pady=10)
        
        self.stats_text = tk.Text(
            stats_frame,
            height=8,
            bg=c["surface"],
            fg=c["text"],
            insertbackground=c["text"],
            selectbackground=c["selected"],
            selectforeground=c["selected_text"],
            highlightbackground=c["border"],
            highlightcolor=c["primary"],
            relief=tk.FLAT,
            font=("Consolas", 10),
            padx=10,
            pady=10,
        )
        self.stats_text.pack(fill="x", padx=15, pady=(0, 10))
        
        # 操作按钮
        btn_frame = tk.Frame(self.dialog, bg=c["bg"])
        btn_frame.pack(fill="x", padx=20, pady=20)
        
        _kb_button(btn_frame, text="👁️ 预览内容", command=self._preview_content, color=c["primary"]).pack(side="left", padx=10)

        _kb_button(btn_frame, text="🧩 查看 Chunk", command=self._preview_chunks, color=c["info"]).pack(side="left", padx=10)
        
        _kb_button(btn_frame, text="🔄 增量更新", command=self._incremental_update, color=c["success"]).pack(side="left", padx=10)

        _kb_button(btn_frame, text="🔨 重建索引", command=self._rebuild_index, color=c["primary"]).pack(side="left", padx=10)
        
        _kb_button(btn_frame, text="📁 添加文档", command=self._add_documents, color=c["accent"]).pack(side="left", padx=10)
        
        _kb_button(btn_frame, text="🗑️ 清除索引", command=self._clear_index, color=c["danger"]).pack(side="left", padx=10)
        
        # 支持的格式说明
        format_frame = tk.Frame(self.dialog, bg=c["panel"])
        format_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(format_frame, text="支持的文档格式:", bg=c["panel"], fg=c["text"],
                 font=("", 11, "bold")).pack(anchor="w", padx=15, pady=10)
        
        formats_text = """• 纯文本: .txt
• Markdown: .md / .markdown
• JSON: .json
• CSV: .csv
• Word文档: .docx (需安装 python-docx)
• PDF文档: .pdf (需安装 pypdf 或 PyPDF2)"""
        
        tk.Label(format_frame, text=formats_text, bg=c["panel"], fg=c["muted"],
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
            documents = []
            for shard in _discover_index_shards(self.index_dir):
                documents.extend(_load_index_documents(Path(shard["db_path"])))
            stats.append(f"资料档案: {len(documents)} 个")
            if documents:
                latest = max(
                    documents,
                    key=lambda item: int(item.get("mtime_ns") or 0),
                )
                latest_name = Path(
                    str(latest.get("path") or latest.get("source_id") or "")
                ).name
                stats.append(f"最新文档: {latest_name}")
            
            # Check whether the current v2 index layout is valid.
            if _has_valid_index_artifacts(self.index_dir):
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

    def _preview_chunks(self):
        """Preview indexed chunks from meta.sqlite."""
        if not _has_valid_index_artifacts(self.index_dir):
            messagebox.showwarning("提示", "未找到有效索引，请先构建索引")
            return
        KBChunkPreviewDialog(self.dialog, str(self.index_dir))
    
    def _rebuild_index(self):
        """重建索引"""
        if self.on_rebuild:
            self.on_rebuild()
            self.after(1000, self._load_stats)

    def _incremental_update(self):
        """Incrementally update the index from the current data directory."""
        if self.on_incremental:
            self.on_incremental()
            self.after(1000, self._load_stats)
    
    def _add_documents(self):
        """添加文档"""
        files = filedialog.askopenfilenames(
            title="选择要添加的文档",
            filetypes=[
                ("所有支持的格式", "*.txt;*.md;*.markdown;*.json;*.csv;*.docx;*.pdf"),
                ("文本文件", "*.txt"),
                ("Markdown", "*.md;*.markdown"),
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
        if copied and self.on_incremental:
            self.on_incremental()
        self._load_stats()
    
    def _clear_index(self):
        """清除索引"""
        if not messagebox.askyesno("确认", "确定要清除所有索引吗？\n这不会删除原始文档。"):
            return
        
        try:
            self.index_dir.mkdir(parents=True, exist_ok=True)
            removed, kept = _clear_known_index_artifacts(self.index_dir)
            if removed:
                detail = f"已清理 {removed} 个索引文件"
                if kept:
                    detail += f"\n保留 {kept} 个非索引文件"
                messagebox.showinfo("完成", detail)
            else:
                messagebox.showinfo("完成", "未发现可清理的索引文件")
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
            
            rebuild_func = self.on_ingest_rebuild if hasattr(self, 'on_ingest_rebuild') else (self.on_ingest if hasattr(self, 'on_ingest') else None)
            incremental_func = self.on_ingest_incremental if hasattr(self, 'on_ingest_incremental') else None
            KBManagerDialog(self, data_path, index_path, rebuild_func, incremental_func)
        else:
            messagebox.showwarning("提示", "请先配置知识库路径")
