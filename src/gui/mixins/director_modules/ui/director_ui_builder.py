"""
导演页面UI构建器 - 从director_mixin.py重构出来
负责构建导演页面的所有UI组件
"""
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import subprocess
from typing import Optional


class DirectorUIBuilder:
    """导演页面UI构建器 - 将所有UI构建逻辑从director_mixin中分离"""
    
    @staticmethod
    def build_left_workflow_panel(director_frame, mixin_instance):
        """构建左侧工作流面板"""
        # 创建可滚动的左侧面板
        left_outer_frame = ttk.Frame(director_frame, width=270)
        left_outer_frame.pack(side="left", fill="y", expand=False, padx=10, pady=10)
        left_outer_frame.pack_propagate(False)

        left_canvas = tk.Canvas(left_outer_frame, bg="#2b2b2b", highlightthickness=0, width=250)
        left_scrollbar = ttk.Scrollbar(left_outer_frame, orient="vertical", command=left_canvas.yview)
        left_panel = ttk.Frame(left_canvas)

        left_panel.bind("<Configure>", 
                       lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all")))
        left_canvas.create_window((0, 0), window=left_panel, anchor="nw", width=250)
        left_canvas.configure(yscrollcommand=left_scrollbar.set)

        # 鼠标滚轮支持
        def _on_left_mousewheel(event):
            left_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        left_canvas.bind("<MouseWheel>", _on_left_mousewheel)
        left_panel.bind("<MouseWheel>", _on_left_mousewheel)

        def bind_mousewheel_recursive(widget):
            widget.bind("<MouseWheel>", _on_left_mousewheel)
            for child in widget.winfo_children():
                bind_mousewheel_recursive(child)

        mixin_instance.after(100, lambda: bind_mousewheel_recursive(left_panel))

        left_canvas.pack(side="left", fill="both", expand=True)
        left_scrollbar.pack(side="right", fill="y")

        # 标题
        workflow_label = ttk.Label(left_panel, text="🎬 导演工作流", 
                                   font=("Microsoft YaHei", 12, "bold"))
        workflow_label.pack(pady=(0, 10))

        # 添加各个工作流步骤
        DirectorUIBuilder._add_step1_script(left_panel, mixin_instance)
        DirectorUIBuilder._add_step2_shots(left_panel, mixin_instance)
        DirectorUIBuilder._add_step3_images(left_panel, mixin_instance)
        DirectorUIBuilder._add_step4_video(left_panel, mixin_instance)
    
    @staticmethod
    def _add_step1_script(parent, mixin_instance):
        """添加步骤1：生成剧本"""
        step1_frame = ttk.LabelFrame(parent, text="【步骤1】生成剧本", padding=10)
        step1_frame.pack(fill="x", pady=5)
        
        ttk.Button(
            step1_frame,
            text="📝 生成剧本",
            command=mixin_instance._on_story_to_script
        ).pack(fill="x", pady=2)
        
        ttk.Label(
            step1_frame,
            text="将故事转换为专业剧本格式",
            font=("", 9),
            foreground="gray"
        ).pack(pady=2)
    
    @staticmethod
    def _add_step2_shots(parent, mixin_instance):
        """添加步骤2：生成分镜"""
        step2_frame = ttk.LabelFrame(parent, text="【步骤2】生成分镜", padding=10)
        step2_frame.pack(fill="x", pady=5)
        
        ttk.Button(
            step2_frame,
            text="🎬 生成分镜",
            command=mixin_instance._on_generate_shots
        ).pack(fill="x", pady=2)
        
        ttk.Label(
            step2_frame,
            text="将剧本转换为详细分镜列表",
            font=("", 9),
            foreground="gray"
        ).pack(pady=2)
    
    @staticmethod
    def _add_step3_images(parent, mixin_instance):
        """添加步骤3：生成图片"""
        step3_frame = ttk.LabelFrame(parent, text="【步骤3】生成图片", padding=10)
        step3_frame.pack(fill="x", pady=5)
        
        # 分镜选择
        selector_frame = ttk.Frame(step3_frame)
        selector_frame.pack(fill="x", pady=5)
        
        ttk.Label(selector_frame, text="选择分镜:").pack(side="left", padx=5)
        
        mixin_instance.shot_select_var = tk.StringVar(value="全部分镜")
        mixin_instance.shot_select_combo = ttk.Combobox(
            selector_frame,
            textvariable=mixin_instance.shot_select_var,
            state="readonly",
            width=15
        )
        mixin_instance.shot_select_combo.pack(side="left", padx=5)
        mixin_instance.shot_select_combo['values'] = ["全部分镜"]
        
        # 生成按钮
        ttk.Button(
            step3_frame,
            text="🖼️ 生成图片",
            command=mixin_instance._on_generate_selected_shot
        ).pack(fill="x", pady=2)
        
        ttk.Button(
            step3_frame,
            text="🗑️ 删除图片",
            command=mixin_instance._on_delete_shot_images
        ).pack(fill="x", pady=2)
        
        ttk.Label(
            step3_frame,
            text="为分镜生成图片",
            font=("", 9),
            foreground="gray"
        ).pack(pady=2)
    
    @staticmethod
    def _add_step4_video(parent, mixin_instance):
        """添加步骤4：生成视频"""
        step4_frame = ttk.LabelFrame(parent, text="【步骤4】生成视频", padding=10)
        step4_frame.pack(fill="x", pady=5)
        
        ttk.Button(
            step4_frame,
            text="🎥 生成视频提示词",
            command=mixin_instance._on_generate_video_prompt
        ).pack(fill="x", pady=2)
        
        ttk.Button(
            step4_frame,
            text="📋 导出视频指南",
            command=mixin_instance._on_export_video_guide
        ).pack(fill="x", pady=2)
        
        ttk.Label(
            step4_frame,
            text="生成视频制作提示词和指南",
            font=("", 9),
            foreground="gray"
        ).pack(pady=2)
    
    @staticmethod
    def build_center_content_panel(director_frame, mixin_instance):
        """构建中间内容展示面板"""
        middle_panel = ttk.Frame(director_frame)
        middle_panel.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        # 使用Notebook来切换显示不同的内容
        mixin_instance.director_content_notebook = ttk.Notebook(middle_panel)
        mixin_instance.director_content_notebook.pack(fill="both", expand=True)

        # Tab1：剧本显示
        DirectorUIBuilder._build_script_tab(mixin_instance.director_content_notebook, mixin_instance)
        
        # Tab2：分镜头显示
        DirectorUIBuilder._build_shots_tab(mixin_instance.director_content_notebook, mixin_instance)
        
        # Tab3：即梦AI提示词
        DirectorUIBuilder._build_jimeng_tab(mixin_instance.director_content_notebook, mixin_instance)
        
        # Tab4：图片预览
        DirectorUIBuilder._build_images_tab(mixin_instance.director_content_notebook, mixin_instance)
    
    @staticmethod
    def _build_script_tab(notebook, mixin_instance):
        """构建剧本Tab"""
        script_frame = ttk.Frame(notebook)
        notebook.add(script_frame, text="📝 剧本")
        
        mixin_instance.script_text = ScrolledText(
            script_frame,
            height=25,
            width=80,
            wrap="word",
            font=("Consolas", 10)
        )
        mixin_instance.script_text.pack(fill="both", expand=True, padx=5, pady=5)
    
    @staticmethod
    def _build_shots_tab(notebook, mixin_instance):
        """构建分镜Tab"""
        shots_frame = ttk.Frame(notebook)
        notebook.add(shots_frame, text="🎬 分镜")

        # 添加工具栏
        shots_toolbar = ttk.Frame(shots_frame)
        shots_toolbar.pack(fill="x", padx=5, pady=5)

        ttk.Button(
            shots_toolbar,
            text="📋 查看详细分镜",
            command=mixin_instance.open_shot_viewer
        ).pack(side="left", padx=5)

        ttk.Label(
            shots_toolbar,
            text="💡 分镜JSON格式，包含所有详细信息",
            font=("", 9),
            foreground="gray"
        ).pack(side="left", padx=10)

        mixin_instance.shots_list = ScrolledText(
            shots_frame,
            height=25,
            width=80,
            wrap="word",
            font=("Consolas", 10)
        )
        mixin_instance.shots_list.pack(fill="both", expand=True, padx=5, pady=5)
    
    @staticmethod
    def _build_jimeng_tab(notebook, mixin_instance):
        """构建即梦AI提示词Tab"""
        jimeng_frame = ttk.Frame(notebook)
        notebook.add(jimeng_frame, text="🎥 即梦AI提示词")

        # 工具栏
        jimeng_toolbar = ttk.Frame(jimeng_frame)
        jimeng_toolbar.pack(fill="x", padx=5, pady=5)

        ttk.Button(
            jimeng_toolbar,
            text="🔄 提取所有提示词",
            command=mixin_instance._extract_all_jimeng_prompts
        ).pack(side="left", padx=5)
        
        ttk.Button(
            jimeng_toolbar,
            text="📋 复制全部",
            command=mixin_instance._copy_all_jimeng_prompts
        ).pack(side="left", padx=5)
        
        ttk.Button(
            jimeng_toolbar,
            text="🌐 打开即梦AI",
            command=lambda: subprocess.Popen(
                ["start", "https://jimeng.jianying.com/ai-tool/image/generate"],
                shell=True
            )
        ).pack(side="left", padx=5)

        mixin_instance.jimeng_prompts_text = ScrolledText(
            jimeng_frame,
            height=25,
            width=80,
            wrap="word",
            font=("Microsoft YaHei", 11)
        )
        mixin_instance.jimeng_prompts_text.pack(fill="both", expand=True, padx=5, pady=5)
    
    @staticmethod
    def _build_images_tab(notebook, mixin_instance):
        """构建图片预览Tab"""
        images_frame = ttk.Frame(notebook)
        notebook.add(images_frame, text="🖼️  图片预览")

        # 顶部：分镜选择器
        selector_frame = ttk.Frame(images_frame)
        selector_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(
            selector_frame,
            text="选择分镜：",
            font=("Microsoft YaHei", 10)
        ).pack(side="left", padx=5)

        mixin_instance.preview_shot_var = tk.StringVar(value="全部分镜")
        mixin_instance.preview_shot_combo = ttk.Combobox(
            selector_frame,
            textvariable=mixin_instance.preview_shot_var,
            state="readonly",
            width=20
        )
        mixin_instance.preview_shot_combo.pack(side="left", padx=5)
        mixin_instance.preview_shot_combo.bind(
            "<<ComboboxSelected>>",
            mixin_instance._on_preview_shot_selected
        )

        ttk.Button(
            selector_frame,
            text="🔄 刷新",
            command=mixin_instance._refresh_preview_images
        ).pack(side="left", padx=5)

        mixin_instance.preview_info_label = ttk.Label(
            selector_frame,
            text="",
            foreground="gray"
        )
        mixin_instance.preview_info_label.pack(side="left", padx=20)

        # 中间：图片展示区（可滚动）
        preview_container = ttk.Frame(images_frame)
        preview_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        mixin_instance.director_images_canvas = tk.Canvas(
            preview_container,
            bg="#2b2b2b",
            highlightthickness=0
        )
        preview_scrollbar = ttk.Scrollbar(
            preview_container,
            orient="vertical",
            command=mixin_instance.director_images_canvas.yview
        )
        mixin_instance.director_images_scrollable = ttk.Frame(
            mixin_instance.director_images_canvas
        )

        mixin_instance.director_images_scrollable.bind(
            "<Configure>",
            lambda e: mixin_instance.director_images_canvas.configure(
                scrollregion=mixin_instance.director_images_canvas.bbox("all")
            )
        )
        mixin_instance.director_images_canvas.create_window(
            (0, 0),
            window=mixin_instance.director_images_scrollable,
            anchor="nw"
        )
        mixin_instance.director_images_canvas.configure(
            yscrollcommand=preview_scrollbar.set
        )

        mixin_instance.director_images_canvas.pack(side="left", fill="both", expand=True)
        preview_scrollbar.pack(side="right", fill="y")

        # 鼠标滚轮支持
        mixin_instance.director_images_canvas.bind_all(
            "<MouseWheel>",
            mixin_instance._on_preview_mousewheel
        )
    
    @staticmethod
    def build_right_settings_panel(director_frame, mixin_instance):
        """构建右侧设置面板"""
        right_panel = ttk.Frame(director_frame, width=250)
        right_panel.pack(
            side="right",
            fill="both",
            expand=False,
            padx=10,
            pady=10
        )
        right_panel.pack_propagate(False)

        settings_label = ttk.Label(
            right_panel,
            text="⚙️  设置",
            font=("Microsoft YaHei", 12, "bold")
        )
        settings_label.pack(pady=(0, 10))

        # 视频平台选择
        DirectorUIBuilder._build_platform_frame(right_panel, mixin_instance)
        
        # 一致性设置
        DirectorUIBuilder._build_consistency_frame(right_panel, mixin_instance)
        
        # 提示词参数
        DirectorUIBuilder._build_params_frame(right_panel, mixin_instance)
        
        # 导出和保存
        DirectorUIBuilder._build_export_frame(right_panel, mixin_instance)

        # 保存对象引用，以便其他地方使用
        mixin_instance.current_shots = []
        mixin_instance.current_script = ""
    
    @staticmethod
    def _build_platform_frame(parent, mixin_instance):
        """构建视频平台选择框架"""
        platform_frame = ttk.LabelFrame(parent, text="📹 视频平台", padding=10)
        platform_frame.pack(fill="x", pady=5)

        mixin_instance.director_video_platform = tk.StringVar(value="jimeng")
        platforms = [
            ("即梦AI (推荐)", "jimeng"),
            ("Runway ML", "runway"),
            ("剪映/CapCut", "capcut"),
        ]
        for text, value in platforms:
            ttk.Radiobutton(
                platform_frame,
                text=text,
                variable=mixin_instance.director_video_platform,
                value=value
            ).pack(anchor="w", pady=2)
    
    @staticmethod
    def _build_consistency_frame(parent, mixin_instance):
        """构建一致性设置框架"""
        consistency_frame = ttk.LabelFrame(
            parent,
            text="👥 一致性设置",
            padding=10
        )
        consistency_frame.pack(fill="x", pady=5)

        ttk.Label(consistency_frame, text="参考人物:").pack(anchor="w")
        mixin_instance.director_reference_char = tk.StringVar()
        char_dropdown = ttk.Combobox(
            consistency_frame,
            textvariable=mixin_instance.director_reference_char,
            values=["不使用参考"],
            state="readonly",
            width=18
        )
        char_dropdown.pack(fill="x", pady=5)
        char_dropdown.current(0)
    
    @staticmethod
    def _build_params_frame(parent, mixin_instance):
        """构建生成参数框架"""
        params_frame = ttk.LabelFrame(parent, text="🎨 生成参数", padding=10)
        params_frame.pack(fill="x", pady=5)

        ttk.Label(params_frame, text="分辨率:").pack(anchor="w")
        mixin_instance.director_resolution = tk.StringVar(value="768x512")
        res_dropdown = ttk.Combobox(
            params_frame,
            textvariable=mixin_instance.director_resolution,
            values=["512x512", "768x512", "1024x768"],
            state="readonly",
            width=18
        )
        res_dropdown.pack(fill="x", pady=5)

        ttk.Label(params_frame, text="图片风格:").pack(anchor="w")
        mixin_instance.director_style = tk.StringVar(value="photorealistic")
        style_dropdown = ttk.Combobox(
            params_frame,
            textvariable=mixin_instance.director_style,
            values=["photorealistic", "cinematic", "artistic"],
            state="readonly",
            width=18
        )
        style_dropdown.pack(fill="x", pady=5)
    
    @staticmethod
    def _build_export_frame(parent, mixin_instance):
        """构建导出框架"""
        export_frame = ttk.LabelFrame(parent, text="📤 导出", padding=10)
        export_frame.pack(fill="x", pady=5)

        ttk.Button(
            export_frame,
            text="💾 保存项目",
            command=mixin_instance._on_save_director_project
        ).pack(fill="x", pady=2)
        
        ttk.Button(
            export_frame,
            text="📋 复制提示词",
            command=mixin_instance._on_copy_video_prompt
        ).pack(fill="x", pady=2)
        
        ttk.Button(
            export_frame,
            text="📁 打开输出目录",
            command=mixin_instance._on_open_output_folder
        ).pack(fill="x", pady=2)

