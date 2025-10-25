"""
一致性设定对话框 - 为人物设定详细的外观和服装信息
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from typing import Dict, List, Optional

class ConsistencyDialog(tk.Toplevel):
    """一致性设定对话框"""
    
    def __init__(self, parent, consistency_data: Dict = None, characters: List[str] = None):
        super().__init__(parent)
        
        self.parent = parent
        self.consistency_data = consistency_data or {"characters": {}, "version": "1.0"}
        self.characters = characters or []
        self.result = None
        
        # 窗口设置
        self.title("🎨 人物一致性设定")
        self.geometry("900x700")
        self.resizable(True, True)
        
        # 居中显示
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 900) // 2
        y = (self.winfo_screenheight() - 700) // 2
        self.geometry(f"900x700+{x}+{y}")
        
        # 设置窗口为非模态，但保持在父窗口之上
        self.transient(parent)
        # 移除 grab_set() 以允许操作其他窗口
        # self.grab_set()
        
        # 初始化界面
        self._init_ui()
        
        # 加载数据
        self._load_data()
        
        # 绑定关闭事件 - 点击X时确认是否保存
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)
        
    def _init_ui(self):
        """初始化界面"""
        # 主容器
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 顶部工具栏
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(toolbar, text="选择人物：", font=("Arial", 10)).pack(side=tk.LEFT, padx=(0, 5))
        
        self.character_var = tk.StringVar()
        self.character_combo = ttk.Combobox(
            toolbar,
            textvariable=self.character_var,
            state="readonly",
            width=20
        )
        self.character_combo.pack(side=tk.LEFT, padx=(0, 20))
        self.character_combo.bind("<<ComboboxSelected>>", self._on_character_selected)
        
        # 导入导出按钮
        ttk.Button(toolbar, text="📥 导入设定", command=self._on_import).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="📤 导出设定", command=self._on_export).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="➕ 添加人物", command=self._on_add_character).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🤖 智能填写", command=self._on_auto_fill).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🎯 智能识别人物", command=self._on_auto_detect_characters).pack(side=tk.LEFT, padx=5)
        
        # 创建Notebook
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 基本信息页
        self.basic_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.basic_frame, text="📝 基本信息")
        self._create_basic_info_tab()
        
        # 外观设定页
        self.appearance_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.appearance_frame, text="👤 外观设定")
        self._create_appearance_tab()
        
        # 服装设定页
        self.outfit_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.outfit_frame, text="👔 服装设定")
        self._create_outfit_tab()
        
        # 表情动作页
        self.expression_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.expression_frame, text="😊 表情动作")
        self._create_expression_tab()
        
        # 预览页
        self.preview_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.preview_frame, text="👁️ 预览")
        self._create_preview_tab()
        
        # 人物图片库页（只读查看）
        self.gallery_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.gallery_frame, text="📸 图片库")
        self._create_gallery_tab()
        
        # 底部按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="保存", command=self._on_save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="取消", command=self._on_cancel).pack(side=tk.RIGHT)
        
    def _create_basic_info_tab(self):
        """创建基本信息标签页"""
        frame = ttk.LabelFrame(self.basic_frame, text="基本信息", padding="10")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建输入控件
        self.basic_info_vars = {}
        
        # 姓名
        ttk.Label(frame, text="姓名：").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.basic_info_vars['name'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.basic_info_vars['name'], width=30).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # 年龄
        ttk.Label(frame, text="年龄：").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.basic_info_vars['age'] = tk.StringVar()
        age_frame = ttk.Frame(frame)
        age_frame.grid(row=1, column=1, sticky=tk.W, pady=5)
        ttk.Entry(age_frame, textvariable=self.basic_info_vars['age'], width=10).pack(side=tk.LEFT)
        ttk.Label(age_frame, text="（如：25岁、青年、中年等）").pack(side=tk.LEFT, padx=(10, 0))
        
        # 性别
        ttk.Label(frame, text="性别：").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.basic_info_vars['gender'] = tk.StringVar()
        gender_frame = ttk.Frame(frame)
        gender_frame.grid(row=2, column=1, sticky=tk.W, pady=5)
        ttk.Radiobutton(gender_frame, text="男", variable=self.basic_info_vars['gender'], value="男").pack(side=tk.LEFT)
        ttk.Radiobutton(gender_frame, text="女", variable=self.basic_info_vars['gender'], value="女").pack(side=tk.LEFT, padx=(20, 0))
        ttk.Radiobutton(gender_frame, text="其他", variable=self.basic_info_vars['gender'], value="其他").pack(side=tk.LEFT, padx=(20, 0))
        
        # 身份/职业
        ttk.Label(frame, text="身份/职业：").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.basic_info_vars['occupation'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.basic_info_vars['occupation'], width=30).grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # 性格特征
        ttk.Label(frame, text="性格特征：").grid(row=4, column=0, sticky=tk.NW, pady=5)
        self.personality_text = tk.Text(frame, width=40, height=3)
        self.personality_text.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        # 背景故事
        ttk.Label(frame, text="背景故事：").grid(row=5, column=0, sticky=tk.NW, pady=5)
        self.background_text = tk.Text(frame, width=40, height=4)
        self.background_text.grid(row=5, column=1, sticky=tk.W, pady=5)
        
    def _create_appearance_tab(self):
        """创建外观设定标签页"""
        # 创建滚动框架
        canvas = tk.Canvas(self.appearance_frame)
        scrollbar = ttk.Scrollbar(self.appearance_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.appearance_vars = {}
        
        # 面部特征
        face_frame = ttk.LabelFrame(scrollable_frame, text="面部特征", padding="10")
        face_frame.pack(fill=tk.X, padx=10, pady=5)
        
        face_items = [
            ("脸型", "face_shape", ["圆脸", "方脸", "瓜子脸", "鹅蛋脸", "长脸", "菱形脸"]),
            ("肤色", "skin_tone", ["白皙", "自然", "小麦色", "古铜色", "黝黑"]),
            ("眼睛", "eyes", ["大眼睛", "小眼睛", "杏仁眼", "凤眼", "圆眼", "细长眼"]),
            ("眉毛", "eyebrows", ["柳叶眉", "剑眉", "一字眉", "弯月眉", "粗眉", "细眉"]),
            ("鼻子", "nose", ["高挺", "小巧", "鹰钩鼻", "塌鼻", "直鼻"]),
            ("嘴巴", "mouth", ["樱桃小嘴", "大嘴", "薄唇", "厚唇", "性感嘴唇"]),
            ("特殊标记", "special_marks", ["无", "痣", "疤痕", "雀斑", "酒窝"])
        ]
        
        for i, (label, key, options) in enumerate(face_items):
            ttk.Label(face_frame, text=f"{label}：").grid(row=i, column=0, sticky=tk.W, pady=3)
            self.appearance_vars[key] = tk.StringVar()
            combo = ttk.Combobox(face_frame, textvariable=self.appearance_vars[key], values=options, width=20)
            combo.grid(row=i, column=1, sticky=tk.W, pady=3)
        
        # 发型特征
        hair_frame = ttk.LabelFrame(scrollable_frame, text="发型特征", padding="10")
        hair_frame.pack(fill=tk.X, padx=10, pady=5)
        
        hair_items = [
            ("发色", "hair_color", ["黑色", "棕色", "金色", "红色", "灰色", "白色", "染色"]),
            ("长度", "hair_length", ["短发", "中长发", "长发", "及肩", "及腰", "光头"]),
            ("发型", "hair_style", ["直发", "卷发", "波浪", "马尾", "双马尾", "丸子头", "披肩发", "编发"]),
            ("刘海", "bangs", ["无刘海", "齐刘海", "斜刘海", "空气刘海", "中分"])
        ]
        
        for i, (label, key, options) in enumerate(hair_items):
            ttk.Label(hair_frame, text=f"{label}：").grid(row=i, column=0, sticky=tk.W, pady=3)
            self.appearance_vars[key] = tk.StringVar()
            combo = ttk.Combobox(hair_frame, textvariable=self.appearance_vars[key], values=options, width=20)
            combo.grid(row=i, column=1, sticky=tk.W, pady=3)
        
        # 身材特征
        body_frame = ttk.LabelFrame(scrollable_frame, text="身材特征", padding="10")
        body_frame.pack(fill=tk.X, padx=10, pady=5)
        
        body_items = [
            ("身高", "height", ["矮小", "偏矮", "中等", "偏高", "高大"]),
            ("体型", "body_type", ["纤瘦", "苗条", "匀称", "健壮", "微胖", "肥胖"]),
            ("特征", "body_features", ["无", "肌肉发达", "啤酒肚", "驼背", "挺拔"])
        ]
        
        for i, (label, key, options) in enumerate(body_items):
            ttk.Label(body_frame, text=f"{label}：").grid(row=i, column=0, sticky=tk.W, pady=3)
            self.appearance_vars[key] = tk.StringVar()
            combo = ttk.Combobox(body_frame, textvariable=self.appearance_vars[key], values=options, width=20)
            combo.grid(row=i, column=1, sticky=tk.W, pady=3)
        
    def _create_outfit_tab(self):
        """创建服装设定标签页"""
        # 主框架
        main_frame = ttk.Frame(self.outfit_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 服装场景选择
        scene_frame = ttk.Frame(main_frame)
        scene_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(scene_frame, text="服装场景：").pack(side=tk.LEFT)
        self.outfit_scene_var = tk.StringVar(value="默认")
        self.outfit_scene_combo = ttk.Combobox(
            scene_frame,
            textvariable=self.outfit_scene_var,
            values=["默认", "工作", "休闲", "正式", "运动", "睡衣"],
            state="readonly",
            width=15
        )
        self.outfit_scene_combo.pack(side=tk.LEFT, padx=(5, 20))
        self.outfit_scene_combo.bind("<<ComboboxSelected>>", self._on_outfit_scene_changed)
        
        ttk.Button(scene_frame, text="➕ 添加场景", command=self._on_add_outfit_scene).pack(side=tk.LEFT)
        
        # 服装详情
        outfit_frame = ttk.LabelFrame(main_frame, text="服装详情", padding="10")
        outfit_frame.pack(fill=tk.BOTH, expand=True)
        
        self.outfit_vars = {}
        
        # 上装
        ttk.Label(outfit_frame, text="上装：").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.outfit_vars['top'] = tk.StringVar()
        top_entry = ttk.Entry(outfit_frame, textvariable=self.outfit_vars['top'], width=40)
        top_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        ttk.Label(outfit_frame, text="（如：白色衬衫、黑色T恤等）").grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        
        # 下装
        ttk.Label(outfit_frame, text="下装：").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.outfit_vars['bottom'] = tk.StringVar()
        bottom_entry = ttk.Entry(outfit_frame, textvariable=self.outfit_vars['bottom'], width=40)
        bottom_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        ttk.Label(outfit_frame, text="（如：蓝色牛仔裤、黑色西裤等）").grid(row=1, column=2, sticky=tk.W, padx=(10, 0))
        
        # 鞋子
        ttk.Label(outfit_frame, text="鞋子：").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.outfit_vars['shoes'] = tk.StringVar()
        shoes_entry = ttk.Entry(outfit_frame, textvariable=self.outfit_vars['shoes'], width=40)
        shoes_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # 配饰
        ttk.Label(outfit_frame, text="配饰：").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.outfit_vars['accessories'] = tk.StringVar()
        accessories_entry = ttk.Entry(outfit_frame, textvariable=self.outfit_vars['accessories'], width=40)
        accessories_entry.grid(row=3, column=1, sticky=tk.W, pady=5)
        ttk.Label(outfit_frame, text="（如：眼镜、手表、项链等）").grid(row=3, column=2, sticky=tk.W, padx=(10, 0))
        
        # 整体风格
        ttk.Label(outfit_frame, text="整体风格：").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.outfit_vars['style'] = tk.StringVar()
        style_combo = ttk.Combobox(
            outfit_frame,
            textvariable=self.outfit_vars['style'],
            values=["休闲", "正式", "商务", "运动", "时尚", "复古", "朋克", "优雅"],
            width=38
        )
        style_combo.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        # 颜色主调
        ttk.Label(outfit_frame, text="颜色主调：").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.outfit_vars['color_scheme'] = tk.StringVar()
        color_entry = ttk.Entry(outfit_frame, textvariable=self.outfit_vars['color_scheme'], width=40)
        color_entry.grid(row=5, column=1, sticky=tk.W, pady=5)
        ttk.Label(outfit_frame, text="（如：黑白配、蓝色系等）").grid(row=5, column=2, sticky=tk.W, padx=(10, 0))
        
    def _create_expression_tab(self):
        """创建表情动作标签页"""
        main_frame = ttk.Frame(self.expression_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 默认表情
        default_frame = ttk.LabelFrame(main_frame, text="默认表情", padding="10")
        default_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(default_frame, text="基础表情：").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.default_expression = tk.StringVar()
        expression_combo = ttk.Combobox(
            default_frame,
            textvariable=self.default_expression,
            values=["中性", "微笑", "严肃", "友善", "冷漠", "忧郁", "自信"],
            width=20
        )
        expression_combo.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # 常用表情
        expressions_frame = ttk.LabelFrame(main_frame, text="常用表情集", padding="10")
        expressions_frame.pack(fill=tk.BOTH, expand=True)
        
        # 表情列表
        self.expression_listbox = tk.Listbox(expressions_frame, height=8)
        self.expression_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 添加一些默认表情
        default_expressions = [
            "开心 - 眼睛弯成月牙，嘴角上扬",
            "悲伤 - 眉头紧锁，嘴角下垂",
            "愤怒 - 怒目圆睁，咬牙切齿",
            "惊讶 - 睁大眼睛，张大嘴巴",
            "思考 - 微皱眉头，手托下巴",
            "害羞 - 低头含笑，脸颊泛红"
        ]
        for expr in default_expressions:
            self.expression_listbox.insert(tk.END, expr)
        
        # 表情编辑区
        edit_frame = ttk.Frame(expressions_frame)
        edit_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        ttk.Button(edit_frame, text="添加", command=self._on_add_expression).pack(pady=2)
        ttk.Button(edit_frame, text="编辑", command=self._on_edit_expression).pack(pady=2)
        ttk.Button(edit_frame, text="删除", command=self._on_delete_expression).pack(pady=2)
        
        # 常用动作
        actions_frame = ttk.LabelFrame(main_frame, text="常用动作", padding="10")
        actions_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(actions_frame, text="动作描述：").grid(row=0, column=0, sticky=tk.NW, pady=5)
        self.actions_text = tk.Text(actions_frame, width=50, height=4)
        self.actions_text.grid(row=0, column=1, sticky=tk.W, pady=5)
        self.actions_text.insert("1.0", "站立姿势挺拔、走路步伐稳健、坐姿端正")
        
    def _create_preview_tab(self):
        """创建预览标签页"""
        # 预览文本框
        preview_frame = ttk.LabelFrame(self.preview_frame, text="一致性约束预览", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(preview_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.preview_text = tk.Text(preview_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set)
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.preview_text.yview)
        
        # 刷新按钮
        ttk.Button(preview_frame, text="🔄 刷新预览", command=self._update_preview).pack(pady=(10, 0))
        
    def _load_data(self):
        """加载数据"""
        # 更新人物列表
        all_characters = list(self.consistency_data.get("characters", {}).keys())
        all_characters.extend([c for c in self.characters if c not in all_characters])
        
        if all_characters:
            self.character_combo['values'] = all_characters
            self.character_combo.set(all_characters[0])
            self._on_character_selected()
        
    def _on_character_selected(self, event=None):
        """当选择人物时"""
        char_name = self.character_var.get()
        if not char_name:
            return
        
        # 获取人物数据
        char_data = self.consistency_data.get("characters", {}).get(char_name, {})
        
        # 加载基本信息
        basic_info = char_data.get("basic_info", {})
        self.basic_info_vars['name'].set(char_name)
        self.basic_info_vars['age'].set(basic_info.get("age", ""))
        self.basic_info_vars['gender'].set(basic_info.get("gender", ""))
        self.basic_info_vars['occupation'].set(basic_info.get("occupation", ""))
        
        # 加载性格和背景
        self.personality_text.delete("1.0", tk.END)
        self.personality_text.insert("1.0", basic_info.get("personality", ""))
        self.background_text.delete("1.0", tk.END)
        self.background_text.insert("1.0", basic_info.get("background", ""))
        
        # 加载外观信息
        appearance = char_data.get("appearance", {})
        face = appearance.get("face", {})
        hair = appearance.get("hair", {})
        body = appearance.get("body", {})
        
        self.appearance_vars['face_shape'].set(face.get("shape", ""))
        self.appearance_vars['skin_tone'].set(face.get("skin_tone", ""))
        self.appearance_vars['eyes'].set(face.get("eyes", ""))
        self.appearance_vars['eyebrows'].set(face.get("eyebrows", ""))
        self.appearance_vars['nose'].set(face.get("nose", ""))
        self.appearance_vars['mouth'].set(face.get("mouth", ""))
        self.appearance_vars['special_marks'].set(face.get("special_marks", "无"))
        
        self.appearance_vars['hair_color'].set(hair.get("color", ""))
        self.appearance_vars['hair_length'].set(hair.get("length", ""))
        self.appearance_vars['hair_style'].set(hair.get("style", ""))
        self.appearance_vars['bangs'].set(hair.get("bangs", ""))
        
        self.appearance_vars['height'].set(body.get("height", ""))
        self.appearance_vars['body_type'].set(body.get("body_type", ""))
        self.appearance_vars['body_features'].set(body.get("features", ""))
        
        # 加载默认服装
        self._load_outfit_data()
        
        # 加载表情动作
        self.default_expression.set(char_data.get("expressions", {}).get("default", "中性"))
        self.actions_text.delete("1.0", tk.END)
        self.actions_text.insert("1.0", char_data.get("actions", {}).get("common", ""))
        
        # 刷新图片库（如果存在）
        if hasattr(self, 'gallery_refresh'):
            self.gallery_refresh()
        
        # 更新预览
        self._update_preview()
        
    def _load_outfit_data(self):
        """加载服装数据"""
        char_name = self.character_var.get()
        if not char_name:
            return
        
        char_data = self.consistency_data.get("characters", {}).get(char_name, {})
        outfits = char_data.get("outfits", {})
        scene = self.outfit_scene_var.get()
        
        # 如果是"默认"但实际键名是"default"
        if scene == "默认":
            outfit_key = "default"
        else:
            outfit_key = scene
        
        outfit = outfits.get(outfit_key, {})
        
        self.outfit_vars['top'].set(outfit.get("top", ""))
        self.outfit_vars['bottom'].set(outfit.get("bottom", ""))
        self.outfit_vars['shoes'].set(outfit.get("shoes", ""))
        self.outfit_vars['accessories'].set(outfit.get("accessories", ""))
        self.outfit_vars['style'].set(outfit.get("style", ""))
        self.outfit_vars['color_scheme'].set(outfit.get("color_scheme", ""))
        
    def _on_outfit_scene_changed(self, event=None):
        """当服装场景改变时"""
        self._save_current_outfit()
        self._load_outfit_data()
        
    def _save_current_outfit(self):
        """保存当前服装设定"""
        char_name = self.character_var.get()
        if not char_name:
            return
        
        # 确保字符存在
        if char_name not in self.consistency_data.get("characters", {}):
            self.consistency_data.setdefault("characters", {})[char_name] = {
                "basic_info": {"name": char_name},
                "appearance": {},
                "outfits": {},
                "expressions": {},
                "actions": {}
            }
        
        scene = self.outfit_scene_var.get()
        outfit_key = "default" if scene == "默认" else scene
        
        outfit_data = {
            "top": self.outfit_vars['top'].get(),
            "bottom": self.outfit_vars['bottom'].get(),
            "shoes": self.outfit_vars['shoes'].get(),
            "accessories": self.outfit_vars['accessories'].get(),
            "style": self.outfit_vars['style'].get(),
            "color_scheme": self.outfit_vars['color_scheme'].get()
        }
        
        self.consistency_data["characters"][char_name].setdefault("outfits", {})[outfit_key] = outfit_data
        
    def _on_add_character(self):
        """添加新人物"""
        dialog = tk.Toplevel(self)
        dialog.title("添加人物")
        dialog.geometry("300x150")
        
        # 居中
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 300) // 2
        y = (dialog.winfo_screenheight() - 150) // 2
        dialog.geometry(f"300x150+{x}+{y}")
        
        ttk.Label(dialog, text="人物名称：").pack(pady=10)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=30)
        name_entry.pack(pady=5)
        name_entry.focus()
        
        def on_ok():
            name = name_var.get().strip()
            if name:
                if name not in self.consistency_data.get("characters", {}):
                    self.consistency_data.setdefault("characters", {})[name] = {
                        "basic_info": {"name": name},
                        "appearance": {"face": {}, "hair": {}, "body": {}},
                        "outfits": {"default": {}},
                        "expressions": {"default": "中性"},
                        "actions": {"common": ""}
                    }
                    
                    # 更新下拉列表
                    values = list(self.character_combo['values'])
                    if name not in values:
                        values.append(name)
                    self.character_combo['values'] = values
                    self.character_combo.set(name)
                    self._on_character_selected()
                else:
                    messagebox.showwarning("提示", "该人物已存在")
            dialog.destroy()
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        ttk.Button(button_frame, text="确定", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT)
        
        # 绑定回车键
        name_entry.bind("<Return>", lambda e: on_ok())
        
    def _on_add_outfit_scene(self):
        """添加服装场景"""
        dialog = tk.Toplevel(self)
        dialog.title("添加服装场景")
        dialog.geometry("300x150")
        
        ttk.Label(dialog, text="场景名称：").pack(pady=10)
        scene_var = tk.StringVar()
        scene_entry = ttk.Entry(dialog, textvariable=scene_var, width=30)
        scene_entry.pack(pady=5)
        
        def on_ok():
            scene = scene_var.get().strip()
            if scene:
                values = list(self.outfit_scene_combo['values'])
                if scene not in values:
                    values.append(scene)
                    self.outfit_scene_combo['values'] = values
                self.outfit_scene_combo.set(scene)
                self._on_outfit_scene_changed()
            dialog.destroy()
        
        ttk.Button(dialog, text="确定", command=on_ok).pack(pady=20)
        
    def _on_add_expression(self):
        """添加表情"""
        dialog = tk.Toplevel(self)
        dialog.title("添加表情")
        dialog.geometry("400x200")
        
        ttk.Label(dialog, text="表情名称：").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var, width=30).grid(row=0, column=1, padx=10, pady=5)
        
        ttk.Label(dialog, text="表情描述：").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        desc_text = tk.Text(dialog, width=30, height=3)
        desc_text.grid(row=1, column=1, padx=10, pady=5)
        
        def on_ok():
            name = name_var.get().strip()
            desc = desc_text.get("1.0", tk.END).strip()
            if name and desc:
                self.expression_listbox.insert(tk.END, f"{name} - {desc}")
            dialog.destroy()
        
        ttk.Button(dialog, text="确定", command=on_ok).grid(row=2, column=0, columnspan=2, pady=20)
        
    def _on_edit_expression(self):
        """编辑表情"""
        selection = self.expression_listbox.curselection()
        if not selection:
            return
        
        # TODO: 实现编辑功能
        messagebox.showinfo("提示", "编辑功能待完善")
        
    def _on_delete_expression(self):
        """删除表情"""
        selection = self.expression_listbox.curselection()
        if selection:
            self.expression_listbox.delete(selection[0])
            
    def _update_preview(self):
        """更新预览"""
        char_name = self.character_var.get()
        if not char_name:
            return
        
        # 保存当前数据
        self._save_current_character_data()
        
        # 生成预览文本
        char_data = self.consistency_data.get("characters", {}).get(char_name, {})
        
        preview_text = f"【{char_name} - 人物一致性设定】\n\n"
        
        # 基本信息
        basic = char_data.get("basic_info", {})
        preview_text += "=== 基本信息 ===\n"
        preview_text += f"姓名：{basic.get('name', char_name)}\n"
        preview_text += f"年龄：{basic.get('age', '未设定')}\n"
        preview_text += f"性别：{basic.get('gender', '未设定')}\n"
        preview_text += f"身份：{basic.get('occupation', '未设定')}\n"
        if basic.get('personality'):
            preview_text += f"性格：{basic.get('personality')}\n"
        preview_text += "\n"
        
        # 外观特征
        appearance = char_data.get("appearance", {})
        face = appearance.get("face", {})
        hair = appearance.get("hair", {})
        body = appearance.get("body", {})
        
        preview_text += "=== 外观特征 ===\n"
        if face.get("shape"):
            preview_text += f"脸型：{face['shape']}\n"
        if face.get("skin_tone"):
            preview_text += f"肤色：{face['skin_tone']}\n"
        if face.get("eyes"):
            preview_text += f"眼睛：{face['eyes']}\n"
        if hair.get("color") and hair.get("style"):
            preview_text += f"发型：{hair['color']}{hair.get('length', '')}{hair['style']}\n"
        if body.get("height") or body.get("body_type"):
            preview_text += f"身材：{body.get('height', '')} {body.get('body_type', '')}\n"
        preview_text += "\n"
        
        # 服装设定
        outfits = char_data.get("outfits", {})
        if outfits:
            preview_text += "=== 服装设定 ===\n"
            for scene, outfit in outfits.items():
                if any(outfit.values()):
                    scene_name = "默认" if scene == "default" else scene
                    preview_text += f"【{scene_name}】\n"
                    if outfit.get("top"):
                        preview_text += f"  上装：{outfit['top']}\n"
                    if outfit.get("bottom"):
                        preview_text += f"  下装：{outfit['bottom']}\n"
                    if outfit.get("shoes"):
                        preview_text += f"  鞋子：{outfit['shoes']}\n"
                    if outfit.get("accessories"):
                        preview_text += f"  配饰：{outfit['accessories']}\n"
            preview_text += "\n"
        
        # 生成约束提示词
        preview_text += "=== AI生成约束提示词 ===\n"
        preview_text += self._generate_constraint_prompt(char_name, char_data)
        
        # 更新预览文本
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", preview_text)
        
    def _generate_constraint_prompt(self, char_name: str, char_data: Dict) -> str:
        """生成约束提示词"""
        basic = char_data.get("basic_info", {})
        appearance = char_data.get("appearance", {})
        outfits = char_data.get("outfits", {})
        
        prompt_parts = []
        
        # 基本特征
        if basic.get("age") and basic.get("gender"):
            prompt_parts.append(f"{basic['age']}{basic['gender']}")
        
        # 外观特征
        face = appearance.get("face", {})
        hair = appearance.get("hair", {})
        
        if face.get("skin_tone"):
            prompt_parts.append(f"{face['skin_tone']}肤色")
        
        if hair.get("color") and hair.get("style"):
            hair_desc = f"{hair['color']}{hair.get('length', '')}{hair['style']}"
            if hair.get("bangs"):
                hair_desc += f"，{hair['bangs']}"
            prompt_parts.append(hair_desc)
        
        if face.get("eyes"):
            prompt_parts.append(face['eyes'])
        
        # 默认服装
        default_outfit = outfits.get("default", {})
        if default_outfit.get("top"):
            prompt_parts.append(f"穿着{default_outfit['top']}")
        if default_outfit.get("bottom"):
            prompt_parts.append(default_outfit['bottom'])
        
        # 特殊标记
        if face.get("special_marks") and face["special_marks"] != "无":
            prompt_parts.append(f"有{face['special_marks']}")
        
        # 组合提示词
        if prompt_parts:
            prompt = f"{char_name}：" + "，".join(prompt_parts)
            prompt += f"\n注意：生成的{char_name}必须严格符合上述特征，确保在所有镜头中保持一致。"
        else:
            prompt = f"{char_name}：角色特征待设定"
        
        return prompt
        
    def _save_current_character_data(self):
        """保存当前人物数据"""
        char_name = self.character_var.get()
        if not char_name:
            return
        
        # 确保字符存在
        if char_name not in self.consistency_data.get("characters", {}):
            self.consistency_data.setdefault("characters", {})[char_name] = {}
        
        char_data = self.consistency_data["characters"][char_name]
        
        # 保存基本信息
        char_data["basic_info"] = {
            "name": self.basic_info_vars['name'].get(),
            "age": self.basic_info_vars['age'].get(),
            "gender": self.basic_info_vars['gender'].get(),
            "occupation": self.basic_info_vars['occupation'].get(),
            "personality": self.personality_text.get("1.0", tk.END).strip(),
            "background": self.background_text.get("1.0", tk.END).strip()
        }
        
        # 保存外观信息
        char_data["appearance"] = {
            "face": {
                "shape": self.appearance_vars['face_shape'].get(),
                "skin_tone": self.appearance_vars['skin_tone'].get(),
                "eyes": self.appearance_vars['eyes'].get(),
                "eyebrows": self.appearance_vars['eyebrows'].get(),
                "nose": self.appearance_vars['nose'].get(),
                "mouth": self.appearance_vars['mouth'].get(),
                "special_marks": self.appearance_vars['special_marks'].get()
            },
            "hair": {
                "color": self.appearance_vars['hair_color'].get(),
                "length": self.appearance_vars['hair_length'].get(),
                "style": self.appearance_vars['hair_style'].get(),
                "bangs": self.appearance_vars['bangs'].get()
            },
            "body": {
                "height": self.appearance_vars['height'].get(),
                "body_type": self.appearance_vars['body_type'].get(),
                "features": self.appearance_vars['body_features'].get()
            }
        }
        
        # 保存当前服装
        self._save_current_outfit()
        
        # 保存表情动作
        char_data["expressions"] = {
            "default": self.default_expression.get(),
            "list": [self.expression_listbox.get(i) for i in range(self.expression_listbox.size())]
        }
        
        char_data["actions"] = {
            "common": self.actions_text.get("1.0", tk.END).strip()
        }
        
        # 生成约束提示词
        char_data["constraint_prompt"] = self._generate_constraint_prompt(char_name, char_data)
        
    def _on_import(self):
        """导入设定"""
        filename = filedialog.askopenfilename(
            title="选择一致性设定文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if "characters" in data:
                    self.consistency_data = data
                    self._load_data()
                    messagebox.showinfo("成功", "导入成功")
                else:
                    messagebox.showwarning("警告", "文件格式不正确")
            except Exception as e:
                messagebox.showerror("错误", f"导入失败：{str(e)}")
                
    def _on_export(self):
        """导出设定"""
        filename = filedialog.asksaveasfilename(
            title="保存一致性设定",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if filename:
            try:
                # 保存当前数据
                self._save_current_character_data()
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.consistency_data, f, ensure_ascii=False, indent=2)
                
                messagebox.showinfo("成功", "导出成功")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败：{str(e)}")
                
    def _on_save(self):
        """保存并关闭"""
        # 保存当前人物数据
        self._save_current_character_data()
        
        # 设置结果
        self.result = self.consistency_data
        self.destroy()
        
    def _on_cancel(self):
        """取消 - 不保存数据"""
        # 询问是否确认取消
        if messagebox.askyesno("确认", "是否放弃所有修改？"):
            self.result = None
            self.destroy()
    
    def _on_window_close(self):
        """点击窗口关闭按钮时"""
        # 询问是否保存
        answer = messagebox.askyesnocancel(
            "保存设定",
            "是否保存人物一致性设定？\n\n是：保存并关闭\n否：放弃修改并关闭\n取消：继续编辑"
        )
        
        if answer is True:
            # 保存
            self._on_save()
        elif answer is False:
            # 不保存
            self.result = None
            self.destroy()
        # answer is None: 取消，不做任何操作
        
    def get_result(self) -> Optional[Dict]:
        """获取结果"""
        return self.result
    
    def _on_auto_fill(self):
        """智能填写 - 根据故事和剧本自动分析人物特征"""
        char_name = self.character_var.get()
        if not char_name:
            messagebox.showwarning("提示", "请先选择一个人物")
            return
        
        # 获取故事或剧本内容
        story_content = ""
        script_content = ""
        
        # 尝试从父窗口获取内容
        if hasattr(self.parent, 'output'):
            story_content = self.parent.output.get("1.0", tk.END).strip()
        if hasattr(self.parent, 'script_text'):
            script_content = self.parent.script_text.get("1.0", tk.END).strip()
        
        content = script_content or story_content
        if not content:
            messagebox.showwarning("提示", "未找到故事或剧本内容，请先生成故事")
            return
        
        # 显示进度窗口
        progress_window = tk.Toplevel(self)
        progress_window.title("智能分析中...")
        progress_window.geometry("400x150")
        progress_window.transient(self)
        
        progress_label = tk.Label(progress_window, text=f"正在分析 {char_name} 的特征...")
        progress_label.pack(pady=30)
        
        progress_bar = ttk.Progressbar(progress_window, length=300, mode='indeterminate')
        progress_bar.pack(pady=20)
        progress_bar.start(10)
        
        def analyze():
            try:
                # 使用AI分析人物特征
                character_info = self._analyze_character_from_story(char_name, content)
                
                # 更新UI
                self.after(0, lambda: self._apply_analyzed_info(character_info))
                self.after(0, lambda: progress_window.destroy())
                self.after(0, lambda: messagebox.showinfo("成功", f"已智能填写 {char_name} 的基本信息"))
                
            except Exception as e:
                self.after(0, lambda: progress_window.destroy())
                self.after(0, lambda: messagebox.showerror("错误", f"分析失败：{str(e)}"))
        
        # 在后台线程执行
        import threading
        threading.Thread(target=analyze, daemon=True).start()
    
    def _analyze_character_from_story(self, character_name: str, content: str) -> Dict:
        """使用AI分析故事中的人物特征"""
        try:
            # 检查是否有API配置
            if not hasattr(self.parent, 'api_key') or not self.parent.api_key.get():
                raise Exception("请先在故事生成页面配置API")
            
            from src.clients.deepseek_client import DeepSeekClient
            
            client = DeepSeekClient(
                api_key=self.parent.api_key.get(),
                base_url=self.parent.base_url.get(),
                model=self.parent.model.get()
            )
            
            # 构建分析提示词 - 更详细的提取
            prompt = f"""
