"""
知乎发布服务 - 使用 Playwright 自动发布文章到知乎
"""

import asyncio
import time
from pathlib import Path
from typing import Optional, Callable
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout


class ZhihuPublisher:
    """知乎自动发布服务"""
    
    def __init__(self, headless: bool = False):
        """
        初始化知乎发布器
        
        Args:
            headless: 是否使用无头模式（True=后台运行，False=显示浏览器）
        """
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.user_data_dir = Path.home() / ".zhihu_publisher"
        self.playwright = None  # 保存 playwright 实例以便清理
        
    async def initialize(self) -> bool:
        """
        初始化浏览器
        
        Returns:
            是否成功初始化
        """
        try:
            self.playwright = await async_playwright().start()
            
            # 使用持久化上下文（保存登录状态）
            # 添加反检测参数
            self.browser = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                headless=self.headless,
                viewport={'width': 1280, 'height': 800},
                locale='zh-CN',
                # 反检测设置
                args=[
                    '--disable-blink-features=AutomationControlled',  # 禁用自动化控制提示
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ],
                # 设置用户代理
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # 注入反检测脚本
            await self.browser.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                window.navigator.chrome = {
                    runtime: {},
                };
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en'],
                });
            """)
            
            self.page = await self.browser.new_page()
            return True
            
        except Exception as e:
            print(f"[ERROR] 初始化浏览器失败: {e}")
            return False
    
    async def check_login_status(self) -> bool:
        """
        检查是否已登录知乎
        
        Returns:
            是否已登录
        """
        try:
            print("[INFO] 正在访问知乎首页...")
            
            # 使用更宽松的等待策略
            await self.page.goto('https://www.zhihu.com', 
                                wait_until='domcontentloaded',
                                timeout=30000)
            
            # 等待页面稳定
            await asyncio.sleep(2)
            
            # 检查是否存在登录按钮（未登录状态）
            login_button = await self.page.query_selector('button:has-text("登录")')
            
            if login_button:
                print("[INFO] 未登录知乎")
                return False
            
            # 检查是否有用户头像（已登录状态）
            user_avatar = await self.page.query_selector('.AppHeader-profile')
            
            if user_avatar:
                print("[OK] 已登录知乎")
                return True
            
            # 如果都没找到，可能页面结构变化，检查URL
            current_url = self.page.url
            if 'signin' in current_url or 'login' in current_url:
                print("[INFO] 当前在登录页面")
                return False
            
            # 尝试其他登录标识
            # 检查是否有创作中心入口（只有登录用户才有）
            creator_link = await self.page.query_selector('a[href*="creator"]')
            if creator_link:
                print("[OK] 检测到创作中心入口，已登录")
                return True
            
            print("[WARN] 无法确定登录状态，假设未登录")
            return False
            
        except Exception as e:
            print(f"[ERROR] 检查登录状态失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def wait_for_manual_login(self, timeout: int = 300) -> bool:
        """
        等待用户手动登录
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            是否成功登录
        """
        try:
            print(f"[INFO] 请在 {timeout} 秒内完成登录")
            print("[INFO] 提示：可以使用扫码或密码登录")
            
            # 先尝试跳转到登录页
            try:
                await self.page.goto('https://www.zhihu.com/signin', 
                                    wait_until='domcontentloaded',
                                    timeout=30000)
            except Exception as e:
                print(f"[WARN] 跳转登录页异常: {e}")
                # 如果跳转失败，用户可能已经在登录页或首页
            
            await asyncio.sleep(2)
            
            # 等待登录完成
            start_time = time.time()
            check_count = 0
            
            while time.time() - start_time < timeout:
                check_count += 1
                
                # 每10秒提醒一次
                if check_count % 5 == 0:
                    remaining = int(timeout - (time.time() - start_time))
                    print(f"[INFO] 等待登录... (剩余 {remaining} 秒)")
                
                # 检查登录状态
                try:
                    # 检查是否有用户头像
                    user_avatar = await self.page.query_selector('.AppHeader-profile')
                    if user_avatar:
                        print("[OK] 检测到登录成功！")
                        await asyncio.sleep(1)
                        return True
                    
                    # 检查URL是否已经跳转到首页或创作中心
                    current_url = self.page.url
                    if 'signin' not in current_url and 'login' not in current_url:
                        # 已经离开登录页，可能登录成功
                        await asyncio.sleep(1)
                        if await self.check_login_status():
                            return True
                
                except Exception as e:
                    print(f"[DEBUG] 登录检查异常: {e}")
                
                await asyncio.sleep(2)
            
            print("[ERROR] 登录超时")
            return False
            
        except Exception as e:
            print(f"[ERROR] 等待登录失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def publish_article(
        self,
        title: str,
        content: str,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> tuple[bool, str]:
        """
        发布文章到知乎
        
        Args:
            title: 文章标题
            content: 文章内容
            progress_callback: 进度回调函数
            
        Returns:
            (是否成功, 错误信息或文章链接)
        """
        try:
            # 1. 检查登录状态
            if progress_callback:
                progress_callback("检查登录状态...")
            
            if not await self.check_login_status():
                if progress_callback:
                    progress_callback("需要登录，请在浏览器中完成登录")
                
                if not await self.wait_for_manual_login():
                    return False, "登录超时或失败"
            
            # 2. 进入创作页面
            if progress_callback:
                progress_callback("打开创作中心...")
            
            print("[INFO] 正在打开创作中心...")
            
            # 步骤1：点击「创作中心」
            try:
                # 先确保在知乎首页
                await self.page.goto('https://www.zhihu.com', 
                                    wait_until='domcontentloaded',
                                    timeout=30000)
                await asyncio.sleep(2)
                
                # 查找并点击「创作中心」按钮
                creator_btn = await self.page.query_selector('a[href*="creator"], button:has-text("创作中心")')
                if creator_btn:
                    print("[INFO] 找到创作中心按钮，点击...")
                    await creator_btn.click()
                    await asyncio.sleep(3)
                else:
                    # 如果找不到，直接跳转到创作中心
                    print("[INFO] 直接跳转到创作中心页面...")
                    await self.page.goto('https://www.zhihu.com/creator', 
                                        wait_until='domcontentloaded',
                                        timeout=30000)
                    await asyncio.sleep(3)
                
                print("[OK] 已进入创作中心")
                
            except Exception as e:
                print(f"[WARN] 进入创作中心异常: {e}")
                # 继续尝试下一步
            
            # 步骤2：点击「内容创作」下的「发布想法」按钮展开菜单
            if progress_callback:
                progress_callback("打开内容创作菜单...")
            
            try:
                print("[INFO] 查找「内容创作」按钮...")
                
                # 可能的选择器
                content_create_btn = await self.page.query_selector('button:has-text("内容创作"), div:has-text("内容创作")')
                
                if content_create_btn:
                    print("[INFO] 找到「内容创作」按钮，点击...")
                    await content_create_btn.click()
                    await asyncio.sleep(1.5)
                else:
                    print("[WARN] 未找到「内容创作」按钮")
                
            except Exception as e:
                print(f"[WARN] 点击内容创作异常: {e}")
            
            # 步骤3：点击「发布文章」
            if progress_callback:
                progress_callback("点击发布文章...")
            
            try:
                print("[INFO] 查找「发布文章」选项...")
                
                # 等待菜单出现并查找「发布文章」
                publish_article_btn = await self.page.wait_for_selector(
                    'button:has-text("发布文章"), a:has-text("发布文章"), div:has-text("发布文章")',
                    timeout=5000
                )
                
                if publish_article_btn:
                    print("[INFO] 找到「发布文章」，点击...")
                    await publish_article_btn.click()
                    await asyncio.sleep(3)
                    print("[OK] 已打开文章编辑器")
                else:
                    print("[WARN] 未找到「发布文章」按钮，尝试直接跳转...")
                    # 直接跳转到写文章页面
                    await self.page.goto('https://zhuanlan.zhihu.com/write', 
                                        wait_until='domcontentloaded',
                                        timeout=30000)
                    await asyncio.sleep(3)
                
            except PlaywrightTimeout:
                print("[WARN] 等待「发布文章」超时，尝试直接跳转...")
                await self.page.goto('https://zhuanlan.zhihu.com/write', 
                                    wait_until='domcontentloaded',
                                    timeout=30000)
                await asyncio.sleep(3)
            except Exception as e:
                print(f"[ERROR] 点击发布文章失败: {e}")
                # 最后尝试直接跳转
                print("[INFO] 尝试直接跳转到编辑器...")
                await self.page.goto('https://zhuanlan.zhihu.com/write', 
                                    wait_until='domcontentloaded',
                                    timeout=30000)
                await asyncio.sleep(3)
            
            # 4. 等待编辑器加载
            if progress_callback:
                progress_callback("等待编辑器加载...")
            
            print("[INFO] 等待编辑器加载...")
            
            # 等待富文本编辑器出现（使用多种选择器）
            editor_loaded = False
            editor_selectors = [
                '.public-DraftEditor-content',  # Draft.js 编辑器
                '.DraftEditor-root',
                '[contenteditable="true"]',     # 通用可编辑区域
                '.RichText-editor',
            ]
            
            for selector in editor_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    print(f"[OK] 编辑器已加载 (selector: {selector})")
                    editor_loaded = True
                    break
                except PlaywrightTimeout:
                    continue
            
            if not editor_loaded:
                print("[WARN] 未检测到编辑器，但继续尝试...")
            
            await asyncio.sleep(2)
            
            # 5. 输入标题
            if progress_callback:
                progress_callback("输入标题...")
            
            print(f"[INFO] 正在输入标题: {title[:30]}...")
            
            # 根据实际页面，标题区域的placeholder是"请输入标题（最多 100 个字）"
            title_input = None
            title_selectors = [
                'div[placeholder*="请输入标题"]',  # 知乎新版编辑器使用div而不是input
                'div[data-text*="请输入标题"]',
                '[contenteditable="true"][placeholder*="标题"]',
                'input[placeholder*="标题"]',
                'textarea[placeholder*="标题"]',
            ]
            
            for selector in title_selectors:
                title_input = await self.page.query_selector(selector)
                if title_input:
                    print(f"[OK] 找到标题输入框 (selector: {selector})")
                    break
            
            if title_input:
                try:
                    # 点击标题区域获取焦点
                    await title_input.click()
                    await asyncio.sleep(0.5)
                    
                    # 清空现有内容
                    await self.page.keyboard.press('Control+A')
                    await asyncio.sleep(0.2)
                    
                    # 输入新标题
                    await self.page.keyboard.type(title, delay=30)  # 模拟真实输入速度
                    print(f"[OK] 标题已输入: {title[:30]}...")
                    
                    # 输入回车或Tab，跳到内容区域
                    await self.page.keyboard.press('Tab')
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    print(f"[WARN] 输入标题异常: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("[WARN] 未找到标题输入框，尝试通过键盘输入")
                # 作为后备，直接在页面上输入
                await self.page.keyboard.type(title, delay=30)
                await self.page.keyboard.press('Tab')
                await asyncio.sleep(0.5)
            
            await asyncio.sleep(1)
            
            # 6. 输入内容
            if progress_callback:
                progress_callback("输入内容...")
            
            print(f"[INFO] 正在输入内容，共 {len(content)} 字符...")
            
            # 根据实际页面，内容区域的placeholder是"请输入正文"
            editor = None
            editor_selectors = [
                'div[placeholder*="请输入正文"]',  # 知乎新版编辑器
                'div[data-text*="请输入正文"]',
                '[contenteditable="true"]',  # 通用可编辑区域
                '.public-DraftEditor-content',
                '.DraftEditor-root',
                '.RichText-editor',
            ]
            
            for selector in editor_selectors:
                editor = await self.page.query_selector(selector)
                if editor:
                    print(f"[OK] 找到内容编辑器 (selector: {selector})")
                    break
            
            # 如果标题后已经按了Tab，焦点应该已经在内容区域了
            # 先尝试直接输入
            if not editor:
                print("[INFO] 未找到特定编辑器，尝试直接在当前焦点输入")
            
            if editor or True:  # 无论是否找到编辑器都尝试
                try:
                    # 如果找到编辑器，点击获取焦点
                    if editor:
                        await editor.click()
                        await asyncio.sleep(0.8)
                    else:
                        # 如果没找到，尝试点击页面中间位置（通常是编辑区域）
                        await self.page.mouse.click(500, 500)
                        await asyncio.sleep(0.8)
                    
                    # 将内容按段落分割并输入
                    paragraphs = content.split('\n')
                    total_paragraphs = len([p for p in paragraphs if p.strip()])
                    current_paragraph = 0
                    
                    for i, paragraph in enumerate(paragraphs):
                        if paragraph.strip():
                            current_paragraph += 1
                            
                            # 使用更快的输入方式（直接输入而不是逐字符）
                            await self.page.keyboard.type(paragraph.strip(), delay=10)
                            await self.page.keyboard.press('Enter')
                            
                            # 每5段给个进度更新
                            if current_paragraph % 5 == 0 and progress_callback:
                                progress = int((current_paragraph / total_paragraphs) * 100)
                                progress_callback(f"正在输入内容... {progress}%")
                            
                            # 适当延迟，避免输入过快
                            if current_paragraph % 10 == 0:
                                await asyncio.sleep(0.5)
                    
                    print(f"[OK] 内容已输入，共 {len(content)} 字符，{total_paragraphs} 段")
                    
                except Exception as e:
                    print(f"[ERROR] 输入内容失败: {e}")
                    import traceback
                    traceback.print_exc()
                    return False, f"输入内容失败: {str(e)}"
            else:
                print("[WARN] 未找到编辑器，尝试直接输入")
                try:
                    # 作为后备，直接输入
                    await self.page.keyboard.type(content, delay=10)
                    print("[OK] 内容已通过键盘输入")
                except Exception as e:
                    return False, f"未找到编辑器且键盘输入失败: {str(e)}"
            
            # 7. 等待用户手动发布
            if progress_callback:
                progress_callback("内容已填充完成，请在浏览器中检查并点击发布")
            
            print("[INFO] 文章内容已填充，请手动检查并发布")
            print("[INFO] 您可以：")
            print("  1. 检查标题和内容")
            print("  2. 添加封面图片")
            print("  3. 选择话题标签")
            print("  4. 点击「发布」按钮")
            
            # 等待发布完成（检测URL变化或成功提示）
            try:
                # 等待URL变化（发布后会跳转到文章页）或超时
                await self.page.wait_for_url('**/p/**', timeout=180000)  # 3分钟超时
                
                article_url = self.page.url
                print(f"[OK] 文章已发布: {article_url}")
                
                if progress_callback:
                    progress_callback(f"发布成功！")
                
                return True, article_url
                
            except PlaywrightTimeout:
                # 超时可能意味着用户未发布
                print("[INFO] 未检测到发布完成")
                return True, "文章内容已填充，等待手动发布"
            
        except Exception as e:
            error_msg = f"发布过程出错: {str(e)}"
            print(f"[ERROR] {error_msg}")
            import traceback
            traceback.print_exc()
            
            if progress_callback:
                progress_callback(f"错误: {error_msg}")
            
            return False, error_msg
    
    async def close(self):
        """关闭浏览器和清理资源"""
        try:
            # 关闭页面
            if self.page:
                try:
                    await self.page.close()
                except Exception:
                    pass
            
            # 关闭浏览器
            if self.browser:
                try:
                    await self.browser.close()
                    print("[OK] 浏览器已关闭")
                except Exception as e:
                    print(f"[WARN] 关闭浏览器异常: {e}")
            
            # 停止 playwright
            if self.playwright:
                try:
                    await self.playwright.stop()
                    print("[OK] Playwright 已停止")
                except Exception as e:
                    print(f"[WARN] 停止 Playwright 异常: {e}")
            
            # 清空引用
            self.page = None
            self.browser = None
            self.playwright = None
            
        except Exception as e:
            print(f"[ERROR] 清理资源失败: {e}")


# 同步包装函数（供Tkinter使用）
def publish_to_zhihu_sync(
    title: str,
    content: str,
    headless: bool = False,
    progress_callback: Optional[Callable[[str], None]] = None
) -> tuple[bool, str]:
    """
    同步版本的知乎发布函数
    
    Args:
        title: 文章标题
        content: 文章内容
        headless: 是否使用无头模式
        progress_callback: 进度回调函数
        
    Returns:
        (是否成功, 错误信息或文章链接)
    """
    async def _run():
        publisher = ZhihuPublisher(headless=headless)
        
        try:
            if not await publisher.initialize():
                return False, "初始化浏览器失败"
            
            return await publisher.publish_article(title, content, progress_callback)
            
        finally:
            # 确保资源被清理
            await publisher.close()
    
    # 在新的事件循环中运行
    loop = None
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_run())
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"执行失败: {str(e)}"
    finally:
        # 确保事件循环被正确关闭
        if loop:
            try:
                # 取消所有待处理的任务
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                
                # 等待所有任务完成
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                
                # 关闭事件循环
                loop.close()
            except Exception as e:
                print(f"[WARN] 关闭事件循环异常: {e}")

