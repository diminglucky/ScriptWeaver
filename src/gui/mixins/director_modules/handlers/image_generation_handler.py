"""
图片生成事件处理器 - 从director_mixin.py重构出来
负责处理图片生成相关的事件
"""
import os
import threading
from pathlib import Path
from typing import Optional
from tkinter import messagebox
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk

from src.core.logging_config import get_logger

logger = get_logger(__name__)


class ImageGenerationHandler:
    """图片生成事件处理器"""
    
    @staticmethod
    def handle_generate_selected_shot(mixin_instance) -> None:
        """处理生成选中分镜图片的事件"""
        print("[DEBUG] ========== handle_generate_selected_shot 被调用 ==========")
        print(f"[DEBUG] hasattr current_shots: {hasattr(mixin_instance, 'current_shots')}")
        
        if hasattr(mixin_instance, 'current_shots'):
            print(f"[DEBUG] current_shots 数量: {len(mixin_instance.current_shots) if mixin_instance.current_shots else 0}")
        
        if not hasattr(mixin_instance, 'current_shots') or not mixin_instance.current_shots:
            messagebox.showwarning("提示", "请先生成分镜")
            return
        
        selection = mixin_instance.shot_select_var.get()
        print(f"[DEBUG] 选中的分镜: {selection}")
        
        if selection == "全部分镜":
            ImageGenerationHandler._generate_all_shots(mixin_instance)
        else:
            # 提取分镜编号
            try:
                shot_num = int(selection.replace("分镜", ""))
                print(f"[DEBUG] 准备生成分镜 {shot_num}")
                ImageGenerationHandler._generate_single_shot(mixin_instance, shot_num)
            except ValueError as e:
                print(f"[ERROR] 解析分镜编号失败: {e}")
                messagebox.showerror("错误", "无法解析分镜编号")
    
    @staticmethod
    def _generate_all_shots(mixin_instance) -> None:
        """生成所有分镜的图片"""
        if not hasattr(mixin_instance, 'current_shots') or not mixin_instance.current_shots:
            return
        
        total_shots = len(mixin_instance.current_shots)
        images_per_shot = getattr(mixin_instance, 'images_per_shot_var', tk.IntVar(value=1)).get()
        
        if messagebox.askyesno(
            "确认",
            f"将为 {total_shots} 个分镜各生成 {images_per_shot} 张图片，共 {total_shots * images_per_shot} 张。\n\n确定继续吗？"
        ):
            mixin_instance.status.set(f"开始生成 {total_shots} 个分镜的图片...")
            # 更新右上角状态
            if hasattr(mixin_instance, 'update_header_status'):
                mixin_instance.update_header_status(f"开始生成 {total_shots} 个分镜的图片...", "🎨")
            
            def generate_task():
                try:
                    success_count = 0
                    fail_count = 0
                    
                    for shot_idx, shot_num in enumerate(range(1, total_shots + 1), 1):
                        def update_status(idx=shot_idx, s=shot_num):
                            status_text = f"正在生成分镜 {idx}/{total_shots}..."
                            mixin_instance.status.set(status_text)
                            if hasattr(mixin_instance, 'update_header_status'):
                                mixin_instance.update_header_status(status_text, "🎨")
                        mixin_instance.after(0, update_status)
                        
                        # 获取输出目录
                        if hasattr(mixin_instance.current_project, 'project_dir'):
                            project_path = str(mixin_instance.current_project.project_dir)
                        elif isinstance(mixin_instance.current_project, dict):
                            project_path = mixin_instance.current_project.get('path', '')
                        else:
                            project_path = str(mixin_instance.current_project)
                        
                        shots_dir = Path(project_path) / "director" / "shots"
                        shots_dir.mkdir(parents=True, exist_ok=True)
                        
                        # 获取分镜信息
                        shot = mixin_instance.current_shots[shot_num - 1]
                        
                        # 生成多个变体
                        shot_success = False
                        for variant in range(1, images_per_shot + 1):
                            try:
                                image_path = mixin_instance._generate_single_shot_image(
                                    shot_num=shot_num,
                                    description=shot.get('visual_description', ''),
                                    output_dir=str(shots_dir),
                                    shot_variant=variant,
                                    seed_offset=(variant - 1) * 1000
                                )
                                
                                if image_path:
                                    shot_success = True
                                    logger.info(f"✅ 分镜 {shot_num} 变体 {variant} 生成成功")
                                else:
                                    logger.warning(f"⚠️ 分镜 {shot_num} 变体 {variant} 生成失败")
                            except Exception as e:
                                logger.error(f"❌ 分镜 {shot_num} 变体 {variant} 生成异常: {e}")
                        
                        if shot_success:
                            success_count += 1
                        else:
                            fail_count += 1
                    
                    # 刷新UI
                    def final_refresh():
                        mixin_instance.status.set("所有分镜图片生成完成！")
                        # 更新右上角状态
                        if hasattr(mixin_instance, 'update_header_status'):
                            mixin_instance.update_header_status(f"所有分镜图片生成完成！成功: {success_count}, 失败: {fail_count}", "✅")
                        ImageGenerationHandler._refresh_preview_images(mixin_instance)
                        if hasattr(mixin_instance, '_refresh_preview_shot_combo'):
                            mixin_instance._refresh_preview_shot_combo()
                        messagebox.showinfo(
                            "完成", 
                            f"已为 {total_shots} 个分镜生成图片\n✅ 成功: {success_count}\n❌ 失败: {fail_count}"
                        )
                    
                    mixin_instance.after(0, final_refresh)
                    
                except Exception as e:
                    logger.error(f"批量生成图片失败: {e}", exc_info=True)
                    def handle_error():
                        mixin_instance.status.set("生成失败")
                        if hasattr(mixin_instance, 'update_header_status'):
                            mixin_instance.update_header_status("生成失败", "❌")
                        messagebox.showerror("错误", f"生成图片时发生错误: {str(e)}")
                    mixin_instance.after(0, handle_error)
            
            threading.Thread(target=generate_task, daemon=True).start()
    
    @staticmethod
    def _generate_single_shot(mixin_instance, shot_num: int) -> None:
        """生成单个分镜的图片"""
        print(f"[DEBUG] _generate_single_shot 被调用: shot_num={shot_num}")
        
        if not hasattr(mixin_instance, 'current_shots') or shot_num > len(mixin_instance.current_shots):
            messagebox.showwarning("提示", f"分镜 {shot_num} 不存在")
            return
        
        shot = mixin_instance.current_shots[shot_num - 1]
        print(f"[DEBUG] 分镜数据类型: {type(shot)}")
        
        if not isinstance(shot, dict):
            logger.error(f"分镜 {shot_num} 不是字典格式: {type(shot)}")
            messagebox.showerror("错误", f"分镜 {shot_num} 数据格式不正确")
            return
        
        # 获取输出目录
        if not hasattr(mixin_instance, 'current_project') or not mixin_instance.current_project:
            messagebox.showwarning("提示", "请先打开一个项目")
            return
        
        project_dir = Path(mixin_instance.current_project.project_dir)
        shots_dir = project_dir / "director" / "shots"
        shots_dir.mkdir(parents=True, exist_ok=True)
        print(f"[DEBUG] 输出目录: {shots_dir}")
        
        mixin_instance.status.set(f"正在生成分镜 {shot_num} 的图片...")
        # 更新右上角状态
        if hasattr(mixin_instance, 'update_header_status'):
            mixin_instance.update_header_status(f"正在生成分镜 {shot_num} 的图片...", "🎨")
        
        def generate_task():
            try:
                # ★★★ 在函数内部获取每个分镜生成的图片数量 ★★★
                images_per_shot = 1  # 默认值
                if hasattr(mixin_instance, 'images_per_shot_var'):
                    try:
                        images_per_shot = mixin_instance.images_per_shot_var.get()
                    except:
                        images_per_shot = 1
                print(f"[DEBUG] 每个分镜生成图片数: {images_per_shot}")
                
                for variant in range(1, images_per_shot + 1):
                    def update_variant_status(v=variant):
                        status_text = f"正在生成分镜 {shot_num} 第 {v}/{images_per_shot} 张..."
                        mixin_instance.status.set(status_text)
                        if hasattr(mixin_instance, 'update_header_status'):
                            mixin_instance.update_header_status(status_text, "🎨")
                    mixin_instance.after(0, update_variant_status)
                    
                    print(f"[DEBUG] 准备调用 _generate_single_shot_image: shot_num={shot_num}, variant={variant}")
                    print(f"[DEBUG] hasattr _generate_single_shot_image: {hasattr(mixin_instance, '_generate_single_shot_image')}")
                    
                    if not hasattr(mixin_instance, '_generate_single_shot_image'):
                        error_msg = "错误：未找到 _generate_single_shot_image 方法"
                        print(f"[ERROR] {error_msg}")
                        mixin_instance.after(0, lambda: messagebox.showerror("错误", error_msg))
                        return
                    
                    image_path = mixin_instance._generate_single_shot_image(
                        shot_num=shot_num,
                        description=shot.get('visual_description', ''),
                        output_dir=str(shots_dir),
                        shot_variant=variant,
                        seed_offset=(variant - 1) * 1000
                    )
                    
                    if image_path:
                        logger.info(f"分镜 {shot_num} 变体 {variant} 生成成功: {image_path}")
                        print(f"[DEBUG] 图片生成成功: {image_path}")
                    else:
                        print(f"[WARNING] 分镜 {shot_num} 变体 {variant} 生成失败")
                
                # 刷新UI显示
                def refresh_ui():
                    mixin_instance.status.set(f"分镜 {shot_num} 图片生成完成")
                    # 更新右上角状态
                    if hasattr(mixin_instance, 'update_header_status'):
                        mixin_instance.update_header_status(f"分镜 {shot_num} 图片生成完成", "✅")
                    ImageGenerationHandler._refresh_preview_images(mixin_instance)
                    # 刷新预览下拉框
                    if hasattr(mixin_instance, '_refresh_preview_shot_combo'):
                        mixin_instance._refresh_preview_shot_combo()
                
                mixin_instance.after(0, refresh_ui)
            except Exception as e:
                logger.error(f"生成分镜 {shot_num} 图片失败: {e}", exc_info=True)
                def handle_single_error():
                    mixin_instance.status.set("生成失败")
                    if hasattr(mixin_instance, 'update_header_status'):
                        mixin_instance.update_header_status(f"分镜 {shot_num} 生成失败", "❌")
                    messagebox.showerror("错误", f"生成图片时发生错误: {str(e)}")
                mixin_instance.after(0, handle_single_error)
        
        threading.Thread(target=generate_task, daemon=True).start()
    
    @staticmethod
    def handle_delete_shot_images(mixin_instance) -> None:
        """处理删除分镜图片的事件"""
        if not hasattr(mixin_instance, 'current_project') or not mixin_instance.current_project:
            messagebox.showwarning("提示", "请先打开一个项目")
            return
        
        project_dir = Path(mixin_instance.current_project.project_dir)
        shots_dir = project_dir / "director" / "shots"
        
        if not shots_dir.exists():
            messagebox.showinfo("提示", "没有找到图片目录")
            return
        
        image_files = [f for f in os.listdir(shots_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        if not image_files:
            messagebox.showinfo("提示", "没有找到图片文件")
            return
        
        if messagebox.askyesno("确认", f"确定要删除 {len(image_files)} 张图片吗？"):
            try:
                for img_file in image_files:
                    os.remove(shots_dir / img_file)
                logger.info(f"已删除 {len(image_files)} 张图片")
                messagebox.showinfo("成功", f"已删除 {len(image_files)} 张图片")
                ImageGenerationHandler._refresh_preview_images(mixin_instance)
            except Exception as e:
                logger.error(f"删除图片失败: {e}", exc_info=True)
                messagebox.showerror("错误", f"删除图片时发生错误: {str(e)}")
    
    @staticmethod
    def handle_open_image_manager(mixin_instance) -> None:
        """处理打开图片管理器的事件"""
        if not hasattr(mixin_instance, 'current_project') or not mixin_instance.current_project:
            messagebox.showwarning("提示", "请先打开一个项目")
            return
        
        project_dir = Path(mixin_instance.current_project.project_dir)
        shots_dir = project_dir / "director" / "shots"
        
        if not shots_dir.exists():
            messagebox.showinfo("提示", "没有找到图片目录")
            return
        
        ImageGenerationHandler._open_image_manager_dialog(mixin_instance, str(shots_dir))
    
    @staticmethod
    def _open_image_manager_dialog(mixin_instance, shots_dir: str) -> None:
        """打开图片管理对话框"""
        image_files = sorted([
            f for f in os.listdir(shots_dir)
            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
        ])
        
        if not image_files:
            messagebox.showinfo("提示", "没有找到图片文件")
            return
        
        dialog = tk.Toplevel(mixin_instance)
        dialog.title("图片管理器")
        dialog.geometry("900x700")
        
        # 创建滚动区域
        canvas = tk.Canvas(dialog)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
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
            except Exception:
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
        
        ttk.Label(btn_frame, text=f"共 {len(image_files)} 张图片").pack(side="left")
        
        def delete_unselected():
            to_delete = [
                f for f, var in selected_images.items() if not var.get()
            ]
            if not to_delete:
                messagebox.showinfo("提示", "没有要删除的图片")
                return
            
            if messagebox.askyesno("确认", f"确定要删除 {len(to_delete)} 张图片吗？"):
                for f in to_delete:
                    try:
                        os.remove(os.path.join(shots_dir, f))
                        logger.info(f"删除图片: {f}")
                    except Exception as e:
                        logger.error(f"删除失败 {f}: {e}")
                
                messagebox.showinfo("完成", f"已删除 {len(to_delete)} 张图片")
                dialog.destroy()
                ImageGenerationHandler._refresh_preview_images(mixin_instance)
        
        ttk.Button(
            btn_frame,
            text="🗑️  删除未选中",
            command=delete_unselected
        ).pack(side="right", padx=5)
        
        ttk.Button(
            btn_frame,
            text="✅ 全选",
            command=lambda: [v.set(True) for v in selected_images.values()]
        ).pack(side="right", padx=5)
        
        ttk.Button(
            btn_frame,
            text="❌ 全不选",
            command=lambda: [v.set(False) for v in selected_images.values()]
        ).pack(side="right", padx=5)
    
    @staticmethod
    def _refresh_preview_images(mixin_instance) -> None:
        """刷新图片预览"""
        if hasattr(mixin_instance, '_refresh_preview_images'):
            mixin_instance._refresh_preview_images()

