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
        
        # 鼠标滚轮支持（只在canvas上绑定，避免窗口关闭后出错）
        def _on_mousewheel(event):
            try:
                # 检查canvas是否还存在
                if canvas.winfo_exists():
                    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except:
                pass
        
        # 只在canvas区域绑定，不使用bind_all
        canvas.bind("<MouseWheel>", _on_mousewheel)
        # 鼠标进入canvas时激活滚动
        canvas.bind("<Enter>", lambda e: canvas.focus_set())
        canvas.bind("<Leave>", lambda e: self.focus_set())
        
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
    
    def _try_parse_paragraph_format(self, description: str) -> bool:
        """尝试从段落格式的描述中提取关键信息"""
        try:
            print("🔍 从段落中提取关键信息...")
            filled_count = 0
            desc_lower = description.lower()
            
            # 提取年龄
            import re
            age_patterns = [
                r'约?(\d+)岁',
                r'(\d+)多岁',
                r'(\d+)岁左右',
            ]
            for pattern in age_patterns:
                match = re.search(pattern, description)
                if match:
                    age = match.group(1)
                    self.age_var.set(age)
                    print(f"✅ 年龄: {age}")
                    filled_count += 1
                    break
            
            # 提取性别
            if '女性' in description or '女人' in description or '女子' in description or '她' in description:
                self.gender_var.set('女')
                print(f"✅ 性别: 女")
                filled_count += 1
            elif '男性' in description or '男人' in description or '男子' in description or '他' in description:
                self.gender_var.set('男')
                print(f"✅ 性别: 男")
                filled_count += 1
            
            # 提取脸型
            face_shapes = ['鹅蛋脸', '瓜子脸', '圆脸', '方脸', '长脸', '菱形脸']
            for shape in face_shapes:
                if shape in description:
                    self.face_shape_var.set(shape)
                    print(f"✅ 脸型: {shape}")
                    filled_count += 1
                    break
            
            # 提取肤色
            skin_tones = ['白皙', '黝黑', '古铜', '健康', '苍白', '红润']
            for tone in skin_tones:
                if tone in description and '肤' in description:
                    self.skin_tone_var.set(tone)
                    print(f"✅ 肤色: {tone}")
                    filled_count += 1
                    break
            
            # 提取眼睛特征
            eye_features = ['大眼睛', '小眼睛', '细长眼睛', '丹凤眼', '杏眼', '圆眼']
            for feature in eye_features:
                if feature in description:
                    self.eyes_var.set(feature)
                    print(f"✅ 眼睛: {feature}")
                    filled_count += 1
                    break
            
            # 提取发色
            hair_colors = ['黑发', '黑色', '棕发', '棕色', '金发', '白发', '银发', '栗色']
            for color in hair_colors:
                if color in description and ('发' in description or '头发' in description):
                    self.hair_color_var.set(color.replace('发', ''))
                    print(f"✅ 发色: {color}")
                    filled_count += 1
                    break
            
            # 提取发长
            hair_lengths = ['长发', '短发', '中长发', '及肩', '齐肩', '披肩', '及腰']
            for length in hair_lengths:
                if length in description:
                    self.hair_length_var.set(length)
                    print(f"✅ 发长: {length}")
                    filled_count += 1
                    break
            
            # 提取体型
            body_types = ['苗条', '瘦弱', '纤细', '丰满', '健壮', '魁梧', '高大', '矮小']
            for body in body_types:
                if body in description:
                    self.body_type_var.set(body)
                    print(f"✅ 体型: {body}")
                    filled_count += 1
                    break
            
            # 提取身高
            height_match = re.search(r'(\d+)厘米|(\d+)cm', description)
            if height_match:
                height = height_match.group(1) or height_match.group(2)
                self.height_var.set(f"{height}cm")
                print(f"✅ 身高: {height}cm")
                filled_count += 1
            
            # 提取服装关键词
            outfits = ['T恤', 't恤', '衬衫', '连衣裙', '牛仔裤', '西装', '卫衣', '针织衫', '外套', '休闲裤']
            found_outfits = []
            for outfit in outfits:
                if outfit in description:
                    found_outfits.append(outfit)
            if found_outfits:
                outfit_desc = '、'.join(found_outfits[:3])  # 最多3个
                self.outfit_desc_text.delete("1.0", tk.END)
                self.outfit_desc_text.insert("1.0", outfit_desc)
                print(f"✅ 服装: {outfit_desc}")
                filled_count += 1
            
            print(f"✅ 从段落中提取了 {filled_count} 个字段")
            return filled_count > 0
            
        except Exception as e:
            print(f"❌ 段落解析失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _try_parse_list_format(self, description: str) -> bool:
        """尝试解析列表格式的描述并填充字段
        
        期望格式：
        性别：男
        年龄：10岁
        发型：短发，深棕色
        体型：瘦弱
        服装：蓝白卫衣，牛仔裤
        特征：圆脸，大眼睛
        """
        try:
            print("🔍 解析列表格式描述...")
            lines = description.strip().split('\n')
            parsed_data = {}
            
            for line in lines:
                line = line.strip()
                if '：' in line:
                    key, value = line.split('：', 1)
                    key = key.strip()
                    value = value.strip()
                    parsed_data[key] = value
                    print(f"  {key}: {value}")
            
            if not parsed_data:
                print("❌ 未解析到任何键值对")
                return False
            
            # 映射并填充字段
            filled_count = 0
            
            # 性别
            if '性别' in parsed_data:
                gender = parsed_data['性别']
                self.gender_var.set(gender)
                print(f"✅ 性别: {gender}")
                filled_count += 1
            
            # 年龄
            if '年龄' in parsed_data:
                age = parsed_data['年龄'].replace('岁', '').replace('约', '').strip()
                self.age_var.set(age)
                print(f"✅ 年龄: {age}")
                filled_count += 1
            
            # 发型（拆分为发长和发色）
            if '发型' in parsed_data:
                hair = parsed_data['发型']
                # 尝试拆分 "短发，深棕色"
                if '，' in hair or ',' in hair:
                    parts = hair.replace(',', '，').split('，')
                    if len(parts) >= 1:
                        self.hair_length_var.set(parts[0].strip())
                        print(f"✅ 发长: {parts[0].strip()}")
                        filled_count += 1
                    if len(parts) >= 2:
                        self.hair_color_var.set(parts[1].strip())
                        print(f"✅ 发色: {parts[1].strip()}")
                        filled_count += 1
                else:
                    self.hair_style_var.set(hair)
                    print(f"✅ 发型: {hair}")
                    filled_count += 1
            
            # 体型
            if '体型' in parsed_data:
                body = parsed_data['体型']
                self.body_type_var.set(body)
                print(f"✅ 体型: {body}")
                filled_count += 1
            
            # 服装
            if '服装' in parsed_data:
                outfit = parsed_data['服装']
                self.outfit_style_var.set(outfit)
                self.outfit_desc_text.delete("1.0", tk.END)
                self.outfit_desc_text.insert("1.0", outfit)
                print(f"✅ 服装: {outfit}")
                filled_count += 1
            
            # 特征（映射到脸型、眼睛等）
            if '特征' in parsed_data:
                features = parsed_data['特征']
                # 尝试拆分多个特征
                feature_list = features.replace('，', ',').split(',')
                for feature in feature_list:
                    feature = feature.strip()
                    if '脸' in feature:
                        self.face_shape_var.set(feature)
                        print(f"✅ 脸型: {feature}")
                        filled_count += 1
                    elif '眼' in feature:
                        self.eyes_var.set(feature)
                        print(f"✅ 眼睛: {feature}")
                        filled_count += 1
            
            print(f"✅ 成功从列表格式填充 {filled_count} 个字段")
            return filled_count > 0
            
        except Exception as e:
            print(f"❌ 解析列表格式失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _on_smart_fill(self):
        """智能填写 - 优先从人物描述解析，否则从故事分析"""
        print(f"\n{'='*60}")
        print(f"🤖 智能填写功能被触发 - 人物：{self.character_name}")
        print(f"{'='*60}")
        
        # 先检查是否有人物描述（列表格式）
        description_text = self.description_text.get("1.0", tk.END).strip()
        print(f"📋 当前人物描述长度: {len(description_text)} 字符")
        
        if description_text and len(description_text) > 20:
            # 尝试解析描述
            print("📝 检测到人物描述，尝试直接解析...")
            
            # 先尝试列表格式
            if self._try_parse_list_format(description_text):
                messagebox.showinfo("成功", f"已从列表格式描述中填写 {self.character_name} 的信息！")
                return
            
            # 再尝试段落格式（使用简单规则提取）
            print("📝 尝试从段落格式提取...")
            if self._try_parse_paragraph_format(description_text):
                messagebox.showinfo("成功", f"已从人物描述中提取并填写 {self.character_name} 的信息！")
                return
            
            print("⚠️ 描述格式无法识别，继续尝试从故事分析...")
        
        # 获取故事内容
        story_content = ""
        
        # 方法1：尝试从项目文件加载
        print("📂 尝试方法1：从项目文件加载")
        if hasattr(self.parent, 'current_project') and self.parent.current_project:
            try:
                story_file = self.parent.current_project.project_dir / "story.txt"
                if story_file.exists():
                    story_content = story_file.read_text(encoding='utf-8').strip()
                    print(f"✅ 从项目文件加载故事内容: {len(story_content)} 字符")
            except Exception as e:
                print(f"⚠️ 从项目文件加载失败: {e}")
        else:
            if not hasattr(self.parent, 'current_project'):
                print("⚠️ parent 没有 current_project 属性")
            elif not self.parent.current_project:
                print("⚠️ current_project 为 None")
        
        # 方法2：尝试从故事生成器的输出框获取
        print("📂 尝试方法2：从故事输出框获取")
        if not story_content and hasattr(self.parent, 'output'):
            try:
                story_content = self.parent.output.get("1.0", tk.END).strip()
                print(f"✅ 从故事输出框获取内容: {len(story_content)} 字符")
            except Exception as e:
                print(f"⚠️ 从输出框获取失败: {e}")
        else:
            print("⚠️ parent 没有 output 属性")
        
        # 方法3：尝试从其他可能的文本框获取
        print("📂 尝试方法3：从story_text获取")
        if not story_content and hasattr(self.parent, 'story_text'):
            try:
                story_content = self.parent.story_text.get("1.0", tk.END).strip()
                print(f"✅ 从story_text获取内容: {len(story_content)} 字符")
            except Exception as e:
                print(f"⚠️ 从story_text获取失败: {e}")
        else:
            print("⚠️ parent 没有 story_text 属性")
        
        print(f"\n📊 最终获取的故事内容长度: {len(story_content)} 字符")
        
        if not story_content or len(story_content) < 50:
            print(f"❌ 故事内容不足，无法继续")
            print(f"   - 内容长度: {len(story_content)}")
            print(f"   - 需要至少: 50 字符")
            messagebox.showwarning("提示", 
                "未找到故事内容！\n\n"
                "请确保：\n"
                "1. 已在故事生成页面创建故事\n"
                "2. 故事已保存到项目中")
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
                error_msg = str(e)
                self.after(0, lambda: progress_bar.stop())
                self.after(0, lambda: progress_window.destroy())
                self.after(0, lambda msg=error_msg: messagebox.showerror("错误", 
                    f"分析失败：{msg}\n\n"
                    f"请检查：\n"
                    f"1. 是否在【配置设置】页面配置了 DeepSeek API\n"
                    f"2. API Key 是否有效\n"
                    f"3. 网络连接是否正常"))
                import traceback
                traceback.print_exc()
        
        # 在后台线程执行
        import threading
        threading.Thread(target=analyze, daemon=True).start()
    
    def _analyze_character_from_story(self, character_name: str, content: str) -> Dict:
        """使用AI分析故事中的人物特征"""
        # 检查是否有API配置
        if not hasattr(self.parent, 'api_key') or not self.parent.api_key.get():
            raise Exception("请先在【配置设置】页面配置 DeepSeek API")
        
        print(f"🔍 开始分析人物【{character_name}】特征...")
        print(f"📝 故事内容长度: {len(content)} 字符")
        
        from src.clients.deepseek_client import DeepSeekClient
        
        # 获取API配置
        api_key = self.parent.api_key.get()
        base_url = self.parent.base_url.get() if hasattr(self.parent, 'base_url') and self.parent.base_url.get() else "https://api.deepseek.com/v1"
        model = self.parent.model.get() if hasattr(self.parent, 'model') and self.parent.model.get() else "deepseek-chat"
        
        print(f"🔗 使用模型: {model}")
        print(f"🔗 API地址: {base_url}")
        
        client = DeepSeekClient(
            api_key=api_key,
            base_url=base_url,
            model=model
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
        
        print(f"📤 正在调用AI分析...")
        response = client.chat([
            {"role": "system", "content": "你是专业的文学分析助手，擅长从文本中提取人物特征。你必须严格按照JSON格式输出。"},
            {"role": "user", "content": prompt}
        ], temperature=0.3)
        
        print(f"📥 AI响应长度: {len(response)} 字符")
        print(f"📥 AI响应内容预览: {response[:200]}...")
        
        # 解析JSON响应
        import json
        import re
        
        # 提取JSON部分
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            json_str = json_match.group()
            print(f"✅ 找到JSON数据，长度: {len(json_str)} 字符")
            character_data = json.loads(json_str)
            print(f"✅ 成功解析JSON，包含 {len(character_data)} 个字段")
            print(f"📊 解析的字段: {list(character_data.keys())}")
        else:
            print(f"⚠️ 未找到JSON格式的响应")
            # 如果没有找到JSON，创建默认结构
            character_data = {}
        
        return character_data
    
    def _apply_analyzed_info(self, character_info: Dict):
        """将分析的信息应用到UI"""
        if not character_info:
            print("⚠️ 没有人物信息可应用")
            return
        
        print(f"🎨 开始应用人物信息，包含 {len(character_info)} 个字段")
        applied_count = 0
        
        # 基本信息
        if character_info.get("age"):
            self.age_var.set(character_info["age"])
            print(f"✅ 年龄: {character_info['age']}")
            applied_count += 1
        
        if character_info.get("gender"):
            self.gender_var.set(character_info["gender"])
            print(f"✅ 性别: {character_info['gender']}")
            applied_count += 1
        
        # occupation 和 personality 字段检查是否存在
        if character_info.get("occupation"):
            if hasattr(self, 'occupation_var'):
                self.occupation_var.set(character_info["occupation"])
                print(f"✅ 职业: {character_info['occupation']}")
                applied_count += 1
            else:
                print(f"ℹ️ 职业: {character_info['occupation']} (当前UI无此字段)")
        
        if character_info.get("personality"):
            if hasattr(self, 'personality_text'):
                self.personality_text.delete("1.0", tk.END)
                self.personality_text.insert("1.0", character_info["personality"])
                print(f"✅ 性格: {character_info['personality'][:50]}...")
                applied_count += 1
            else:
                print(f"ℹ️ 性格: {character_info['personality'][:50]}... (当前UI无此字段)")
        
        # 外观特征
        if character_info.get("face_shape"):
            self.face_shape_var.set(character_info["face_shape"])
            print(f"✅ 脸型: {character_info['face_shape']}")
            applied_count += 1
        
        if character_info.get("skin_tone"):
            self.skin_tone_var.set(character_info["skin_tone"])
            print(f"✅ 肤色: {character_info['skin_tone']}")
            applied_count += 1
        
        if character_info.get("eyes"):
            self.eyes_var.set(character_info["eyes"])
            print(f"✅ 眼睛: {character_info['eyes']}")
            applied_count += 1
        
        if character_info.get("eyebrows"):
            self.eyebrows_var.set(character_info["eyebrows"])
            applied_count += 1
        
        if character_info.get("nose"):
            self.nose_var.set(character_info["nose"])
            applied_count += 1
        
        if character_info.get("mouth"):
            self.mouth_var.set(character_info["mouth"])
            applied_count += 1
        
        # 发型
        if character_info.get("hair_color"):
            self.hair_color_var.set(character_info["hair_color"])
            print(f"✅ 发色: {character_info['hair_color']}")
            applied_count += 1
        
        if character_info.get("hair_length"):
            self.hair_length_var.set(character_info["hair_length"])
            print(f"✅ 发长: {character_info['hair_length']}")
            applied_count += 1
        
        if character_info.get("hair_style"):
            self.hair_style_var.set(character_info["hair_style"])
            print(f"✅ 发型: {character_info['hair_style']}")
            applied_count += 1
        
        if character_info.get("height"):
            self.height_var.set(character_info["height"])
            print(f"✅ 身高: {character_info['height']}")
            applied_count += 1
        
        if character_info.get("body_type"):
            self.body_type_var.set(character_info["body_type"])
            print(f"✅ 体型: {character_info['body_type']}")
            applied_count += 1
        
        # 服装
        if character_info.get("default_outfit"):
            self.outfit_style_var.set(character_info["default_outfit"])
            print(f"✅ 默认服装: {character_info['default_outfit']}")
            applied_count += 1
        
        if character_info.get("outfit_description"):
            self.outfit_desc_text.delete("1.0", tk.END)
            self.outfit_desc_text.insert("1.0", character_info["outfit_description"])
            print(f"✅ 服装描述: {character_info['outfit_description'][:50]}...")
            applied_count += 1
        
        if character_info.get("accessories"):
            self.accessories_text.delete("1.0", tk.END)
            self.accessories_text.insert("1.0", character_info["accessories"])
            print(f"✅ 配饰: {character_info['accessories'][:50]}...")
            applied_count += 1
        
        # 其他特征
        if character_info.get("typical_expression"):
            self.default_expression_var.set(character_info["typical_expression"])
            print(f"✅ 典型表情: {character_info['typical_expression']}")
            applied_count += 1
        
        if character_info.get("mannerisms"):
            self.actions_text.delete("1.0", tk.END)
            self.actions_text.insert("1.0", character_info["mannerisms"])
            print(f"✅ 行为习惯: {character_info['mannerisms'][:50]}...")
            applied_count += 1
        
        print(f"✅ 已应用智能分析结果到UI，共填充 {applied_count} 个字段")
        print(f"📋 填充的字段: {[k for k in character_info.keys() if character_info.get(k)]}")


