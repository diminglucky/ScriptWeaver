"""
分镜头可视化查看器 - 提供友好的分镜头展示界面
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText


class ShotViewerMixin:
    """分镜头可视化查看器"""
    
    def open_shot_viewer(self) -> None:
        """打开分镜头查看器窗口"""
        if not hasattr(self, 'current_shots') or not self.current_shots:
            messagebox.showwarning("提示", "请先生成分镜头")
            return
        
        # 创建新窗口
        viewer = tk.Toplevel(self)
        viewer.title(f"🎬 分镜头预览 - 共 {len(self.current_shots)} 个镜头")
        viewer.geometry("1200x800")
        viewer.transient(self)
        
        # 创建主容器
        main_frame = ttk.Frame(viewer)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 顶部工具栏
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill="x", pady=(0, 10))
        
        ttk.Label(
            toolbar, 
            text=f"共 {len(self.current_shots)} 个分镜头",
            font=("Microsoft YaHei", 12, "bold")
        ).pack(side="left", padx=5)
        
        # 视图切换按钮
        self._shot_view_mode = tk.StringVar(value="cards")
        ttk.Radiobutton(
            toolbar, 
            text="📇 卡片视图", 
            variable=self._shot_view_mode, 
            value="cards",
            command=lambda: self._switch_shot_view(content_frame, self._shot_view_mode.get())
        ).pack(side="left", padx=5)
        
        ttk.Radiobutton(
            toolbar, 
            text="📋 列表视图", 
            variable=self._shot_view_mode, 
            value="list",
            command=lambda: self._switch_shot_view(content_frame, self._shot_view_mode.get())
        ).pack(side="left", padx=5)
        
        ttk.Button(
            toolbar,
            text="💾 导出文本",
            command=lambda: self._export_shots_text()
        ).pack(side="right", padx=5)
        
        # 创建可滚动的内容区域
        canvas = tk.Canvas(main_frame, bg="#f5f5f5", highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        content_frame = ttk.Frame(canvas)
        
        content_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=content_frame, anchor="nw", width=1160)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 鼠标滚轮支持 - 直接绑定到canvas避免冲突
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # 绑定滚轮到canvas和content_frame
        canvas.bind("<MouseWheel>", _on_mousewheel)
        content_frame.bind("<MouseWheel>", _on_mousewheel)
        
        # 递归绑定所有子控件，确保无论鼠标在哪里都能滚动
        def bind_mousewheel_recursive(widget):
            try:
                widget.bind("<MouseWheel>", _on_mousewheel)
                for child in widget.winfo_children():
                    bind_mousewheel_recursive(child)
            except:
                pass
        
        # 延迟绑定，确保所有控件都已创建
        def bind_all_children():
            bind_mousewheel_recursive(content_frame)
        viewer.after(200, bind_all_children)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 显示分镜头（默认卡片视图）
        self._display_shots_cards(content_frame)
        
        # 窗口关闭时清理
        def on_close():
            viewer.destroy()
        
        viewer.protocol("WM_DELETE_WINDOW", on_close)
    
    def _switch_shot_view(self, content_frame: ttk.Frame, mode: str) -> None:
        """切换分镜头显示模式"""
        # 清空当前内容
        for widget in content_frame.winfo_children():
            widget.destroy()
        
        if mode == "cards":
            self._display_shots_cards(content_frame)
        else:
            self._display_shots_list(content_frame)
    
    def _display_shots_cards(self, parent: ttk.Frame) -> None:
        """以卡片形式显示分镜头"""
        for idx, shot in enumerate(self.current_shots):
            # 创建卡片框架
            card = ttk.LabelFrame(
                parent,
                text=f"🎬 镜头 {shot.get('shot_number', idx+1)} - {shot.get('shot_type', '未知类型')}",
                padding=15
            )
            card.pack(fill="x", padx=10, pady=10)
            
            # 使用网格布局
            row = 0
            
            # 场景信息
            scene_id = shot.get('scene_id', '')
            if scene_id:
                ttk.Label(
                    card,
                    text="📍 场景:",
                    font=("Microsoft YaHei", 10, "bold"),
                    foreground="#2c3e50"
                ).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=5)
                
                ttk.Label(
                    card,
                    text=scene_id,
                    font=("Microsoft YaHei", 10),
                    foreground="#34495e",
                    wraplength=900
                ).grid(row=row, column=1, sticky="w", pady=5)
                row += 1
            
            # 位置信息
            location = shot.get('location', '')
            if location:
                ttk.Label(
                    card,
                    text="📌 位置:",
                    font=("Microsoft YaHei", 10, "bold"),
                    foreground="#2c3e50"
                ).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=5)
                
                location_label = tk.Text(
                    card,
                    height=2,
                    width=100,
                    wrap="word",
                    font=("Microsoft YaHei", 10),
                    bg="#f8f9fa",
                    relief="flat",
                    borderwidth=0
                )
                location_label.insert("1.0", location)
                location_label.config(state="disabled")
                location_label.grid(row=row, column=1, sticky="w", pady=5)
                row += 1
            
            # 人物信息
            characters = shot.get('characters', [])
            if characters:
                ttk.Label(
                    card,
                    text="👥 人物:",
                    font=("Microsoft YaHei", 10, "bold"),
                    foreground="#2c3e50"
                ).grid(row=row, column=0, sticky="nw", padx=(0, 10), pady=5)
                
                chars_text = ', '.join(characters) if isinstance(characters, list) else str(characters)
                ttk.Label(
                    card,
                    text=chars_text,
                    font=("Microsoft YaHei", 10),
                    foreground="#e74c3c",
                    wraplength=900
                ).grid(row=row, column=1, sticky="w", pady=5)
                row += 1
            
            # 人物详细信息
            character_details = shot.get('character_details', {})
            if character_details and isinstance(character_details, dict):
                for char_name, details in character_details.items():
                    # 创建人物详情子框架
                    char_frame = ttk.LabelFrame(card, text=f"👤 {char_name}", padding=10)
                    char_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=5)
                    row += 1
                    
                    if isinstance(details, dict):
                        detail_text = ""
                        if details.get('appearance'):
                            detail_text += f"【外貌】{details['appearance']}\n"
                        if details.get('clothing'):
                            detail_text += f"【服装】{details['clothing']}\n"
                        if details.get('expression'):
                            detail_text += f"【表情】{details['expression']}\n"
                        if details.get('posture'):
                            detail_text += f"【姿势】{details['posture']}\n"
                        
                        detail_widget = tk.Text(
                            char_frame,
                            height=4,
                            width=110,
                            wrap="word",
                            font=("Microsoft YaHei", 9),
                            bg="#fff5e1",
                            relief="flat"
                        )
                        detail_widget.insert("1.0", detail_text.strip())
                        detail_widget.config(state="disabled")
                        detail_widget.pack(fill="x")
                    else:
                        detail_label = ttk.Label(
                            char_frame,
                            text=str(details),
                            font=("Microsoft YaHei", 9),
                            wraplength=1000
                        )
                        detail_label.pack(fill="x")
            
            # 视觉描述
            visual_desc = shot.get('visual_description', '')
            if visual_desc:
                ttk.Label(
                    card,
                    text="🎨 画面:",
                    font=("Microsoft YaHei", 10, "bold"),
                    foreground="#2c3e50"
                ).grid(row=row, column=0, sticky="nw", padx=(0, 10), pady=5)
                
                visual_text = tk.Text(
                    card,
                    height=6,
                    width=100,
                    wrap="word",
                    font=("Microsoft YaHei", 9),
                    bg="#e8f4f8",
                    relief="solid",
                    borderwidth=1
                )
                visual_text.insert("1.0", visual_desc)
                visual_text.config(state="disabled")
                visual_text.grid(row=row, column=1, sticky="w", pady=5)
                row += 1
            
            # 动作描述
            action = shot.get('action', '')
            if action:
                ttk.Label(
                    card,
                    text="🎭 动作:",
                    font=("Microsoft YaHei", 10, "bold"),
                    foreground="#2c3e50"
                ).grid(row=row, column=0, sticky="nw", padx=(0, 10), pady=5)
                
                action_text = tk.Text(
                    card,
                    height=5,
                    width=100,
                    wrap="word",
                    font=("Microsoft YaHei", 9),
                    bg="#fff3e0",
                    relief="solid",
                    borderwidth=1
                )
                action_text.insert("1.0", action)
                action_text.config(state="disabled")
                action_text.grid(row=row, column=1, sticky="w", pady=5)
                row += 1
            
            # 情绪
            emotion = shot.get('emotion', '')
            if emotion:
                ttk.Label(
                    card,
                    text="💭 情绪:",
                    font=("Microsoft YaHei", 10, "bold"),
                    foreground="#2c3e50"
                ).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=5)
                
                ttk.Label(
                    card,
                    text=emotion,
                    font=("Microsoft YaHei", 10),
                    foreground="#9b59b6",
                    wraplength=900
                ).grid(row=row, column=1, sticky="w", pady=5)
                row += 1
            
            # 光线和氛围
            lighting = shot.get('lighting', '')
            atmosphere = shot.get('atmosphere', '')
            if lighting or atmosphere:
                info_text = ""
                if lighting:
                    info_text += f"💡 光线: {lighting}"
                if atmosphere:
                    info_text += f"  |  🌟 氛围: {atmosphere}"
                
                ttk.Label(
                    card,
                    text=info_text,
                    font=("Microsoft YaHei", 9),
                    foreground="#7f8c8d",
                    wraplength=1000
                ).grid(row=row, column=0, columnspan=2, sticky="w", pady=5)
                row += 1
            
            # 摄影机信息
            camera = shot.get('camera', {})
            if camera and isinstance(camera, dict):
                camera_info = []
                if camera.get('movement'):
                    camera_info.append(f"运动: {camera['movement']}")
                if camera.get('angle'):
                    camera_info.append(f"角度: {camera['angle']}")
                if camera.get('lens'):
                    camera_info.append(f"镜头: {camera['lens']}")
                
                if camera_info:
                    ttk.Label(
                        card,
                        text="📷 " + " | ".join(camera_info),
                        font=("Microsoft YaHei", 9),
                        foreground="#16a085",
                        wraplength=1000
                    ).grid(row=row, column=0, columnspan=2, sticky="w", pady=5)
                    row += 1
            
            # 连贯性提示
            continuity = shot.get('continuity', '')
            if continuity:
                ttk.Label(
                    card,
                    text="🔗 连贯性:",
                    font=("Microsoft YaHei", 10, "bold"),
                    foreground="#2c3e50"
                ).grid(row=row, column=0, sticky="nw", padx=(0, 10), pady=5)
                
                continuity_label = tk.Text(
                    card,
                    height=2,
                    width=100,
                    wrap="word",
                    font=("Microsoft YaHei", 9),
                    bg="#f0f0f0",
                    relief="flat"
                )
                continuity_label.insert("1.0", continuity)
                continuity_label.config(state="disabled")
                continuity_label.grid(row=row, column=1, sticky="w", pady=5)
                row += 1
    
    def _display_shots_list(self, parent: ttk.Frame) -> None:
        """以列表形式显示分镜头（紧凑版）"""
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 创建文本框显示所有分镜
        text_widget = ScrolledText(
            list_frame,
            font=("Consolas", 10),
            wrap="word",
            bg="#ffffff"
        )
        text_widget.pack(fill="both", expand=True)
        
        for idx, shot in enumerate(self.current_shots):
            shot_num = shot.get('shot_number', idx+1)
            scene_id = shot.get('scene_id', '未知场景')
            shot_type = shot.get('shot_type', '未知类型')
            
            # 标题
            text_widget.insert("end", "="*100 + "\n", "separator")
            text_widget.insert("end", f"【镜头 {shot_num}】{scene_id} - {shot_type}\n", "title")
            text_widget.insert("end", "="*100 + "\n", "separator")
            
            # 位置
            location = shot.get('location', '')
            if location:
                text_widget.insert("end", f"📌 位置: {location}\n", "location")
            
            # 人物
            characters = shot.get('characters', [])
            if characters:
                chars_text = ', '.join(characters) if isinstance(characters, list) else str(characters)
                text_widget.insert("end", f"👥 人物: {chars_text}\n", "characters")
            
            # 人物详情
            character_details = shot.get('character_details', {})
            if character_details and isinstance(character_details, dict):
                for char_name, details in character_details.items():
                    text_widget.insert("end", f"\n👤 {char_name}:\n", "char_name")
                    if isinstance(details, dict):
                        if details.get('appearance'):
                            text_widget.insert("end", f"   【外貌】{details['appearance']}\n", "detail")
                        if details.get('clothing'):
                            text_widget.insert("end", f"   【服装】{details['clothing']}\n", "detail")
                        if details.get('expression'):
                            text_widget.insert("end", f"   【表情】{details['expression']}\n", "detail")
                        if details.get('posture'):
                            text_widget.insert("end", f"   【姿势】{details['posture']}\n", "detail")
            
            # 画面
            visual_desc = shot.get('visual_description', '')
            if visual_desc:
                text_widget.insert("end", f"\n🎨 画面描述:\n{visual_desc}\n", "visual")
            
            # 动作
            action = shot.get('action', '')
            if action:
                text_widget.insert("end", f"\n🎭 动作:\n{action}\n", "action")
            
            # 情绪
            emotion = shot.get('emotion', '')
            if emotion:
                text_widget.insert("end", f"\n💭 情绪: {emotion}\n", "emotion")
            
            # 光线和氛围
            lighting = shot.get('lighting', '')
            if lighting:
                text_widget.insert("end", f"💡 光线: {lighting}\n", "lighting")
            
            atmosphere = shot.get('atmosphere', '')
            if atmosphere:
                text_widget.insert("end", f"🌟 氛围: {atmosphere}\n", "atmosphere")
            
            # 摄影机
            camera = shot.get('camera', {})
            if camera and isinstance(camera, dict):
                text_widget.insert("end", f"\n📷 摄影机:\n", "camera")
                if camera.get('movement'):
                    text_widget.insert("end", f"   运动: {camera['movement']}\n", "camera")
                if camera.get('angle'):
                    text_widget.insert("end", f"   角度: {camera['angle']}\n", "camera")
                if camera.get('lens'):
                    text_widget.insert("end", f"   镜头: {camera['lens']}\n", "camera")
            
            # 连贯性
            continuity = shot.get('continuity', '')
            if continuity:
                text_widget.insert("end", f"\n🔗 连贯性: {continuity}\n", "continuity")
            
            text_widget.insert("end", "\n\n")
        
        # 配置文本样式
        text_widget.tag_config("title", font=("Microsoft YaHei", 12, "bold"), foreground="#2c3e50")
        text_widget.tag_config("separator", foreground="#95a5a6")
        text_widget.tag_config("location", foreground="#3498db")
        text_widget.tag_config("characters", foreground="#e74c3c", font=("Microsoft YaHei", 10, "bold"))
        text_widget.tag_config("char_name", foreground="#e67e22", font=("Microsoft YaHei", 10, "bold"))
        text_widget.tag_config("detail", foreground="#34495e")
        text_widget.tag_config("visual", foreground="#16a085")
        text_widget.tag_config("action", foreground="#d35400")
        text_widget.tag_config("emotion", foreground="#9b59b6")
        text_widget.tag_config("lighting", foreground="#f39c12")
        text_widget.tag_config("atmosphere", foreground="#8e44ad")
        text_widget.tag_config("camera", foreground="#27ae60")
        text_widget.tag_config("continuity", foreground="#7f8c8d")
        
        text_widget.config(state="disabled")
    
    def _export_shots_text(self) -> None:
        """导出分镜头为文本文件"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("Markdown", "*.md")],
            initialfile=f"分镜头表_{len(self.current_shots)}个镜头.txt"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"分镜头表\n")
                f.write(f"共 {len(self.current_shots)} 个镜头\n")
                f.write(f"{'='*100}\n\n")
                
                for idx, shot in enumerate(self.current_shots):
                    shot_num = shot.get('shot_number', idx+1)
                    scene_id = shot.get('scene_id', '未知场景')
                    shot_type = shot.get('shot_type', '未知类型')
                    
                    f.write(f"【镜头 {shot_num}】{scene_id} - {shot_type}\n")
                    f.write(f"{'-'*100}\n")
                    
                    location = shot.get('location', '')
                    if location:
                        f.write(f"位置: {location}\n")
                    
                    characters = shot.get('characters', [])
                    if characters:
                        chars_text = ', '.join(characters) if isinstance(characters, list) else str(characters)
                        f.write(f"人物: {chars_text}\n")
                    
                    character_details = shot.get('character_details', {})
                    if character_details and isinstance(character_details, dict):
                        for char_name, details in character_details.items():
                            f.write(f"\n{char_name}:\n")
                            if isinstance(details, dict):
                                if details.get('appearance'):
                                    f.write(f"  外貌: {details['appearance']}\n")
                                if details.get('clothing'):
                                    f.write(f"  服装: {details['clothing']}\n")
                                if details.get('expression'):
                                    f.write(f"  表情: {details['expression']}\n")
                                if details.get('posture'):
                                    f.write(f"  姿势: {details['posture']}\n")
                    
                    visual_desc = shot.get('visual_description', '')
                    if visual_desc:
                        f.write(f"\n画面描述:\n{visual_desc}\n")
                    
                    action = shot.get('action', '')
                    if action:
                        f.write(f"\n动作:\n{action}\n")
                    
                    emotion = shot.get('emotion', '')
                    if emotion:
                        f.write(f"\n情绪: {emotion}\n")
                    
                    lighting = shot.get('lighting', '')
                    if lighting:
                        f.write(f"光线: {lighting}\n")
                    
                    atmosphere = shot.get('atmosphere', '')
                    if atmosphere:
                        f.write(f"氛围: {atmosphere}\n")
                    
                    camera = shot.get('camera', {})
                    if camera and isinstance(camera, dict):
                        f.write(f"\n摄影机:\n")
                        if camera.get('movement'):
                            f.write(f"  运动: {camera['movement']}\n")
                        if camera.get('angle'):
                            f.write(f"  角度: {camera['angle']}\n")
                        if camera.get('lens'):
                            f.write(f"  镜头: {camera['lens']}\n")
                    
                    continuity = shot.get('continuity', '')
                    if continuity:
                        f.write(f"\n连贯性: {continuity}\n")
                    
                    f.write(f"\n{'='*100}\n\n")
            
            messagebox.showinfo("成功", f"分镜头表已导出到:\n{file_path}")
        
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")

