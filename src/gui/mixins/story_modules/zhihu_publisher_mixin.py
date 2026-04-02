"""
Zhihu publish feature mixin.
"""

from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import END, messagebox, scrolledtext, ttk

from src.clients.deepseek_client import DeepSeekClient
from src.gui.helpers.story_writing_guardrails import (
    get_article_title_limits,
    get_non_ai_banned_phrases,
    normalize_article_title,
)
from src.utils.story_extractor import StoryExtractor
from src.utils.text import sanitize as _sanitize

try:
    from dotenv import find_dotenv, set_key
except Exception:  # pragma: no cover - optional dependency
    def find_dotenv(*args, **kwargs):
        return ""

    def set_key(*args, **kwargs):
        return None


class ZhihuPublisherMixin:
    """Provide UI and actions for publishing stories to Zhihu."""

    def _is_zhihu_mention_neutralize_enabled(self) -> bool:
        raw = str(os.getenv("ZHIHU_NEUTRALIZE_MENTIONS", "0") or "0").strip().lower()
        return raw in {"1", "true", "yes", "on"}

    def _persist_zhihu_publish_preferences(self) -> None:
        """Persist Zhihu publish preferences to .env."""
        try:
            env_path_str = find_dotenv(usecwd=True)
            env_path = env_path_str if env_path_str else str(Path.cwd() / ".env")
            value = "1" if bool(self.zhihu_neutralize_mentions_var.get()) else "0"
            set_key(env_path, "ZHIHU_NEUTRALIZE_MENTIONS", value)
        except Exception:
            # Persist failure should never block publish flow.
            pass

    def _build_zhihu_publish_ui(self, parent_frame) -> None:
        publish_frame = ttk.Frame(parent_frame)
        publish_frame.pack(fill="x", padx=10, pady=6)

        ttk.Label(
            publish_frame,
            text="📤 知乎:",
            font=("Microsoft YaHei", 10, "bold"),
            width=7,
        ).pack(side="left", padx=(0, 8))

        self.zhihu_title_var = tk.StringVar(value="")
        title_entry = ttk.Entry(
            publish_frame,
            textvariable=self.zhihu_title_var,
            font=("Microsoft YaHei", 10),
        )
        title_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ttk.Button(
            publish_frame,
            text="🤖 AI生成标题",
            command=self._on_generate_zhihu_title,
            width=13,
        ).pack(side="left", padx=(0, 10))

        self.zhihu_headless_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            publish_frame,
            text="后台运行",
            variable=self.zhihu_headless_var,
            width=8,
        ).pack(side="left", padx=(0, 10))

        self.zhihu_neutralize_mentions_var = tk.BooleanVar(value=self._is_zhihu_mention_neutralize_enabled())
        try:
            self.zhihu_neutralize_mentions_var.trace_add("write", lambda *_: self._persist_zhihu_publish_preferences())
        except Exception:
            pass
        ttk.Checkbutton(
            publish_frame,
            text="中和@提及(兼容)",
            variable=self.zhihu_neutralize_mentions_var,
            width=14,
        ).pack(side="left", padx=(0, 10))

        self.zhihu_publish_btn = ttk.Button(
            publish_frame,
            text="📤 发布到知乎",
            command=self._on_publish_to_zhihu,
            width=13,
        )
        self.zhihu_publish_btn.pack(side="left", padx=(0, 15))

        self.zhihu_progress_label = ttk.Label(
            publish_frame,
            text="",
            font=("Microsoft YaHei", 9),
            foreground="#0066cc",
            width=18,
        )
        self.zhihu_progress_label.pack(side="left", padx=(0, 10))

        ttk.Label(
            publish_frame,
            text="💡 首次使用需在浏览器登录，登录状态会保存",
            font=("Microsoft YaHei", 8),
            foreground="#666666",
        ).pack(side="left")

    def _resolve_zhihu_title_api_config(self) -> dict:
        fallback_provider = None
        if hasattr(self, "story_gen_api"):
            try:
                fallback_provider = self.story_gen_api.get()
            except Exception:
                fallback_provider = None
        if not fallback_provider and hasattr(self, "quick_story_api"):
            try:
                fallback_provider = self.quick_story_api.get()
            except Exception:
                fallback_provider = None
        if not fallback_provider and hasattr(self, "api_preset"):
            try:
                fallback_provider = self.api_preset.get()
            except Exception:
                fallback_provider = None

        fallback_model = None
        if hasattr(self, "story_model_var"):
            try:
                fallback_model = self.story_model_var.get()
            except Exception:
                fallback_model = None
        elif hasattr(self, "model"):
            try:
                fallback_model = self.model.get()
            except Exception:
                fallback_model = None

        if hasattr(self, "_resolve_task_api"):
            return self._resolve_task_api(
                "story_generate",
                fallback_provider=fallback_provider,
                fallback_model=fallback_model,
            )

        if hasattr(self, "api_presets") and fallback_provider in self.api_presets:
            preset = self.api_presets.get(fallback_provider, {}) or {}
            return {
                "provider": fallback_provider,
                "key": preset.get("key", ""),
                "base_url": preset.get("base_url", ""),
                "model": preset.get("model", ""),
            }
        return {"provider": "", "key": "", "base_url": "", "model": ""}

    def _on_generate_zhihu_title(self) -> None:
        raw_story_text = self.output.get("1.0", END).strip()
        if not raw_story_text:
            messagebox.showwarning("提示", "请先生成故事内容")
            return
        if len(raw_story_text) < 100:
            messagebox.showwarning("提示", "故事内容太短，请生成完整故事后再生成标题")
            return

        story_text = StoryExtractor.extract_pure_story(raw_story_text)
        if not story_text or len(story_text) < 100:
            messagebox.showwarning("提示", "无法提取有效的故事内容")
            return

        api_config = self._resolve_zhihu_title_api_config()
        api_key = _sanitize(api_config.get("key", ""))
        if not api_key:
            messagebox.showwarning("提示", "请先在设置中配置故事生成 API Key")
            return

        self.zhihu_publish_btn.config(state="disabled")
        self.zhihu_progress_label.config(text="正在生成标题...")

        def generate_title_task():
            try:
                client = DeepSeekClient(
                    api_key=api_key,
                    base_url=_sanitize(api_config.get("base_url", "")),
                    model=_sanitize(api_config.get("model", "")),
                )
                summary = story_text[:500]
                article_title_min_len, article_title_max_len = get_article_title_limits()
                banned_phrase_preview = " / ".join(get_non_ai_banned_phrases()[:4]) or "总的来说 / 不难发现"
                prompt = f"""请为以下故事生成一个吸引点击的知乎标题。

要求：
1. {article_title_min_len}-{article_title_max_len}字，超过{article_title_max_len}字必须压缩
2. 有冲突、悬念或反转，但表达克制
3. 禁止营销号措辞（如“震惊”“逆天”“看哭了”“绝了”）
4. 不要使用“{banned_phrase_preview}”这类模板化表达
5. 只返回标题文本，不要附加解释

故事内容摘要：
{summary}

请直接输出标题："""
                title = client.chat([{"role": "user", "content": prompt}], temperature=0.7).strip()
                title = normalize_article_title(
                    title,
                    min_len=article_title_min_len,
                    max_len=article_title_max_len,
                )

                self.after(0, lambda: self.zhihu_title_var.set(title))
                self.after(0, lambda: self.zhihu_progress_label.config(text="✅ 标题生成完成"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("错误", f"生成标题失败: {str(e)}"))
                self.after(0, lambda: self.zhihu_progress_label.config(text="❌ 生成失败"))
            finally:
                self.after(0, lambda: self.zhihu_publish_btn.config(state="normal"))

        threading.Thread(target=generate_title_task, daemon=True).start()

    def _on_publish_to_zhihu(self) -> None:
        article_title_min_len, article_title_max_len = get_article_title_limits()
        title = normalize_article_title(
            self.zhihu_title_var.get().strip(),
            min_len=article_title_min_len,
            max_len=article_title_max_len,
        )
        if title != self.zhihu_title_var.get().strip():
            self.zhihu_title_var.set(title)
        if not title:
            messagebox.showwarning("提示", "请先输入或生成文章标题")
            return

        raw_content = self.output.get("1.0", END).strip()
        if not raw_content:
            messagebox.showwarning("提示", "请先生成故事内容")
            return
        if len(raw_content) < 100:
            messagebox.showwarning("提示", "故事内容太短，建议至少100字以上")
            return

        neutralize_mentions = True
        if hasattr(self, "zhihu_neutralize_mentions_var"):
            try:
                neutralize_mentions = bool(self.zhihu_neutralize_mentions_var.get())
            except Exception:
                neutralize_mentions = True
        content = (
            StoryExtractor.sanitize_for_zhihu_publish(raw_content)
            if neutralize_mentions
            else StoryExtractor.sanitize_for_publish(raw_content)
        )
        if not content or len(content) < 100:
            messagebox.showwarning("提示", "无法提取有效的故事内容")
            return

        preview_window = tk.Toplevel(self)
        preview_window.title("发布预览 - 确认内容")
        screen_width = preview_window.winfo_screenwidth()
        screen_height = preview_window.winfo_screenheight()
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height * 0.8)
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        preview_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

        main_canvas = tk.Canvas(preview_window, highlightthickness=0)
        main_scrollbar = ttk.Scrollbar(preview_window, orient="vertical", command=main_canvas.yview)
        scrollable_main = ttk.Frame(main_canvas)
        scrollable_main.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all")),
        )
        main_canvas.create_window((0, 0), window=scrollable_main, anchor="nw")
        main_canvas.configure(yscrollcommand=main_scrollbar.set)

        def _on_mousewheel(event):
            main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        main_canvas.bind("<MouseWheel>", _on_mousewheel)
        main_canvas.bind("<Enter>", lambda _event: main_canvas.focus_set())
        main_canvas.pack(side="left", fill="both", expand=True)
        main_scrollbar.pack(side="right", fill="y")

        title_frame = ttk.Frame(scrollable_main)
        title_frame.pack(fill="x", padx=20, pady=(20, 10))
        title_header = ttk.Frame(title_frame)
        title_header.pack(fill="x")
        ttk.Label(title_header, text="📝 文章标题", font=("Microsoft YaHei", 11, "bold")).pack(side="left")
        stats_text = (
            f"📊 原始: {len(raw_content)}字 → 过滤后: {len(content)}字 "
            f"(已过滤: {len(raw_content) - len(content)}字)"
        )
        ttk.Label(
            title_header,
            text=stats_text,
            font=("Microsoft YaHei", 8),
            foreground="#666",
        ).pack(side="right", padx=(10, 0))

        title_var = tk.StringVar(value=title)
        title_entry = ttk.Entry(title_frame, textvariable=title_var, font=("Microsoft YaHei", 13))
        title_entry.pack(fill="x", pady=(5, 0))
        ttk.Label(
            title_frame,
            text="💡 标题可编辑，建议15-25字",
            font=("Microsoft YaHei", 8),
            foreground="gray",
        ).pack(anchor="w", pady=(3, 0))

        content_frame = ttk.LabelFrame(
            scrollable_main,
            text="📄 将要发布的内容（可编辑，删除不需要的部分）",
            padding=10,
        )
        content_frame.pack(fill="both", expand=True, padx=20, pady=15)
        content_text = scrolledtext.ScrolledText(
            content_frame,
            wrap=tk.WORD,
            font=("Microsoft YaHei", 10),
            height=25,
            width=100,
        )
        content_text.pack(fill="both", expand=True)
        content_text.insert("1.0", content)
        ttk.Label(
            content_frame,
            text="✏️ 提示：内容可直接编辑后再发布",
            font=("Microsoft YaHei", 8),
            foreground="#0066cc",
        ).pack(anchor="w", pady=(5, 0))

        button_frame = ttk.Frame(scrollable_main)
        button_frame.pack(fill="x", padx=20, pady=(10, 20))
        publish_confirmed = [False]

        def confirm_publish():
            edited_title = title_var.get().strip()
            edited_content = content_text.get("1.0", "end-1c").strip()
            edited_content = (
                StoryExtractor.sanitize_for_zhihu_publish(edited_content)
                if neutralize_mentions
                else StoryExtractor.sanitize_for_publish(edited_content)
            )
            if not edited_title:
                messagebox.showwarning("提示", "标题不能为空")
                return
            if not edited_content:
                messagebox.showwarning("提示", "内容不能为空")
                return
            self.zhihu_title_var.set(edited_title)
            self._zhihu_edited_title = edited_title
            self._zhihu_edited_content = edited_content
            publish_confirmed[0] = True
            main_canvas.unbind("<MouseWheel>")
            preview_window.destroy()

        def cancel_publish():
            main_canvas.unbind("<MouseWheel>")
            preview_window.destroy()

        ttk.Button(
            button_frame,
            text="✅ 确认发布到知乎",
            command=confirm_publish,
            width=20,
        ).pack(side="left", padx=(0, 10))
        ttk.Button(button_frame, text="❌ 取消", command=cancel_publish, width=10).pack(side="left")

        preview_window.transient(self)
        preview_window.grab_set()
        self.wait_window(preview_window)
        if not publish_confirmed[0]:
            return

        if hasattr(self, "_zhihu_edited_title"):
            title = self._zhihu_edited_title
            delattr(self, "_zhihu_edited_title")
        if hasattr(self, "_zhihu_edited_content"):
            content = self._zhihu_edited_content
            delattr(self, "_zhihu_edited_content")

        try:
            import playwright  # noqa: F401
        except ImportError:
            messagebox.showerror(
                "缺少依赖",
                "未安装 Playwright。\n\n请执行：\n"
                "1. pip install playwright\n"
                "2. playwright install chromium",
            )
            return

        self.zhihu_publish_btn.config(state="disabled", text="发布中...")
        self.zhihu_progress_label.config(text="正在初始化...")

        def publish_task():
            try:
                from src.gui.services.zhihu_publisher import publish_to_zhihu_sync

                headless = bool(self.zhihu_headless_var.get())
                if headless:
                    # Zhihu 发布流程通常需要人工最终确认，后台模式无法手动点击发布按钮。
                    headless = False
                    self.after(
                        0,
                        lambda: self.zhihu_progress_label.config(text="⚠ 后台模式已切换为前台"),
                    )

                def progress_callback(message: str):
                    self.after(0, lambda msg=message: self.zhihu_progress_label.config(text=msg))

                success, result = publish_to_zhihu_sync(
                    title=title,
                    content=content,
                    headless=headless,
                    progress_callback=progress_callback,
                )
                if success:
                    if isinstance(result, str) and result.startswith("http"):
                        self.after(
                            0,
                            lambda: messagebox.showinfo(
                                "发布成功",
                                f"文章已成功发布到知乎！\n\n链接: {result}\n\n已复制到剪贴板",
                            ),
                        )
                        self.after(0, self.clipboard_clear)
                        self.after(0, lambda: self.clipboard_append(result))
                    else:
                        self.after(
                            0,
                            lambda: messagebox.showinfo(
                                "内容已填充",
                                f"{result}\n\n请在浏览器中检查内容并手动点击发布按钮。",
                            ),
                        )
                    self.after(0, lambda: self.zhihu_progress_label.config(text="✅ 完成"))
                    if hasattr(self, "status"):
                        self.after(0, lambda: self.status.set("✅ 知乎发布完成"))
                else:
                    self.after(0, lambda: messagebox.showerror("发布失败", str(result)))
                    self.after(0, lambda: self.zhihu_progress_label.config(text="❌ 失败"))
                    if hasattr(self, "status"):
                        self.after(0, lambda: self.status.set("❌ 发布失败"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("错误", f"发布过程出错: {str(e)}"))
                self.after(0, lambda: self.zhihu_progress_label.config(text="❌ 错误"))
                if hasattr(self, "status"):
                    self.after(0, lambda: self.status.set("❌ 发布错误"))
            finally:
                self.after(0, lambda: self.zhihu_publish_btn.config(state="normal", text="📤 发布到知乎"))

        threading.Thread(target=publish_task, daemon=True).start()