请作为专业的人物特征分析师，仔细分析以下故事/剧本中关于【{character_name}】的**所有外貌和特征描述**。

## 分析要求
1. 逐字逐句搜索关于【{character_name}】的描述
2. 特别关注：外貌、穿着、发型、表情、动作等细节
3. 如果故事中未明确提及某项，推测合理的默认值
4. 必须输出完整的JSON格式

## 需要提取的详细信息

### 基本信息
- age: 年龄（精确数字或范围，如"25岁"、"20-25岁"、"青年"）
- gender: 性别（"男"或"女"）
- occupation: 职业/身份/角色定位（如"高中生"、"公司白领"、"警察"）
- personality: 性格特点（3-5个关键词，如"开朗、热情、勇敢"）

### 面部特征（详细）
- face_shape: 脸型（如"瓜子脸"、"国字脸"、"圆脸"、"鹅蛋脸"）
- skin_tone: 肤色（如"白皙"、"小麦色"、"健康肤色"、"黝黑"）
- eyes: 眼睛特征（如"大眼睛"、"丹凤眼"、"深邃的眼睛"、"明亮的黑眼睛"）
- eyebrows: 眉毛（如"浓眉"、"柳叶眉"、"剑眉"）
- nose: 鼻子（如"高挺"、"小巧"、"秀气"）
- mouth: 嘴唇（如"薄唇"、"红润"、"丰满"）
- special_marks: 特殊标记（如"左颊有痣"、"眼镜"、"酒窝"）

