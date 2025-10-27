"""
知乎发布服务 - 使用 Playwright 自动发布文章到知乎
"""

import asyncio
import time
import re
from pathlib import Path
from typing import Optional, Callable, List
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
        # 输入验证
        if not title or not title.strip():
            return False, "标题不能为空"
        
        if not content or not content.strip():
            return False, "内容不能为空"
        
        title = title.strip()
        content = content.strip()
        
        if len(title) > 100:
            return False, "标题过长（最多100字）"
        
        if len(content) < 100:
            return False, "内容过短（至少100字）"
        
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
            
            # 7. 自动完成发布前的设置
            await asyncio.sleep(2)  # 等待页面加载完成
            
            # 7.1 投稿至问题
            if progress_callback:
                progress_callback("正在选择投稿问题...")
            
            try:
                print("[INFO] 正在处理投稿至问题...")
                # 方法1：通过文本找到"投稿至问题"标签后，点击其下拉框
                # 等待页面元素加载
                await asyncio.sleep(1)
                
                # 使用更通用的选择器找到投稿至问题区域并点击
                # 直接查找包含"未选择"文本的元素（这通常是下拉框）
                dropdown_trigger = await self.page.query_selector('text="未选择"')
                if not dropdown_trigger:
                    dropdown_trigger = await self.page.query_selector('text="投稿至问题" >> .. >> div[role="button"]')
                if not dropdown_trigger:
                    # 尝试通过 CSS 选择器查找
                    dropdown_trigger = await self.page.query_selector('div:has-text("投稿至问题") ~ div')
                
                if dropdown_trigger:
                    await dropdown_trigger.click()
                    print("[INFO] 已点击投稿至问题下拉框")
                    await asyncio.sleep(2.5)  # 等待弹窗完全加载和稳定
                    
                    # 关键：先定位弹窗元素，然后在弹窗内部查找按钮
                    print("[INFO] 正在定位投稿问题弹窗...")
                    
                    # 查找弹窗容器
                    modal = None
                    modal_selectors = [
                        'div[role="dialog"]',
                        'div[class*="Modal"]',
                        'div[class*="QuestionModal"]',
                        '[class*="ArticleQuestionModal"]'
                    ]
                    
                    for selector in modal_selectors:
                        try:
                            modal = await self.page.query_selector(selector)
                            if modal:
                                is_visible = await modal.is_visible()
                                if is_visible:
                                    print(f"[INFO] 找到弹窗容器 (selector: {selector})")
                                    break
                                else:
                                    modal = None
                        except Exception:
                            continue
                    
                    if not modal:
                        print("[WARN] 未找到弹窗容器，尝试直接查找按钮")
                    
                    # 在弹窗内部查找第一个"选择"按钮
                    print("[INFO] 正在弹窗内查找第一个问题的选择按钮...")
                    select_button = None
                    
                    if modal:
                        # 在弹窗内部查找
                        try:
                            # 在弹窗内查找所有"选择"按钮
                            all_select_buttons = await modal.query_selector_all('button:has-text("选择")')
                            print(f"[INFO] 在弹窗内找到 {len(all_select_buttons)} 个选择按钮")
                            
                            if all_select_buttons:
                                # 选择第一个可见的
                                for i, btn in enumerate(all_select_buttons):
                                    is_visible = await btn.is_visible()
                                    if is_visible:
                                        select_button = btn
                                        print(f"[INFO] 选择弹窗内第 {i+1} 个可见的选择按钮")
                                        break
                        except Exception as e:
                            print(f"[DEBUG] 在弹窗内查找失败: {e}")
                    
                    # 如果在弹窗内没找到，尝试全局查找（带弹窗限定）
                    if not select_button:
                        print("[INFO] 尝试全局查找（带弹窗限定）...")
                        select_selectors = [
                            'div[role="dialog"] >> button:has-text("选择") >> nth=0',
                            '[class*="Modal"] >> button:has-text("选择") >> nth=0',
                            '[class*="QuestionItem"] button:has-text("选择") >> nth=0'
                        ]
                        
                        for selector in select_selectors:
                            try:
                                select_button = await self.page.query_selector(selector)
                                if select_button:
                                    is_visible = await select_button.is_visible()
                                    if is_visible:
                                        print(f"[INFO] 找到选择按钮 (selector: {selector})")
                                        break
                                    else:
                                        select_button = None
                            except Exception as e:
                                print(f"[DEBUG] selector {selector} 失败: {e}")
                                continue
                    
                    if select_button:
                        # 点击"选择"按钮
                        await select_button.click()
                        print("[OK] 已点击「选择」按钮")
                        await asyncio.sleep(1)
                        
                        # 点击"确定"按钮确认选择
                        print("[INFO] 正在弹窗内查找确定按钮...")
                        await asyncio.sleep(1)  # 等待UI更新
                        
                        confirm_btn = None
                        
                        # 优先在弹窗内部查找
                        if modal:
                            try:
                                all_confirm_buttons = await modal.query_selector_all('button:has-text("确定")')
                                print(f"[INFO] 在弹窗内找到 {len(all_confirm_buttons)} 个确定按钮")
                                
                                if all_confirm_buttons:
                                    for i, btn in enumerate(all_confirm_buttons):
                                        is_visible = await btn.is_visible()
                                        if is_visible:
                                            confirm_btn = btn
                                            print(f"[INFO] 选择弹窗内第 {i+1} 个可见的确定按钮")
                                            break
                            except Exception as e:
                                print(f"[DEBUG] 在弹窗内查找确定按钮失败: {e}")
                        
                        # 如果在弹窗内没找到，使用全局查找（带弹窗限定）
                        if not confirm_btn:
                            print("[INFO] 尝试全局查找确定按钮（带弹窗限定）...")
                            confirm_selectors = [
                                'div[role="dialog"] >> button:has-text("确定")',
                                '[class*="Modal"] >> button:has-text("确定")',
                                'div[role="dialog"] >> button.Button--primary',
                                '[class*="Modal"] >> button.Button--primary:has-text("确定")'
                            ]
                            
                            for selector in confirm_selectors:
                                try:
                                    confirm_btn = await self.page.query_selector(selector)
                                    if confirm_btn:
                                        is_visible = await confirm_btn.is_visible()
                                        if is_visible:
                                            print(f"[INFO] 找到确定按钮 (selector: {selector})")
                                            break
                                        else:
                                            confirm_btn = None
                                except Exception as e:
                                    print(f"[DEBUG] selector {selector} 失败: {e}")
                                    continue
                        
                        if confirm_btn:
                            await confirm_btn.click()
                            print("[OK] ✅ 已点击「确定」按钮，问题选择完成！")
                            await asyncio.sleep(1.5)
                        else:
                            print("[WARN] 未找到「确定」按钮，可能需要手动点击")
                    else:
                        print("[WARN] 未找到「选择」按钮")
                else:
                    print("[WARN] 未找到投稿至问题下拉框")
            except Exception as e:
                print(f"[WARN] 投稿至问题设置失败（可选操作）: {e}")
            
            # 7.2 设置创作声明为"虚构创作"
            if progress_callback:
                progress_callback("正在设置创作声明...")
            
            try:
                print("[INFO] 正在设置创作声明...")
                # 查找"创作声明"下拉框（显示"无声明"或其他默认值）
                await asyncio.sleep(1)
                
                # 尝试多种方式查找创作声明下拉框
                declaration_dropdown = await self.page.query_selector('text="无声明"')
                if not declaration_dropdown:
                    declaration_dropdown = await self.page.query_selector('text="创作声明" >> .. >> div[role="button"]')
                if not declaration_dropdown:
                    # 通过 CSS 查找
                    declaration_dropdown = await self.page.query_selector('div:has-text("创作声明") ~ div')
                
                if declaration_dropdown:
                    await declaration_dropdown.click()
                    print("[INFO] 已点击创作声明下拉框")
                    await asyncio.sleep(1)
                    
                    # 在下拉列表中选择"虚构创作"
                    fiction_selectors = [
                        'text="虚构创作"',
                        'div:has-text("虚构创作")',
                        'li:has-text("虚构创作")',
                        'div[role="option"]:has-text("虚构创作")'
                    ]
                    
                    for selector in fiction_selectors:
                        fiction_option = await self.page.query_selector(selector)
                        if fiction_option:
                            await fiction_option.click()
                            print("[OK] 已设置创作声明为「虚构创作」")
                            await asyncio.sleep(0.5)
                            break
                else:
                    print("[WARN] 未找到创作声明下拉框")
            except Exception as e:
                print(f"[WARN] 创作声明设置失败（可选操作）: {e}")
            
            # 7.3 提取并添加话题词
            if progress_callback:
                progress_callback("正在添加话题标签...")
            
            try:
                print("[INFO] 正在提取话题词...")
                await asyncio.sleep(1)
                
                # 使用简单的关键词提取
                topics = await self._extract_topics_from_content(title, content)
                
                if topics:
                    print(f"[INFO] 提取到话题词: {', '.join(topics)}")
                    
                    # 查找"文章话题"区域的添加按钮
                    add_topic_selectors = [
                        'text="+ 添加话题"',
                        'button:has-text("添加话题")',
                        'div:has-text("添加话题")',
                        'text="文章话题" >> .. >> button'
                    ]
                    
                    add_topic_btn = None
                    for selector in add_topic_selectors:
                        add_topic_btn = await self.page.query_selector(selector)
                        if add_topic_btn:
                            print(f"[INFO] 找到添加话题按钮 (selector: {selector})")
                            break
                    
                    if add_topic_btn:
                        # 只添加第一个话题即可
                        topic = topics[0]
                        try:
                            print(f"[INFO] 准备添加话题: {topic}")
                            await add_topic_btn.click()
                            await asyncio.sleep(1)
                            
                            # 输入话题 - 尝试多种输入框选择器
                            topic_input = None
                            input_selectors = [
                                'input[placeholder*="话题"]',
                                'input[placeholder*="搜索"]',
                                'input[type="text"]:visible',
                                'input:focus'
                            ]
                            
                            for selector in input_selectors:
                                topic_input = await self.page.query_selector(selector)
                                if topic_input:
                                    print(f"[INFO] 找到话题输入框 (selector: {selector})")
                                    break
                            
                            if topic_input:
                                # 清空并输入话题
                                await topic_input.fill('')
                                await asyncio.sleep(0.3)
                                await topic_input.type(topic, delay=80)
                                print(f"[INFO] 已输入话题文字: {topic}")
                                await asyncio.sleep(1.5)  # 等待下拉列表出现
                                
                                # 点击下拉列表中的第一个选项
                                print("[INFO] 正在查找话题下拉选项...")
                                await asyncio.sleep(0.5)  # 确保下拉列表完全展开
                                
                                topic_option = None
                                
                                # 方法1：直接使用nth=0获取第一个选项
                                print("[INFO] 方法1: 使用nth=0获取第一个选项...")
                                try:
                                    topic_option = await self.page.query_selector('div[role="option"] >> nth=0')
                                    if topic_option:
                                        is_visible = await topic_option.is_visible()
                                        if is_visible:
                                            print(f"[OK] 找到第一个话题选项 (nth=0)")
                                        else:
                                            print(f"[DEBUG] 第一个选项不可见")
                                            topic_option = None
                                except Exception as e:
                                    print(f"[DEBUG] nth=0方法失败: {e}")
                                    topic_option = None
                                
                                # 方法2：获取所有选项，打印详情，选第一个可见的
                                if not topic_option:
                                    print("[INFO] 方法2: 遍历所有选项...")
                                    try:
                                        all_options = await self.page.query_selector_all('div[role="option"]')
                                        print(f"[INFO] 找到 {len(all_options)} 个话题选项")
                                        
                                        if all_options:
                                            # 遍历找到第一个可见的
                                            for i, option in enumerate(all_options):
                                                is_visible = await option.is_visible()
                                                
                                                # 获取选项文本
                                                try:
                                                    option_text = await option.inner_text()
                                                    print(f"[DEBUG] 选项 {i+1}: '{option_text[:20]}...' (visible={is_visible})")
                                                except:
                                                    print(f"[DEBUG] 选项 {i+1}: (visible={is_visible})")
                                                
                                                if is_visible and i == 0:  # 确保是第一个
                                                    topic_option = option
                                                    print(f"[OK] ✅ 确认选择第 1 个话题选项")
                                                    break
                                    except Exception as e:
                                        print(f"[DEBUG] 方法2失败: {e}")
                                
                                # 方法3：使用first-of-type
                                if not topic_option:
                                    print("[INFO] 方法3: 使用first-of-type...")
                                    try:
                                        topic_option = await self.page.query_selector('div[role="option"]:first-of-type')
                                        if topic_option and await topic_option.is_visible():
                                            print(f"[OK] 找到第一个话题选项 (first-of-type)")
                                        else:
                                            topic_option = None
                                    except Exception as e:
                                        print(f"[DEBUG] first-of-type失败: {e}")
                                
                                if topic_option:
                                    # 点击选择话题
                                    await topic_option.click()
                                    print(f"[OK] ✅ 已点击话题选项")
                                    await asyncio.sleep(1)
                                else:
                                    # 如果没找到下拉选项，尝试按回车
                                    print("[WARN] 未找到话题下拉选项，尝试按回车")
                                    await self.page.keyboard.press('Enter')
                                    await asyncio.sleep(1)
                                
                                print(f"[OK] 话题添加完成: {topic}")
                            else:
                                print(f"[WARN] 未找到话题输入框")
                        except Exception as e:
                            print(f"[WARN] 添加话题失败: {e}")
                    else:
                        print("[WARN] 未找到添加话题按钮")
                else:
                    print("[INFO] 未提取到合适的话题词，跳过话题添加")
            except Exception as e:
                print(f"[WARN] 话题添加失败（可选操作）: {e}")
            
            # 7.4 点击发布按钮
            if progress_callback:
                progress_callback("正在发布文章...")
            
            try:
                print("\n" + "="*60)
                print("🚀 准备点击发布按钮")
                print("="*60)
                
                await asyncio.sleep(2.5)  # 等待页面稳定
                
                publish_btn = None
                
                # 先滚动到页面底部，确保发布按钮可见
                print("[INFO] 滚动到页面底部...")
                try:
                    await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"[DEBUG] 滚动失败: {e}")
                
                # 方法1：查找蓝色的主按钮（Primary）
                print("[INFO] 方法1: 查找主按钮...")
                primary_selectors = [
                    'button.Button--primary:has-text("发布")',
                    'button[class*="Button"][class*="primary"]:has-text("发布")',
                    'button[class*="Primary"]:has-text("发布")',
                    'button[type="submit"]:has-text("发布")'
                ]
                
                for selector in primary_selectors:
                    try:
                        publish_btn = await self.page.query_selector(selector)
                        if publish_btn:
                            is_visible = await publish_btn.is_visible()
                            is_enabled = await publish_btn.is_enabled()
                            if is_visible and is_enabled:
                                print(f"[OK] 找到主按钮 (selector: {selector})")
                                break
                            else:
                                print(f"[DEBUG] 按钮不可用: visible={is_visible}, enabled={is_enabled}")
                                publish_btn = None
                    except Exception as e:
                        print(f"[DEBUG] selector {selector} 失败: {e}")
                        continue
                
                # 方法2：获取所有"发布"按钮，选最后一个（通常在页面底部）
                if not publish_btn:
                    print("[INFO] 方法2: 获取所有发布按钮...")
                    try:
                        all_publish_buttons = await self.page.query_selector_all('button:has-text("发布")')
                        print(f"[INFO] 找到 {len(all_publish_buttons)} 个发布按钮")
                        
                        if all_publish_buttons:
                            # 倒序遍历（从最后一个开始，通常页面底部的才是真正的发布按钮）
                            for i in range(len(all_publish_buttons) - 1, -1, -1):
                                btn = all_publish_buttons[i]
                                is_visible = await btn.is_visible()
                                is_enabled = await btn.is_enabled()
                                
                                # 获取按钮的类名，优先选择包含primary的
                                try:
                                    class_name = await btn.get_attribute('class') or ''
                                    has_primary = 'primary' in class_name.lower()
                                except:
                                    has_primary = False
                                
                                if is_visible and is_enabled:
                                    publish_btn = btn
                                    print(f"[INFO] 选择第 {i+1} 个按钮 (primary={has_primary})")
                                    if has_primary:
                                        print("[OK] 这是主按钮，确认选择！")
                                        break
                    except Exception as e:
                        print(f"[DEBUG] 方法2失败: {e}")
                
                # 方法3：使用页面右下角的固定位置按钮
                if not publish_btn:
                    print("[INFO] 方法3: 查找固定位置按钮...")
                    fixed_selectors = [
                        'button[style*="fixed"]:has-text("发布")',
                        'div[style*="fixed"] button:has-text("发布")',
                    ]
                    
                    for selector in fixed_selectors:
                        try:
                            publish_btn = await self.page.query_selector(selector)
                            if publish_btn and await publish_btn.is_visible():
                                print(f"[OK] 找到固定位置按钮")
                                break
                            else:
                                publish_btn = None
                        except:
                            continue
                
                if publish_btn:
                    print("\n[INFO] 🎯 找到发布按钮！准备点击...")
                    
                    # 再次确保按钮可见
                    try:
                        await publish_btn.scroll_into_view_if_needed()
                        await asyncio.sleep(0.8)
                    except Exception as e:
                        print(f"[DEBUG] 滚动到按钮失败: {e}")
                    
                    # 点击发布按钮
                    try:
                        await publish_btn.click()
                        print("\n" + "🎉"*20)
                        print("✅✅✅ 已成功点击「发布」按钮！")
                        print("📝 文章正在发布到知乎...")
                        print("🎉"*20 + "\n")
                        
                        if progress_callback:
                            progress_callback("✅ 文章已发布，等待跳转...")
                        
                        # 等待页面跳转
                        await asyncio.sleep(3)
                    except Exception as e:
                        print(f"[ERROR] 点击按钮失败: {e}")
                        raise
                else:
                    print("\n" + "❌"*20)
                    print("⚠️ 未找到发布按钮！")
                    print("请手动点击页面上的蓝色「发布」按钮")
                    print("❌"*20 + "\n")
                    
                    if progress_callback:
                        progress_callback("❌ 请手动点击发布按钮")
            except Exception as e:
                print(f"\n[ERROR] 发布流程失败: {e}")
                import traceback
                traceback.print_exc()
                if progress_callback:
                    progress_callback("❌ 请手动点击发布按钮")
            
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
    
    async def _extract_topics_from_content(self, title: str, content: str) -> List[str]:
        """
        从标题和内容中智能提取知乎话题
        
        根据内容关键词匹配知乎真实存在的热门话题
        
        Args:
            title: 文章标题
            content: 文章内容
            
        Returns:
            话题词列表（知乎真实话题）
        """
        try:
            # 知乎热门话题映射库
            # 格式：{关键词集合: 推荐话题}
            topic_mapping = {
                # 校园类
                ('校园', '学生', '同学', '老师', '教室', '课堂', '班级', '操场', '宿舍', '高考', '中考'): '校园故事',
                ('青春', '高中', '初中', '大学', '毕业'): '青春',
                ('霸凌', '欺负', '被欺负'): '校园霸凌',
                
                # 职场类
                ('职场', '公司', '上班', '同事', '领导', '老板', '工作', '面试', '加班', '辞职', '升职'): '职场',
                ('创业', '创业者', '企业'): '创业故事',
                
                # 情感类
                ('爱情', '恋爱', '男友', '女友', '男朋友', '女朋友', '前任', '分手', '表白', '暗恋'): '情感故事',
                ('婚姻', '老公', '老婆', '丈夫', '妻子', '离婚', '结婚'): '婚姻',
                ('亲情', '父母', '妈妈', '爸爸', '母亲', '父亲', '家人'): '亲情',
                ('友情', '朋友', '闺蜜', '兄弟'): '友情',
                
                # 成长类
                ('成长', '改变', '蜕变', '转变', '成熟'): '个人成长',
                ('人生', '经历', '往事', '回忆', '过去'): '人生故事',
                ('励志', '奋斗', '坚持', '努力', '拼搏'): '励志',
                ('逆袭', '反转', '翻身'): '逆袭',
                
                # 悬疑惊悚类
                ('悬疑', '推理', '侦探', '案件', '真相'): '悬疑',
                ('恐怖', '鬼', '灵异', '诡异', '惊悚'): '惊悚故事',
                ('谜团', '秘密', '隐藏'): '悬疑推理',
                
                # 都市生活类
                ('都市', '城市', '北京', '上海', '深圳', '广州'): '都市故事',
                ('生活', '日常', '平凡'): '生活故事',
                ('家庭', '家族', '亲人'): '家庭',
                
                # 玄幻奇幻类
                ('穿越', '重生', '系统', '异世界'): '网络小说',
                ('修仙', '武侠', '江湖'): '武侠',
                
                # 社会类
                ('社会', '现实', '人性', '道德'): '社会',
                ('正义', '善恶', '报应'): '因果',
            }
            
            # 合并标题和内容前300字
            full_text = title + ' ' + content[:300]
            
            # 匹配话题
            matched_topics = []
            matched_scores = []
            
            for keywords, topic in topic_mapping.items():
                # 计算匹配分数（关键词出现次数）
                score = sum(1 for keyword in keywords if keyword in full_text)
                if score > 0:
                    matched_topics.append(topic)
                    matched_scores.append(score)
            
            # 按匹配分数排序
            if matched_topics:
                sorted_topics = [topic for _, topic in sorted(zip(matched_scores, matched_topics), reverse=True)]
                
                # 去重
                unique_topics = []
                seen = set()
                for topic in sorted_topics:
                    if topic not in seen:
                        unique_topics.append(topic)
                        seen.add(topic)
                        if len(unique_topics) >= 3:
                            break
                
                # 如果匹配到的话题少于3个，添加通用话题
                if len(unique_topics) < 3:
                    default_topics = ['故事', '短篇小说', '小说']
                    for topic in default_topics:
                        if topic not in seen and len(unique_topics) < 3:
                            unique_topics.append(topic)
                            seen.add(topic)
                
                print(f"[INFO] 智能匹配到的知乎话题: {', '.join(unique_topics)}")
                return unique_topics
            else:
                # 未匹配到任何话题，返回通用话题
                default = ['故事', '短篇小说', '小说']
                print(f"[INFO] 使用默认话题: {', '.join(default)}")
                return default
            
        except Exception as e:
            print(f"[ERROR] 提取话题词失败: {e}")
            # 返回通用话题作为后备
            return ['故事', '短篇小说']
    
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

