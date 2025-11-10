"""
文章发布流程 - 从zhihu_publisher.py重构出来
负责知乎文章发布的完整流程
"""
import asyncio
from typing import Optional, Callable
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from .login_handler import LoginHandler
from .topic_extractor import TopicExtractor
from src.core.logging_config import get_logger

logger = get_logger(__name__)


class ArticlePublisher:
    """文章发布器 - 负责知乎文章发布的完整流程"""
    
    def __init__(self, page: Page):
        """
        初始化文章发布器
        
        Args:
            page: Playwright Page对象
        """
        self.page = page
    
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
            
            if not await LoginHandler.check_login_status(self.page):
                if progress_callback:
                    progress_callback("需要登录，请在浏览器中完成登录")
                
                if not await LoginHandler.wait_for_manual_login(self.page):
                    return False, "登录超时或失败"
            
            # 2. 进入编辑器
            if not await self._navigate_to_editor(progress_callback):
                return False, "无法进入文章编辑器"
            
            # 3. 输入标题和内容
            if not await self._input_title_and_content(title, content, input_mode, progress_callback):
                return False, "输入标题或内容失败"
            
            # 4. 设置发布选项
            await self._configure_publish_options(title, content, custom_question, progress_callback)
            
            # 5. 点击发布
            if progress_callback:
                progress_callback("正在发布文章...")
            
            # 等待发布完成
            return await self._wait_for_publish_complete(progress_callback)
            
        except Exception as e:
            error_msg = f"发布过程出错: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    async def _navigate_to_editor(self, progress_callback: Optional[Callable[[str], None]]) -> bool:
        """导航到文章编辑器"""
        try:
            if progress_callback:
                progress_callback("打开创作中心...")
            
            logger.info("正在打开创作中心...")
            
            # 先确保在知乎首页
            await self.page.goto('https://www.zhihu.com', 
                                wait_until='domcontentloaded',
                                timeout=30000)
            await asyncio.sleep(2)
            
            # 查找并点击「创作中心」按钮
            creator_btn = await self.page.query_selector('a[href*="creator"], button:has-text("创作中心")')
            if creator_btn:
                logger.info("找到创作中心按钮，点击...")
                await creator_btn.click()
                await asyncio.sleep(3)
            else:
                # 如果找不到，直接跳转到创作中心
                logger.info("直接跳转到创作中心页面...")
                await self.page.goto('https://www.zhihu.com/creator', 
                                    wait_until='domcontentloaded',
                                    timeout=30000)
                await asyncio.sleep(3)
            
            logger.info("已进入创作中心")
            
            # 打开内容创作菜单
            if progress_callback:
                progress_callback("打开内容创作菜单...")
            
            try:
                logger.info("查找「内容创作」按钮...")
                content_create_btn = await self.page.query_selector('button:has-text("内容创作"), div:has-text("内容创作")')
                
                if content_create_btn:
                    logger.info("找到「内容创作」按钮，点击...")
                    await content_create_btn.click()
                    await asyncio.sleep(1.5)
                else:
                    logger.warning("未找到「内容创作」按钮")
            except Exception as e:
                logger.warning(f"点击内容创作异常: {e}")
            
            # 点击「发布文章」
            if progress_callback:
                progress_callback("点击发布文章...")
            
            try:
                logger.info("查找「发布文章」选项...")
                
                # 等待菜单出现并查找「发布文章」
                publish_article_btn = await self.page.wait_for_selector(
                    'button:has-text("发布文章"), a:has-text("发布文章"), div:has-text("发布文章")',
                    timeout=5000
                )
                
                if publish_article_btn:
                    logger.info("找到「发布文章」，点击...")
                    await publish_article_btn.click()
                    await asyncio.sleep(3)
                    logger.info("已打开文章编辑器")
                else:
                    logger.warning("未找到「发布文章」按钮，尝试直接跳转...")
                    await self.page.goto('https://zhuanlan.zhihu.com/write', 
                                        wait_until='domcontentloaded',
                                        timeout=30000)
                    await asyncio.sleep(3)
                
            except PlaywrightTimeout:
                logger.warning("等待「发布文章」超时，尝试直接跳转...")
                await self.page.goto('https://zhuanlan.zhihu.com/write', 
                                    wait_until='domcontentloaded',
                                    timeout=30000)
                await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"点击发布文章失败: {e}")
                # 最后尝试直接跳转
                logger.info("尝试直接跳转到编辑器...")
                await self.page.goto('https://zhuanlan.zhihu.com/write', 
                                    wait_until='domcontentloaded',
                                    timeout=30000)
                await asyncio.sleep(3)
            
            # 等待编辑器加载
            if progress_callback:
                progress_callback("等待编辑器加载...")
            
            logger.info("等待编辑器加载...")
            
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
                    logger.info(f"编辑器已加载 (selector: {selector})")
                    editor_loaded = True
                    break
                except PlaywrightTimeout:
                    continue
            
            if not editor_loaded:
                logger.warning("未检测到编辑器，但继续尝试...")
            
            await asyncio.sleep(2)
            return True
            
        except Exception as e:
            logger.error(f"导航到编辑器失败: {e}", exc_info=True)
            return False
    
    async def _input_title_and_content(
        self,
        title: str,
        content: str,
        input_mode: str,
        progress_callback: Optional[Callable[[str], None]]
    ) -> bool:
        """输入标题和内容"""
        try:
            # 输入标题
            if progress_callback:
                progress_callback("输入标题...")
            
            logger.info(f"正在输入标题: {title[:30]}...")
            
            title_input = None
            title_selectors = [
                'div[placeholder*="请输入标题"]',
                'div[data-text*="请输入标题"]',
                '[contenteditable="true"][placeholder*="标题"]',
                'input[placeholder*="标题"]',
                'textarea[placeholder*="标题"]',
            ]
            
            for selector in title_selectors:
                title_input = await self.page.query_selector(selector)
                if title_input:
                    logger.info(f"找到标题输入框 (selector: {selector})")
                    break
            
            if title_input:
                try:
                    await title_input.click()
                    await asyncio.sleep(0.5)
                    await self.page.keyboard.press('Control+A')
                    await asyncio.sleep(0.2)
                    await self.page.keyboard.type(title, delay=30)
                    logger.info(f"标题已输入: {title[:30]}...")
                    await self.page.keyboard.press('Tab')
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.warning(f"输入标题异常: {e}")
            else:
                logger.warning("未找到标题输入框，尝试通过键盘输入")
                await self.page.keyboard.type(title, delay=30)
                await self.page.keyboard.press('Tab')
                await asyncio.sleep(0.5)
            
            await asyncio.sleep(1)
            
            # 输入内容
            if progress_callback:
                progress_callback("输入内容...")
            
            logger.info(f"正在输入内容，共 {len(content)} 字符...")
            
            editor = None
            editor_selectors = [
                'div[placeholder*="请输入正文"]',
                'div[data-text*="请输入正文"]',
                '[contenteditable="true"]',
                '.public-DraftEditor-content',
                '.DraftEditor-root',
                '.RichText-editor',
            ]
            
            for selector in editor_selectors:
                editor = await self.page.query_selector(selector)
                if editor:
                    logger.info(f"找到内容编辑器 (selector: {selector})")
                    break
            
            if not editor:
                logger.info("未找到特定编辑器，尝试直接在当前焦点输入")
            
            if editor or True:  # 无论是否找到编辑器都尝试
                try:
                    # 如果找到编辑器，点击获取焦点
                    if editor:
                        await editor.click()
                        await asyncio.sleep(0.8)
                    else:
                        await self.page.mouse.click(500, 500)
                        await asyncio.sleep(0.8)
                    
                    paste_success = False
                    
                    # 根据input_mode选择输入方式
                    if input_mode == "stream":
                        paste_success = await self._input_content_stream(content, editor, progress_callback)
                    else:
                        paste_success = await self._input_content_paste(content, editor)
                    
                    if paste_success:
                        logger.info(f"内容已成功填充，共 {len(content)} 字符")
                        return True
                    else:
                        raise Exception("内容填充失败，请检查浏览器")
                        
                except Exception as e:
                    logger.error(f"输入内容失败: {e}", exc_info=True)
                    return False
            else:
                logger.warning("未找到编辑器，尝试直接输入")
                try:
                    await self.page.keyboard.type(content, delay=10)
                    logger.info("内容已通过键盘输入")
                    return True
                except Exception as e:
                    logger.error(f"键盘输入失败: {e}")
                    return False
                    
        except Exception as e:
            logger.error(f"输入标题和内容失败: {e}", exc_info=True)
            return False
    
    async def _input_content_stream(
        self,
        content: str,
        editor,
        progress_callback: Optional[Callable[[str], None]]
    ) -> bool:
        """流式输入内容"""
        try:
            if progress_callback:
                progress_callback(f"正在流式输入内容...")
            
            logger.info("使用流式输入模式（逐字输入）")
            paragraphs = content.split('\n')
            total_paragraphs = len([p for p in paragraphs if p.strip()])
            current_paragraph = 0
            
            for i, paragraph in enumerate(paragraphs):
                if paragraph.strip():
                    current_paragraph += 1
                    await self.page.keyboard.type(paragraph.strip(), delay=50)
                    await self.page.keyboard.press('Enter')
                    await asyncio.sleep(0.1)
                    
                    if current_paragraph % 5 == 0 and progress_callback:
                        progress = int((current_paragraph / total_paragraphs) * 100)
                        progress_callback(f"流式输入中... {progress}%")
            
            logger.info(f"流式输入完成，共 {total_paragraphs} 段")
            return True
            
        except Exception as e:
            logger.error(f"流式输入失败: {e}", exc_info=True)
            return False
    
    async def _input_content_paste(self, content: str, editor) -> bool:
        """快速粘贴内容"""
        try:
            # 方法1：使用剪贴板粘贴（最可靠）
            try:
                logger.info("尝试使用剪贴板粘贴")
                await self.page.evaluate(f"navigator.clipboard.writeText({repr(content)})")
                await asyncio.sleep(0.5)
                
                if editor:
                    await editor.click()
                    await asyncio.sleep(0.3)
                
                await self.page.keyboard.press('Control+V')
                await asyncio.sleep(1.0)
                
                # 验证内容是否粘贴成功
                if editor:
                    try:
                        current_content = await editor.evaluate("element => element.innerText || element.textContent || ''")
                        if len(current_content) > 50:
                            logger.info(f"剪贴板粘贴成功，已填充 {len(current_content)} 字符")
                            return True
                    except:
                        pass
                
                logger.warning("剪贴板粘贴可能失败，尝试备用方案")
                raise Exception("剪贴板粘贴验证失败")
                
            except Exception as e1:
                logger.warning(f"剪贴板粘贴失败: {e1}")
                
                # 方法2：使用快速输入（delay=0，无延迟）
                try:
                    logger.info("使用快速键盘输入")
                    paragraphs = content.split('\n')
                    
                    for i, paragraph in enumerate(paragraphs):
                        if paragraph.strip():
                            await self.page.keyboard.type(paragraph.strip(), delay=0)
                            await self.page.keyboard.press('Enter')
                    
                    logger.info(f"快速键盘输入完成")
                    return True
                    
                except Exception as e2:
                    logger.error(f"快速输入也失败: {e2}")
                    return False
                    
        except Exception as e:
            logger.error(f"粘贴内容失败: {e}", exc_info=True)
            return False
    
    async def _configure_publish_options(
        self,
        title: str,
        content: str,
        custom_question: str,
        progress_callback: Optional[Callable[[str], None]]
    ) -> None:
        """配置发布选项（投稿、声明、话题）"""
        await asyncio.sleep(2)  # 等待页面加载完成
        
        # 设置投稿至问题
        await self._set_question_submission(custom_question, progress_callback)
        
        # 设置创作声明
        await self._set_creation_declaration(progress_callback)
        
        # 添加话题（自动提取）
        await self._add_topics(title, content, "", progress_callback)
    
    async def _set_question_submission(self, custom_question: str, progress_callback: Optional[Callable[[str], None]]) -> None:
        """设置投稿至问题"""
        if progress_callback:
            progress_callback("正在选择投稿问题...")
        
        try:
            logger.info("正在处理投稿至问题...")
            await asyncio.sleep(1)
            
            # 查找投稿至问题下拉框
            dropdown_trigger = await self.page.query_selector('text="未选择"')
            if not dropdown_trigger:
                dropdown_trigger = await self.page.query_selector('text="投稿至问题" >> .. >> div[role="button"]')
            if not dropdown_trigger:
                dropdown_trigger = await self.page.query_selector('div:has-text("投稿至问题") ~ div')
            
            if dropdown_trigger:
                await dropdown_trigger.click()
                logger.info("已点击投稿至问题下拉框")
                await asyncio.sleep(2.5)
                
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
                        if modal and await modal.is_visible():
                            logger.info(f"找到弹窗容器 (selector: {selector})")
                            break
                        else:
                            modal = None
                    except Exception:
                        continue
                
                # 如果用户输入了问题标题，尝试搜索
                if custom_question:
                    logger.info(f"用户指定了问题标题: {custom_question}，尝试搜索")
                    try:
                        # 查找搜索框（多种选择器）
                        search_input = None
                        search_selectors = [
                            'input[placeholder*="关键词"]',
                            'input[placeholder*="搜索"]',
                            'input[placeholder*="问题"]',
                            'input[type="text"]',
                            'input.Input',
                        ]
                        
                        for selector in search_selectors:
                            if modal:
                                search_input = await modal.query_selector(selector)
                            if not search_input:
                                search_input = await self.page.query_selector(selector)
                            if search_input:
                                logger.info(f"找到搜索框 (selector: {selector})")
                                break
                        
                        if search_input:
                            logger.info("输入问题标题到搜索框")
                            await search_input.click()
                            await asyncio.sleep(0.5)
                            await search_input.fill('')  # 先清空
                            await asyncio.sleep(0.3)
                            await search_input.type(custom_question, delay=50)
                            await asyncio.sleep(1)
                            await self.page.keyboard.press('Enter')
                            await asyncio.sleep(2.5)
                            logger.info(f"已搜索问题: {custom_question}")
                        else:
                            logger.warning("未找到搜索框，将选择第一个问题")
                    except Exception as e:
                        logger.warning(f"搜索问题失败: {e}，将选择第一个问题")
                
                # 查找并点击第一个"选择"按钮
                select_button = None
                if modal:
                    try:
                        all_select_buttons = await modal.query_selector_all('button:has-text("选择")')
                        if all_select_buttons:
                            for btn in all_select_buttons:
                                if await btn.is_visible():
                                    select_button = btn
                                    break
                    except Exception as e:
                        logger.debug(f"在弹窗内查找失败: {e}")
                
                if not select_button:
                    select_selectors = [
                        'div[role="dialog"] >> button:has-text("选择") >> nth=0',
                        '[class*="Modal"] >> button:has-text("选择") >> nth=0',
                    ]
                    for selector in select_selectors:
                        try:
                            select_button = await self.page.query_selector(selector)
                            if select_button and await select_button.is_visible():
                                break
                            else:
                                select_button = None
                        except Exception:
                            continue
                
                if select_button:
                    await select_button.click()
                    logger.info("已点击「选择」按钮")
                    await asyncio.sleep(1)
                    
                    # 点击"确定"按钮
                    confirm_btn = None
                    if modal:
                        try:
                            all_confirm_buttons = await modal.query_selector_all('button:has-text("确定")')
                            if all_confirm_buttons:
                                for btn in all_confirm_buttons:
                                    if await btn.is_visible():
                                        confirm_btn = btn
                                        break
                        except Exception:
                            pass
                    
                    if not confirm_btn:
                        confirm_selectors = [
                            'div[role="dialog"] >> button:has-text("确定")',
                            '[class*="Modal"] >> button:has-text("确定")',
                        ]
                        for selector in confirm_selectors:
                            try:
                                confirm_btn = await self.page.query_selector(selector)
                                if confirm_btn and await confirm_btn.is_visible():
                                    break
                                else:
                                    confirm_btn = None
                            except Exception:
                                continue
                    
                    if confirm_btn:
                        await confirm_btn.click()
                        logger.info("已点击「确定」按钮，问题选择完成！")
                        await asyncio.sleep(1.5)
                    else:
                        logger.warning("未找到「确定」按钮")
                else:
                    logger.warning("未找到「选择」按钮")
            else:
                logger.warning("未找到投稿至问题下拉框")
        except Exception as e:
            logger.warning(f"投稿至问题设置失败（可选操作）: {e}")
    
    async def _set_creation_declaration(self, progress_callback: Optional[Callable[[str], None]]) -> None:
        """设置创作声明为虚构创作"""
        if progress_callback:
            progress_callback("正在设置创作声明...")
        
        try:
            logger.info("正在设置创作声明...")
            await asyncio.sleep(1)
            
            # 查找创作声明下拉框
            declaration_dropdown = await self.page.query_selector('text="无声明"')
            if not declaration_dropdown:
                declaration_dropdown = await self.page.query_selector('text="创作声明" >> .. >> div[role="button"]')
            if not declaration_dropdown:
                declaration_dropdown = await self.page.query_selector('div:has-text("创作声明") ~ div')
            
            if declaration_dropdown:
                await declaration_dropdown.click()
                logger.info("已点击创作声明下拉框")
                await asyncio.sleep(1)
                
                # 选择"虚构创作"
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
                        logger.info("已设置创作声明为「虚构创作」")
                        await asyncio.sleep(0.5)
                        break
            else:
                logger.warning("未找到创作声明下拉框")
        except Exception as e:
            logger.warning(f"创作声明设置失败（可选操作）: {e}")
    
    async def _add_topics(
        self,
        title: str,
        content: str,
        custom_topic: str,
        progress_callback: Optional[Callable[[str], None]]
    ) -> None:
        """提取并添加话题词"""
        if progress_callback:
            progress_callback("正在添加话题标签...")
        
        try:
            logger.info("正在提取话题词...")
            await asyncio.sleep(1)
            
            # 如果用户指定了话题，使用用户的话题；否则自动提取
            if custom_topic:
                topics = [custom_topic]
                logger.info(f"使用用户指定的话题: {custom_topic}")
            else:
                # 使用TopicExtractor提取话题
                topics = TopicExtractor.extract_topics_from_content(title, content)
                logger.info(f"自动提取话题: {topics}")
            
            if topics:
                logger.info(f"提取到话题词: {', '.join(topics)}")
                
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
                        logger.info(f"找到添加话题按钮 (selector: {selector})")
                        break
                
                if add_topic_btn:
                    # 只添加第一个话题即可
                    topic = topics[0]
                    try:
                        logger.info(f"准备添加话题: {topic}")
                        await add_topic_btn.click()
                        await asyncio.sleep(1)
                        
                        # 输入话题
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
                                logger.info(f"找到话题输入框 (selector: {selector})")
                                break
                        
                        if topic_input:
                            await topic_input.fill('')
                            await asyncio.sleep(0.3)
                            await topic_input.type(topic, delay=80)
                            logger.info(f"已输入话题文字: {topic}")
                            await asyncio.sleep(1.5)
                            
                            # 点击下拉列表中的第一个选项
                            topic_option = await self.page.query_selector('div[role="option"] >> nth=0')
                            if topic_option and await topic_option.is_visible():
                                await topic_option.click()
                                logger.info("已点击话题选项")
                                await asyncio.sleep(1)
                            else:
                                logger.warning("未找到话题下拉选项，尝试按回车")
                                await self.page.keyboard.press('Enter')
                                await asyncio.sleep(1)
                            
                            logger.info(f"话题添加完成: {topic}")
                        else:
                            logger.warning("未找到话题输入框")
                    except Exception as e:
                        logger.warning(f"添加话题失败: {e}")
                else:
                    logger.warning("未找到添加话题按钮")
            else:
                logger.info("未提取到合适的话题词，跳过话题添加")
        except Exception as e:
            logger.warning(f"话题添加失败（可选操作）: {e}")
    
    async def _wait_for_publish_complete(self, progress_callback: Optional[Callable[[str], None]]) -> tuple[bool, str]:
        """等待发布完成"""
        try:
            # 点击发布按钮
            logger.info("准备点击发布按钮")
            await asyncio.sleep(2.5)
            
            # 滚动到页面底部
            try:
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)
            except Exception:
                pass
            
            # 查找发布按钮
            publish_btn = None
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
                            logger.info(f"找到主按钮 (selector: {selector})")
                            break
                        else:
                            publish_btn = None
                except Exception:
                    continue
            
            # 如果没找到主按钮，获取所有发布按钮
            if not publish_btn:
                try:
                    all_publish_buttons = await self.page.query_selector_all('button:has-text("发布")')
                    if all_publish_buttons:
                        for i in range(len(all_publish_buttons) - 1, -1, -1):
                            btn = all_publish_buttons[i]
                            if await btn.is_visible() and await btn.is_enabled():
                                publish_btn = btn
                                break
                except Exception:
                    pass
            
            if publish_btn:
                logger.info("找到发布按钮！准备点击...")
                try:
                    await publish_btn.scroll_into_view_if_needed()
                    await asyncio.sleep(0.8)
                    await publish_btn.click()
                    logger.info("已成功点击「发布」按钮！")
                    
                    if progress_callback:
                        progress_callback("✅ 文章已发布，等待跳转...")
                    
                    # 等待页面跳转
                    await asyncio.sleep(3)
                except Exception as e:
                    logger.error(f"点击按钮失败: {e}")
                    raise
            else:
                logger.warning("未找到发布按钮！")
                if progress_callback:
                    progress_callback("❌ 请手动点击发布按钮")
            
            # 等待发布完成（检测URL变化）
            try:
                await self.page.wait_for_url('**/p/**', timeout=180000)  # 3分钟超时
                article_url = self.page.url
                logger.info(f"文章已发布: {article_url}")
                
                if progress_callback:
                    progress_callback(f"发布成功！")
                
                return True, article_url
                
            except PlaywrightTimeout:
                logger.info("未检测到发布完成")
                return True, "文章内容已填充，等待手动发布"
                
        except Exception as e:
            logger.error(f"等待发布完成失败: {e}", exc_info=True)
            if progress_callback:
                progress_callback("❌ 请手动点击发布按钮")
            return True, "文章内容已填充，等待手动发布"

