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
        
        # ★★★ 章节选择器 ★★★
        chapter_frame = ttk.Frame(step2_frame)
        chapter_frame.pack(fill="x", pady=5)
        
        ttk.Label(chapter_frame, text="生成范围:").pack(side="left", padx=5)
        
        mixin_instance.shot_generation_range_var = tk.StringVar(value="全部章节")
        mixin_instance.shot_generation_range_combo = ttk.Combobox(
            chapter_frame,
            textvariable=mixin_instance.shot_generation_range_var,
            state="readonly",
            width=15
        )
        mixin_instance.shot_generation_range_combo.pack(side="left", padx=5)
        mixin_instance.shot_generation_range_combo['values'] = ["全部章节", "前3段", "前5段", "前10段"]
        
        ttk.Button(
            step2_frame,
            text="🎬 生成分镜",
            command=mixin_instance._on_generate_shots
        ).pack(fill="x", pady=2)
        
        ttk.Label(
            step2_frame,
            text="将剧本转换为详细分镜列表\n💡 可选择部分章节快速测试",
            font=("", 9),
            foreground="gray",
            justify="left"
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
            width=15,  # 增加宽度以显示完整选项
            height=15  # 设置下拉列表高度
        )
        mixin_instance.shot_select_combo.pack(side="left", padx=5)
        mixin_instance.shot_select_combo['values'] = ["全部分镜"]
        mixin_instance.shot_select_combo.current(0)  # 确保初始选中
        
        # 添加刷新按钮
        ttk.Button(
            selector_frame,
            text="🔄",
            width=3,
            command=lambda: DirectorUIBuilder._debug_and_refresh_shots(mixin_instance)
        ).pack(side="left", padx=2)
        
        # 绑定选择事件，自动推荐图片数量
        mixin_instance.shot_select_combo.bind(
            "<<ComboboxSelected>>",
            lambda e: DirectorUIBuilder._on_shot_selected_for_recommendation(mixin_instance)
        )
        
        # 每个分镜生成图片数量
        num_frame = ttk.Frame(step3_frame)
        num_frame.pack(fill="x", pady=5)
        
        ttk.Label(num_frame, text="每个分镜:").pack(side="left", padx=5)
        
        mixin_instance.images_per_shot_var = tk.IntVar(value=1)
        ttk.Spinbox(
            num_frame,
            from_=1,
            to=5,
            width=5,
            textvariable=mixin_instance.images_per_shot_var
        ).pack(side="left", padx=5)
        
        ttk.Label(num_frame, text="张图片").pack(side="left")
        
        # 推荐提示标签
        mixin_instance.image_count_recommendation_label = ttk.Label(
            num_frame,
            text="💡",
            foreground="gray",
            font=("", 9)
        )
        mixin_instance.image_count_recommendation_label.pack(side="left", padx=5)
        
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
            text="为分镜生成图片（可生成1-5个变体）",
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
            width=25,  # 增加宽度以显示完整选项
            height=15  # 设置下拉列表高度
        )
        mixin_instance.preview_shot_combo.pack(side="left", padx=5)
        mixin_instance.preview_shot_combo['values'] = ["全部分镜"]
        mixin_instance.preview_shot_combo.current(0)
        mixin_instance.preview_shot_combo.bind(
            "<<ComboboxSelected>>",
            mixin_instance._on_preview_shot_selected
        )

        def refresh_preview_all():
            """刷新预览页面的所有内容（下拉框+图片）"""
            if hasattr(mixin_instance, '_refresh_preview_shot_combo'):
                mixin_instance._refresh_preview_shot_combo()
            mixin_instance._refresh_preview_images()
        
        ttk.Button(
            selector_frame,
            text="🔄 刷新",
            command=refresh_preview_all
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
    
    @staticmethod
    def _on_shot_selected_for_recommendation(mixin_instance):
        """当选择分镜时，根据分镜类型推荐图片数量"""
        selection = mixin_instance.shot_select_var.get()
        
        # 如果选择的是"全部分镜"
        if selection == "全部分镜":
            if hasattr(mixin_instance, 'current_shots') and mixin_instance.current_shots:
                total_shots = len(mixin_instance.current_shots)
                # 全部分镜时推荐较少的数量（因为要生成很多）
                if total_shots <= 3:
                    recommended = 3  # 分镜少，可以多生成几张
                elif total_shots <= 6:
                    recommended = 2
                else:
                    recommended = 1  # 分镜多，推荐只生成1张
            else:
                recommended = 1
        else:
            # 单个分镜，根据分镜类型推荐
            try:
                shot_num = int(selection.replace("分镜", ""))
                if hasattr(mixin_instance, 'current_shots') and mixin_instance.current_shots:
                    if shot_num <= len(mixin_instance.current_shots):
                        shot = mixin_instance.current_shots[shot_num - 1]
                        recommended = DirectorUIBuilder._recommend_image_count_for_shot(shot)
                    else:
                        recommended = 2
                else:
                    recommended = 2
            except (ValueError, IndexError):
                recommended = 2
        
        # 设置推荐值并更新提示
        if hasattr(mixin_instance, 'images_per_shot_var'):
            mixin_instance.images_per_shot_var.set(recommended)
            print(f"[推荐] {selection} → 推荐生成 {recommended} 张图片")
            
            # 更新提示标签
            if hasattr(mixin_instance, 'image_count_recommendation_label'):
                reason = DirectorUIBuilder._get_recommendation_reason(
                    selection, 
                    mixin_instance.current_shots if hasattr(mixin_instance, 'current_shots') else None
                )
                mixin_instance.image_count_recommendation_label.config(
                    text=f"💡 推荐 {recommended} 张 ({reason})"
                )
    
    @staticmethod
    def _recommend_image_count_for_shot(shot: dict) -> int:
        """根据分镜特征推荐图片生成数量
        
        推荐规则：
        - 特写/近景：3-4张（需要多个角度和表情）
        - 中景：2-3张（需要一些变化）
        - 全景/远景：1-2张（环境为主，变化不大）
        - 动作镜头：3-4张（捕捉不同动作瞬间）
        - 静态镜头：1-2张（变化较少）
        """
        recommended = 2  # 默认推荐2张
        
        shot_type = shot.get('shot_type', '').lower()
        action = shot.get('action', '').lower()
        
        # 根据镜头类型推荐
        if any(keyword in shot_type for keyword in ['特写', 'close', 'cu', 'ecu', '近景']):
            # 特写/近景：推荐3-4张
            recommended = 3
        elif any(keyword in shot_type for keyword in ['中景', 'medium', 'ms', 'mcu']):
            # 中景：推荐2-3张
            recommended = 2
        elif any(keyword in shot_type for keyword in ['全景', '远景', 'wide', 'long', 'ls', 'ws']):
            # 全景/远景：推荐1-2张
            recommended = 2
        
        # 根据动作类型调整
        action_keywords = ['跑', '跳', '打', '追', '飞', '舞', '战', '飘']
        if any(keyword in action for keyword in action_keywords):
            # 动作镜头：增加1张
            recommended = min(recommended + 1, 4)
        
        # 根据人物数量调整
        characters = shot.get('characters', [])
        if len(characters) >= 3:
            # 多人场景：增加1张（需要不同构图）
            recommended = min(recommended + 1, 4)
        
        return recommended
    
    @staticmethod
    def _get_recommendation_reason(selection: str, current_shots: list) -> str:
        """获取推荐理由"""
        if selection == "全部分镜":
            if current_shots:
                total = len(current_shots)
                if total <= 3:
                    return "分镜少"
                elif total <= 6:
                    return "适中"
                else:
                    return "分镜多，节省时间"
            return "默认"
        
        # 单个分镜
        try:
            shot_num = int(selection.replace("分镜", ""))
            if current_shots and shot_num <= len(current_shots):
                shot = current_shots[shot_num - 1]
                shot_type = shot.get('shot_type', '').lower()
                
                if any(k in shot_type for k in ['特写', 'close', 'cu']):
                    return "特写镜头"
                elif any(k in shot_type for k in ['全景', 'wide', 'long']):
                    return "全景镜头"
                elif any(k in shot_type for k in ['中景', 'medium']):
                    return "中景镜头"
        except:
            pass
        
        return "标准"
    
    @staticmethod
    def _debug_and_refresh_shots(mixin_instance):
        """调试并刷新分镜列表"""
        from tkinter import messagebox
        
        print("\n" + "="*80)
        print("🔍 分镜下拉框调试信息")
        print("="*80)
        
        # 检查项目
        has_project = hasattr(mixin_instance, 'current_project') and mixin_instance.current_project
        print(f"1. 是否有当前项目: {has_project}")
        if has_project:
            if hasattr(mixin_instance.current_project, 'project_dir'):
                print(f"   项目路径: {mixin_instance.current_project.project_dir}")
            elif isinstance(mixin_instance.current_project, dict):
                print(f"   项目路径: {mixin_instance.current_project.get('path', 'N/A')}")
        
        # 检查分镜数据
        has_shots = hasattr(mixin_instance, 'current_shots')
        print(f"2. 是否有 current_shots 属性: {has_shots}")
        if has_shots:
            shots = mixin_instance.current_shots
            print(f"   分镜数量: {len(shots) if shots else 0}")
            if shots:
                print(f"   第一个分镜类型: {type(shots[0])}")
                if isinstance(shots[0], dict):
                    print(f"   第一个分镜内容: shot_number={shots[0].get('shot_number')}, shot_type={shots[0].get('shot_type')}")
                    print(f"   所有分镜编号: {[s.get('shot_number', '?') if isinstance(s, dict) else '?' for s in shots[:10]]}")
        
        # 检查下拉框
        has_combo = hasattr(mixin_instance, 'shot_select_combo')
        print(f"3. 是否有 shot_select_combo: {has_combo}")
        if has_combo:
            try:
                current_values = mixin_instance.shot_select_combo['values']
                print(f"   当前下拉框选项: {current_values}")
            except:
                print(f"   无法读取下拉框选项")
        
        print("="*80)
        
        # 如果没有分镜数据，尝试从项目加载
        if has_project and (not has_shots or not mixin_instance.current_shots):
            print("\n⚠️ 检测到没有分镜数据，尝试从项目加载...")
            if hasattr(mixin_instance, '_load_director_data_from_project'):
                try:
                    mixin_instance._load_director_data_from_project()
                    print("✅ 已尝试加载项目数据")
                except Exception as e:
                    print(f"❌ 加载失败: {e}")
        
        # 刷新下拉框
        print("\n🔄 开始刷新下拉框...")
        mixin_instance._refresh_shot_combo(silent=False)
        
        # 同时刷新预览页面下拉框
        if hasattr(mixin_instance, '_refresh_preview_shot_combo'):
            print("🔄 同时刷新预览页面下拉框...")
            mixin_instance._refresh_preview_shot_combo()
        
        print("="*80 + "\n")

