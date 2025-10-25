"""
人物详情编辑对话框 - 用于图片管理页面的详细人物设定
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
from typing import Dict, Optional

class CharacterDetailDialog(tk.Toplevel):
    """人物详情编辑对话框"""
    
    def __init__(self, parent, character_data: Dict = None, character_name: str = ""):
        super().__init__(parent)
        
        self.parent = parent
        self.character_name = character_name
        self.character_data = character_data or {}
        self.result = None
        
        # 窗口设置
        self.title(f"✏️ 编辑人物详情 - {character_name}")
        self.geometry("850x750")
        self.resizable(True, True)
        
        # 居中显示
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 850) // 2
        y = (self.winfo_screenheight() - 750) // 2
        self.geometry(f"850x750+{x}+{y}")
        
        # 设置窗口为模态
        self.transient(parent)
        self.grab_set()
        
        # 初始化界面
        self._init_ui()
        
        # 加载数据
        self._load_data()
        
        # 绑定关闭事件
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
    def _init_ui(self):
        """初始化界面"""
        # 主容器
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(title_frame, text=f"👤 {self.character_name}", 
                 font=("", 14, "bold")).pack(side=tk.LEFT)
        ttk.Label(title_frame, text="完善人物信息，以获得更好的图片生成效果", 
                 font=("", 9), foreground="#888").pack(side=tk.LEFT, padx=(15, 0))
        
        # 创建Notebook
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # 基本信息页
        self.basic_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.basic_frame, text="📝 基本信息")
        self._create_basic_tab()
        
        # 外观设定页
        self.appearance_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.appearance_frame, text="👤 外观特征")
        self._create_appearance_tab()
        
        # 服装设定页
        self.outfit_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.outfit_frame, text="👔 服装造型")
        self._create_outfit_tab()
        
        # 表情动作页
        self.expression_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.expression_frame, text="😊 表情动作")
        self._create_expression_tab()
        
        # 底部按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="💾 保存", command=self._on_save, 
                  style="Accent.TButton", width=15).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="❌ 取消", command=self._on_cancel, 
                  width=15).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="🤖 智能填写", command=self._on_smart_fill, 
                  width=15).pack(side=tk.LEFT)
        
    def _create_basic_tab(self):
        """创建基本信息标签页"""
        frame = ttk.Frame(self.basic_frame)
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # 基本信息
        info_group = ttk.LabelFrame(frame, text="基本信息", padding="10")
        info_group.pack(fill=tk.X, pady=(0, 10))
        
        # 姓名
        ttk.Label(info_group, text="姓名：").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar(value=self.character_name)
        ttk.Entry(info_group, textvariable=self.name_var, width=30, state="readonly").grid(
            row=0, column=1, sticky=tk.W, pady=5)
        
        # 年龄
        ttk.Label(info_group, text="年龄：").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.age_var = tk.StringVar()
        ttk.Entry(info_group, textvariable=self.age_var, width=30).grid(
            row=1, column=1, sticky=tk.W, pady=5)
        
        # 性别
        ttk.Label(info_group, text="性别：").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.gender_var = tk.StringVar()
        gender_frame = ttk.Frame(info_group)
        gender_frame.grid(row=2, column=1, sticky=tk.W, pady=5)
        ttk.Radiobutton(gender_frame, text="男", variable=self.gender_var, value="男").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(gender_frame, text="女", variable=self.gender_var, value="女").pack(side=tk.LEFT)
        
        # 角色定位
        ttk.Label(info_group, text="角色定位：").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.role_var = tk.StringVar()
        ttk.Combobox(info_group, textvariable=self.role_var, width=27,
                    values=["主角", "配角", "龙套", "反派", "导师", "好友", "亲人"]).grid(
            row=3, column=1, sticky=tk.W, pady=5)
        
        # 人物描述
        desc_group = ttk.LabelFrame(frame, text="人物描述", padding="10")
        desc_group.pack(fill=tk.BOTH, expand=True)
        
        self.description_text = scrolledtext.ScrolledText(desc_group, height=10, wrap=tk.WORD)
        self.description_text.pack(fill=tk.BOTH, expand=True)
        
    def _create_appearance_tab(self):
        """创建外观特征标签页"""
        frame = ttk.Frame(self.appearance_frame)
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # 创建滚动区域
        canvas = tk.Canvas(frame, bg="#2b2b2b")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 面部特征
        face_group = ttk.LabelFrame(scrollable_frame, text="👱 面部特征", padding="10")
        face_group.pack(fill=tk.X, pady=(0, 10))
        
        # 脸型
        ttk.Label(face_group, text="脸型：").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.face_shape_var = tk.StringVar()
        ttk.Combobox(face_group, textvariable=self.face_shape_var, width=25,
                    values=["瓜子脸", "圆脸", "方脸", "长脸", "鹅蛋脸", "菱形脸"]).grid(
            row=0, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        
        # 肤色
        ttk.Label(face_group, text="肤色：").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.skin_tone_var = tk.StringVar()
        ttk.Combobox(face_group, textvariable=self.skin_tone_var, width=25,
                    values=["白皙", "偏白", "自然", "小麦色", "偏黑", "深色"]).grid(
            row=1, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        
        # 眼睛
        ttk.Label(face_group, text="眼睛：").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.eyes_var = tk.StringVar()
        ttk.Entry(face_group, textvariable=self.eyes_var, width=27).grid(
            row=2, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        ttk.Label(face_group, text="例如：大眼睛、双眼皮", foreground="#888", font=("", 8)).grid(
            row=2, column=2, sticky=tk.W, pady=5, padx=(5, 0))
        
        # 鼻子
        ttk.Label(face_group, text="鼻子：").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.nose_var = tk.StringVar()
        ttk.Entry(face_group, textvariable=self.nose_var, width=27).grid(
            row=3, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        
        # 嘴巴
        ttk.Label(face_group, text="嘴巴：").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.mouth_var = tk.StringVar()
        ttk.Entry(face_group, textvariable=self.mouth_var, width=27).grid(
            row=4, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        
        # 发型特征
        hair_group = ttk.LabelFrame(scrollable_frame, text="💇 发型特征", padding="10")
        hair_group.pack(fill=tk.X, pady=(0, 10))
        
        # 发型
        ttk.Label(hair_group, text="发型：").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.hairstyle_var = tk.StringVar()
        ttk.Combobox(hair_group, textvariable=self.hairstyle_var, width=25,
                    values=["长发", "短发", "中长发", "披肩发", "马尾", "丸子头", "波波头", "寸头"]).grid(
            row=0, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        
        # 发色
        ttk.Label(hair_group, text="发色：").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.hair_color_var = tk.StringVar()
        ttk.Combobox(hair_group, textvariable=self.hair_color_var, width=25,
                    values=["黑色", "棕色", "金色", "银色", "红色", "蓝色", "渐变色"]).grid(
            row=1, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        
        # 体型特征
        body_group = ttk.LabelFrame(scrollable_frame, text="🏃 体型特征", padding="10")
        body_group.pack(fill=tk.X, pady=(0, 10))
        
        # 身高
        ttk.Label(body_group, text="身高：").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.height_var = tk.StringVar()
        ttk.Combobox(body_group, textvariable=self.height_var, width=25,
                    values=["矮小", "中等偏矮", "中等", "中等偏高", "高挑", "很高"]).grid(
            row=0, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        
        # 体型
        ttk.Label(body_group, text="体型：").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.build_var = tk.StringVar()
        ttk.Combobox(body_group, textvariable=self.build_var, width=25,
                    values=["纤瘦", "苗条", "标准", "健壮", "强壮", "魁梧", "丰满"]).grid(
            row=1, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        
        # 特殊标记
        special_group = ttk.LabelFrame(scrollable_frame, text="✨ 特殊标记", padding="10")
        special_group.pack(fill=tk.X, pady=(0, 10))
        
        self.special_marks_text = scrolledtext.ScrolledText(special_group, height=4, wrap=tk.WORD)
        self.special_marks_text.pack(fill=tk.BOTH, expand=True)
        ttk.Label(special_group, text="例如：眼镜、疤痕、纹身、胎记等", 
                 foreground="#888", font=("", 8)).pack(anchor=tk.W, pady=(5, 0))
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 鼠标滚轮支持
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
    def _create_outfit_tab(self):
        """创建服装造型标签页"""
        frame = ttk.Frame(self.outfit_frame)
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # 默认服装
        default_group = ttk.LabelFrame(frame, text="👔 默认服装", padding="10")
        default_group.pack(fill=tk.X, pady=(0, 10))
        
        # 服装风格
        ttk.Label(default_group, text="风格：").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.outfit_style_var = tk.StringVar()
        ttk.Combobox(default_group, textvariable=self.outfit_style_var, width=25,
                    values=["休闲", "正式", "运动", "古装", "现代", "职业装", "学生装"]).grid(
            row=0, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        
        # 主要颜色
        ttk.Label(default_group, text="主色调：").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.outfit_color_var = tk.StringVar()
        ttk.Entry(default_group, textvariable=self.outfit_color_var, width=27).grid(
            row=1, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        
        # 详细描述
        ttk.Label(default_group, text="详细描述：").grid(row=2, column=0, sticky=tk.NW, pady=5)
        self.outfit_desc_text = scrolledtext.ScrolledText(default_group, height=6, wrap=tk.WORD)
        self.outfit_desc_text.grid(row=2, column=1, columnspan=2, sticky=tk.EW, pady=5, padx=(5, 0))
        
        # 配饰
        accessories_group = ttk.LabelFrame(frame, text="💍 配饰", padding="10")
        accessories_group.pack(fill=tk.BOTH, expand=True)
        
        self.accessories_text = scrolledtext.ScrolledText(accessories_group, height=6, wrap=tk.WORD)
        self.accessories_text.pack(fill=tk.BOTH, expand=True)
        ttk.Label(accessories_group, text="例如：项链、耳环、手表、帽子、围巾等", 
                 foreground="#888", font=("", 8)).pack(anchor=tk.W, pady=(5, 0))
        
    def _create_expression_tab(self):
        """创建表情动作标签页"""
        frame = ttk.Frame(self.expression_frame)
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # 默认表情
        expr_group = ttk.LabelFrame(frame, text="😊 默认表情", padding="10")
        expr_group.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(expr_group, text="选择默认表情：").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.default_expression_var = tk.StringVar(value="中性")
        expr_combo = ttk.Combobox(expr_group, textvariable=self.default_expression_var, width=25,
                                 values=["中性", "微笑", "开心", "难过", "愤怒", "惊讶", "害怕"],
                                 state="readonly")
        expr_combo.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        
        # 常用动作
        action_group = ttk.LabelFrame(frame, text="🎭 常用动作/姿态", padding="10")
        action_group.pack(fill=tk.BOTH, expand=True)
        
        self.actions_text = scrolledtext.ScrolledText(action_group, height=10, wrap=tk.WORD)
        self.actions_text.pack(fill=tk.BOTH, expand=True)
        ttk.Label(action_group, text="例如：双手插兜、托腮思考、挥手打招呼等", 
                 foreground="#888", font=("", 8)).pack(anchor=tk.W, pady=(5, 0))
        
    def _load_data(self):
        """加载人物数据"""
        if not self.character_data:
            return
        
        # 基本信息
        self.age_var.set(self.character_data.get("age", ""))
        self.gender_var.set(self.character_data.get("gender", ""))
        self.role_var.set(self.character_data.get("role", ""))
        self.description_text.delete("1.0", tk.END)
        self.description_text.insert("1.0", self.character_data.get("description", ""))
        
        # 外观特征
        appearance = self.character_data.get("appearance", {})
        face = appearance.get("face", {})
        self.face_shape_var.set(face.get("shape", ""))
        self.skin_tone_var.set(face.get("skin_tone", ""))
        self.eyes_var.set(face.get("eyes", ""))
        self.nose_var.set(face.get("nose", ""))
        self.mouth_var.set(face.get("mouth", ""))
        
        hair = appearance.get("hair", {})
        self.hairstyle_var.set(hair.get("style", ""))
        self.hair_color_var.set(hair.get("color", ""))
        
        body = appearance.get("body", {})
        self.height_var.set(body.get("height", ""))
        self.build_var.set(body.get("build", ""))
        
        self.special_marks_text.delete("1.0", tk.END)
        self.special_marks_text.insert("1.0", appearance.get("special_marks", ""))
        
        # 服装
        outfit = self.character_data.get("outfit", {})
        self.outfit_style_var.set(outfit.get("style", ""))
        self.outfit_color_var.set(outfit.get("color", ""))
        self.outfit_desc_text.delete("1.0", tk.END)
        self.outfit_desc_text.insert("1.0", outfit.get("description", ""))
        self.accessories_text.delete("1.0", tk.END)
        self.accessories_text.insert("1.0", outfit.get("accessories", ""))
        
        # 表情动作
        expressions = self.character_data.get("expressions", {})
        self.default_expression_var.set(expressions.get("default", "中性"))
        self.actions_text.delete("1.0", tk.END)
        self.actions_text.insert("1.0", self.character_data.get("actions", {}).get("common", ""))
        
    def _save_data(self) -> Dict:
        """保存人物数据"""
        data = {
            "name": self.character_name,
            "age": self.age_var.get(),
            "gender": self.gender_var.get(),
            "role": self.role_var.get(),
            "description": self.description_text.get("1.0", tk.END).strip(),
            "appearance": {
                "face": {
                    "shape": self.face_shape_var.get(),
                    "skin_tone": self.skin_tone_var.get(),
                    "eyes": self.eyes_var.get(),
                    "nose": self.nose_var.get(),
                    "mouth": self.mouth_var.get()
                },
                "hair": {
                    "style": self.hairstyle_var.get(),
                    "color": self.hair_color_var.get()
                },
                "body": {
                    "height": self.height_var.get(),
                    "build": self.build_var.get()
                },
                "special_marks": self.special_marks_text.get("1.0", tk.END).strip()
            },
            "outfit": {
                "style": self.outfit_style_var.get(),
                "color": self.outfit_color_var.get(),
                "description": self.outfit_desc_text.get("1.0", tk.END).strip(),
                "accessories": self.accessories_text.get("1.0", tk.END).strip()
            },
            "expressions": {
                "default": self.default_expression_var.get()
            },
            "actions": {
                "common": self.actions_text.get("1.0", tk.END).strip()
            }
        }
        return data
        
    def _on_save(self):
        """保存并关闭"""
        self.result = self._save_data()
        self.destroy()
        
    def _on_cancel(self):
        """取消并关闭"""
        self.result = None
        self.destroy()
        
    def show(self) -> Optional[Dict]:
        """显示对话框并返回结果"""
        self.wait_window()
        return self.result
    
    def _on_smart_fill(self):
        """智能填写 - 根据故事内容自动分析人物特征"""
        # 获取故事内容
        story_content = ""
        
        # 尝试从父窗口获取故事内容
        if hasattr(self.parent, 'output'):
            story_content = self.parent.output.get("1.0", tk.END).strip()
        elif hasattr(self.parent, 'story_text'):
            story_content = self.parent.story_text.get("1.0", tk.END).strip()
        
        if not story_content or len(story_content) < 50:
            messagebox.showwarning("提示", "未找到故事内容，请先在故事生成页面创建故事")
            return
        
        # 显示进度窗口
        progress_window = tk.Toplevel(self)
        progress_window.title("智能分析中...")
        progress_window.geometry("400x150")
        progress_window.transient(self)
        progress_window.grab_set()
        
        # 居中显示
        x = (progress_window.winfo_screenwidth() - 400) // 2
        y = (progress_window.winfo_screenheight() - 150) // 2
        progress_window.geometry(f"400x150+{x}+{y}")
        
        progress_label = tk.Label(progress_window, text=f"正在分析 {self.character_name} 的特征...", 
                                 font=("", 10))
        progress_label.pack(pady=30)
        
        progress_bar = ttk.Progressbar(progress_window, length=300, mode='indeterminate')
        progress_bar.pack(pady=20)
        progress_bar.start(10)
        
        def analyze():
            try:
                # 使用AI分析人物特征
                character_info = self._analyze_character_from_story(
                    self.character_name, 
                    story_content
                )
                
                # 更新UI
                self.after(0, lambda: self._apply_analyzed_info(character_info))
                self.after(0, lambda: progress_bar.stop())
                self.after(0, lambda: progress_window.destroy())
                self.after(0, lambda: messagebox.showinfo("成功", 
                    f"已智能填写 {self.character_name} 的基本信息！\n\n请检查并调整生成的内容。"))
                
            except Exception as e:
                self.after(0, lambda: progress_bar.stop())
                self.after(0, lambda: progress_window.destroy())
                self.after(0, lambda: messagebox.showerror("错误", 
                    f"分析失败：{str(e)}\n\n请确保已在故事生成页面配置API"))
                import traceback
                traceback.print_exc()
        
        # 在后台线程执行
        import threading
        threading.Thread(target=analyze, daemon=True).start()
    
    def _analyze_character_from_story(self, character_name: str, content: str) -> Dict:
        """使用AI分析故事中的人物特征"""
        # 检查是否有API配置
        if not hasattr(self.parent, 'api_key') or not self.parent.api_key.get():
            raise Exception("请先在故事生成页面配置API")
        
        from src.clients.deepseek_client import DeepSeekClient
        
        client = DeepSeekClient(
            api_key=self.parent.api_key.get(),
            base_url=self.parent.base_url.get(),
            model=self.parent.model.get()
        )
        
        # 构建分析提示词
        prompt = f"""