### 发型特征
- hair_color: 发色（如"黑色"、"棕色"、"金色"、"染色"）
- hair_length: 发长（如"短发"、"齐肩"、"长发"、"及腰"）
- hair_style: 发型（如"马尾"、"披肩"、"短寸"、"卷发"、"直发"）
- bangs: 刘海（如"齐刘海"、"空气刘海"、"中分"、"无刘海"）

### 身材体型
- height: 身高（如"高挑"、"中等"、"娇小"、"约170cm"）
- body_type: 体型（如"苗条"、"健壮"、"匀称"、"丰满"、"瘦削"）
- body_features: 身体特征（如"长腿"、"宽肩"、"纤细的手指"）

### 服装风格
- default_outfit: 常穿服装（如"校服"、"西装"、"休闲装"、"运动装"）
- outfit_description: 服装详细描述（颜色、款式、配饰等）

### 其他特征
- accessories: 配饰（如"手表"、"项链"、"耳环"、"眼镜"）
- typical_expression: 典型表情（如"微笑"、"严肃"、"温柔"）
- mannerisms: 行为习惯（如"爱笑"、"说话轻声"、"走路匆忙"）

## 故事内容
{content[:3000]}

## 输出格式
请直接输出JSON，不要任何其他文字：
{{
    "age": "具体年龄",
    "gender": "性别",
    "occupation": "职业",
    "personality": "性格描述",
    "face_shape": "脸型",
    "skin_tone": "肤色",
    "eyes": "眼睛",
    "eyebrows": "眉毛",
    "nose": "鼻子",
    "mouth": "嘴唇",
    "special_marks": "特殊标记",
    "hair_color": "发色",
    "hair_length": "发长",
    "hair_style": "发型",
    "bangs": "刘海",
    "height": "身高",
    "body_type": "体型",
    "body_features": "身体特征",
    "default_outfit": "常穿服装",
    "outfit_description": "服装详细描述",
    "accessories": "配饰",
    "typical_expression": "典型表情",
    "mannerisms": "行为习惯"
}}
"""
            
            response = client.chat([
                {"role": "system", "content": "你是专业的文学分析助手，擅长从文本中提取人物特征。"},
                {"role": "user", "content": prompt}
            ], temperature=0.3)
            
            # 解析JSON响应
            import json
            import re
            
            # 提取JSON部分
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                character_data = json.loads(json_match.group())
            else:
                # 如果没有找到JSON，创建默认结构
                character_data = {}
            
            # 转换为内部格式
            character_info = {
                "age": character_data.get("年龄", "未提及"),
                "gender": character_data.get("性别", "未提及"),
                "occupation": character_data.get("职业", "") or character_data.get("身份", ""),
                "face_shape": character_data.get("脸型", ""),
                "skin_tone": character_data.get("肤色", ""),
                "eyes": character_data.get("眼睛", ""),
                "hair_color": character_data.get("发色", "") or character_data.get("头发颜色", ""),
                "hair_style": character_data.get("发型", ""),
                "hair_length": character_data.get("发长", ""),
                "clothing": character_data.get("服装", "") or character_data.get("常穿服装", ""),
                "personality": character_data.get("性格", "") or character_data.get("性格特点", ""),
                "special_marks": character_data.get("特殊标记", "") or character_data.get("其他特征", "")
            }
            
            return character_info
            
        except Exception as e:
            print(f"AI分析失败：{str(e)}")
            # 返回空信息
            return {}
    
    def _apply_analyzed_info(self, character_info: Dict):
        """将分析的信息应用到UI"""
        if not character_info:
            return
        
        # 基本信息
        if character_info.get("age") and character_info["age"] != "未提及":
            self.basic_info_vars['age'].set(character_info["age"])
        
        if character_info.get("gender") and character_info["gender"] != "未提及":
            self.basic_info_vars['gender'].set(character_info["gender"])
        
        if character_info.get("occupation"):
            self.basic_info_vars['occupation'].set(character_info["occupation"])
        
        if character_info.get("personality"):
            self.personality_text.delete("1.0", tk.END)
            self.personality_text.insert("1.0", character_info["personality"])
        
        # 外观信息
        if character_info.get("face_shape"):
            self.appearance_vars['face_shape'].set(character_info["face_shape"])
        
        if character_info.get("skin_tone"):
            self.appearance_vars['skin_tone'].set(character_info["skin_tone"])
        
        if character_info.get("eyes"):
            self.appearance_vars['eyes'].set(character_info["eyes"])
        
        # 发型
        if character_info.get("hair_color"):
            self.appearance_vars['hair_color'].set(character_info["hair_color"])
        
        if character_info.get("hair_length"):
            self.appearance_vars['hair_length'].set(character_info["hair_length"])
        
        if character_info.get("hair_style"):
            self.appearance_vars['hair_style'].set(character_info["hair_style"])
        
        # 服装
        if character_info.get("clothing"):
            # 尝试解析服装描述
            clothing = character_info["clothing"]
            if "衬衫" in clothing or "T恤" in clothing or "上衣" in clothing:
                self.outfit_vars['top'].set(clothing)
            elif "裤" in clothing or "裙" in clothing:
                self.outfit_vars['bottom'].set(clothing)
            else:
                # 如果无法区分，放在上装
                self.outfit_vars['top'].set(clothing)
        
        # 特殊标记
        if character_info.get("special_marks"):
            self.appearance_vars['special_marks'].set(character_info["special_marks"])
        
        # 更新预览
        self._update_preview()
    
    def _on_auto_detect_characters(self):
        """智能识别故事中的所有人物并自动创建和填写"""
        # 获取故事或剧本内容
        story_content = ""
        script_content = ""
        
        # 尝试从父窗口获取内容
        if hasattr(self.parent, 'output'):
            story_content = self.parent.output.get("1.0", tk.END).strip()
        if hasattr(self.parent, 'script_text'):
            script_content = self.parent.script_text.get("1.0", tk.END).strip()
        
        content = script_content or story_content
        if not content:
            messagebox.showwarning("提示", "未找到故事或剧本内容，请先生成故事")
            return
        
        # 显示进度窗口
        progress_window = tk.Toplevel(self)
        progress_window.title("智能识别人物中...")
        progress_window.geometry("500x250")
        progress_window.transient(self)
        
        progress_label = tk.Label(progress_window, text="正在分析故事，识别所有人物...")
        progress_label.pack(pady=20)
        
        progress_bar = ttk.Progressbar(progress_window, length=400, mode='indeterminate')
        progress_bar.pack(pady=20)
        progress_bar.start(10)
        
        result_text = tk.Text(progress_window, height=6, width=60)
        result_text.pack(pady=10, padx=10)
        
        def analyze():
            try:
                # 使用AI识别所有人物
                characters_info = self._detect_all_characters(content)
                
                if not characters_info:
                    self.after(0, lambda: result_text.insert("1.0", "未能识别到人物信息"))
                    self.after(0, lambda: progress_window.after(2000, progress_window.destroy))
                    return
                
                # 更新进度显示
                self.after(0, lambda: progress_label.config(text=f"识别到 {len(characters_info)} 个人物，正在创建..."))
                self.after(0, lambda: result_text.insert("1.0", f"识别到的人物：\n"))
                
                # 为每个人物创建设定
                for i, (char_name, char_info) in enumerate(characters_info.items()):
                    # 添加到一致性数据
                    if char_name not in self.consistency_data.get("characters", {}):
                        self.consistency_data.setdefault("characters", {})[char_name] = {
                            "basic_info": {"name": char_name},
                            "appearance": {"face": {}, "hair": {}, "body": {}},
                            "outfits": {"default": {}},
                            "expressions": {"default": "中性"},
                            "actions": {"common": ""}
                        }
                    
                    # 更新显示
                    self.after(0, lambda n=char_name, info=char_info: result_text.insert("end", f"• {n}: {info.get('brief', '已识别')}\n"))
                    
                    # 应用分析的信息
                    if char_info:
                        self.consistency_data["characters"][char_name]["basic_info"].update({
                            "age": char_info.get("age", ""),
                            "gender": char_info.get("gender", ""),
                            "occupation": char_info.get("occupation", "")
                        })
                        
                        if char_info.get("appearance"):
                            self._update_character_appearance(char_name, char_info)
                
                # 更新UI
                self.after(0, self._refresh_character_list)
                self.after(0, lambda: progress_label.config(text="✅ 人物识别完成！"))
                self.after(0, lambda: progress_window.after(3000, progress_window.destroy))
                
                # 如果有人物，选择第一个并自动填写
                if characters_info:
                    first_char = list(characters_info.keys())[0]
                    self.after(100, lambda: self.character_combo.set(first_char))
                    self.after(200, lambda: self._on_character_selected())
                    self.after(300, lambda: self._on_auto_fill())
                
            except Exception as e:
                self.after(0, lambda: progress_window.destroy())
                self.after(0, lambda: messagebox.showerror("错误", f"人物识别失败：{str(e)}"))
        
        # 在后台线程执行
        import threading
        threading.Thread(target=analyze, daemon=True).start()
    
    def _detect_all_characters(self, content: str) -> Dict[str, Dict]:
        """使用AI检测故事中的所有人物"""
        try:
            # 检查是否有API配置
            if not hasattr(self.parent, 'api_key') or not self.parent.api_key.get():
                raise Exception("请先在故事生成页面配置API")
            
            from src.clients.deepseek_client import DeepSeekClient
            
            client = DeepSeekClient(
                api_key=self.parent.api_key.get(),
                base_url=self.parent.base_url.get(),
                model=self.parent.model.get()
            )
            
            # 构建人物识别提示词 - 精准提取文章人物
            prompt = f"""
