"""
统一的异常处理模块
提供全局异常处理和用户友好的错误消息
"""

import logging
import traceback
from typing import Optional, Callable, Any
from functools import wraps

from src.core.exceptions import APIError, ConfigError

logger = logging.getLogger(__name__)


class AppException(Exception):
    """应用基础异常类"""
    
    def __init__(self, message: str, user_message: Optional[str] = None, error_code: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.user_message = user_message or message
        self.error_code = error_code


class ValidationError(AppException):
    """数据验证错误"""
    pass


class BusinessLogicError(AppException):
    """业务逻辑错误"""
    pass


class FileOperationError(AppException):
    """文件操作错误"""
    pass


class ExceptionHandler:
    """统一异常处理器"""
    
    @staticmethod
    def handle_exception(
        exception: Exception,
        context: str = "",
        show_traceback: bool = False,
        log_error: bool = True
    ) -> str:
        """
        处理异常并返回用户友好的错误消息
        
        Args:
            exception: 异常对象
            context: 上下文信息
            show_traceback: 是否显示完整堆栈跟踪
            log_error: 是否记录日志
        
        Returns:
            用户友好的错误消息
        """
        # 记录详细错误信息
        if log_error:
            error_context = f"{context}: " if context else ""
            logger.error(
                f"{error_context}{type(exception).__name__}: {str(exception)}",
                exc_info=True
            )
        
        # 获取用户友好的错误消息
        if isinstance(exception, AppException):
            user_message = exception.user_message
        elif isinstance(exception, APIError):
            user_message = f"API请求失败: {str(exception)}"
        elif isinstance(exception, ConfigError):
            user_message = f"配置错误: {str(exception)}"
        elif isinstance(exception, FileNotFoundError):
            user_message = f"文件未找到: {str(exception)}"
        elif isinstance(exception, PermissionError):
            user_message = f"权限不足: {str(exception)}"
        elif isinstance(exception, ValueError):
            user_message = f"输入值错误: {str(exception)}"
        elif isinstance(exception, KeyError):
            user_message = f"缺少必需的配置项: {str(exception)}"
        else:
            user_message = f"发生错误: {str(exception)}"
        
        # 添加上下文信息
        if context:
            user_message = f"{context}\n{user_message}"
        
        # 如果需要显示堆栈跟踪
        if show_traceback:
            user_message += f"\n\n详细错误信息:\n{traceback.format_exc()}"
        
        return user_message
    
    @staticmethod
    def safe_execute(
        func: Callable,
        *args,
        default_return: Any = None,
        error_message: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        安全执行函数，捕获异常
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            default_return: 发生异常时的默认返回值
            error_message: 自定义错误消息
            **kwargs: 关键字参数
        
        Returns:
            函数返回值或默认返回值
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            context = error_message or f"执行 {func.__name__} 时出错"
            ExceptionHandler.handle_exception(e, context=context)
            return default_return


def handle_exceptions(
    default_return: Any = None,
    show_traceback: bool = False,
    error_message: Optional[str] = None
):
    """
    异常处理装饰器
    
    Args:
        default_return: 发生异常时的默认返回值
        show_traceback: 是否显示完整堆栈跟踪
        error_message: 自定义错误消息前缀
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = error_message or f"执行 {func.__name__} 时出错"
                error_msg = ExceptionHandler.handle_exception(
                    e,
                    context=context,
                    show_traceback=show_traceback
                )
                
                # 如果是GUI应用，显示错误对话框
                if hasattr(args[0] if args else None, 'after'):
                    from tkinter import messagebox
                    try:
                        app = args[0]
                        app.after(0, lambda: messagebox.showerror("错误", error_msg))
                    except Exception:
                        pass
                
                return default_return
        
        return wrapper
    return decorator


def safe_method(default_return: Any = None):
    """安全方法装饰器（用于GUI方法）"""
    return handle_exceptions(default_return=default_return, show_traceback=False)


def critical_method(error_message: str = "操作失败"):
    """关键方法装饰器，记录错误并重新抛出"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.critical(
                    f"{error_message} - {func.__name__}: {str(e)}",
                    exc_info=True
                )
                raise AppException(f"{error_message}: {str(e)}") from e
        return wrapper
    return decorator

