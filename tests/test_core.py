"""核心模块测试"""

import unittest
from src.core.exceptions import APIError, ConfigError, ValidationError
from src.core.logging_config import get_logger


class TestExceptions(unittest.TestCase):
    """测试自定义异常"""
    
    def test_api_error(self):
        """测试API错误"""
        with self.assertRaises(APIError):
            raise APIError("测试错误")
    
    def test_config_error(self):
        """测试配置错误"""
        with self.assertRaises(ConfigError):
            raise ConfigError("配置错误")
    
    def test_validation_error(self):
        """测试验证错误"""
        with self.assertRaises(ValidationError):
            raise ValidationError("验证失败")


class TestLogging(unittest.TestCase):
    """测试日志配置"""
    
    def test_get_logger(self):
        """测试获取日志记录器"""
        logger = get_logger(__name__)
        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, __name__)
    
    def test_logger_methods(self):
        """测试日志方法"""
        logger = get_logger("test")
        # 这些不应该抛出异常
        logger.info("测试信息")
        logger.warning("测试警告")
        logger.error("测试错误")


if __name__ == '__main__':
    unittest.main()
