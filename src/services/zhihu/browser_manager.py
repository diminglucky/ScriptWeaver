"""
浏览器管理器 - 从zhihu_publisher.py重构出来
负责Playwright浏览器的初始化和配置
"""
import asyncio
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page

from src.core.logging_config import get_logger

logger = get_logger(__name__)


class BrowserManager:
    """浏览器管理器 - 负责Playwright浏览器的初始化和管理"""
    
    def __init__(self, headless: bool = False):
        """
        初始化浏览器管理器
        
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
            logger.info("浏览器初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"初始化浏览器失败: {e}", exc_info=True)
            return False
    
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
                    logger.info("浏览器已关闭")
                except Exception as e:
                    logger.warning(f"关闭浏览器异常: {e}")
            
            # 停止 playwright
            if self.playwright:
                try:
                    await self.playwright.stop()
                    logger.info("Playwright 已停止")
                except Exception as e:
                    logger.warning(f"停止 Playwright 异常: {e}")
            
            # 清空引用
            self.page = None
            self.browser = None
            self.playwright = None
            
        except Exception as e:
            logger.error(f"清理资源失败: {e}", exc_info=True)

