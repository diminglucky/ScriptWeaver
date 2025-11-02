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
            text="💡 点击发布后可在预览窗口选择输入模式（流式/粘贴）",
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
                
                # 提取故事前800字作为摘要（增加信息量）
                summary = story_text[:800]
                
                # 系统提示词 - 设定AI角色
                system_prompt = """你是知乎创作者，擅长写简洁、精准的标题。
你的标题简单但能直通故事要点或精髓，一句话抓住故事的核心。
你相信好的标题应该简单、精准，一句话说清楚故事最核心的点。"""
                
                # 用户提示词 - 简洁明了
                user_prompt = f"""为以下故事生成一个简短、精准的标题。

核心要求：
1. **简单但直通要点** - 10-15字以内，但要抓住故事的核心/精髓
2. **直通故事要点** - 不要流于表面，要体现故事最核心的点或精髓
3. **精准** - 一句话说清楚故事主题，不要啰嗦
4. **真实** - 不夸张、不煽情，贴合故事内容

✅ 好的标题示例（简单但直通要点）：
"一支520烟，毁了我三年"
"我妈给我打电话，说我爸不见了"
"我在平安夜对他说：让我追你"
"毕业三年，我变了"
"那个同学后来怎样了"
"我差点毁掉整个大学"

✅ 要点分析：
- "一支520烟" - 简单，但直通故事核心（烟是故事的起点和关键）
- "我爸不见了" - 直入主题，直接抓住故事要点
- "让我追你" - 简单直接，抓住故事的核心冲突
- "我变了" - 简单，但直通故事精髓（变化是核心）

❌ 不好的标题（流于表面或太啰嗦）：
"从班级角落的受气包到职场精英的完整蜕变之路"  ← 太长太啰嗦
"那个被全校孤立的女生，毕业十年后回母校时的故事"  ← 太啰嗦，没有直通要点
"震惊！逆袭打脸复仇的爽文情节"  ← 太夸张，不是真实故事
"我的校园往事"  ← 太泛泛，没有抓住故事要点
"关于一段职场经历"  ← 太表面，没有直通精髓

💡 **标题生成思路**：
1. 找出故事最核心的点是什么？（是某个决定？某个转折？某个真相？）
2. 这个核心点用最简单的话怎么说？
3. 确保标题直通这个故事的精髓，而不是泛泛的描述

故事内容：
{summary}

请生成一个10-15字的标题，要求简单但能直通故事要点或精髓："""
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                title = client.chat(messages, temperature=0.5).strip()
                
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
        
        # 输入模式选择区域
        mode_frame = ttk.Frame(scrollable_main)
        mode_frame.pack(fill="x", padx=20, pady=10)
        
        # 输入模式变量
        input_mode_var = tk.StringVar(value="stream")
        
        # 两个单选按钮并排
        ttk.Radiobutton(
            mode_frame,
            text="⚡ 快速粘贴（推荐）",
            variable=input_mode_var,
            value="paste"
        ).pack(side="left", padx=(0, 20))
        
        ttk.Radiobutton(
            mode_frame,
            text="✍️ 流式输出",
            variable=input_mode_var,
            value="stream"
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
            self._zhihu_input_mode = input_mode_var.get()  # 保存选择的输入模式
            
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
        
        # 获取编辑后的内容和输入模式
        if hasattr(self, '_zhihu_edited_content'):
            content = self._zhihu_edited_content
            delattr(self, '_zhihu_edited_content')  # 清理临时属性
        
        # 获取输入模式
        input_mode = getattr(self, '_zhihu_input_mode', 'paste')
        if hasattr(self, '_zhihu_input_mode'):
            delattr(self, '_zhihu_input_mode')  # 清理临时属性
        
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
                # input_mode 已经在外部作用域中定义好了
                
                # 进度回调
                def progress_callback(message: str):
                    self.after(0, lambda msg=message: self.zhihu_progress_label.config(text=msg))
                    print(f"[INFO] {message}")
                
                # 执行发布
                success, result = publish_to_zhihu_sync(
                    title=title,
                    content=content,
                    headless=headless,
                    input_mode=input_mode,  # 传递输入模式（从预览窗口获取）
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

