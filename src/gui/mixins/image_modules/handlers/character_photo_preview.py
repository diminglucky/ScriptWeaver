"""
人物照片预览管理器 - 从char_photo.py重构出来
负责人物照片的预览和显示逻辑
"""
from typing import Optional, Union
from pathlib import Path
from PIL import Image, ImageTk
import tkinter as tk

from src.core.logging_config import get_logger

logger = get_logger(__name__)


class CharacterPhotoPreview:
    """人物照片预览管理器 - 负责人物照片的预览和显示逻辑"""
    
    @staticmethod
    def update_preview(mixin_instance, img: Image.Image) -> None:
        """
        更新人物照片预览
        
        Args:
            mixin_instance: CharacterPhotoMixin实例
            img: 图片对象
        """
        try:
            canvas_width = mixin_instance.char_canvas.winfo_width()
            canvas_height = mixin_instance.char_canvas.winfo_height()
            
            # 如果Canvas还没有初始化大小，使用默认值
            if canvas_width <= 1:
                canvas_width = 400
            if canvas_height <= 1:
                canvas_height = 400
            
            img_width, img_height = img.size
            
            # 计算缩放比例
            width_ratio = canvas_width / img_width
            height_ratio = canvas_height / img_height
            scale_ratio = min(width_ratio, height_ratio, 1.0)
            
            new_w = int(img_width * scale_ratio)
            new_h = int(img_height * scale_ratio)
            
            # 缩放图片
            resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # 转换为PhotoImage
            mixin_instance.character_preview_photo = ImageTk.PhotoImage(resized_img)
            
            # 更新Label
            mixin_instance.char_preview.configure(image=mixin_instance.character_preview_photo, text="")
            
            # 更新Canvas的滚动区域
            scroll_width = max(new_w, canvas_width)
            scroll_height = max(new_h, canvas_height)
            mixin_instance.char_canvas.configure(scrollregion=(0, 0, scroll_width, scroll_height))
            
            # 居中显示
            if new_w < canvas_width:
                x_offset = (canvas_width - new_w) // 2
            else:
                x_offset = 0
            
            if new_h < canvas_height:
                y_offset = (canvas_height - new_h) // 2
            else:
                y_offset = 0
            
            mixin_instance.char_canvas.coords(mixin_instance.char_canvas_window, x_offset, y_offset)
            
        except Exception as e:
            logger.error(f"更新预览失败: {e}", exc_info=True)
    
    @staticmethod
    def show_fullsize(mixin_instance, img_path: Union[str, Path]) -> None:
        """
        显示完整尺寸图片
        
        Args:
            mixin_instance: CharacterPhotoMixin实例
            img_path: 图片路径（可以是字符串或Path对象）
        """
        try:
            # 确保转换为Path对象
            from pathlib import Path as PathLib
            
            if isinstance(img_path, str):
                img_path_obj = PathLib(img_path)
            elif isinstance(img_path, PathLib):
                img_path_obj = img_path
            else:
                img_path_obj = PathLib(str(img_path))
            
            # 处理相对路径：如果是相对路径，转换为绝对路径（相对于项目目录）
            if not img_path_obj.is_absolute():
                if hasattr(mixin_instance, 'current_project') and mixin_instance.current_project:
                    # 检查路径是否已经包含项目目录路径（避免重复拼接）
                    img_path_str = str(img_path_obj).replace("\\", "/")
                    project_dir_str = str(mixin_instance.current_project.project_dir).replace("\\", "/")
                    
                    # 如果路径已经以项目目录开头，直接使用
                    if img_path_str.startswith(project_dir_str):
                        img_path_obj = Path(img_path_str)
                        logger.debug(f"路径已包含项目目录，直接使用：{img_path_obj}")
                    else:
                        # 否则拼接项目目录
                        img_path_obj = mixin_instance.current_project.project_dir / img_path_obj
                        logger.debug(f"相对路径转换为绝对路径：{img_path} -> {img_path_obj}")
                else:
                    logger.warning(f"无法处理相对路径，没有当前项目：{img_path}")
            
            # 检查文件是否存在
            if not img_path_obj.exists():
                logger.error(f"图片文件不存在: {img_path_obj}")
                import tkinter.messagebox as messagebox
                messagebox.showerror("错误", f"图片文件不存在：\n{img_path_obj}")
                return
            
            # 创建新窗口
            fullsize_window = tk.Toplevel(mixin_instance)
            fullsize_window.title(f"完整尺寸预览 - {img_path_obj.name}")
            fullsize_window.configure(bg="#000000")
            
            # 加载图片
            img = Image.open(img_path_obj)
            img_width, img_height = img.size
            
            # 获取屏幕尺寸（使用窗口的父窗口来获取屏幕尺寸）
            try:
                screen_width = mixin_instance.winfo_screenwidth()
                screen_height = mixin_instance.winfo_screenheight()
            except:
                screen_width = 1920
                screen_height = 1080
            
            # 限制最大尺寸（适应屏幕，留出边距）
            max_width = screen_width * 0.9
            max_height = screen_height * 0.85  # 留出更多空间给标题栏
            
            # 判断是否需要缩放
            needs_scaling = img_width > max_width or img_height > max_height
            
            if needs_scaling:
                scale_ratio = min(max_width / img_width, max_height / img_height)
                display_width = int(img_width * scale_ratio)
                display_height = int(img_height * scale_ratio)
                display_img = img.resize((display_width, display_height), Image.Resampling.LANCZOS)
            else:
                display_width = img_width
                display_height = img_height
                display_img = img
            
            # 转换为PhotoImage
            photo = ImageTk.PhotoImage(display_img)
            
            # 创建主容器
            main_frame = tk.Frame(fullsize_window, bg="#000000")
            main_frame.pack(fill="both", expand=True)
            
            # 创建Canvas用于显示图片（支持滚动）
            canvas = tk.Canvas(
                main_frame, 
                bg="#000000",
                highlightthickness=0,
                width=int(max_width),
                height=int(max_height)
            )
            
            # 判断是否需要滚动条（如果原始图片大于显示区域）
            needs_scroll = img_width > max_width or img_height > max_height
            
            if needs_scroll:
                # 需要滚动条：显示原始尺寸图片
                original_photo = ImageTk.PhotoImage(img)
                canvas.image = original_photo  # 保持引用
                
                # 创建滚动条
                v_scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
                h_scrollbar = tk.Scrollbar(main_frame, orient="horizontal", command=canvas.xview)
                
                canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
                
                # 使用grid布局以支持滚动条
                canvas.grid(row=0, column=0, sticky="nsew")
                v_scrollbar.grid(row=0, column=1, sticky="ns")
                h_scrollbar.grid(row=1, column=0, sticky="ew")
                
                main_frame.grid_rowconfigure(0, weight=1)
                main_frame.grid_columnconfigure(0, weight=1)
                
                # 在Canvas上显示原始尺寸图片
                canvas.create_image(0, 0, anchor="nw", image=original_photo)
                
                # 设置滚动区域为图片的实际大小
                canvas.configure(scrollregion=(0, 0, img_width, img_height))
                
                # 绑定鼠标滚轮事件到canvas（支持垂直滚动）
                def on_canvas_mousewheel(event):
                    """Canvas上的鼠标滚轮事件"""
                    try:
                        # Windows和Mac的滚轮事件
                        if event.delta:
                            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                        # Linux的滚轮事件
                        elif event.num == 4:
                            canvas.yview_scroll(-1, "units")
                        elif event.num == 5:
                            canvas.yview_scroll(1, "units")
                    except Exception as e:
                        logger.debug(f"鼠标滚轮事件处理出错: {e}")
                
                # 绑定到canvas和窗口（确保在任何位置都能滚动）
                canvas.bind("<MouseWheel>", on_canvas_mousewheel)
                canvas.bind("<Button-4>", on_canvas_mousewheel)  # Linux向上滚动
                canvas.bind("<Button-5>", on_canvas_mousewheel)  # Linux向下滚动
                
                # 同时绑定到窗口（作为备用，确保鼠标在窗口任何位置都能滚动）
                fullsize_window.bind("<MouseWheel>", on_canvas_mousewheel)
                fullsize_window.bind("<Button-4>", on_canvas_mousewheel)  # Linux向上滚动
                fullsize_window.bind("<Button-5>", on_canvas_mousewheel)  # Linux向下滚动
                
                # 确保canvas能够获得焦点（这样鼠标滚轮事件才能正常工作）
                canvas.focus_set()
                
                # 窗口大小设置为显示区域
                window_width = int(min(max_width + 20, screen_width))
                window_height = int(min(max_height + 40, screen_height))
            else:
                # 不需要滚动条：直接显示
                canvas.image = photo  # 保持引用
                canvas.pack(fill="both", expand=True)
                
                # 在Canvas上显示图片
                canvas.create_image(0, 0, anchor="nw", image=photo)
                
                # 设置Canvas大小
                canvas.configure(width=display_width, height=display_height)
                
                # 设置滚动区域
                canvas.configure(scrollregion=(0, 0, display_width, display_height))
                
                # 窗口大小设置为图片大小
                window_width = display_width
                window_height = display_height
            
            # 设置窗口大小
            fullsize_window.geometry(f"{int(window_width)}x{int(window_height)}")
            
            # 居中窗口
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            fullsize_window.geometry(f"{int(window_width)}x{int(window_height)}+{int(x)}+{int(y)}")
            
            # 绑定ESC键关闭
            fullsize_window.bind("<Escape>", lambda e: fullsize_window.destroy())
            fullsize_window.focus_set()
            
            # 清理函数：窗口关闭时解绑事件
            def on_close():
                try:
                    if needs_scroll:
                        canvas.unbind("<MouseWheel>")
                        canvas.unbind("<Button-4>")
                        canvas.unbind("<Button-5>")
                        fullsize_window.unbind("<MouseWheel>")
                        fullsize_window.unbind("<Button-4>")
                        fullsize_window.unbind("<Button-5>")
                except:
                    pass
                fullsize_window.destroy()
            
            fullsize_window.protocol("WM_DELETE_WINDOW", on_close)
            
        except Exception as e:
            logger.error(f"显示完整尺寸图片失败: {e}", exc_info=True)
            import tkinter.messagebox as messagebox
            import traceback
            messagebox.showerror("错误", f"显示图片失败：\n{str(e)}\n\n{traceback.format_exc()}")

