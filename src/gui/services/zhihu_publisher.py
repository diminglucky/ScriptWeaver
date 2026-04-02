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
            if progress_callback:
                progress_callback("检查登录状态...")
            if not await self.check_login_status():
                if progress_callback:
                    progress_callback("需要登录，请在浏览器中完成登录")
                if not await self.wait_for_manual_login():
                    return False, "登录超时或失败"

            if progress_callback:
                progress_callback("打开创作中心...")
            await self.page.goto("https://www.zhihu.com", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            creator_btn = await self.page.query_selector('a[href*="creator"], button:has-text("创作中心")')
            if creator_btn:
                await creator_btn.click()
                await asyncio.sleep(3)
            else:
                await self.page.goto("https://www.zhihu.com/creator", wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)

            if progress_callback:
                progress_callback("点击发布文章...")
            try:
                content_create_btn = await self.page.query_selector(
                    'button:has-text("内容创作"), div:has-text("内容创作")'
                )
                if content_create_btn:
                    await content_create_btn.click()
                    await asyncio.sleep(1.5)
            except Exception:
                pass

            publish_article_btn = None
            selectors = [
                'button:has-text("发布文章")',
                'a:has-text("发布文章")',
                'div:has-text("发布文章")',
            ]
            for selector in selectors:
                try:
                    publish_article_btn = await self.page.wait_for_selector(selector, timeout=4000)
                    if publish_article_btn:
                        break
                except Exception:
                    continue

            if publish_article_btn:
                await publish_article_btn.click()
                await asyncio.sleep(3)
            else:
                await self.page.goto("https://zhuanlan.zhihu.com/write", wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)

            if progress_callback:
                progress_callback("等待编辑器加载...")
            editor_loaded = False
            for selector in [
                '.public-DraftEditor-content',
                '.DraftEditor-root',
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

            if progress_callback:
                progress_callback("输入标题...")
            title_input = None
            for selector in [
                'div[placeholder*="请输入标题"]',
                'div[data-text*="请输入标题"]',
                '[contenteditable="true"][placeholder*="标题"]',
                'input[placeholder*="标题"]',
                'textarea[placeholder*="标题"]',
            ]:
                title_input = await self.page.query_selector(selector)
                if title_input:
                    break

            if title_input:
                await title_input.click()
                await asyncio.sleep(0.4)
                await self.page.keyboard.press("Control+A")
                await asyncio.sleep(0.2)
                try:
                    await self.page.keyboard.insert_text(title)
                except Exception:
                    await self.page.keyboard.type(title, delay=25)
                await self.page.keyboard.press("Tab")
                await asyncio.sleep(0.4)
            else:
                try:
                    await self.page.keyboard.insert_text(title)
                except Exception:
                    await self.page.keyboard.type(title, delay=25)
                await self.page.keyboard.press("Tab")
                await asyncio.sleep(0.4)

            if progress_callback:
                progress_callback("输入内容...")
            editor = None
            for selector in [
                'div[placeholder*="请输入正文"]',
                'div[data-text*="请输入正文"]',
                '[contenteditable="true"]',
                ".public-DraftEditor-content",
                ".DraftEditor-root",
                ".RichText-editor",
            ]:
                editor = await self.page.query_selector(selector)
                if editor:
                    break

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
                text = paragraph.strip()
                try:
                    await self.page.keyboard.insert_text(text)
                except Exception:
                    await self.page.keyboard.type(text, delay=8)
                await self.page.keyboard.press("Enter")
                if current % 5 == 0 and progress_callback:
                    progress = int((current / total_paragraphs) * 100)
                    progress_callback(f"正在输入内容... {progress}%")
                if current % 10 == 0:
                    await asyncio.sleep(0.4)

            if progress_callback:
                progress_callback("内容已填充完成，请在浏览器中检查并点击发布")

            # Wait user publish manually; detect redirect to article URL.
            try:
                await self.page.wait_for_url("**/p/**", timeout=180000)
                return True, self.page.url
            except Exception:
                return True, "文章内容已填充，等待手动发布"
        except Exception as e:
            msg = f"发布过程出错: {str(e)}"
            if progress_callback:
                progress_callback(f"错误: {msg}")
            return False, msg

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
            return await publisher.publish_article(title, content, progress_callback)
        finally:
            await publisher.close()

    loop = None
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_run())
    except Exception as e:
        return False, f"执行失败: {str(e)}"
    finally:
        if loop:
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                loop.close()
            except Exception:
                pass
