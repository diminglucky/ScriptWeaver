"""
登录处理器 - 从zhihu_publisher.py重构出来
负责知乎登录状态检查和等待手动登录
"""
import asyncio
from typing import Optional

from src.core.logging_config import get_logger

logger = get_logger(__name__)


class LoginHandler:
    """登录处理器 - 负责知乎登录相关操作"""
    
    @staticmethod
    async def check_login_status(page) -> bool:
        """
        检查是否已登录知乎
        
        Args:
            page: Playwright Page对象
            
        Returns:
            是否已登录
        """
        try:
            logger.info("正在访问知乎首页...")
            
            # 使用更宽松的等待策略
            await page.goto('https://www.zhihu.com', 
                            wait_until='domcontentloaded',
                            timeout=30000)
            
            # 等待页面稳定
            await asyncio.sleep(2)
            
            # 检查是否已登录（多种方式）
            # 方式1: 检查是否有登录按钮（未登录时会有）
            login_btn = await page.query_selector('button:has-text("登录"), a:has-text("登录")')
            if login_btn:
                is_visible = await login_btn.is_visible()
                if is_visible:
                    logger.info("未检测到登录状态（找到登录按钮）")
                    return False
            
            # 方式2: 检查是否有用户头像或用户名（已登录时会有）
            user_elements = await page.query_selector_all(
                'img[alt*="头像"], [class*="Avatar"], [class*="UserInfo"]'
            )
            if user_elements:
                logger.info("检测到已登录（找到用户元素）")
                return True
            
            # 方式3: 检查URL是否包含登录相关
            current_url = page.url
            if 'signin' in current_url or 'login' in current_url:
                logger.info("当前在登录页面，未登录")
                return False
            
            # 方式4: 检查页面标题
            title = await page.title()
            if '登录' in title or 'Sign in' in title:
                logger.info("页面标题显示需要登录")
                return False
            
            # 默认认为已登录（如果上述检查都未触发）
            logger.info("默认认为已登录")
            return True
            
        except Exception as e:
            logger.error(f"检查登录状态失败: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def wait_for_manual_login(page, timeout: int = 300) -> bool:
        """
        等待用户手动登录
        
        Args:
            page: Playwright Page对象
            timeout: 超时时间（秒）
            
        Returns:
            是否登录成功
        """
        try:
            logger.info(f"等待手动登录（超时时间: {timeout}秒）...")
            
            # 打开登录页面
            await page.goto('https://www.zhihu.com/signin', 
                           wait_until='domcontentloaded',
                           timeout=30000)
            
            start_time = asyncio.get_event_loop().time()
            
            # 轮询检查登录状态
            while True:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    logger.warning("登录超时")
                    return False
                
                # 检查是否已登录
                if await LoginHandler.check_login_status(page):
                    logger.info("检测到登录成功！")
                    return True
                
                # 等待一段时间后再次检查
                await asyncio.sleep(3)
                
        except Exception as e:
            logger.error(f"等待登录失败: {e}", exc_info=True)
            return False