你是专业的中文文学分析师。请从以下故事/剧本中**精准识别和提取所有人物角色**。

## 识别规则（必须严格遵守）

### 第一步：找出所有人物名字
1. **姓名识别标准**
   - 完整姓名：如"张伟"、"李小明"、"王晓红"
   - 单姓：如"张强"、"李明"、"王磊"
   - 称呼：如"张老师"、"李医生"、"王总"
   - 昵称：如"小明"、"阿强"（如果在故事中被多次提及）
   
2. **必须在故事中出现**
   - 有对话："张强说..."
   - 有动作："李明走进教室"
   - 被提及："王老师讲课"
   - 至少出现2次以上

3. **排除项**
   - 泛指：如"同学们"、"路人"、"大家"
   - 群体：如"警察"、"医生"（除非有具体名字）
   - 仅提及未出场的人物

### 第二步：提取人物详细信息
对每个识别出的人物，提取以下信息（必须基于原文）：

- **name**: 人物名字（必填，如"张强"、"李明"、"王老师"）
- **brief**: 一句话概括（身份+主要特点，15字内）
- **age**: 年龄（"17岁"、"25岁"、"中年"、"老年"等）
- **gender**: 性别（"男"或"女"，根据代词或描述判断）
- **occupation**: 职业/身份（"高中生"、"教师"、"医生"等）
- **appearance**: 外貌特征（只写故事中提到的）
- **role**: 重要性（"主角"、"重要配角"、"次要角色"）

