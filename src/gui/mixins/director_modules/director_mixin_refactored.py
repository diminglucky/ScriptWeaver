"""
导演页面混入类 - 故事到视频的完整工作流UI
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog, END, DISABLED, NORMAL, LEFT, RIGHT, BOTH, VERTICAL, Y
from tkinter.scrolledtext import ScrolledText
import threading
import os
import subprocess

from .script_generator import ScriptGeneratorMixin
from .shot_list_generator import ShotListGeneratorMixin
from .video_prompt_builder import VideoPromptBuilderMixin
# from .scene_image_generator import SceneImageGeneratorMixin  # ❌ 已删除：功能被
# SDConsistencyMixin 替代
from .project_persistence import ProjectPersistenceMixin
from .sd_consistency_generator import SDConsistencyMixin
from .shot_viewer import ShotViewerMixin
from .prompt_adapter import PromptAdapter
from .image_preview_methods import add_image_preview_methods
from .jimeng_prompt_generator import JimengPromptGenerator


@add_image_preview_methods
class DirectorMixin(
        ScriptGeneratorMixin,
        ShotListGeneratorMixin,
        VideoPromptBuilderMixin,
        ProjectPersistenceMixin,
        SDConsistencyMixin,
        ShotViewerMixin):
    """导演页面 - 整合所有视频制作功能

    图片生成统一使用 SDConsistencyMixin（支持人物一致性）
    """

    def _build_director_page(self) -> None:
        """构建导演页面UI（重构后 - 从517行减少到~30行）"""
        # 初始化
        if not hasattr(self, 'character_seed_map'):
            self.character_seed_map = {}

        # 创建主容器
        director_frame = ttk.Frame(self.notebook)
        self.notebook.add(director_frame, text="🎬 导演")

        # 构建三列布局
        self._build_left_workflow_panel(director_frame)
        self._build_center_content_panel(director_frame)
        self._build_right_settings_panel(director_frame)

    def _build_left_workflow_panel(self, director_frame):
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

        self.after(100, lambda: bind_mousewheel_recursive(left_panel))

        left_canvas.pack(side="left", fill="both", expand=True)
        left_scrollbar.pack(side="right", fill="y")

        # 标题
        workflow_label = ttk.Label(left_panel, text="🎬 导演工作流", 
                                   font=("Microsoft YaHei", 12, "bold"))
        workflow_label.pack(pady=(0, 10))

        # 添加各个工作流步骤
        self._add_step1_script(left_panel)
        self._add_step2_shots(left_panel)
        self._add_step3_images(left_panel)
        self._add_step4_video(left_panel)

    def _add_step1_script(self, parent):
        """添加步骤1：生成剧本"""
        step1_frame = ttk.LabelFrame(parent, text="【步骤1】生成剧本", padding=10)
        step1_frame.pack(fill="x", pady=5)

        def _safe_generate_script():
            try:
                self._on_story_to_script()
            except Exception as e:
                print(f"[ERROR] 生成剧本异常: {e}")
                import traceback
                traceback.print_exc()
                messagebox.showerror("严重错误", f"生成剧本时发生异常:\n{str(e)}\n\n详情请查看控制台")

        script_btn = ttk.Button(step1_frame, text="📝 生成剧本",
                               command=_safe_generate_script, style="Accent.TButton")
        script_btn.pack(fill="x")
        print(f"[OK] 生成剧本按钮已创建: {script_btn}")

        ttk.Label(
            step1_frame,
            text="将故事转换为专业电影剧本",
            font=(
                "",
                8),
            foreground="gray").pack(
            pady=(
                5,
                0))

        # 步骤2：剧本转分镜（含即梦AI提示词）
        step2_frame = ttk.LabelFrame(left_panel, text="【步骤2】生成分镜", padding=10)
        step2_frame.pack(fill="x", pady=5)

        def _safe_generate_shots():
            try:
                print("[DEBUG] 生成分镜按钮被点击")
                print(f"[DEBUG] self对象类型: {type(self)}")
                print(
                    f"[DEBUG] 是否有_on_script_to_shots方法: {
                        hasattr(
                            self,
                            '_on_script_to_shots')}")
                self._on_script_to_shots()
            except Exception as e:
                print(f"[ERROR] 生成分镜异常: {e}")
                import traceback
                traceback.print_exc()
                messagebox.showerror(
                    "严重错误", f"生成分镜时发生异常:\n{
                        str(e)}\n\n详情请查看控制台")

        shots_btn = ttk.Button(
            step2_frame,
            text="🎬 生成分镜",
            command=_safe_generate_shots,
            style="Accent.TButton")
        shots_btn.pack(fill="x", pady=(0, 5))
        print(f"[OK] 生成分镜按钮已创建: {shots_btn}")

        ttk.Button(
            step2_frame,
            text="📋 查看所有分镜",
            command=self.open_shot_viewer).pack(
            fill="x")

        # 提示信息
        info_label = ttk.Label(step2_frame,
                               text="✓ 自动生成即梦AI提示词\n✓ 支持分段生成长剧本",
                               font=("", 8),
                               foreground="gray",
                               justify="left")
        info_label.pack(pady=(5, 0))

        # 步骤3：生成分镜图片
        step3_frame = ttk.LabelFrame(left_panel, text="【步骤3】生成图片", padding=10)
        step3_frame.pack(fill="x", pady=5)

        # 选择分镜
        ttk.Label(step3_frame, text="选择分镜:").pack(anchor="w", pady=(0, 2))
        self.shot_select_var = tk.StringVar()
        self.shot_select_combo = ttk.Combobox(
            step3_frame,
            textvariable=self.shot_select_var,
            state="readonly",
            width=22
        )
        self.shot_select_combo.pack(fill="x", pady=(0, 8))
        self.shot_select_combo['values'] = ["全部分镜"]
        self.shot_select_combo.current(0)

        # 每个分镜生成几张
        num_frame = ttk.Frame(step3_frame)
        num_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(num_frame, text="每个分镜:").pack(side="left")
        self.images_per_shot_var = tk.IntVar(value=1)
        ttk.Spinbox(
            num_frame,
            from_=1,
            to=5,
            width=5,
            textvariable=self.images_per_shot_var).pack(
            side="left",
            padx=5)
        ttk.Label(num_frame, text="张图片").pack(side="left")

        # 生成按钮
        self.generate_images_btn = ttk.Button(
            step3_frame,
            text="🖼️ 生成图片",
            command=self._on_generate_selected_shot,
            style="Accent.TButton")
        self.generate_images_btn.pack(fill="x", pady=(0, 5))

        # 进度显示
        self.image_progress_var = tk.DoubleVar(value=0)
        self.image_progress_bar = ttk.Progressbar(
            step3_frame,
            variable=self.image_progress_var,
            maximum=100,
            mode='determinate'
        )
        self.image_progress_bar.pack(fill="x", pady=(5, 5))

        self.image_progress_label = ttk.Label(
            step3_frame, text="", font=(
                "", 8), foreground="gray")
        self.image_progress_label.pack(pady=(0, 5))

        ttk.Button(
            step3_frame,
            text="🗑️ 删除已生成图片",
            command=self._on_delete_shot_images).pack(
            fill="x",
            pady=(
                0,
                5))

        ttk.Label(step3_frame, text="提示：删除后可重新生成",
                  font=("", 8), foreground="gray").pack(pady=(0, 0))

        # 步骤4：使用即梦AI
        step4_frame = ttk.LabelFrame(left_panel, text="【步骤4】生成视频", padding=10)
        step4_frame.pack(fill="x", pady=5)

        # 提示信息
        usage_info = tk.Frame(
            step4_frame,
            bg="#1e3a5f",
            relief=tk.SOLID,
            borderwidth=1)
        usage_info.pack(fill="x", pady=(0, 8))

        usage_text = tk.Text(
            usage_info,
            height=4,
            wrap="word",
            font=(
                "",
                8),
            bg="#1e3a5f",
            fg="white",
            relief=tk.FLAT,
            borderwidth=0)
        usage_text.pack(padx=8, pady=8, fill="x")
        usage_text.insert("1.0", "💡 使用方法：\n"
                          "1. 在【即梦AI提示词】标签页复制\n"
                          "2. 访问 jimeng.jianying.com\n"
                          "3. 粘贴提示词生成视频")
        usage_text.config(state="disabled")

        ttk.Button(step4_frame,
                   text="🌐 打开即梦AI",
                   command=lambda: subprocess.Popen(["start",
                                                     "https://jimeng.jianying.com/ai-tool/image/generate"],
                                                    shell=True)).pack(fill="x")

        # ===== 中间内容展示区 =====
        middle_panel = ttk.Frame(director_frame)
        middle_panel.pack(
            side="left",
            fill="both",
            expand=True,
            padx=10,
            pady=10)

        # 使用Notebook来切换显示不同的内容
        self.director_content_notebook = ttk.Notebook(middle_panel)
        self.director_content_notebook.pack(fill="both", expand=True)

        # Tab1：剧本显示
        script_frame = ttk.Frame(self.director_content_notebook)
        self.director_content_notebook.add(script_frame, text="📝 剧本")
        self.script_text = ScrolledText(
            script_frame,
            height=25,
            width=80,
            wrap="word",
            font=(
                "Consolas",
                10))
        self.script_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Tab2：分镜头显示
        shots_frame = ttk.Frame(self.director_content_notebook)
        self.director_content_notebook.add(shots_frame, text="🎬 分镜")

        # 添加工具栏
        shots_toolbar = ttk.Frame(shots_frame)
        shots_toolbar.pack(fill="x", padx=5, pady=5)

        ttk.Button(
            shots_toolbar,
            text="📋 查看详细分镜",
            command=self.open_shot_viewer
        ).pack(side="left", padx=5)

        ttk.Label(shots_toolbar, text="💡 分镜JSON格式，包含所有详细信息",
                  font=("", 9), foreground="gray").pack(side="left", padx=10)

        self.shots_list = ScrolledText(
            shots_frame,
            height=25,
            width=80,
            wrap="word",
            font=(
                "Consolas",
                10))
        self.shots_list.pack(fill="both", expand=True, padx=5, pady=5)

        # Tab3：即梦AI提示词（专门展示）
        jimeng_frame = ttk.Frame(self.director_content_notebook)
        self.director_content_notebook.add(jimeng_frame, text="🎥 即梦AI提示词")

        # 工具栏
        jimeng_toolbar = ttk.Frame(jimeng_frame)
        jimeng_toolbar.pack(fill="x", padx=5, pady=5)

        ttk.Button(
            jimeng_toolbar,
            text="🔄 提取所有提示词",
            command=self._extract_all_jimeng_prompts).pack(
            side="left",
            padx=5)
        ttk.Button(
            jimeng_toolbar,
            text="📋 复制全部",
            command=self._copy_all_jimeng_prompts).pack(
            side="left",
            padx=5)
        ttk.Button(jimeng_toolbar,
                   text="🌐 打开即梦AI",
                   command=lambda: subprocess.Popen(["start",
                                                     "https://jimeng.jianying.com/ai-tool/image/generate"],
                                                    shell=True)).pack(side="left",
                                                                      padx=5)

        self.jimeng_prompts_text = ScrolledText(
            jimeng_frame, height=25, width=80, wrap="word", font=(
                "Microsoft YaHei", 11))
        self.jimeng_prompts_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Tab4：图片预览
        images_frame = ttk.Frame(self.director_content_notebook)
        self.director_content_notebook.add(images_frame, text="🖼️  图片预览")

        # 顶部：分镜选择器
        selector_frame = ttk.Frame(images_frame)
        selector_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(
            selector_frame,
            text="选择分镜：",
            font=(
                "Microsoft YaHei",
                10)).pack(
            side="left",
            padx=5)

        self.preview_shot_var = tk.StringVar(value="全部分镜")
        self.preview_shot_combo = ttk.Combobox(
            selector_frame,
            textvariable=self.preview_shot_var,
            state="readonly",
            width=20
        )
        self.preview_shot_combo.pack(side="left", padx=5)
        self.preview_shot_combo.bind(
            "<<ComboboxSelected>>",
            self._on_preview_shot_selected)

        ttk.Button(
            selector_frame,
            text="🔄 刷新",
            command=self._refresh_preview_images).pack(
            side="left",
            padx=5)

        self.preview_info_label = ttk.Label(
            selector_frame, text="", foreground="gray")
        self.preview_info_label.pack(side="left", padx=20)

        # 中间：图片展示区（可滚动）
        preview_container = ttk.Frame(images_frame)
        preview_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.director_images_canvas = tk.Canvas(
            preview_container, bg="#2b2b2b", highlightthickness=0)
        preview_scrollbar = ttk.Scrollbar(
            preview_container,
            orient="vertical",
            command=self.director_images_canvas.yview)
        self.director_images_scrollable = ttk.Frame(
            self.director_images_canvas)

        self.director_images_scrollable.bind(
            "<Configure>", lambda e: self.director_images_canvas.configure(
                scrollregion=self.director_images_canvas.bbox("all")))
        self.director_images_canvas.create_window(
            (0, 0), window=self.director_images_scrollable, anchor="nw")
        self.director_images_canvas.configure(
            yscrollcommand=preview_scrollbar.set)

        self.director_images_canvas.pack(side="left", fill="both", expand=True)
        preview_scrollbar.pack(side="right", fill="y")

        # 鼠标滚轮支持
        self.director_images_canvas.bind_all(
            "<MouseWheel>", self._on_preview_mousewheel)

        # ===== 右侧设置面板 =====
        right_panel = ttk.Frame(director_frame, width=250)
        right_panel.pack(
            side="right",
            fill="both",
            expand=False,
            padx=10,
            pady=10)
        right_panel.pack_propagate(False)

        settings_label = ttk.Label(
            right_panel, text="⚙️  设置", font=(
                "Microsoft YaHei", 12, "bold"))
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
            ttk.Radiobutton(
                platform_frame,
                text=text,
                variable=self.director_video_platform,
                value=value).pack(
                anchor="w",
                pady=2)

        # 一致性设置
        consistency_frame = ttk.LabelFrame(
            right_panel, text="👥 一致性设置", padding=10)
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

        ttk.Button(
            export_frame,
            text="💾 保存项目",
            command=self._on_save_director_project).pack(
            fill="x",
            pady=2)
        ttk.Button(
            export_frame,
            text="📋 复制提示词",
            command=self._on_copy_video_prompt).pack(
            fill="x",
            pady=2)
        ttk.Button(
            export_frame,
            text="📁 打开输出目录",
            command=self._on_open_output_folder).pack(
            fill="x",
            pady=2)

        # 保存对象引用，以便其他地方使用
        self.current_shots = []
        self.current_script = ""

    def _refresh_shot_combo(self, silent=False) -> None:
        """刷新分镜下拉框

        Args:
                silent: 是否静默刷新（不显示提示框）
        """
        print(f"[DEBUG] _refresh_shot_combo 被调用，silent={silent}")

        if not hasattr(self, 'shot_select_combo'):
            print("[ERROR] 未找到分镜选择下拉框")
            return

        if not hasattr(self, 'current_shots') or not self.current_shots:
            # 没有分镜时，只显示默认选项
            self.shot_select_combo['values'] = ["全部分镜"]
            self.shot_select_combo.current(0)
            print("[DEBUG] 没有分镜，设置默认选项")
            if not silent:
                messagebox.showinfo("提示", "还没有生成分镜")
            return

        # 生成简洁的选项列表
        shot_options = ["全部分镜"] + [
            f"分镜{s.get('shot_number', i + 1)}"
            for i, s in enumerate(self.current_shots)
        ]

        self.shot_select_combo['values'] = shot_options
        self.shot_select_combo.current(0)
        self.shot_select_combo.update_idletasks()

        print(f"[OK] 刷新下拉框成功，共 {len(self.current_shots)} 个分镜")

        if not silent:
            messagebox.showinfo("成功", f"已刷新！共 {len(self.current_shots)} 个分镜")

    def _generate_jimeng_prompts_for_all_shots(self, shots=None) -> None:
        """为所有分镜生成即梦AI视频提示词（智能版）"""
        print("[DEBUG] _generate_jimeng_prompts_for_all_shots 被调用")

        if shots is None:
            if not hasattr(self, 'current_shots') or not self.current_shots:
                messagebox.showwarning("提示", "请先生成分镜")
                return
            shots = self.current_shots

        print(f"[DEBUG] 开始为 {len(shots)} 个分镜生成即梦AI提示词")

        # 加载人物详细信息
        character_details = {}
        if hasattr(self, 'current_project') and self.current_project:
            try:
                from pathlib import Path
                import json

                project_dir = Path(self.current_project.project_dir)
                char_info_file = project_dir / "characters" / "characters_info.json"

                if char_info_file.exists():
                    with open(char_info_file, 'r', encoding='utf-8') as f:
                        char_data = json.load(f)
                        character_details = char_data.get('characters', {})
                        print(f"[OK] 加载了 {len(character_details)} 个人物信息")
            except Exception as e:
                print(f"[WARN] 加载人物信息失败: {e}")

        # 获取故事背景
        story_context = ""
        if hasattr(self, 'story_text'):
            try:
                story_context = self.story_text.get("1.0", END).strip()[
                    :500]  # 前500字作为背景
            except BaseException:
                pass

        # 使用新生成器生成提示词
        prompts_dict = JimengPromptGenerator.generate_batch_prompts(
            shots, character_details, story_context
        )

        # 格式化显示
        prompts_text = JimengPromptGenerator.format_prompts_for_display(
            prompts_dict)

        print(f"[DEBUG] 生成的提示词文本长度: {len(prompts_text)}")

        # 显示到UI
        if hasattr(self, 'jimeng_prompts_text'):
            print("[DEBUG] 找到 jimeng_prompts_text，更新显示")
            self.jimeng_prompts_text.config(state="normal")
            self.jimeng_prompts_text.delete("1.0", "end")
            self.jimeng_prompts_text.insert("end", prompts_text)
            self.jimeng_prompts_text.config(state="disabled")
            print("[OK] 即梦AI提示词已生成并显示")
        else:
            print("[ERROR] 没有找到 jimeng_prompts_text")

    def _extract_all_jimeng_prompts(self, show_message=True) -> None:
        """提取所有分镜的即梦AI提示词（兼容旧方法）"""
        # 调用新方法
        self._generate_jimeng_prompts_for_all_shots()

        if show_message:
            messagebox.showinfo("成功",
                                f"已提取 {len(self.current_shots)} 个分镜的即梦AI提示词")

    def _copy_all_jimeng_prompts(self) -> None:
        """复制所有即梦AI提示词到剪贴板"""
        if not hasattr(self, 'current_shots') or not self.current_shots:
            messagebox.showwarning("提示", "请先生成分镜")
            return

        prompts_text = ""
        for i, shot in enumerate(self.current_shots, 1):
            jimeng_prompt = shot.get('jimeng_prompt', '未生成提示词')
            prompts_text += f"【分镜 {i}】\n{jimeng_prompt}\n\n"

        # 复制到剪贴板
        self.clipboard_clear()
        self.clipboard_append(prompts_text)
        messagebox.showinfo(
            "成功", f"已复制 {len(self.current_shots)} 个分镜的即梦AI提示词到剪贴板")

    def _auto_save_script_to_project(self, script_text: str) -> None:
        """自动保存剧本到项目"""
        print("[DEBUG] _auto_save_script_to_project 被调用")

        if not hasattr(self, 'current_project') or not self.current_project:
            print("[ERROR] 没有当前项目")
            return

        try:
            from pathlib import Path
            project_dir = Path(self.current_project.project_dir)
            director_dir = project_dir / "director"
            director_dir.mkdir(parents=True, exist_ok=True)

            # 保存剧本
            script_file = director_dir / "script.txt"
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write(script_text)

            print(f"[OK] 剧本已保存到: {script_file}")

            # 更新项目元数据
            if hasattr(self.current_project, 'metadata'):
                self.current_project.metadata['has_script'] = True
                self.current_project.metadata['script_updated_at'] = datetime.now(
                ).isoformat()
                self.current_project._save_metadata()

        except Exception as e:
            print(f"[ERROR] 保存剧本失败: {e}")
            import traceback
            traceback.print_exc()

    def _auto_save_shots_to_project(self) -> None:
        """自动保存分镜到项目"""
        print("[DEBUG] _auto_save_shots_to_project 被调用")

        if not hasattr(self, 'current_project') or not self.current_project:
            print("[ERROR] 没有当前项目")
            return

        if not hasattr(self, 'current_shots') or not self.current_shots:
            print("[ERROR] 没有分镜数据")
            return

        try:
            from pathlib import Path
            import json
            from datetime import datetime

            project_dir = Path(self.current_project.project_dir)
            director_dir = project_dir / "director"
            director_dir.mkdir(parents=True, exist_ok=True)

            # 保存分镜JSON
            shots_file = director_dir / "shots.json"
            
            # 将 Shot 对象转换为字典以便 JSON 序列化
            shots_list = []
            for shot in self.current_shots:
                # 检查是否是 Shot 对象（有 to_dict 方法）
                if hasattr(shot, 'to_dict'):
                    shots_list.append(shot.to_dict())
                elif isinstance(shot, dict):
                    # 已经是字典，直接使用
                    shots_list.append(shot)
                else:
                    # 其他类型，跳过
                    print(f"警告：无法序列化的分镜对象类型: {type(shot)}")
                    continue
            
            with open(shots_file, 'w', encoding='utf-8') as f:
                json.dump({"shots": shots_list},
                          f, ensure_ascii=False, indent=2)

            print(f"[OK] 分镜已保存到: {shots_file}，共 {len(self.current_shots)} 个")

            # 更新项目元数据
            if hasattr(self.current_project, 'metadata'):
                self.current_project.metadata['has_shots'] = True
                self.current_project.metadata['shots_count'] = len(
                    self.current_shots)
                self.current_project.metadata['shots_updated_at'] = datetime.now(
                ).isoformat()
                self.current_project._save_metadata()

        except Exception as e:
            print(f"[ERROR] 保存分镜失败: {e}")
            import traceback
            traceback.print_exc()

    def _load_director_data_from_project(self) -> None:
        """从项目加载导演数据（剧本和分镜）"""
        print("[DEBUG] _load_director_data_from_project 被调用")

        if not hasattr(self, 'current_project') or not self.current_project:
            print("[DEBUG] 没有当前项目，跳过加载")
            return

        try:
            from pathlib import Path
            import json

            project_dir = Path(self.current_project.project_dir)
            director_dir = project_dir / "director"

            if not director_dir.exists():
                print("[DEBUG] director 目录不存在，跳过加载")
                return

            # 加载剧本
            script_file = director_dir / "script.txt"
            if script_file.exists():
                with open(script_file, 'r', encoding='utf-8') as f:
                    script_text = f.read()

                if hasattr(self, 'script_text'):
                    self.script_text.config(state="normal")
                    self.script_text.delete("1.0", "end")
                    self.script_text.insert("end", script_text)
                    self.script_text.config(state="disabled")
                    print(f"[OK] 已加载剧本，长度: {len(script_text)}")

            # 加载分镜
            shots_file = director_dir / "shots.json"
            if shots_file.exists():
                with open(shots_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.current_shots = data.get('shots', [])

                print(f"[OK] 已加载分镜，共 {len(self.current_shots)} 个")

                # 使用友好格式显示分镜（不是JSON）
                if hasattr(self, 'shots_list') and self.current_shots:
                    self.shots_list.config(state="normal")
                    self.shots_list.delete("1.0", "end")

                    # 友好的格式化显示
                    for idx, shot in enumerate(self.current_shots, 1):
                        self.shots_list.insert("end", "=" * 100 + "\n")
                        self.shots_list.insert("end",
                                               f"【分镜 {shot.get('shot_number',
                                                               idx)}】{shot.get('scene_id',
                                                                               '')} - {shot.get('shot_type',
                                                                                                '')}\n")
                        self.shots_list.insert("end", "=" * 100 + "\n\n")

                        self.shots_list.insert(
                            "end", f"📍 位置: {
                                shot.get(
                                    'location', '')}\n")
                        self.shots_list.insert(
                            "end", f"👥 人物: {
                                ', '.join(
                                    shot.get(
                                        'characters', []))}\n\n")

                        self.shots_list.insert(
                            "end", f"🎨 画面描述:\n{
                                shot.get(
                                    'visual_description', '')}\n\n")
                        self.shots_list.insert(
                            "end", f"🎭 动作:\n{
                                shot.get(
                                    'action', '')}\n\n")

                        if shot.get('dialogue'):
                            self.shots_list.insert(
                                "end", f"💬 对白: {shot.get('dialogue', '')}\n\n")

                        camera = shot.get('camera', {})
                        if camera:
                            self.shots_list.insert(
                                "end",
                                f"📷 镜头: {
                                    camera.get(
                                        'movement',
                                        '')} | {
                                    camera.get(
                                        'angle',
                                        '')} | {
                                    camera.get(
                                        'lens',
                                        '')}\n")

                        self.shots_list.insert(
                            "end",
                            f"⏱️  时长: {
                                shot.get(
                                    'duration',
                                    '')} | 过渡: {
                                shot.get(
                                    'transition_to_next',
                                    '')}\n\n")

                        if shot.get('notes'):
                            self.shots_list.insert(
                                "end", f"📝 备注: {shot.get('notes', '')}\n\n")

                        self.shots_list.insert("end", "\n")

                    self.shots_list.config(state="disabled")

                # 提取即梦AI提示词
                if hasattr(self, '_extract_all_jimeng_prompts'):
                    self._extract_all_jimeng_prompts(show_message=False)

                # 刷新下拉框（静默刷新，不弹提示框）
                if hasattr(self, '_refresh_shot_combo'):
                    self._refresh_shot_combo(silent=True)

                # 刷新图片预览下拉框
                if hasattr(self, '_refresh_preview_shot_combo'):
                    self._refresh_preview_shot_combo()

        except Exception as e:
            print(f"[ERROR] 加载导演数据失败: {e}")
            import traceback
            traceback.print_exc()

    def _goto_image_page(self) -> None:
        """跳转到图片管理页面"""
        try:
            if hasattr(self, 'notebook'):
                for i in range(self.notebook.index("end")):
                    if "图片" in self.notebook.tab(i, "text"):
                        self.notebook.select(i)
                        messagebox.showinfo("提示",
                                            "已切换到图片管理页面！\n\n"
                                            "请在【人物管理】标签页：\n"
                                            "1. 提取或选择人物\n"
                                            "2. 点击【编辑人物详情】完善信息\n"
                                            "3. 选择生成类型（标准/表情/角度）\n"
                                            "4. 点击【开始生成】")
                        break
        except Exception as e:
            print(f"跳转失败: {e}")

    def _view_character_gallery(self) -> None:
        """查看人物图片库"""
        if not self.current_project:
            messagebox.showwarning("提示", "请先创建或打开一个项目！")
            return

        from pathlib import Path
        from PIL import Image, ImageTk
        char_dir = Path(self.current_project.project_dir) / "characters"

        if not char_dir.exists() or not list(char_dir.glob("*.png")):
            messagebox.showinfo("提示",
                                "还没有生成人物照片！\n\n"
                                "请先前往【图片管理】页面生成人物形象。")
            return

        # 创建图片库窗口
        gallery_window = tk.Toplevel(self)
        gallery_window.title("人物图片库")
        gallery_window.geometry("950x750")

        # 标题
        title_frame = ttk.Frame(gallery_window)
        title_frame.pack(fill="x", padx=20, pady=15)

        all_images = list(char_dir.glob("*.png"))
        ttk.Label(title_frame, text="🎨 人物图片库",
                  font=("", 14, "bold")).pack(side=LEFT)
        ttk.Label(title_frame, text=f"共 {len(all_images)} 张图片",
                  font=("", 11)).pack(side=RIGHT)

        # 创建可滚动区域
        canvas = tk.Canvas(gallery_window, bg="#2b2b2b")
        scrollbar = ttk.Scrollbar(
            gallery_window,
            orient=VERTICAL,
            command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 加载和显示图片（网格布局）
        col_count = 4
        for idx, img_path in enumerate(sorted(all_images)):
            row = idx // col_count
            col = idx % col_count

            # 创建图片卡片
            card = ttk.Frame(scrollable_frame, relief="solid", borderwidth=1)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

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
            scrollable_frame.columnconfigure(i, weight=1)

        canvas.pack(
            side=LEFT, fill=BOTH, expand=True, padx=(
                20, 0), pady=(
                0, 20))
        scrollbar.pack(side=RIGHT, fill=Y, padx=(0, 20), pady=(0, 20))

        # 鼠标滚轮支持
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # 关闭时解绑
        def on_close():
            canvas.unbind_all("<MouseWheel>")
            gallery_window.destroy()

        gallery_window.protocol("WM_DELETE_WINDOW", on_close)

    def _on_generate_selected_shot(self) -> None:
        """生成选中的分镜图片"""
        print("[DEBUG] _on_generate_selected_shot 被调用")

        # 检查项目
        if not hasattr(self, 'current_project') or not self.current_project:
            messagebox.showwarning("提示", "请先创建或加载项目")
            print("[ERROR] 没有当前项目")
            return

        # 检查分镜
        if not hasattr(self, 'current_shots') or not self.current_shots:
            messagebox.showwarning("提示", "请先生成分镜头")
            print("[ERROR] 没有分镜数据")
            return

        print(f"[OK] 当前有 {len(self.current_shots)} 个分镜")

        # 获取选择
        selected = self.shot_select_var.get()
        print(f"[DEBUG] 用户选择: {selected}")

        if selected == "全部分镜":
            # 生成所有分镜
            print("[DEBUG] 准备生成所有分镜")
            self._on_generate_shot_images()
        else:
            # 生成单个分镜
            # 从选项中提取分镜编号
            import re
            match = re.match(r"分镜(\d+)", selected)
            if match:
                shot_num = int(match.group(1))
                print(f"[DEBUG] 准备生成单个分镜: {shot_num}")
                self._generate_single_shot(shot_num)
            else:
                print(f"[ERROR] 无法从 '{selected}' 提取分镜编号")
                messagebox.showwarning("提示", "无法识别选中的分镜")

    def _on_delete_shot_images(self) -> None:
        """删除选中分镜的图片"""
        if not hasattr(self, 'current_project') or not self.current_project:
            messagebox.showwarning("提示", "请先创建项目")
            return

        if not hasattr(self, 'current_shots') or not self.current_shots:
            messagebox.showwarning("提示", "请先生成分镜")
            return

        selected = self.shot_select_var.get()

        if selected == "全部分镜":
            # 确认删除所有
            if not messagebox.askyesno("确认", "确定要删除所有分镜的图片吗？"):
                return

            try:
                from pathlib import Path
                import shutil

                project_dir = Path(self.current_project.project_dir)
                shots_dir = project_dir / "director" / "shots"

                if shots_dir.exists():
                    shutil.rmtree(shots_dir)
                    shots_dir.mkdir(parents=True, exist_ok=True)
                    messagebox.showinfo("成功", "已删除所有分镜图片")
                    print(f"[OK] 已删除所有分镜图片: {shots_dir}")
                else:
                    messagebox.showinfo("提示", "没有找到分镜图片")

            except Exception as e:
                messagebox.showerror("错误", f"删除失败: {e}")
                print(f"[ERROR] 删除失败: {e}")
        else:
            # 删除单个分镜的图片
            import re
            match = re.match(r"分镜(\d+)", selected)
            if match:
                shot_num = int(match.group(1))

                if not messagebox.askyesno("确认", f"确定要删除分镜 {shot_num} 的图片吗？"):
                    return

                try:
                    from pathlib import Path

                    project_dir = Path(self.current_project.project_dir)
                    shots_dir = project_dir / "director" / "shots"

                    if shots_dir.exists():
                        # 删除该分镜的所有图片
                        deleted_count = 0
                        for img_file in shots_dir.glob(
                                f"shot_{shot_num}_*.png"):
                            img_file.unlink()
                            deleted_count += 1

                        if deleted_count > 0:
                            messagebox.showinfo(
                                "成功", f"已删除分镜 {shot_num} 的 {deleted_count} 张图片")
                            print(
                                f"[OK] 已删除分镜 {shot_num} 的 {deleted_count} 张图片")
                        else:
                            messagebox.showinfo("提示", f"分镜 {shot_num} 没有图片")

                except Exception as e:
                    messagebox.showerror("错误", f"删除失败: {e}")
                    print(f"[ERROR] 删除失败: {e}")

    def _generate_single_shot(self, shot_num: int) -> None:
        """生成单个分镜的图片 - 带进度条和取消功能"""
        # 找到对应的分镜
        shot = None
        for s in self.current_shots:
            if s.get('shot_number') == shot_num:
                shot = s
                break

        if not shot:
            messagebox.showwarning("提示", f"未找到分镜 {shot_num}")
            return

        # 使用设置的数量
        num_images = self.images_per_shot_var.get() if hasattr(
            self, 'images_per_shot_var') else 1

        print(f"[DEBUG] 准备生成分镜 {shot_num}，共 {num_images} 张")

        # 取消标志
        self._cancel_generation = False

        def task():
            try:
                # 禁用生成按钮，显示进度
                self.after(
                    0, lambda: self.generate_images_btn.config(
                        state="disabled", text="⏸️ 生成中..."))
                self.after(0, lambda: self.image_progress_var.set(0))

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
                failed = 0

                for i in range(num_images):
                    # 检查取消标志
                    if self._cancel_generation:
                        print("[INFO] 用户取消生成")
                        self.after(
                            0, lambda: messagebox.showinfo(
                                "提示", "已取消生成"))
                        break

                    # 更新进度
                    progress = (i / num_images) * 100
                    self.after(
                        0,
                        lambda p=progress,
                        idx=i + 1,
                        total=num_images: (
                            self.image_progress_var.set(p),
                            self.image_progress_label.config(
                                text=f"正在生成第 {idx}/{total} 张...")))
                    self.status.set(
                        f"🖼️  分镜 {shot_num} - 图片 {i + 1}/{num_images}")

                    try:
                        image_path = self._generate_single_shot_image(
                            shot_num=shot_num,
                            shot_variant=i + 1,
                            description=description,
                            output_dir=output_dir,
                            seed_offset=i
                        )

                        if image_path and os.path.exists(image_path):
                            generated.append(image_path)
                            print(
                                f"[OK] 生成分镜 {shot_num} 变体 {
                                    i +
                                    1}: {
                                    os.path.basename(image_path)}")
                        else:
                            failed += 1
                            print(f"[WARN] 分镜 {shot_num} 变体 {i + 1} 返回空路径")
                    except Exception as e:
                        failed += 1
                        error_msg = f"[ERROR] 生成分镜 {shot_num} 变体 {
                            i +
                            1} 失败: {
                            str(e)}"
                        print(error_msg)
                        print("=" * 60)
                        print("详细错误信息:")
                        import traceback
                        traceback.print_exc()
                        print("=" * 60)

                # 完成
                self.after(0, lambda: self.image_progress_var.set(100))
                self.after(
                    0, lambda: self.image_progress_label.config(
                        text="完成"))

                if generated:
                    self.after(
                        0, lambda: messagebox.showinfo(
                            "生成完成", f"分镜 {shot_num} 生成结果:\n✅ 成功: {
                                len(generated)} 张\n❌ 失败: {failed} 张"))
                    self.status.set(f"✅ 完成 ({len(generated)}/{num_images})")
                    # 刷新预览下拉框
                    self.after(0, self._refresh_preview_shot_combo)
                else:
                    self.after(
                        0,
                        lambda: messagebox.showerror(
                            "生成失败",
                            f"分镜 {shot_num} 所有图片都生成失败\n请检查:\n1. SD服务是否启动\n2. API配置是否正确\n3. 查看控制台详细错误"))
                    self.status.set("❌ 生成失败")

            except Exception as e:
                print(f"[ERROR] 生成任务异常: {e}")
                import traceback
                traceback.print_exc()
                self.after(
                    0, lambda: messagebox.showerror(
                        "严重错误", f"生成过程发生异常:\n{
                            str(e)}\n\n请查看控制台详情"))
                self.status.set("❌ 异常")
            finally:
                # 恢复按钮
                self.after(
                    0, lambda: self.generate_images_btn.config(
                        state="normal", text="🖼️ 生成图片"))

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
        image_files = [
            f for f in os.listdir(shots_dir) if f.endswith(
                ('.png', '.jpg', '.jpeg'))]
        image_files.sort()

        if not image_files:
            ttk.Label(dialog, text="没有找到图片", font=("Arial", 14)).pack(pady=50)
            ttk.Button(dialog, text="关闭", command=dialog.destroy).pack()
            return

        # 创建滚动区域
        canvas = tk.Canvas(dialog)
        scrollbar = ttk.Scrollbar(
            dialog, orient="vertical", command=canvas.yview)
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
            except BaseException:
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

        ttk.Label(
            btn_frame, text=f"共 {
                len(image_files)} 张图片").pack(
            side="left")

        def delete_unselected():
            to_delete = [
                f for f,
                var in selected_images.items() if not var.get()]
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

        ttk.Button(
            btn_frame,
            text="🗑️  删除未选中",
            command=delete_unselected).pack(
            side="right",
            padx=5)
        ttk.Button(
            btn_frame, text="✅ 全选", command=lambda: [
                v.set(True) for v in selected_images.values()]).pack(
            side="right", padx=5)
        ttk.Button(
            btn_frame, text="❌ 全不选", command=lambda: [
                v.set(False) for v in selected_images.values()]).pack(
            side="right", padx=5)

    def _on_generate_shot_images(self) -> None:
        """生成所有分镜头图片"""
        if not self.current_shots:
            messagebox.showwarning("提示", "请先生成分镜头")
            return

        def task():
            try:
                self.status.set("🖼️  正在生成分镜头图片...")
                if hasattr(self, 'update_header_status'):
                    self.after(
                        0, lambda: self.update_header_status(
                            "生成分镜图片中...", "🖼️"))

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

                # 使用UI上的spinbox设置的数量，不再弹窗询问
                num_images_per_shot = self.images_per_shot_var.get(
                ) if hasattr(self, 'images_per_shot_var') else 1
                print(f"[DEBUG] 全部分镜生成，每个分镜 {num_images_per_shot} 张图片")

                total_images = len(self.current_shots) * num_images_per_shot
                current_image = 0

                for i, shot in enumerate(self.current_shots, 1):
                    try:
                        # 调用图片生成逻辑
                        self.status.set(
                            f"🖼️  正在生成分镜 {i}/{len(self.current_shots)}...")

                        # 构建图片描述
                        description = self._build_shot_description(shot, i)

                        # 为每个分镜生成多张图片
                        shot_images = []
                        for j in range(num_images_per_shot):
                            current_image += 1
                            self.status.set(
                                f"🖼️  分镜 {i}/{len(self.current_shots)} - 图片 {j + 1}/{num_images_per_shot} (总进度: {current_image}/{total_images})")

                            try:
                                # 生成图片（每次略微调整种子以产生变化）
                                image_path = self._generate_single_shot_image(
                                    shot_num=i,
                                    shot_variant=j + 1,
                                    description=description,
                                    output_dir=output_dir,
                                    seed_offset=j  # 添加种子偏移以产生变化
                                )

                                if image_path and os.path.exists(image_path):
                                    shot_images.append(image_path)
                                    print(
                                        f"✅ 生成分镜 {i} 变体 {
                                            j +
                                            1}: {
                                            os.path.basename(image_path)}")
                                else:
                                    print(f"⚠️  生成分镜 {i} 变体 {j + 1} 失败")
                            except Exception as e:
                                print(f"❌ 生成分镜 {i} 变体 {j + 1} 失败: {str(e)}")

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
                self.after(
                    0, lambda: messagebox.showerror(
                        "错误", f"生成分镜图片失败: {
                            str(e)}"))
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

        guide_text = ScrolledText(
            guide_window, font=(
                "Consolas", 10), wrap="word")
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

        ttk.Button(
            button_frame,
            text="💾 保存指南",
            command=save_guide).pack(
            side="left",
            padx=5)
        ttk.Button(
            button_frame,
            text="复制全部",
            command=lambda: self._copy_text(guide)).pack(
            side="left",
            padx=5)

    def _on_save_director_project(self) -> None:
        """保存导演项目"""
        try:
            # 获取当前项目路径
            if not hasattr(
                    self,
                    'current_project') or not self.current_project:
                messagebox.showwarning("提示", "请先打开一个项目")
                return

            project_path = self.current_project.path if hasattr(
                self.current_project, 'path') else str(
                self.current_project)

            # 保存项目
            success = self.save_director_project(project_path)

            if success:
                messagebox.showinfo(
                    "成功", "导演项目已保存完成！\n\n已保存内容：\n- 剧本\n- 分镜头列表\n- 一致性设定\n- 生成参数\n- 视频提示词")
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
        if hasattr(
                self,
                'img_api_preset') and hasattr(
                self,
                'img_api_presets'):
            preset_name = self.img_api_preset.get()
            if preset_name in self.img_api_presets:
                provider = self.img_api_presets[preset_name].get(
                    "provider", "")
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
                if isinstance(
                        character_details,
                        dict) and char_name in character_details:
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
                    consistency_chars = self.consistency_data.get(
                        'characters', {})
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
                                hair_desc = f"{
                                    hair['color']}{
                                    hair.get(
                                        'length',
                                        '')}{
                                    hair['style']}"
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
                                char_parts.append(
                                    f"服装：{'，'.join(outfit_parts)}")

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
        # 不需要SDPromptOptimizer，直接内联实现

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
            if isinstance(
                    character_details,
                    dict) and char_name in character_details:
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
                            char_parts.append(
                                "wearing glasses, black frame glasses")

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
                            char_parts.append(
                                "tired expression, exhausted face")
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
                    if gender and 'male' not in ' '.join(
                            char_parts) and 'female' not in ' '.join(char_parts):
                        if "男" in gender:
                            char_parts.insert(1, "male")
                        elif "女" in gender:
                            char_parts.insert(1, "female")

                    # 年龄
                    age = char_data.get('age', '')
                    if age and 'teenage' not in ' '.join(char_parts):
                        if "16" in str(age) or "17" in str(
                                age) or "18" in str(age):
                            char_parts.insert(
                                2, "teenage, high school student")
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
                                char_parts.append(
                                    "tan skin, healthy complexion")

                        if face.get('face_shape'):
                            face_shape = face['face_shape']
                            if "国字" in face_shape:
                                char_parts.append(
                                    "square face, strong jawline")
                            elif "瓜子" in face_shape or "鹅蛋" in face_shape:
                                char_parts.append(
                                    "oval face, delicate features")

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
                            char_parts.append(
                                "wearing " + ", ".join(outfit_parts))

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

    def _generate_single_shot_image(
            self,
            shot_num: int,
            description: str,
            output_dir: str,
            shot_variant: int = 1,
            seed_offset: int = 0) -> str:
        """生成单个分镜图片（使用服务层）

        Args:
            shot_num: 分镜编号
            description: 图片描述
            output_dir: 输出目录
            shot_variant: 变体编号（用于文件命名）
            seed_offset: 种子偏移量（用于产生不同变体）
            
        Returns:
            str: 生成的图片路径，失败时返回None
        """
        try:
            print(f"\n=== 生成分镜 {shot_num} 变体 {shot_variant} ===")
            
            # 验证API配置
            if not hasattr(self, 'img_api_preset') or not hasattr(self, 'img_api_presets'):
                raise Exception("请先在图片生成页面配置API")
                
            preset_name = self.img_api_preset.get()
            if preset_name not in self.img_api_presets:
                raise Exception(f"未找到预设配置：{preset_name}")
                
            api_config = self.img_api_presets[preset_name]
            provider = api_config.get("provider", "openai")
            print(f"📌 API提供商: {provider}")

            # 获取当前分镜
            current_shot = None
            if hasattr(self, 'current_shots') and shot_num <= len(self.current_shots):
                current_shot = self.current_shots[shot_num - 1]

            # 优先使用SD一致性生成器
            if provider == "sd" and current_shot and hasattr(self, 'consistency_data') and self.consistency_data:
                print("使用SD一致性生成器...")
                image_path = self._generate_shot_with_sd_consistency(
                    current_shot, shot_num, output_dir, shot_variant
                )
                if image_path:
                    return image_path

            # 使用 ImageGeneratorService
            from .services.image_generator_service import ImageGeneratorService
            from .models.shot import Shot
            from pathlib import Path
            
            # 初始化服务
            if not hasattr(self, '_image_generator'):
                self._image_generator = ImageGeneratorService()
            
            # 转换为Shot对象（如果有分镜信息）
            if current_shot:
                # 处理camera参数
                from .models.shot import ShotCamera
                camera_data = current_shot.get('camera', {})
                if isinstance(camera_data, dict):
                    camera = ShotCamera(
                        movement=camera_data.get('movement', ''),
                        angle=camera_data.get('angle', current_shot.get('camera_angle', '')),
                        lens=camera_data.get('lens', '')
                    )
                else:
                    camera = ShotCamera()
                
                shot = Shot(
                    shot_number=shot_num,
                    characters=current_shot.get('characters', []),
                    location=current_shot.get('location', ''),
                    action=current_shot.get('action', ''),
                    emotion=current_shot.get('emotion', ''),
                    shot_type=current_shot.get('shot_type', ''),
                    visual_description=current_shot.get('visual_description', description),
                    duration=current_shot.get('duration', ''),
                    transition=current_shot.get('transition', ''),
                    camera=camera,
                    scene_description=current_shot.get('scene_description', ''),
                    jimeng_prompt=current_shot.get('jimeng_prompt', ''),
                    lighting=current_shot.get('lighting', ''),
                    atmosphere=current_shot.get('atmosphere', ''),
                    character_details=current_shot.get('character_details', {}),
                    props=current_shot.get('props', []),
                    continuity=current_shot.get('continuity', ''),
                    scene_id=current_shot.get('scene_id', ''),
                    time=current_shot.get('time', '')
                )
            else:
                # 创建基本Shot对象
                shot = Shot(
                    shot_number=shot_num,
                    visual_description=description
                )
            
            # 准备人物数据（如果有）
            characters_data = None
            if hasattr(self, 'characters') and self.characters:
                from .models.character import Character
                characters_data = {}
                for char_name, char_info in self.characters.items():
                    characters_data[char_name] = Character(
                        name=char_name,
                        description=char_info.get('description', ''),
                        portrait_image=char_info.get('portrait_image', None)
                    )
            
            # 使用服务生成图片
            image_path = self._image_generator.generate_shot_image(
                shot=shot,
                shot_variant=shot_variant,
                output_dir=Path(output_dir),
                api_config=api_config,
                characters_data=characters_data,
                seed_offset=seed_offset
            )
            
            return image_path

        except Exception as e:
            print(f"生成图片失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
