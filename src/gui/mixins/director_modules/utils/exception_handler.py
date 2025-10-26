"""
异常处理工具
"""

import traceback
import logging
from typing import Callable, Any, Optional
from functools import wraps


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class DirectorError(Exception):
    """导演模块自定义异常基类"""
    pass


class ValidationError(DirectorError):
    """数据验证错误"""
    pass


class FileOperationError(DirectorError):
    """文件操作错误"""
    pass


class APIError(DirectorError):
    """API调用错误"""
    pass


class ConfigurationError(DirectorError):
    """配置错误"""
    pass


class ExceptionHandler:
    """异常处理工具类"""
    
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """获取日志记录器"""
        return logging.getLogger(name)
    
    @staticmethod
    def handle_exception(
        exception: Exception,
        context: str = "",
        logger: Optional[logging.Logger] = None
    ) -> str:
        """
        处理异常
        
        Args:
            exception: 异常对象
            context: 上下文信息
            logger: 日志记录器
        
        Returns:
            错误消息
        """
        error_msg = f"{context}: {str(exception)}" if context else str(exception)
        
        if logger:
            logger.error(error_msg, exc_info=True)
        else:
            print(f"❌ 错误: {error_msg}")
            traceback.print_exc()
        
        return error_msg
    
    @staticmethod
    def safe_execute(
        func: Callable,
        *args,
        default_return: Any = None,
        error_callback: Optional[Callable] = None,
        **kwargs
    ) -> Any:
        """
        安全执行函数，捕获异常
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            default_return: 发生异常时的默认返回值
            error_callback: 错误回调函数
            **kwargs: 关键字参数
        
        Returns:
            函数返回值或默认返回值
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            ExceptionHandler.handle_exception(e, f"执行 {func.__name__} 时出错")
            
            if error_callback:
                error_callback(e)
            
            return default_return
    
    @staticmethod
    def with_exception_handling(
        default_return: Any = None,
        reraise: bool = False,
        log_errors: bool = True
    ):
        """
        装饰器：为函数添加异常处理
        
        Args:
            default_return: 发生异常时的默认返回值
            reraise: 是否重新抛出异常
            log_errors: 是否记录错误日志
        """
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if log_errors:
                        logger = logging.getLogger(func.__module__)
                        logger.error(
                            f"函数 {func.__name__} 执行失败: {str(e)}",
                            exc_info=True
                        )
                    
                    if reraise:
                        raise
                    
                    return default_return
            
            return wrapper
        return decorator


# 便捷装饰器
def safe_method(default_return: Any = None):
    """安全方法装饰器，捕获所有异常"""
    return ExceptionHandler.with_exception_handling(
        default_return=default_return,
        reraise=False,
        log_errors=True
    )


def critical_method(error_message: str = "操作失败"):
    """关键方法装饰器，记录错误并重新抛出"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger = logging.getLogger(func.__module__)
                logger.critical(
                    f"{error_message} - {func.__name__}: {str(e)}",
                    exc_info=True
                )
                raise DirectorError(f"{error_message}: {str(e)}") from e
        return wrapper
    return decorator