### 第三步：按重要性排序
- 主角最前
- 按出场频率和重要性排序
- **提取所有出现的人物，不限数量**

## 输出格式（严格JSON）

```json
{{
  "人物姓名1": {{
    "brief": "身份和特点简述",
    "age": "年龄",
    "gender": "性别",
    "occupation": "职业/身份",
    "appearance": "外貌描述（如有）",
    "role": "主角/配角/次要角色"
  }},
  "人物姓名2": {{
    ...
  }}
}}
```

## 示例输出

```json
{{
  "李明": {{
    "brief": "17岁高中生，班长，成绩优异",
    "age": "17岁",
    "gender": "男",
    "occupation": "高中生",
    "appearance": "戴黑框眼镜，白色校服，短发",
    "role": "主角"
  }},
  "王老师": {{
    "brief": "语文老师，严格但关心学生",
    "age": "40多岁",
    "gender": "女",
    "occupation": "语文教师",
    "appearance": "穿职业装，盘发",
    "role": "配角"
  }}
}}
```

## 注意事项
- 只提取故事中真实出现的人物
- 不要添加故事中没有的人物
- 外貌描述必须基于原文
- 如果信息不明确，留空或标注"未提及"

## 故事内容（请从中提取人物）

{content[:4000]}

请直接输出JSON，不要其他说明：
"""
            
            response = client.chat([
                {"role": "system", "content": "你是专业的文学分析助手，擅长识别和分析故事人物。"},
                {"role": "user", "content": prompt}
            ], temperature=0.3)
            
            # 解析JSON响应
            import json
            import re
            
            # 提取JSON部分
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                characters_data = json.loads(json_match.group())
                return characters_data
            else:
                return {}
                
        except Exception as e:
            print(f"AI人物识别失败：{str(e)}")
            return {}
    
    def _refresh_character_list(self):
        """刷新人物下拉列表"""
        all_characters = list(self.consistency_data.get("characters", {}).keys())
        if all_characters:
            self.character_combo['values'] = all_characters
            if not self.character_var.get() and all_characters:
                self.character_combo.set(all_characters[0])
                self._on_character_selected()
    
    def _update_character_appearance(self, char_name: str, char_info: Dict):
        """更新人物外观信息到一致性数据"""
        char_data = self.consistency_data["characters"][char_name]
        
        # 解析外观描述
        appearance_text = char_info.get("appearance", "")
        
        # 简单的关键词匹配
        if "白大褂" in appearance_text or "医生" in char_info.get("occupation", ""):
            char_data["outfits"]["default"]["top"] = "白大褂"
        elif "护士服" in appearance_text or "护士" in char_info.get("occupation", ""):
            char_data["outfits"]["default"]["top"] = "护士服"
        elif "西装" in appearance_text:
            char_data["outfits"]["default"]["top"] = "西装"
        elif "校服" in appearance_text:
            char_data["outfits"]["default"]["top"] = "校服"
        
        # 解析发型
        if "短发" in appearance_text:
            char_data["appearance"]["hair"]["length"] = "短发"
        elif "长发" in appearance_text:
            char_data["appearance"]["hair"]["length"] = "长发"
        
        if "黑发" in appearance_text or "黑色" in appearance_text:
            char_data["appearance"]["hair"]["color"] = "黑色"
    
    def _create_gallery_tab(self):
        """创建人物图片库标签页（只读查看）"""
        main_frame = ttk.Frame(self.gallery_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 顶部说明
        info_frame = ttk.LabelFrame(main_frame, text="💡 使用说明", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        info_text = """
