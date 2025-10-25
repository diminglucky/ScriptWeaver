"""
核心异常定义
"""


class APIError(Exception):
	"""统一的API错误"""
	pass


class ConfigError(Exception):
	"""配置错误（缺少必填项/不合法）"""
	pass

