"""
知乎发布服务 - 使用 Playwright 自动发布文章到知乎
重构后：使用分离的浏览器管理、登录处理、文章发布模块
"""
import asyncio
from typing import Optional, Callable

from .zhihu.browser_manager import BrowserManager
from .zhihu.login_handler import LoginHandler
from .zhihu.article_publisher import ArticlePublisher

from src.core.logging_config import get_logger

logger = get_logger(__name__)


class ZhihuPublisher:
    """知乎自动发布服务"""
    
    def __init__(self, headless: bool = False):
        """
        初始化知乎发布器
        
        Args:
            headless: 是否使用无头模式（True=后台运行，False=显示浏览器）
        """
        self.browser_manager = BrowserManager(headless=headless)
        self.article_publisher = None
    
    async def initialize(self) -> bool:
        """初始化浏览器"""
        return await self.browser_manager.initialize()
    
    async def check_login_status(self) -> bool:
        """检查是否已登录知乎"""
        if not self.browser_manager.page:
            return False
        return await LoginHandler.check_login_status(self.browser_manager.page)
    
    async def wait_for_manual_login(self, timeout: int = 300) -> bool:
        """等待用户手动登录"""
        if not self.browser_manager.page:
            return False
        return await LoginHandler.wait_for_manual_login(self.browser_manager.page, timeout)
    
    async def publish_article(
        self,
        title: str,
        content: str,
        input_mode: str = "paste",
        custom_question: str = "",
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> tuple[bool, str]:
        """
        发布文章到知乎
        
        Args:
            title: 文章标题
            content: 文章内容
            input_mode: 输入模式 ("paste"=快速粘贴, "stream"=流式输出)
            custom_question: 用户自定义问题标题（留空则自动选择第一个）
            progress_callback: 进度回调函数
            
        Returns:
            (是否成功, 错误信息或文章链接)
        """
        if not self.browser_manager.page:
            return False, "浏览器未初始化"
        
        # 创建文章发布器
        if not self.article_publisher:
            self.article_publisher = ArticlePublisher(self.browser_manager.page)
        
        return await self.article_publisher.publish_article(
            title, content, input_mode, custom_question, progress_callback
        )
    
    async def close(self):
        """关闭浏览器和清理资源"""
        await self.browser_manager.close()


# 同步包装函数（供Tkinter使用）
def publish_to_zhihu_sync(
    title: str,
    content: str,
    headless: bool = False,
    input_mode: str = "paste",
    custom_question: str = "",
    progress_callback: Optional[Callable[[str], None]] = None
) -> tuple[bool, str]:
    """
    同步版本的知乎发布函数
    
    Args:
        title: 文章标题
        content: 文章内容
        headless: 是否使用无头模式
        input_mode: 输入模式 ("paste"=快速粘贴, "stream"=流式输出)
        custom_question: 用户自定义问题标题（留空则自动选择第一个）
        progress_callback: 进度回调函数
        
    Returns:
        (是否成功, 错误信息或文章链接)
    """
    async def _run():
        publisher = ZhihuPublisher(headless=headless)
        
        try:
            if not await publisher.initialize():
                return False, "初始化浏览器失败"
            
            return await publisher.publish_article(title, content, input_mode, custom_question, progress_callback)
            
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
        logger.error(f"执行失败: {e}", exc_info=True)
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
                logger.warning(f"关闭事件循环异常: {e}")
