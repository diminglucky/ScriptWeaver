"""
Zhihu publish service based on Playwright.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Callable, Optional


class ZhihuPublisher:
    """Automate filling title/body into Zhihu article editor."""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser = None
        self.page = None
        self.playwright = None
        self.user_data_dir = Path.home() / ".zhihu_publisher"

    async def initialize(self) -> bool:
        try:
            from playwright.async_api import async_playwright

            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                headless=self.headless,
                viewport={"width": 1280, "height": 800},
                locale="zh-CN",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ],
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            await self.browser.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.navigator.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en'],
                });
                """
            )
            self.page = await self.browser.new_page()
            return True
        except Exception as e:
            print(f"[ERROR] 初始化浏览器失败: {e}")
            return False

    async def check_login_status(self) -> bool:
        if not self.page:
            return False
        try:
            await self.page.goto("https://www.zhihu.com", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            login_button = await self.page.query_selector('button:has-text("登录")')
            if login_button:
                return False

            if await self.page.query_selector(".AppHeader-profile"):
                return True

            current_url = self.page.url
            if "signin" in current_url or "login" in current_url:
                return False

            if await self.page.query_selector('a[href*="creator"]'):
                return True

            return False
        except Exception as e:
            print(f"[ERROR] 检查登录状态失败: {e}")
            return False

    async def wait_for_manual_login(self, timeout: int = 300) -> bool:
        if not self.page:
            return False
        try:
            try:
                await self.page.goto("https://www.zhihu.com/signin", wait_until="domcontentloaded", timeout=30000)
            except Exception:
                pass
            await asyncio.sleep(2)

            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    if await self.page.query_selector(".AppHeader-profile"):
                        await asyncio.sleep(1)
                        return True
                    current_url = self.page.url
                    if "signin" not in current_url and "login" not in current_url:
                        await asyncio.sleep(1)
                        if await self.check_login_status():
                            return True
                except Exception:
                    pass
                await asyncio.sleep(2)
            return False
        except Exception as e:
            print(f"[ERROR] 等待登录失败: {e}")
            return False

    async def publish_article(
        self,
        title: str,
        content: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> tuple[bool, str]:
        if not self.page:
            return False, "浏览器未初始化"
        try:
            if not await self._ensure_logged_in(progress_callback):
                return False, "登录超时或失败"

            # 直接打开写文章页面（跳过创作中心导航）
            self._report_progress(progress_callback, "打开文章编辑器...")
            await self.page.goto(
                "https://zhuanlan.zhihu.com/write",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            await asyncio.sleep(3)

            await self._wait_editor_ready(progress_callback)
            await self._input_article_title(title, progress_callback)
            await self._input_article_content(content, progress_callback)

            # 标题和内容已填好，通知用户自行选择专栏/标签后发布
            self._report_progress(progress_callback, "✅ 标题和内容已填好，请手动发布")
            return True, "标题和内容已填充完毕，请在浏览器中选择专栏、标签后点击发布。"
        except Exception as e:
            msg = f"发布过程出错: {str(e)}"
            if progress_callback:
                progress_callback(f"错误: {msg}")
            return False, msg

    @staticmethod
    def _report_progress(
        progress_callback: Optional[Callable[[str], None]], message: str
    ) -> None:
        if progress_callback:
            progress_callback(message)

    async def _ensure_logged_in(
        self,
        progress_callback: Optional[Callable[[str], None]],
    ) -> bool:
        self._report_progress(progress_callback, "检查登录状态...")
        if await self.check_login_status():
            return True
        self._report_progress(progress_callback, "需要登录，请在浏览器中完成登录")
        return await self.wait_for_manual_login()

    async def _open_creator_center(
        self,
        progress_callback: Optional[Callable[[str], None]],
    ) -> None:
        self._report_progress(progress_callback, "打开创作中心...")
        await self.page.goto(
            "https://www.zhihu.com",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        await asyncio.sleep(2)
        creator_btn = await self.page.query_selector(
            'a[href*="creator"], button:has-text("创作中心")'
        )
        if creator_btn:
            await creator_btn.click()
            await asyncio.sleep(3)
        else:
            await self.page.goto(
                "https://www.zhihu.com/creator",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            await asyncio.sleep(3)

    async def _open_article_editor_page(
        self,
        progress_callback: Optional[Callable[[str], None]],
    ) -> None:
        self._report_progress(progress_callback, "点击发布文章...")
        try:
            content_create_btn = await self.page.query_selector(
                'button:has-text("内容创作"), div:has-text("内容创作")'
            )
            if content_create_btn:
                await content_create_btn.click()
                await asyncio.sleep(1.5)
        except Exception:
            pass

        publish_article_btn = await self._wait_first_selector(
            [
                'button:has-text("发布文章")',
                'a:has-text("发布文章")',
                'div:has-text("发布文章")',
            ],
            timeout=4000,
        )
        if publish_article_btn:
            await publish_article_btn.click()
            await asyncio.sleep(3)
            return
        await self.page.goto(
            "https://zhuanlan.zhihu.com/write",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        await asyncio.sleep(3)

    async def _wait_editor_ready(
        self,
        progress_callback: Optional[Callable[[str], None]],
    ) -> None:
        self._report_progress(progress_callback, "等待编辑器加载...")
        editor_loaded = False
        for selector in [
            ".public-DraftEditor-content",
            ".DraftEditor-root",
            '[contenteditable="true"]',
            ".RichText-editor",
        ]:
            try:
                await self.page.wait_for_selector(selector, timeout=5000)
                editor_loaded = True
                break
            except Exception:
                continue
        if not editor_loaded:
            print("[WARN] 未检测到编辑器，继续尝试输入")
        await asyncio.sleep(1.5)

    async def _wait_first_selector(self, selectors: list[str], timeout: int):
        for selector in selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=timeout)
                if element:
                    return element
            except Exception:
                continue
        return None

    async def _find_first_selector(self, selectors: list[str]):
        for selector in selectors:
            element = await self.page.query_selector(selector)
            if element:
                return element
        return None

    async def _input_article_title(
        self,
        title: str,
        progress_callback: Optional[Callable[[str], None]],
    ) -> None:
        self._report_progress(progress_callback, "输入标题...")
        title_input = await self._find_first_selector(
            [
                'div[placeholder*="请输入标题"]',
                'div[data-text*="请输入标题"]',
                '[contenteditable="true"][placeholder*="标题"]',
                'input[placeholder*="标题"]',
                'textarea[placeholder*="标题"]',
            ]
        )
        if title_input:
            await title_input.click()
            await asyncio.sleep(0.4)
            await self.page.keyboard.press("Control+A")
            await asyncio.sleep(0.2)
        await self._insert_text_with_fallback(title, type_delay=25)
        await self.page.keyboard.press("Tab")
        await asyncio.sleep(0.4)

    async def _input_article_content(
        self,
        content: str,
        progress_callback: Optional[Callable[[str], None]],
    ) -> None:
        self._report_progress(progress_callback, "输入内容...")
        editor = await self._find_first_selector(
            [
                'div[placeholder*="请输入正文"]',
                'div[data-text*="请输入正文"]',
                '[contenteditable="true"]',
                ".public-DraftEditor-content",
                ".DraftEditor-root",
                ".RichText-editor",
            ]
        )
        if editor:
            await editor.click()
        else:
            await self.page.mouse.click(500, 500)
        await asyncio.sleep(0.6)

        paragraphs = content.split("\n")
        valid_paragraphs = [x for x in paragraphs if x.strip()]
        total_paragraphs = len(valid_paragraphs) if valid_paragraphs else 1
        current = 0
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
            current += 1
            await self._insert_text_with_fallback(paragraph.strip(), type_delay=8)
            await self.page.keyboard.press("Enter")
            if current % 5 == 0 and progress_callback:
                progress = int((current / total_paragraphs) * 100)
                progress_callback(f"正在输入内容... {progress}%")
            if current % 10 == 0:
                await asyncio.sleep(0.4)
        self._report_progress(progress_callback, "内容已填充完成，请在浏览器中检查并点击发布")

    async def _insert_text_with_fallback(self, text: str, type_delay: int) -> None:
        try:
            await self.page.keyboard.insert_text(text)
        except Exception:
            await self.page.keyboard.type(text, delay=type_delay)

    async def _wait_for_manual_publish(self) -> tuple[bool, str]:
        try:
            await self.page.wait_for_url("**/p/**", timeout=180000)
            return True, self.page.url
        except Exception:
            return True, "文章内容已填充，等待手动发布"

    async def close(self):
        try:
            if self.page:
                try:
                    await self.page.close()
                except Exception:
                    pass
            if self.browser:
                try:
                    await self.browser.close()
                except Exception:
                    pass
            if self.playwright:
                try:
                    await self.playwright.stop()
                except Exception:
                    pass
        finally:
            self.page = None
            self.browser = None
            self.playwright = None


def publish_to_zhihu_sync(
    title: str,
    content: str,
    headless: bool = False,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> tuple[bool, str]:
    async def _run():
        publisher = ZhihuPublisher(headless=headless)
        try:
            if not await publisher.initialize():
                return False, "初始化浏览器失败"
            result = await publisher.publish_article(title, content, progress_callback)
            # 不关闭浏览器，让用户自行操作后关闭
            return result
        except Exception as e:
            await publisher.close()
            raise

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_run())
        # 注意：不关闭 loop，不取消 tasks，不 stop playwright
        # 浏览器由 playwright 管理，loop 关闭 = playwright 断开 = 浏览器关闭
        # 让 loop 和 publisher 自然存活，用户关闭浏览器窗口后自行回收
    except Exception as e:
        return False, f"执行失败: {str(e)}"
