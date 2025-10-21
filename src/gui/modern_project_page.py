"""
现代化项目管理页面
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from .theme import Theme
from .custom_widgets import ModernButton, ModernCard, ModernEntry


class ModernProjectPage:
    """现代化项目管理页面"""
    
    def __init__(self, parent, project_manager):
        self.parent = parent
        self.project_manager = project_manager
        self.current_project = None
        
        self._build_page()
    
    def _build_page(self):
        """构建页面"""
        # 页面容器
        self.container = tk.Frame(self.parent, bg=Theme.BG_SECONDARY)
        self.container.pack(fill="both", expand=True)
        
        # 顶部操作栏
        self._create_action_bar()
        
        # 项目统计卡片
        self._create_stats_cards()
        
        # 项目列表
        self._create_project_list()
    
    def _create_action_bar(self):
        """创建顶部操作栏"""
        action_bar = tk.Frame(self.container, bg=Theme.BG_SECONDARY)
        action_bar.pack(fill="x", pady=(0, 24))
        
        # 左侧：标题和描述
        left_frame = tk.Frame(action_bar, bg=Theme.BG_SECONDARY)
        left_frame.pack(side="left")
        
        tk.Label(
            left_frame,
            text="我的项目",
            font=(Theme.FONT_FAMILY, 24, "bold"),
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_PRIMARY
        ).pack(anchor="w")
        
        tk.Label(
            left_frame,
            text="管理你的创作项目，追踪进度",
            font=(Theme.FONT_FAMILY, 13),
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_SECONDARY
        ).pack(anchor="w", pady=(4, 0))
        
        # 右侧：操作按钮
        right_frame = tk.Frame(action_bar, bg=Theme.BG_SECONDARY)
        right_frame.pack(side="right")
        
        # 新建项目按钮
        new_btn = ModernButton(
            right_frame,
            text="➕ 新建项目",
            variant="primary",
            command=self._on_new_project
        )
        new_btn.pack(side="left", padx=8)
        
        # 刷新按钮
        refresh_btn = ModernButton(
            right_frame,
            text="🔄 刷新",
            variant="secondary",
            command=self._refresh_project_list
        )
        refresh_btn.pack(side="left")
    
    def _create_stats_cards(self):
        """创建统计卡片"""
        stats_frame = tk.Frame(self.container, bg=Theme.BG_SECONDARY)
        stats_frame.pack(fill="x", pady=(0, 24))
        
        # 统计数据
        projects = self.project_manager.list_projects()
        total_projects = len(projects)
        total_words = sum(p.get("story_length", 0) for p in projects)
        total_images = sum(p.get("image_count", 0) for p in projects)
        recent_projects = len([p for p in projects if self._is_recent(p.get("updated_at", ""))])
        
        # 创建4个统计卡片
        cards_data = [
            ("📁", "项目总数", str(total_projects), Theme.PRIMARY),
            ("📝", "总字数", f"{total_words:,}", Theme.ACCENT),
            ("🎨", "图片总数", str(total_images), Theme.WARNING),
            ("🕐", "近期项目", str(recent_projects), Theme.INFO)
        ]
        
        for i, (icon, title, value, color) in enumerate(cards_data):
            self._create_stat_card(stats_frame, icon, title, value, color, i)
    
    def _create_stat_card(self, parent, icon, title, value, color, index):
        """创建单个统计卡片"""
        card = tk.Frame(parent, bg=Theme.SURFACE, highlightthickness=1, highlightbackground=Theme.BORDER)
        card.pack(side="left", fill="both", expand=True, padx=(0 if index == 0 else 8, 0))
        
        # 内容
        inner = tk.Frame(card, bg=Theme.SURFACE)
        inner.pack(padx=20, pady=16)
        
        # 图标
        icon_frame = tk.Frame(inner, bg=color + "20", width=48, height=48)  # 20% 透明度
        icon_frame.pack(pady=(0, 12))
        icon_frame.pack_propagate(False)
        
        tk.Label(
            icon_frame,
            text=icon,
            font=(Theme.FONT_FAMILY, 20),
            bg=color + "20",
            fg=color
        ).place(relx=0.5, rely=0.5, anchor="center")
        
        # 数值
        tk.Label(
            inner,
            text=value,
            font=(Theme.FONT_FAMILY, 24, "bold"),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY
        ).pack()
        
        # 标题
        tk.Label(
            inner,
            text=title,
            font=(Theme.FONT_FAMILY, 12),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_SECONDARY
        ).pack(pady=(4, 0))
    
    def _create_project_list(self):
        """创建项目列表"""
        # 列表容器
        list_card = tk.Frame(self.container, bg=Theme.SURFACE, highlightthickness=1, highlightbackground=Theme.BORDER)
        list_card.pack(fill="both", expand=True)
        
        # 列表头部
        list_header = tk.Frame(list_card, bg=Theme.SURFACE)
        list_header.pack(fill="x", padx=24, pady=16)
        
        tk.Label(
            list_header,
            text="项目列表",
            font=(Theme.FONT_FAMILY, 16, "bold"),
            bg=Theme.SURFACE,
            fg=Theme.TEXT_PRIMARY
        ).pack(side="left")
        
        # 搜索框
        search_frame = tk.Frame(list_header, bg=Theme.BG_SECONDARY)
        search_frame.pack(side="right")
        
        search_icon = tk.Label(
            search_frame,
            text="🔍",
            font=(Theme.FONT_FAMILY, 12),
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_HINT
        )
        search_icon.pack(side="left", padx=(12, 8))
        
        self.search_entry = tk.Entry(
            search_frame,
            font=(Theme.FONT_FAMILY, 12),
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_PRIMARY,
            bd=0,
            width=20,
            insertbackground=Theme.PRIMARY
        )
        self.search_entry.pack(side="left", pady=6)
        self.search_entry.insert(0, "搜索项目...")
        self.search_entry.bind("<FocusIn>", self._on_search_focus_in)
        self.search_entry.bind("<FocusOut>", self._on_search_focus_out)
        self.search_entry.bind("<KeyRelease>", self._on_search_change)
        
        tk.Label(search_frame, bg=Theme.BG_SECONDARY, width=1).pack(side="left", padx=8)
        
        # 分隔线
        tk.Frame(list_card, bg=Theme.DIVIDER, height=1).pack(fill="x", padx=24)
        
        # 项目列表
        self.list_container = tk.Frame(list_card, bg=Theme.SURFACE)
        self.list_container.pack(fill="both", expand=True, padx=24, pady=16)
        
        # 滚动区域
        self.canvas = tk.Canvas(self.list_container, bg=Theme.SURFACE, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.list_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=Theme.SURFACE)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 加载项目
        self._load_projects()
    
    def _load_projects(self, search_term=""):
        """加载项目列表"""
        # 清空现有内容
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # 获取项目
        projects = self.project_manager.list_projects()
        
        # 搜索过滤
        if search_term and search_term != "搜索项目...":
            projects = [p for p in projects if search_term.lower() in p.get("name", "").lower()]
        
        if not projects:
            # 空状态
            empty_frame = tk.Frame(self.scrollable_frame, bg=Theme.SURFACE)
            empty_frame.pack(fill="both", expand=True, pady=60)
            
            tk.Label(
                empty_frame,
                text="📂",
                font=(Theme.FONT_FAMILY, 48),
                bg=Theme.SURFACE,
                fg=Theme.TEXT_HINT
            ).pack()
            
            tk.Label(
                empty_frame,
                text="暂无项目",
                font=(Theme.FONT_FAMILY, 16),
                bg=Theme.SURFACE,
                fg=Theme.TEXT_SECONDARY
            ).pack(pady=(12, 4))
            
            tk.Label(
                empty_frame,
                text="点击上方"新建项目"开始创作",
                font=(Theme.FONT_FAMILY, 13),
                bg=Theme.SURFACE,
                fg=Theme.TEXT_HINT
            ).pack()
            return
        
        # 显示项目
        for i, project in enumerate(projects):
            self._create_project_item(self.scrollable_frame, project, i)
    
    def _create_project_item(self, parent, project, index):
        """创建项目列表项"""
        # 项目卡片
        item_frame = tk.Frame(parent, bg=Theme.BG_SECONDARY, cursor="hand2")
        item_frame.pack(fill="x", pady=(0 if index == 0 else 8, 0))
        
        # 内容
        inner = tk.Frame(item_frame, bg=Theme.BG_SECONDARY)
        inner.pack(fill="x", padx=16, pady=12)
        
        # 左侧：项目信息
        left_frame = tk.Frame(inner, bg=Theme.BG_SECONDARY)
        left_frame.pack(side="left", fill="x", expand=True)
        
        # 项目名称
        name_frame = tk.Frame(left_frame, bg=Theme.BG_SECONDARY)
        name_frame.pack(anchor="w")
        
        tk.Label(
            name_frame,
            text=project.get("name", "未命名项目"),
            font=(Theme.FONT_FAMILY, 14, "bold"),
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_PRIMARY
        ).pack(side="left", padx=(0, 8))
        
        # 分类标签
        if project.get("category"):
            category_label = tk.Frame(name_frame, bg=Theme.PRIMARY_SUBTLE)
            category_label.pack(side="left")
            
            tk.Label(
                category_label,
                text=project["category"],
                font=(Theme.FONT_FAMILY, 10),
                bg=Theme.PRIMARY_SUBTLE,
                fg=Theme.PRIMARY,
                padx=8,
                pady=2
            ).pack()
        
        # 项目详情
        details_frame = tk.Frame(left_frame, bg=Theme.BG_SECONDARY)
        details_frame.pack(anchor="w", pady=(4, 0))
        
        details = [
            f"📝 {project.get('story_length', 0):,} 字",
            f"🎨 {project.get('image_count', 0)} 张图片",
            f"🕐 {self._format_time(project.get('updated_at', ''))}"
        ]
        
        for detail in details:
            tk.Label(
                details_frame,
                text=detail,
                font=(Theme.FONT_FAMILY, 11),
                bg=Theme.BG_SECONDARY,
                fg=Theme.TEXT_SECONDARY
            ).pack(side="left", padx=(0, 16))
        
        # 右侧：操作按钮
        right_frame = tk.Frame(inner, bg=Theme.BG_SECONDARY)
        right_frame.pack(side="right")
        
        # 打开按钮
        open_btn = ModernButton(
            right_frame,
            text="打开",
            variant="primary",
            command=lambda: self._open_project(project)
        )
        open_btn.pack(side="left", padx=4)
        
        # 删除按钮
        delete_btn = ModernButton(
            right_frame,
            text="🗑️",
            variant="ghost",
            command=lambda: self._delete_project(project)
        )
        delete_btn.pack(side="left")
        
        # 绑定整个卡片点击事件
        for widget in [item_frame, inner, left_frame]:
            widget.bind("<Button-1>", lambda e, p=project: self._open_project(p))
        
        # 悬停效果
        def on_enter(e):
            item_frame.configure(bg=Theme.BG_HOVER)
            inner.configure(bg=Theme.BG_HOVER)
            for child in inner.winfo_children():
                self._update_bg_recursive(child, Theme.BG_HOVER)
        
        def on_leave(e):
            item_frame.configure(bg=Theme.BG_SECONDARY)
            inner.configure(bg=Theme.BG_SECONDARY)
            for child in inner.winfo_children():
                self._update_bg_recursive(child, Theme.BG_SECONDARY)
        
        item_frame.bind("<Enter>", on_enter)
        item_frame.bind("<Leave>", on_leave)
    
    def _update_bg_recursive(self, widget, bg):
        """递归更新背景色"""
        try:
            if widget.winfo_class() in ["Button", "TButton"]:
                return
            if hasattr(widget, 'configure'):
                current_bg = widget.cget("bg")
                if current_bg in [Theme.BG_SECONDARY, Theme.BG_HOVER]:
                    widget.configure(bg=bg)
            for child in widget.winfo_children():
                self._update_bg_recursive(child, bg)
        except:
            pass
    
    def _is_recent(self, date_str):
        """判断是否为近期项目（7天内）"""
        try:
            if not date_str:
                return False
            update_time = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            days_diff = (datetime.now(update_time.tzinfo) - update_time).days
            return days_diff <= 7
        except:
            return False
    
    def _format_time(self, date_str):
        """格式化时间显示"""
        try:
            if not date_str:
                return "未知时间"
            update_time = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return update_time.strftime("%Y-%m-%d %H:%M")
        except:
            return date_str[:19].replace("T", " ") if date_str else "未知时间"
    
    def _on_search_focus_in(self, event):
        """搜索框获得焦点"""
        if self.search_entry.get() == "搜索项目...":
            self.search_entry.delete(0, tk.END)
            self.search_entry.configure(fg=Theme.TEXT_PRIMARY)
    
    def _on_search_focus_out(self, event):
        """搜索框失去焦点"""
        if not self.search_entry.get():
            self.search_entry.insert(0, "搜索项目...")
            self.search_entry.configure(fg=Theme.TEXT_HINT)
    
    def _on_search_change(self, event):
        """搜索内容变化"""
        search_term = self.search_entry.get()
        self._load_projects(search_term)
    
    def _on_new_project(self):
        """创建新项目"""
        # 弹出对话框
        dialog = tk.Toplevel(self.parent)
        dialog.title("新建项目")
        dialog.geometry("400x200")
        dialog.configure(bg=Theme.BG_PRIMARY)
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - dialog.winfo_width()) // 2
        y = (dialog.winfo_screenheight() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # 内容
        content = tk.Frame(dialog, bg=Theme.BG_PRIMARY)
        content.pack(fill="both", expand=True, padx=24, pady=24)
        
        tk.Label(
            content,
            text="项目名称",
            font=(Theme.FONT_FAMILY, 13),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, 8))
        
        name_entry = ModernEntry(content, placeholder="输入项目名称...")
        name_entry.pack(fill="x", pady=(0, 16))
        name_entry.focus()
        
        # 按钮
        btn_frame = tk.Frame(content, bg=Theme.BG_PRIMARY)
        btn_frame.pack(anchor="e")
        
        def create_project():
            name = name_entry.get_value()
            if name:
                try:
                    project = self.project_manager.create_project(name)
                    self.current_project = project
                    dialog.destroy()
                    self._refresh_project_list()
                    messagebox.showinfo("成功", f"项目 '{name}' 创建成功！")
                except Exception as e:
                    messagebox.showerror("错误", f"创建项目失败: {e}")
        
        ModernButton(
            btn_frame,
            text="取消",
            variant="secondary",
            command=dialog.destroy
        ).pack(side="left", padx=4)
        
        ModernButton(
            btn_frame,
            text="创建",
            variant="primary",
            command=create_project
        ).pack(side="left")
        
        # 回车创建
        name_entry.bind("<Return>", lambda e: create_project())
    
    def _open_project(self, project):
        """打开项目"""
        try:
            self.current_project = self.project_manager.load_project(project["path"])
            messagebox.showinfo("成功", f"项目 '{project['name']}' 已加载")
            # TODO: 切换到故事页面并加载内容
        except Exception as e:
            messagebox.showerror("错误", f"加载项目失败: {e}")
    
    def _delete_project(self, project):
        """删除项目"""
        if messagebox.askyesno("确认删除", f"确定要删除项目 '{project['name']}' 吗？\n此操作不可恢复！"):
            try:
                self.project_manager.delete_project(project["path"])
                self._refresh_project_list()
                messagebox.showinfo("成功", "项目已删除")
            except Exception as e:
                messagebox.showerror("错误", f"删除项目失败: {e}")
    
    def _refresh_project_list(self):
        """刷新项目列表"""
        self._load_projects()
        self._create_stats_cards()  # 同时刷新统计




