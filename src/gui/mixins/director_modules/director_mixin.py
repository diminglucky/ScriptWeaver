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
from .sd_prompt_builder import SDPromptBuilder
from .ui.director_ui_builder import DirectorUIBuilder
from .handlers import ImageGenerationHandler, ProjectHandler, JimengHandler

from src.core.logging_config import get_logger

logger = get_logger(__name__)


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
        
        # 初始化current_shots（如果还没有）
        if not hasattr(self, 'current_shots'):
            self.current_shots = []
            logger.info("初始化 current_shots 为空列表")

        # 创建主容器
        director_frame = ttk.Frame(self.notebook)
        self.notebook.add(director_frame, text="🎬 导演")

        # 构建三列布局
        DirectorUIBuilder.build_left_workflow_panel(director_frame, self)
        DirectorUIBuilder.build_center_content_panel(director_frame, self)
        DirectorUIBuilder.build_right_settings_panel(director_frame, self)
        
        # 绑定标签页切换事件，当切换到导演页面时重新加载数据
        def on_tab_changed(event):
            try:
                current_tab = self.notebook.index(self.notebook.select())
                # 找到导演标签页的索引
                for i in range(self.notebook.index("end")):
                    if "导演" in self.notebook.tab(i, "text"):
                        if current_tab == i:
                            # 切换到导演页面，重新加载数据
                            logger.info("切换到导演页面，重新加载数据")
                            self.after(50, self._load_director_data_from_project)
                        break
            except Exception as e:
                logger.error(f"标签页切换事件处理失败: {e}")
        
        # 绑定事件（只绑定一次）
        if not hasattr(self, '_director_tab_bound'):
            self.notebook.bind("<<NotebookTabChanged>>", on_tab_changed)
            self._director_tab_bound = True
        
        # 加载项目数据（如果有当前项目）
        self.after(100, self._load_director_data_from_project)

    def _on_generate_shots(self) -> None:
        """生成分镜 - 从剧本转换为分镜列表（别名方法）"""
        print("[DEBUG] ========== _on_generate_shots 被调用 ==========")
        print(f"[DEBUG] self 类型: {type(self)}")
        print(f"[DEBUG] 是否有 _on_script_to_shots: {hasattr(self, '_on_script_to_shots')}")
        
        try:
            self._on_script_to_shots()
        except Exception as e:
            print(f"[ERROR] _on_generate_shots 调用失败: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("错误", f"生成分镜失败:\n{str(e)}")
    
    def _refresh_shot_combo(self, silent=False) -> None:
        """刷新分镜下拉框

        Args:
                silent: 是否静默刷新（不显示提示框）
        """
        logger.info(f"========== _refresh_shot_combo 被调用，silent={silent} ==========")

        if not hasattr(self, 'shot_select_combo'):
            logger.error("未找到分镜选择下拉框 shot_select_combo")
            return

        if not hasattr(self, 'current_shots'):
            logger.error("未找到 current_shots 属性")
            self.shot_select_combo['values'] = ["全部分镜"]
            self.shot_select_combo.current(0)
            return
            
        if not self.current_shots:
            # 没有分镜时，只显示默认选项
            logger.warning("current_shots 为空")
            self.shot_select_combo['values'] = ["全部分镜"]
            self.shot_select_combo.current(0)
            if not silent:
                messagebox.showinfo("提示", "还没有生成分镜")
            return

        logger.info(f"当前分镜数量: {len(self.current_shots)}")
        logger.info(f"第一个分镜类型: {type(self.current_shots[0]) if self.current_shots else 'N/A'}")
        
        # 生成简洁的选项列表
        shot_options = ["全部分镜"]
        for i, s in enumerate(self.current_shots):
            if isinstance(s, dict):
                shot_num = s.get('shot_number', i + 1)
                shot_options.append(f"分镜{shot_num}")
            else:
                logger.warning(f"分镜 {i} 不是字典类型: {type(s)}")

        logger.info(f"生成的选项列表: {shot_options}")

        # 设置新的选项列表
        try:
            # 保存当前状态
            original_state = self.shot_select_combo['state']
            
            # 方法1：临时改变状态来触发刷新
            self.shot_select_combo.configure(state='normal')
            self.shot_select_combo.configure(values=tuple(shot_options))
            self.shot_select_combo.configure(state=original_state)
            logger.info(f"✅ 方法1: 通过状态切换设置values")
            
            # 设置当前选中项
            self.shot_select_combo.current(0)
            logger.info(f"✅ 已设置选中项为: {self.shot_select_combo.get()}")
            
            # 方法2：强制刷新UI
            self.shot_select_combo.update()
            self.shot_select_combo.update_idletasks()
            
            # 方法3：刷新父容器
            if self.shot_select_combo.master:
                self.shot_select_combo.master.update_idletasks()
            
            # 方法4：使用 after 延迟再次刷新
            def double_check_refresh():
                try:
                    current_values = self.shot_select_combo['values']
                    logger.info(f"🔍 延迟检查：下拉框values = {current_values}")
                    logger.info(f"🔍 延迟检查：当前显示 = {self.shot_select_combo.get()}")
                    
                    # 如果还是不对，再次强制设置
                    if len(current_values) <= 1:
                        logger.warning("⚠️ 下拉框values还是为空，强制重设")
                        self.shot_select_combo.configure(state='normal')
                        self.shot_select_combo.configure(values=tuple(shot_options))
                        self.shot_select_combo.configure(state=original_state)
                        self.shot_select_combo.current(0)
                        self.shot_select_combo.update_idletasks()
                    
                    logger.info("✅ 延迟刷新完成")
                except Exception as e:
                    logger.error(f"延迟刷新失败: {e}")
            
            self.after(100, double_check_refresh)
            
            # 立即验证设置是否成功
            current_values = self.shot_select_combo['values']
            logger.info(f"验证：下拉框当前values = {current_values}")
            
        except Exception as e:
            logger.error(f"设置下拉框失败: {e}")
            import traceback
            traceback.print_exc()

        logger.info(f"✅ 刷新下拉框成功，共 {len(shot_options) - 1} 个分镜选项")

        if not silent:
            messagebox.showinfo("成功", f"已刷新！共 {len(shot_options) - 1} 个分镜")

    def _generate_jimeng_prompts_for_all_shots(self, shots=None) -> None:
        """为所有分镜生成即梦AI视频提示词（智能版）"""
        JimengHandler.generate_prompts_for_all_shots(self, shots)

    def _extract_all_jimeng_prompts(self, show_message=True) -> None:
        """提取所有分镜的即梦AI提示词（兼容旧方法）"""
        JimengHandler.extract_all_prompts(self, show_message)

    def _copy_all_jimeng_prompts(self) -> None:
        """复制所有即梦AI提示词"""
        JimengHandler.copy_all_prompts(self)

    def _auto_save_script_to_project(self, script_text: str) -> None:
        """自动保存剧本到项目"""
        ProjectHandler.auto_save_script_to_project(self, script_text)

    def _auto_save_shots_to_project(self) -> None:
        """自动保存分镜到项目"""
        ProjectHandler.auto_save_shots_to_project(self)

    def _load_director_data_from_project(self) -> None:
        """从项目加载导演数据（剧本和分镜）"""
        ProjectHandler.load_director_data_from_project(self)

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
            logger.error(f"跳转失败: {e}", exc_info=True)

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
        ImageGenerationHandler.handle_generate_selected_shot(self)

    def _on_delete_shot_images(self) -> None:
        """删除选中分镜的图片"""
        ImageGenerationHandler.handle_delete_shot_images(self)

    def _generate_single_shot(self, shot_num: int) -> None:
        """生成单个分镜的图片 - 带进度条和取消功能"""
        ImageGenerationHandler._generate_single_shot(self, shot_num)

    def _on_manage_images(self) -> None:
        """管理已生成的图片"""
        ImageGenerationHandler.handle_open_image_manager(self)

    def _open_image_manager_dialog(self, shots_dir: str) -> None:
        """打开图片管理对话框"""
        ImageGenerationHandler._open_image_manager_dialog(self, shots_dir)

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
                logger.debug(f"全部分镜生成，每个分镜 {num_images_per_shot} 张图片")

                total_images = len(self.current_shots) * num_images_per_shot
                current_image = 0

                for i, shot in enumerate(self.current_shots, 1):
                    # 跳过非字典元素
                    if not isinstance(shot, dict):
                        logger.warning(f"跳过非字典格式的分镜 {i}: {type(shot)}")
                        continue
                    
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
                                    logger.info(
                                        f"✅ 生成分镜 {i} 变体 {
                                            j +
                                            1}: {
                                            os.path.basename(image_path)}")
                                else:
                                    logger.warning(f"⚠️  生成分镜 {i} 变体 {j + 1} 失败")
                            except Exception as e:
                                logger.error(f"❌ 生成分镜 {i} 变体 {j + 1} 失败: {str(e)}", exc_info=True)

                        if shot_images:
                            generated_count += 1
                            logger.info(f"✅ 分镜 {i} 完成，共生成 {len(shot_images)} 张图片")
                        else:
                            failed_shots.append(i)
                            logger.error(f"❌ 分镜 {i} 所有变体都失败")

                    except Exception as e:
                        failed_shots.append(i)
                        logger.error(f"生成分镜 {i} 失败: {str(e)}", exc_info=True)
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
        ProjectHandler.handle_save_director_project(self)

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
            consistency_data = getattr(self, 'consistency_data', None)
            return SDPromptBuilder.build_optimized_prompt(shot, shot_num, consistency_data)
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
        """为SD构建优化的英文提示词，确保人物和场景一致性
        
        注意：此方法已重构到SDPromptBuilder类中，保留此方法仅用于向后兼容
        """
        consistency_data = getattr(self, 'consistency_data', None)
        return SDPromptBuilder.build_optimized_prompt(shot, shot_num, consistency_data)

    def _build_sd_negative_prompt(self, shot: dict) -> str:
        """构建SD负面提示词 - 加强人物一致性约束"""
        return SDPromptBuilder.build_negative_prompt(shot)

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
            logger.info(f"\n=== 生成分镜 {shot_num} 变体 {shot_variant} ===")
            
            # 验证API配置
            if not hasattr(self, 'img_api_preset') or not hasattr(self, 'img_api_presets'):
                raise Exception("请先在图片生成页面配置API")
                
            preset_name = self.img_api_preset.get()
            if preset_name not in self.img_api_presets:
                raise Exception(f"未找到预设配置：{preset_name}")
                
            api_config = self.img_api_presets[preset_name]
            provider = api_config.get("provider", "openai")
            logger.debug(f"📌 API提供商: {provider}")

            # 获取当前分镜
            current_shot = None
            if hasattr(self, 'current_shots') and shot_num <= len(self.current_shots):
                shot = self.current_shots[shot_num - 1]
                if isinstance(shot, dict):
                    current_shot = shot
                else:
                    logger.warning(f"分镜 {shot_num} 不是字典格式: {type(shot)}")

            # 优先使用SD一致性生成器
            if provider == "sd" and current_shot and hasattr(self, 'consistency_data') and self.consistency_data:
                logger.debug("使用SD一致性生成器...")
                image_path = self._generate_shot_with_sd_consistency(
                    current_shot, shot_num, output_dir, shot_variant
                )
                if image_path:
                    return image_path

            # 使用 ImageGeneratorService
            from src.services.director.image_generator_service import ImageGeneratorService
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
            logger.error(f"生成图片失败: {str(e)}", exc_info=True)
            return None