请作为专业的人物特征分析师，仔细分析以下故事中关于【{character_name}】的所有外貌和特征描述。

## 分析要求
1. 逐字逐句搜索关于【{character_name}】的描述
2. 特别关注：外貌、穿着、发型、表情、动作等细节
3. 如果故事中未明确提及某项，推测合理的默认值
4. 必须输出完整的JSON格式

## 需要提取的详细信息

### 基本信息
- age: 年龄（精确数字或范围）
- gender: 性别（"男"或"女"）
- occupation: 职业/身份
- personality: 性格特点

### 面部特征
- face_shape: 脸型
- skin_tone: 肤色
- eyes: 眼睛特征
- eyebrows: 眉毛
- nose: 鼻子
- mouth: 嘴唇
- special_marks: 特殊标记

### 发型特征
- hair_color: 发色
- hair_length: 发长
- hair_style: 发型
- bangs: 刘海

### 身材体型
- height: 身高
- body_type: 体型
- body_features: 身体特征

### 服装风格
- default_outfit: 常穿服装
- outfit_description: 服装详细描述

### 其他特征
- accessories: 配饰
- typical_expression: 典型表情
- mannerisms: 行为习惯

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
        
        return character_data
    
    def _apply_analyzed_info(self, character_info: Dict):
        """将分析的信息应用到UI"""
        if not character_info:
            return
        
        # 基本信息
        if character_info.get("age"):
            self.age_var.set(character_info["age"])
        
        if character_info.get("gender"):
            self.gender_var.set(character_info["gender"])
        
        if character_info.get("occupation"):
            self.occupation_var.set(character_info["occupation"])
        
        if character_info.get("personality"):
            self.personality_text.delete("1.0", tk.END)
            self.personality_text.insert("1.0", character_info["personality"])
        
        # 外观特征
        if character_info.get("face_shape"):
            self.face_shape_var.set(character_info["face_shape"])
        
        if character_info.get("skin_tone"):
            self.skin_tone_var.set(character_info["skin_tone"])
        
        if character_info.get("eyes"):
            self.eyes_var.set(character_info["eyes"])
        
        if character_info.get("eyebrows"):
            self.eyebrows_var.set(character_info["eyebrows"])
        
        if character_info.get("nose"):
            self.nose_var.set(character_info["nose"])
        
        if character_info.get("mouth"):
            self.mouth_var.set(character_info["mouth"])
        
        # 发型
        if character_info.get("hair_color"):
            self.hair_color_var.set(character_info["hair_color"])
        
        if character_info.get("hair_length"):
            self.hair_length_var.set(character_info["hair_length"])
        
        if character_info.get("hair_style"):
            self.hair_style_var.set(character_info["hair_style"])
        
        if character_info.get("height"):
            self.height_var.set(character_info["height"])
        
        if character_info.get("body_type"):
            self.body_type_var.set(character_info["body_type"])
        
        # 服装
        if character_info.get("default_outfit"):
            self.outfit_style_var.set(character_info["default_outfit"])
        
        if character_info.get("outfit_description"):
            self.outfit_desc_text.delete("1.0", tk.END)
            self.outfit_desc_text.insert("1.0", character_info["outfit_description"])
        
        if character_info.get("accessories"):
            self.accessories_text.delete("1.0", tk.END)
            self.accessories_text.insert("1.0", character_info["accessories"])
        
        # 其他特征
        if character_info.get("typical_expression"):
            self.default_expression_var.set(character_info["typical_expression"])
        
        if character_info.get("mannerisms"):
            self.actions_text.delete("1.0", tk.END)
            self.actions_text.insert("1.0", character_info["mannerisms"])
        
        print(f"✅ 已应用智能分析结果到UI")


