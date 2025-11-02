"""
完善的日志配置模块
支持文件日志、日志轮转、日志级别配置
"""

import logging
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Optional
import os


def setup_logging(
    log_dir: Optional[Path] = None,
    log_level: str = "INFO",
    log_to_file: bool = True,
    log_to_console: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    console_level: Optional[str] = None
) -> logging.Logger:
    """
    设置应用程序日志
    
    Args:
        log_dir: 日志文件目录（默认：项目根目录/logs）
        log_level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_to_file: 是否记录到文件
        log_to_console: 是否输出到控制台
        max_bytes: 单个日志文件最大大小（字节）
        backup_count: 保留的备份文件数量
        console_level: 控制台日志级别（默认与log_level相同）
    
    Returns:
        配置好的根日志记录器
    """
    # 确定日志目录
    if log_dir is None:
        log_dir = Path(__file__).parent.parent.parent / "logs"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 获取日志级别
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    console_numeric_level = getattr(
        logging,
        (console_level or log_level).upper(),
        numeric_level
    )
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # 清除现有的处理器
    root_logger.handlers.clear()
    
    # 创建格式化器
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # 文件处理器（按大小轮转）
    if log_to_file:
        file_handler = RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # 错误日志单独记录
        error_handler = RotatingFileHandler(
            log_dir / "error.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)
    
    # 控制台处理器
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_numeric_level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    return root_logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称（默认使用调用模块名）
    
    Returns:
        日志记录器实例
    """
    if name is None:
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'root')
    
    return logging.getLogger(name)


# 初始化日志系统
def init_logging():
    """初始化日志系统（在应用启动时调用）"""
    log_level = os.getenv("APP_LOG_LEVEL", "INFO")
    log_to_file = os.getenv("APP_LOG_TO_FILE", "true").lower() == "true"
    
    setup_logging(
        log_level=log_level,
        log_to_file=log_to_file,
        log_to_console=True
    )
    
    logger = get_logger(__name__)
    logger.info("日志系统初始化完成")
    logger.info(f"日志级别: {log_level}")
    logger.info(f"文件日志: {'启用' if log_to_file else '禁用'}")
    
    return logger