📸 人物照片已移至【图片管理页面】生成
• 标准形象、表情库(7种)、角度库(3种)
• 生成后，导演页面将自动使用这些图片保持人物一致性

👉 请前往：图片管理 → 人物管理 → 生成人物形象
        """
        ttk.Label(info_frame, text=info_text.strip(), justify=tk.LEFT, foreground="#FF9800").pack()
        
        # 引导按钮
        guide_frame = ttk.Frame(main_frame)
        guide_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(
            guide_frame,
            text="🎬 前往图片管理页面",
            command=self._goto_image_page,
            style="Accent.TButton"
        ).pack(pady=10)
        
        # 已有照片列表
        list_frame = ttk.LabelFrame(main_frame, text="已生成的人物照片", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建可滚动区域
        canvas = tk.Canvas(list_frame, bg="#2b2b2b")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.gallery_container = scrollable_frame
        self.gallery_refresh = lambda: self._refresh_gallery()
        
        # 加载照片
        self._refresh_gallery()
    
    def _goto_image_page(self):
        """跳转到图片管理页面"""
        try:
            # 获取主窗口的notebook
            if hasattr(self.parent, 'notebook'):
                for i in range(self.parent.notebook.index("end")):
                    if "图片" in self.parent.notebook.tab(i, "text"):
                        self.parent.notebook.select(i)
                        messagebox.showinfo("提示", 
                                          "已切换到图片管理页面！\n\n"
                                          "请在【人物管理】标签页：\n"
                                          "1. 选择人物\n"
                                          "2. 选择生成类型（标准/表情/角度）\n"
                                          "3. 点击【开始生成】")
                        break
        except Exception as e:
            print(f"跳转失败: {e}")
    
    def _refresh_gallery(self):
        """刷新人物图片库"""
        # 清空容器
        for widget in self.gallery_container.winfo_children():
            widget.destroy()
        
        char_name = self.character_var.get()
        if not char_name:
            ttk.Label(self.gallery_container, text="请先选择一个人物", 
                     foreground="#888888").pack(pady=50)
            return
        
        # 获取当前项目路径
        if hasattr(self.parent, 'current_project') and self.parent.current_project:
            from pathlib import Path
            char_dir = Path(self.parent.current_project.project_dir) / "characters"
        elif hasattr(self.parent, 'current_project_path') and self.parent.current_project_path:
            from pathlib import Path
            char_dir = Path(self.parent.current_project_path) / "characters"
        else:
            ttk.Label(self.gallery_container, text="未找到项目目录", 
                     foreground="#888888").pack(pady=50)
            return
        
        if not char_dir.exists():
            ttk.Label(self.gallery_container, text=f"{char_name} 还没有生成照片\n\n请前往图片管理页面生成", 
                     foreground="#888888").pack(pady=50)
            return
        
        # 查找该人物的所有图片
        import re
        clean_name = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', char_name)
        char_images = list(char_dir.glob(f"{clean_name}*.png"))
        
        if not char_images:
            ttk.Label(self.gallery_container, text=f"{char_name} 还没有生成照片\n\n请前往图片管理页面生成", 
                     foreground="#888888").pack(pady=50)
            return
        
        # 显示照片数量
        info_label = ttk.Label(self.gallery_container, text=f"共 {len(char_images)} 张照片", 
                              font=("", 10, "bold"))
        info_label.pack(pady=(0, 10))
        
        # 加载和显示图片（网格布局）
        from PIL import Image, ImageTk
        col_count = 3
        for idx, img_path in enumerate(sorted(char_images)):
            row = idx // col_count
            col = idx % col_count
            
            # 创建图片卡片
            card = ttk.Frame(self.gallery_container)
            card.grid(row=row+1, column=col, padx=10, pady=10, sticky="nsew")
            
            try:
                # 加载图片
                img = Image.open(img_path)
                # 缩略图
                img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                # 图片标签
                img_label = tk.Label(card, image=photo, bg="#1e1e1e")
                img_label.image = photo  # 保持引用
                img_label.pack(padx=5, pady=5)
                
                # 文件名标签
                filename = img_path.stem
                ttk.Label(card, text=filename, font=("", 8)).pack(pady=(0, 5))
                
            except Exception as e:
                ttk.Label(card, text=f"加载失败:\n{img_path.name}").pack(pady=20)
        
        # 配置列权重
        for i in range(col_count):
            self.gallery_container.columnconfigure(i, weight=1)
    
    def _load_current_portrait(self):
        """加载当前人物的形象（已弃用，保留兼容性）"""
        char_name = self.character_var.get()
        if not char_name:
            return
        
        char_data = self.consistency_data.get("characters", {}).get(char_name, {})
        portrait_path = char_data.get("portrait_image")
        
        if portrait_path and os.path.exists(portrait_path):
            try:
                from PIL import Image, ImageTk
                img = Image.open(portrait_path)
                img.thumbnail((200, 200))
                photo = ImageTk.PhotoImage(img)
                
                self.current_portrait_label.configure(image=photo, text="")
                self.current_portrait_label.image = photo  # 保持引用
                
            except Exception as e:
                print(f"加载人物形象失败：{str(e)}")
                self.current_portrait_label.configure(text=f"形象: {os.path.basename(portrait_path)}")
        else:
            self.current_portrait_label.configure(text="尚未选择人物形象")
    
    def _on_generate_portraits(self):
        """生成人物照片"""
        char_name = self.character_var.get()
        if not char_name:
            messagebox.showwarning("提示", "请先选择一个人物")
            return
        
        # 检查是否有SD API配置
        if not hasattr(self.parent, 'sd_api_url') or not self.parent.sd_api_url.get():
            messagebox.showwarning(
                "提示",
                "请先在导演页面配置Stable Diffusion API！\n\n"
                "配置路径：导演页面 → 步骤4：生成图片 → SD API配置"
            )
            return
        
        # 保存当前数据以确保使用最新信息
        self._save_current_character_data()
        
        # 获取人物数据
        char_data = self.consistency_data.get("characters", {}).get(char_name, {})
        
        # 显示进度窗口
        progress_window = tk.Toplevel(self)
        progress_window.title("生成人物照片中...")
        progress_window.geometry("400x150")
        progress_window.transient(self)
        progress_window.grab_set()
        
        # 居中
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() - 400) // 2
        y = (progress_window.winfo_screenheight() - 150) // 2
        progress_window.geometry(f"400x150+{x}+{y}")
        
        progress_label = tk.Label(
            progress_window,
            text=f"正在生成 {char_name} 的照片...\n请稍候..."
        )
        progress_label.pack(pady=30)
        
        progress_bar = ttk.Progressbar(progress_window, length=300, mode='indeterminate')
        progress_bar.pack(pady=20)
        progress_bar.start(10)
        
        def generate():
            try:
                # 调用SD生成图片
                from src.clients.sd_client import StableDiffusionClient
                
                client = StableDiffusionClient(self.parent.sd_api_url.get())
                
                # 获取生成类型
                gen_type = self.portrait_type_var.get()
                
                # 生成多张图片
                generated_images = []
                image_labels = []  # 存储每张图片的标签（表情名/角度名）
                
                if gen_type == "expressions":
                    # 表情库生成（7种表情）
                    expressions = {
                        "happy": "开心",
                        "sad": "难过", 
                        "angry": "愤怒",
                        "surprised": "惊讶",
                        "fear": "害怕",
                        "neutral": "中性",
                        "smile": "微笑"
                    }
                    
                    total = len(expressions)
                    for idx, (emotion_en, emotion_cn) in enumerate(expressions.items()):
                        self.after(0, lambda idx=idx, e=emotion_cn, t=total: progress_label.config(
                            text=f"正在生成【{e}】表情... ({idx+1}/{t})"
                        ))
                        
                        # 构建带表情的提示词
                        prompt = self._build_portrait_prompt(char_name, char_data, emotion=emotion_en)
                        negative_prompt = self._build_portrait_negative_prompt()
                        
                        seed = abs(hash(char_name + emotion_en)) % 1000000
                        
                        images = client.txt2img(
                            prompt=prompt,
                            negative_prompt=negative_prompt,
                            width=512,
                            height=768,
                            steps=30,
                            cfg_scale=7.5,
                            sampler_name="DPM++ 2M Karras",
                            seed=seed
                        )
                        
                        if images:
                            generated_images.append(images[0])
                            image_labels.append(emotion_cn)
                
                elif gen_type == "angles":
                    # 角度库生成（3种角度）
                    angles = {
                        "front": "正面",
                        "side": "侧面",
                        "back": "背面"
                    }
                    
                    total = len(angles)
                    for idx, (angle_en, angle_cn) in enumerate(angles.items()):
                        self.after(0, lambda idx=idx, a=angle_cn, t=total: progress_label.config(
                            text=f"正在生成【{a}】视角... ({idx+1}/{t})"
                        ))
                        
                        # 构建带角度的提示词
                        prompt = self._build_portrait_prompt(char_name, char_data, angle=angle_en)
                        negative_prompt = self._build_portrait_negative_prompt()
                        
                        seed = abs(hash(char_name + angle_en)) % 1000000
                        
                        images = client.txt2img(
                            prompt=prompt,
                            negative_prompt=negative_prompt,
                            width=512,
                            height=768,
                            steps=30,
                            cfg_scale=7.5,
                            sampler_name="DPM++ 2M Karras",
                            seed=seed
                        )
                        
                        if images:
                            generated_images.append(images[0])
                            image_labels.append(angle_cn)
                
                else:
                    # 标准形象生成（原有逻辑）
                    count = self.portrait_count_var.get()
                    prompt = self._build_portrait_prompt(char_name, char_data)
                    negative_prompt = self._build_portrait_negative_prompt()
                    
                    for i in range(count):
                        self.after(0, lambda i=i, c=count: progress_label.config(
                            text=f"正在生成第 {i+1}/{c} 张照片..."
                        ))
                        
                        seed = abs(hash(char_name + str(i))) % 1000000
                        
                        images = client.txt2img(
                            prompt=prompt,
                            negative_prompt=negative_prompt,
                            width=512,
                            height=768,
                            steps=30,
                            cfg_scale=7.5,
                            sampler_name="DPM++ 2M Karras",
                            seed=seed
                        )
                        
                        if images:
                            generated_images.append(images[0])
                            image_labels.append(f"变体{i+1}")
                
                if not generated_images:
                    raise Exception("未能生成任何图片")
                
                # 保存图片
                import os
                from datetime import datetime
                
                # 创建保存目录
                if hasattr(self.parent, 'current_project_path') and self.parent.current_project_path:
                    save_dir = os.path.join(self.parent.current_project_path, "characters", "portraits")
                else:
                    save_dir = os.path.join("projects", "temp", "portraits")
                
                os.makedirs(save_dir, exist_ok=True)
                
                # 保存所有图片
                saved_paths = []
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                for i, img_data in enumerate(generated_images):
                    filename = f"{char_name}_portrait_{timestamp}_{i+1}.png"
                    filepath = os.path.join(save_dir, filename)
                    
                    with open(filepath, 'wb') as f:
                        f.write(img_data)
                    
                    saved_paths.append(filepath)
                
                # 在UI中显示
                self.after(0, lambda: self._display_generated_portraits(saved_paths))
                self.after(0, lambda: progress_window.destroy())
                self.after(0, lambda: messagebox.showinfo(
                    "成功",
                    f"已生成 {len(saved_paths)} 张照片！\n请点击选择一张作为标准形象。"
                ))
                
            except Exception as e:
                self.after(0, lambda: progress_window.destroy())
                self.after(0, lambda: messagebox.showerror("错误", f"生成失败：{str(e)}"))
        
        # 在后台线程执行
        import threading
        threading.Thread(target=generate, daemon=True).start()
    
    def _build_portrait_prompt(self, char_name: str, char_data: Dict) -> str:
        """构建人物肖像提示词"""
        prompt_parts = []
        
        # 基础质量标签
        quality_tags = [
            "masterpiece", "best quality", "ultra detailed", "8k",
            "professional photography", "portrait", "clear face",
            "high quality portrait", "sharp focus", "detailed face",
            "photorealistic"
        ]
        
        # 根据风格添加标签
        style = self.portrait_style_var.get()
        if style == "写实肖像":
            quality_tags.extend(["realistic portrait", "professional headshot", "studio lighting"])
        elif style == "证件照":
            quality_tags.extend(["ID photo", "passport photo", "neutral background", "front view"])
        elif style == "半身照":
            quality_tags.extend(["half body portrait", "waist up"])
        elif style == "全身照":
            quality_tags.extend(["full body portrait", "standing pose"])
        elif style == "特写":
            quality_tags.extend(["close-up portrait", "face focus", "detailed facial features"])
        elif style == "动漫风格":
            quality_tags = ["anime style", "illustration", "high quality anime portrait"]
        
        # 基本信息
        basic_info = char_data.get("basic_info", {})
        age = basic_info.get("age", "")
        gender = basic_info.get("gender", "")
        
        if age:
            prompt_parts.append(f"{age} years old" if age.isdigit() else age)
        if gender:
            gender_en = "male" if gender == "男" else "female" if gender == "女" else "person"
            prompt_parts.append(gender_en)
        
        # 外观特征
        appearance = char_data.get("appearance", {})
        face = appearance.get("face", {})
        hair = appearance.get("hair", {})
        
        # 面部特征
        if face.get("skin_tone"):
            skin_map = {"白皙": "fair skin", "自然": "natural skin", "小麦色": "tan skin"}
            prompt_parts.append(skin_map.get(face["skin_tone"], "natural skin"))
        
        if face.get("eyes"):
            prompt_parts.append(face["eyes"])
        
        # 发型 - 详细描述
        hair_desc = []
        if hair.get("color"):
            color_map = {"黑色": "black", "棕色": "brown", "金色": "blonde", "红色": "red"}
            hair_desc.append(color_map.get(hair["color"], hair["color"]))
        
        if hair.get("length"):
            length_map = {"短发": "short", "中长发": "medium length", "长发": "long"}
            hair_desc.append(length_map.get(hair["length"], hair["length"]))
        
        if hair.get("style"):
            style_map = {"直发": "straight", "卷发": "curly", "波浪": "wavy"}
            hair_desc.append(style_map.get(hair["style"], hair["style"]))
        
        if hair_desc:
            prompt_parts.append(" ".join(hair_desc) + " hair")
        
        # 服装
        outfits = char_data.get("outfits", {})
        default_outfit = outfits.get("default", {})
        
        if default_outfit.get("top"):
            prompt_parts.append(f"wearing {default_outfit['top']}")
        
        if default_outfit.get("accessories"):
            prompt_parts.append(default_outfit["accessories"])
        
        # 组合提示词
        final_prompt = ", ".join(quality_tags)
        if prompt_parts:
            final_prompt += ", " + ", ".join(prompt_parts)
        
        # 添加一致性关键词
        final_prompt += ", character reference, consistent character design, same person"
        
        return final_prompt
    
    def _build_portrait_negative_prompt(self) -> str:
        """构建负面提示词"""
        negative_tags = [
            "low quality", "worst quality", "blurry", "out of focus",
            "multiple people", "crowd", "duplicate", "multiple heads",
            "deformed", "disfigured", "bad anatomy", "bad proportions",
            "extra limbs", "extra arms", "extra legs",
            "ugly", "distorted face", "asymmetric face",
            "watermark", "signature", "text", "logo",
            "mutation", "mutated", "malformed",
            "bad hands", "missing fingers", "extra fingers",
            "cropped", "cut off"
        ]
        
        return ", ".join(negative_tags)
    
    def _display_generated_portraits(self, image_paths: list):
        """显示生成的照片"""
        # 清空现有显示
        for widget in self.portraits_container.winfo_children():
            widget.destroy()
        
        self.generated_portraits = image_paths
        
        # 以网格形式显示
        from PIL import Image, ImageTk
        
        cols = 3
        for i, img_path in enumerate(image_paths):
            row = i // cols
            col = i % cols
            
            try:
                # 加载图片
                img = Image.open(img_path)
                img.thumbnail((180, 270))  # 肖像比例缩略图
                photo = ImageTk.PhotoImage(img)
                
                # 创建框架
                frame = ttk.Frame(self.portraits_container, relief="solid", borderwidth=2)
                frame.grid(row=row, column=col, padx=5, pady=5)
                
                # 显示图片
                label = ttk.Label(frame, image=photo, cursor="hand2")
                label.image = photo  # 保持引用
                label.pack(padx=5, pady=5)
                
                # 文件名
                filename = os.path.basename(img_path)
                ttk.Label(frame, text=filename[:20], font=("Arial", 8)).pack()
                
                # 选择按钮
                ttk.Button(
                    frame,
                    text="✅ 选择此形象",
                    command=lambda path=img_path: self._on_select_portrait(path)
                ).pack(pady=5)
                
                # 点击图片也可以选择
                label.bind("<Button-1>", lambda e, path=img_path: self._on_select_portrait(path))
                
            except Exception as e:
                print(f"显示图片失败 {img_path}: {str(e)}")
    
    def _on_select_portrait(self, image_path: str):
        """选择人物形象"""
        char_name = self.character_var.get()
        if not char_name:
            return
        
        # 保存到一致性数据
        if char_name not in self.consistency_data.get("characters", {}):
            self.consistency_data.setdefault("characters", {})[char_name] = {}
        
        self.consistency_data["characters"][char_name]["portrait_image"] = image_path
        
        # 更新显示
        self._load_current_portrait()
        
        messagebox.showinfo("成功", f"已设置 {char_name} 的标准形象！\n后续分镜生成将以此为参考。")
    
    def _on_import_portrait(self):
        """从文件导入人物形象"""
        char_name = self.character_var.get()
        if not char_name:
            messagebox.showwarning("提示", "请先选择一个人物")
            return
        
        from tkinter import filedialog
        
        filename = filedialog.askopenfilename(
            title="选择人物照片",
            filetypes=[
                ("图片文件", "*.png *.jpg *.jpeg *.webp"),
                ("所有文件", "*.*")
            ]
        )
        
        if filename:
            self._on_select_portrait(filename)
    
    def _on_view_current_portrait(self):
        """查看当前人物形象大图"""
        char_name = self.character_var.get()
        if not char_name:
            return
        
        char_data = self.consistency_data.get("characters", {}).get(char_name, {})
        portrait_path = char_data.get("portrait_image")
        
        if not portrait_path or not os.path.exists(portrait_path):
            messagebox.showinfo("提示", "尚未选择人物形象")
            return
        
        # 创建查看窗口
        view_window = tk.Toplevel(self)
        view_window.title(f"{char_name} - 人物形象")
        view_window.geometry("600x800")
        
        try:
            from PIL import Image, ImageTk
            img = Image.open(portrait_path)
            img.thumbnail((580, 780))
            photo = ImageTk.PhotoImage(img)
            
            label = ttk.Label(view_window, image=photo)
            label.image = photo
            label.pack(padx=10, pady=10)
            
        except Exception as e:
            messagebox.showerror("错误", f"无法加载图片：{str(e)}")
            view_window.destroy()
    
    def _on_clear_portrait(self):
        """清除人物形象选择"""
        char_name = self.character_var.get()
        if not char_name:
            return
        
        if messagebox.askyesno("确认", f"确定要清除 {char_name} 的形象设定吗？"):
            char_data = self.consistency_data.get("characters", {}).get(char_name, {})
            if "portrait_image" in char_data:
                del char_data["portrait_image"]
            
            self._load_current_portrait()
