"""
知乎发布功能混入类
"""

import tkinter as tk
from tkinter import ttk, messagebox, END, scrolledtext
import threading


class ZhihuPublisherMixin:
    """知乎发布功能 Mixin"""
    
    def _build_zhihu_publish_ui(self, parent_frame: ttk.Frame) -> None:
        """
        构建知乎发布UI（完全优化版本，确保所有文字显示）
        
        Args:
            parent_frame: 父容器
        """
        # 发布区域 - 单行布局
        publish_frame = ttk.Frame(parent_frame)
        publish_frame.pack(fill="x", padx=10, pady=6)
        
        # 左侧：标签
        ttk.Label(
            publish_frame,
            text="📤 知乎:",
            font=("Microsoft YaHei", 10, "bold"),
            width=6  # 固定宽度
        ).pack(side="left", padx=(0, 8))
        
        # 标题输入框（使用fill='x'和expand让它自适应）
        self.zhihu_title_var = tk.StringVar(value="")
        title_entry = ttk.Entry(
            publish_frame,
            textvariable=self.zhihu_title_var,
            font=("Microsoft YaHei", 10)
        )
        title_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # AI生成标题按钮（固定宽度，文字完整）
        ttk.Button(
            publish_frame,
            text="🤖 AI生成标题",
            command=self._on_generate_zhihu_title,
            width=13  # 增加到13确保文字显示
        ).pack(side="left", padx=(0, 10))
        
        # 后台运行选项
        self.zhihu_headless_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            publish_frame,
            text="后台运行",
            variable=self.zhihu_headless_var,
            width=8  # 固定宽度
        ).pack(side="left", padx=(0, 10))
        
        # 发布按钮（固定宽度，文字完整）
        self.zhihu_publish_btn = ttk.Button(
            publish_frame,
            text="📤 发布到知乎",
            command=self._on_publish_to_zhihu,
            style="Accent.TButton",
            width=13  # 增加到13确保文字显示
        )
        self.zhihu_publish_btn.pack(side="left", padx=(0, 15))
        
        # 进度显示（可扩展区域）
        self.zhihu_progress_label = ttk.Label(
            publish_frame,
            text="",
            font=("Microsoft YaHei", 9),
            foreground="#0066cc",
            width=15  # 固定宽度供进度显示
        )
        self.zhihu_progress_label.pack(side="left", padx=(0, 10))
        
        # 说明（自适应剩余空间）
        ttk.Label(
            publish_frame,
            text="💡 首次使用需在浏览器登录，登录状态会保存",
            font=("Microsoft YaHei", 8),
            foreground="#666666"
        ).pack(side="left", fill="x", expand=False)
    
    def _on_generate_zhihu_title(self) -> None:
        """使用AI生成文章标题"""
        # 获取故事内容
        raw_story_text = self.output.get("1.0", END).strip()
        
        if not raw_story_text:
            messagebox.showwarning("提示", "请先生成故事内容")
            return
        
        if len(raw_story_text) < 100:
            messagebox.showwarning("提示", "故事内容太短，请生成完整故事后再生成标题")
            return
        
        # 提取纯净的故事内容
        from src.utils.story_extractor import StoryExtractor
        
        story_text = StoryExtractor.extract_pure_story(raw_story_text)
        
        if not story_text or len(story_text) < 100:
            messagebox.showwarning("提示", "无法提取有效的故事内容")
            return
        
        # 获取API配置
        selected_api = self.story_gen_api.get() if hasattr(self, 'story_gen_api') else "DeepSeek"
        if not hasattr(self, 'api_presets') or selected_api not in self.api_presets:
            messagebox.showerror("错误", "未找到API配置")
            return
        
        api_config = self.api_presets[selected_api]
        from src.utils.text import sanitize as _sanitize
        api_key = _sanitize(api_config.get("key", ""))
        
        if not api_key:
            messagebox.showwarning("提示", "请先配置API Key")
            return
        
        # 禁用按钮
        self.zhihu_publish_btn.config(state="disabled")
        self.zhihu_progress_label.config(text="正在生成标题...")
        
        def generate_title_task():
            try:
                from src.clients.deepseek_client import DeepSeekClient
                
                client = DeepSeekClient(
                    api_key=api_key,
                    base_url=_sanitize(api_config.get("base_url", "")),
                    model=_sanitize(api_config.get("model", "")),
                )
                
                # 提取故事前500字作为摘要
                summary = story_text[:500]
                
                prompt = f"""请为以下故事生成一个极具创意和吸引力的知乎爆款标题。

核心要求：
1. 标题长度：15-25字
2. 必须有强烈的冲突感、悬念或反转
3. 优先使用这些创意手法：
   - 反差对比（"从...到..."）
   - 震撼问句（"为什么..."、"如何..."）
   - 数字冲击（"三年"、"十年"、"一夜之间"）
   - 情感共鸣（"那个..."、"这个..."）
   - 戏剧性转折（"却..."、"反而..."）
4. 避免平淡陈述和俗套表达
5. 标题要有画面感和故事感
6. 只返回标题文本，不要引号

爆款标题示例（供参考风格，不要照搬）：
- "那个被全班孤立的少年，如何在十年后成了所有人的救赎？"
- "从校园受气包到职场精英，我用了整整三年证明：沉默是最昂贵的反击"
- "被霸凌的经历，反而成了我最宝贵的财富——这不是鸡汤"
- "他们以为欺负我很有趣，直到我在职场上遇见了他们"
- "校园霸凌毁了我的青春，但我用十年夺回了人生的主动权"

故事内容：
{summary}

要求：
- 标题必须独特新颖，不要模仿示例
- 要抓住故事最核心的冲突或反转
- 让读者一看就想点进去
- 避免说教和鸡汤语气

请生成创新标题："""
                
                messages = [{"role": "user", "content": prompt}]
                title = client.chat(messages, temperature=0.7).strip()
                
                # 移除可能的引号
                title = title.strip('"\'「」『』""''')
                
                # 更新UI
                self.after(0, lambda: self.zhihu_title_var.set(title))
                self.after(0, lambda: self.zhihu_progress_label.config(text="✅ 标题生成完成"))
                self.after(0, lambda: messagebox.showinfo("成功", f"标题已生成:\n\n{title}"))
                
            except Exception as e:
                error_msg = f"生成标题失败: {str(e)}"
                print(f"[ERROR] {error_msg}")
                self.after(0, lambda: messagebox.showerror("错误", error_msg))
                self.after(0, lambda: self.zhihu_progress_label.config(text="❌ 生成失败"))
            
            finally:
                self.after(0, lambda: self.zhihu_publish_btn.config(state="normal"))
        
        threading.Thread(target=generate_title_task, daemon=True).start()
    
    def _on_publish_to_zhihu(self) -> None:
        """发布到知乎"""
        # 获取标题
        title = self.zhihu_title_var.get().strip()
        if not title:
            messagebox.showwarning("提示", "请先输入或生成文章标题")
            return
        
        # 获取故事内容
        raw_content = self.output.get("1.0", END).strip()
        if not raw_content:
            messagebox.showwarning("提示", "请先生成故事内容")
            return
        
        if len(raw_content) < 100:
            messagebox.showwarning("提示", "故事内容太短，建议至少100字以上")
            return
        
        # 提取纯净的故事内容（去除目录、章节标题等）
        from src.utils.story_extractor import StoryExtractor
        
        content = StoryExtractor.extract_pure_story(raw_content)
        
        if not content:
            messagebox.showwarning("提示", "无法提取有效的故事内容")
            return
        
        if len(content) < 100:
            messagebox.showwarning("提示", "提取的故事内容太短，建议至少100字以上")
            return
        
        print(f"[INFO] 原始内容: {len(raw_content)} 字符")
        print(f"[INFO] 提取后内容: {len(content)} 字符")
        print(f"[INFO] 已过滤: 目录、章节标题、分隔线等结构信息")
        
        # 显示预览窗口（更大尺寸，支持滚动）
        preview_window = tk.Toplevel(self)
        preview_window.title("发布预览 - 确认内容")
        
        # 设置为屏幕的80%大小
        screen_width = preview_window.winfo_screenwidth()
        screen_height = preview_window.winfo_screenheight()
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height * 0.8)
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        preview_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 创建主滚动区域
        main_canvas = tk.Canvas(preview_window, highlightthickness=0)
        main_scrollbar = ttk.Scrollbar(preview_window, orient="vertical", command=main_canvas.yview)
        scrollable_main = ttk.Frame(main_canvas)
        
        scrollable_main.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=scrollable_main, anchor="nw")
        main_canvas.configure(yscrollcommand=main_scrollbar.set)
        
        # 鼠标滚轮支持
        def _on_mousewheel(event):
            main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        main_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        main_canvas.pack(side="left", fill="both", expand=True)
        main_scrollbar.pack(side="right", fill="y")
        
        # 标题编辑区域（全宽）
        title_frame = ttk.Frame(scrollable_main)
        title_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        # 标题标签和统计信息在同一行
        title_header = ttk.Frame(title_frame)
        title_header.pack(fill="x")
        
        ttk.Label(title_header, text="📝 文章标题", font=("Microsoft YaHei", 11, "bold")).pack(side="left")
        
        # 统计信息（紧凑显示在右侧）
        stats_text = f"📊 原始: {len(raw_content)}字 → 过滤后: {len(content)}字 (已过滤: {len(raw_content) - len(content)}字)"
        ttk.Label(
            title_header,
            text=stats_text,
            font=("Microsoft YaHei", 8),
            foreground="#666"
        ).pack(side="right", padx=(10, 0))
        
        # 标题编辑框（允许修改）
        title_var = tk.StringVar(value=title)
        title_entry = ttk.Entry(
            title_frame,
            textvariable=title_var,
            font=("Microsoft YaHei", 13)
        )
        title_entry.pack(fill="x", pady=(5, 0))
        
        ttk.Label(
            title_frame,
            text="💡 标题可编辑，建议15-25字",
            font=("Microsoft YaHei", 8),
            foreground="gray"
        ).pack(anchor="w", pady=(3, 0))
        
        # 内容编辑区域（可编辑）
        content_frame = ttk.LabelFrame(
            scrollable_main,
            text="📄 将要发布的内容（可编辑，删除不需要的部分）",
            padding=10
        )
        content_frame.pack(fill="both", expand=True, padx=20, pady=15)
        
        # 可编辑的文本框
        content_text = scrolledtext.ScrolledText(
            content_frame,
            wrap=tk.WORD,
            font=("Microsoft YaHei", 10),
            height=25,
            width=100
        )
        content_text.pack(fill="both", expand=True)
        content_text.insert("1.0", content)
        # 不设置为只读，允许编辑
        
        # 编辑提示
        edit_hint = ttk.Frame(content_frame)
        edit_hint.pack(fill="x", pady=(5, 0))
        
        ttk.Label(
            edit_hint,
            text="✏️ 提示：内容可以直接编辑，删除不需要的部分后再发布",
            font=("Microsoft YaHei", 8),
            foreground="#0066cc"
        ).pack(side="left")
        
        # 按钮区域
        button_frame = ttk.Frame(scrollable_main)
        button_frame.pack(fill="x", padx=20, pady=(10, 20))
        
        publish_confirmed = [False]  # 使用列表来在闭包中修改值
        
        def confirm_publish():
            # 获取编辑后的标题和内容
            edited_title = title_var.get().strip()
            edited_content = content_text.get("1.0", "end-1c").strip()
            
            if not edited_title:
                messagebox.showwarning("提示", "标题不能为空")
                return
            
            if not edited_content:
                messagebox.showwarning("提示", "内容不能为空")
                return
            
            # 更新标题和内容（通过一个临时变量传递）
            self.zhihu_title_var.set(edited_title)
            self._zhihu_edited_content = edited_content  # 保存编辑后的内容
            
            publish_confirmed[0] = True
            main_canvas.unbind_all("<MouseWheel>")  # 解绑滚轮事件
            preview_window.destroy()
        
        def cancel_publish():
            main_canvas.unbind_all("<MouseWheel>")  # 解绑滚轮事件
            preview_window.destroy()
        
        ttk.Button(
            button_frame,
            text="✅ 确认发布到知乎",
            command=confirm_publish,
            style="Accent.TButton",
            width=20
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            button_frame,
            text="❌ 取消",
            command=cancel_publish,
            width=10
        ).pack(side="left")
        
        # 等待窗口关闭
        preview_window.transient(self)
        preview_window.grab_set()
        self.wait_window(preview_window)
        
        # 如果用户取消
        if not publish_confirmed[0]:
            return
        
        # 获取编辑后的内容
        if hasattr(self, '_zhihu_edited_content'):
            content = self._zhihu_edited_content
            delattr(self, '_zhihu_edited_content')  # 清理临时属性
        
        # 检查是否安装了playwright
        try:
            import playwright
        except ImportError:
            error_msg = """未安装 Playwright！

请在终端运行以下命令安装：

1. 安装 playwright:
   pip install playwright

2. 安装浏览器:
   playwright install chromium

安装完成后重启应用。"""
            
            messagebox.showerror("缺少依赖", error_msg)
            return
        
        # 禁用按钮
        self.zhihu_publish_btn.config(state="disabled", text="发布中...")
        self.zhihu_progress_label.config(text="正在初始化...")
        
        def publish_task():
            try:
                from src.services.zhihu_publisher import publish_to_zhihu_sync
                
                headless = self.zhihu_headless_var.get()
                
                # 进度回调
                def progress_callback(message: str):
                    self.after(0, lambda msg=message: self.zhihu_progress_label.config(text=msg))
                    print(f"[INFO] {message}")
                
                # 执行发布
                success, result = publish_to_zhihu_sync(
                    title=title,
                    content=content,
                    headless=headless,
                    progress_callback=progress_callback
                )
                
                # 显示结果
                if success:
                    if result.startswith("http"):
                        # 成功发布并获得链接
                        self.after(0, lambda: messagebox.showinfo(
                            "发布成功",
                            f"文章已成功发布到知乎！\n\n链接: {result}\n\n已复制到剪贴板"
                        ))
                        # 复制链接到剪贴板
                        self.after(0, lambda: self.clipboard_clear())
                        self.after(0, lambda: self.clipboard_append(result))
                    else:
                        # 内容已填充，等待手动发布
                        self.after(0, lambda: messagebox.showinfo(
                            "内容已填充",
                            f"{result}\n\n请在浏览器中检查内容并手动点击发布按钮。"
                        ))
                    
                    self.after(0, lambda: self.zhihu_progress_label.config(text="✅ 完成"))
                    self.after(0, lambda: self.status.set("✅ 知乎发布完成"))
                    
                else:
                    # 发布失败
                    self.after(0, lambda: messagebox.showerror("发布失败", result))
                    self.after(0, lambda: self.zhihu_progress_label.config(text="❌ 失败"))
                    self.after(0, lambda: self.status.set("❌ 发布失败"))
                
            except Exception as e:
                error_msg = f"发布过程出错: {str(e)}"
                print(f"[ERROR] {error_msg}")
                import traceback
                traceback.print_exc()
                
                self.after(0, lambda: messagebox.showerror("错误", error_msg))
                self.after(0, lambda: self.zhihu_progress_label.config(text="❌ 错误"))
                self.after(0, lambda: self.status.set("❌ 发布错误"))
            
            finally:
                # 恢复按钮
                self.after(0, lambda: self.zhihu_publish_btn.config(state="normal", text="📤 发布到知乎"))
        
        # 在后台线程中运行
        threading.Thread(target=publish_task, daemon=True).start()

