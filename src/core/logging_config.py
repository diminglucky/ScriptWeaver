"""
简单的日志配置
"""

import logging
import os
from typing import Optional


def get_logger(name: Optional[str] = None) -> logging.Logger:
	logger = logging.getLogger(name or __name__)
	if logger.handlers:
		return logger
	level_name = os.getenv("APP_LOG_LEVEL", "INFO").upper()
	level = getattr(logging, level_name, logging.INFO)
	logger.setLevel(level)
	handler = logging.StreamHandler()
	handler.setLevel(level)
	formatter = logging.Formatter(
		"%(asctime)s | %(levelname)s | %(name)s | %(message)s",
		datefmt="%H:%M:%S",
	)
	handler.setFormatter(formatter)
	logger.addHandler(handler)
	logger.propagate = False
	return logger

