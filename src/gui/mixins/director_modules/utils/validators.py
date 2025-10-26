"""
数据验证工具
"""

from typing import Any, List, Dict, Tuple, Optional
import re


class Validator:
    """数据验证工具类"""
    
    @staticmethod
    def is_not_empty(value: Any) -> bool:
        """检查值是否非空"""
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, dict)):
            return bool(value)
        return True
    
    @staticmethod
    def is_valid_name(name: str) -> bool:
        """检查是否为有效的名称（字母、数字、中文、下划线）"""
        if not name:
            return False
        # 允许中文、英文、数字、下划线
        pattern = r'^[\w\u4e00-\u9fff]+$'
        return bool(re.match(pattern, name))
    
    @staticmethod
    def is_valid_number(value: Any, min_val: float = None, max_val: float = None) -> bool:
        """检查是否为有效数字"""
        try:
            num = float(value)
            if min_val is not None and num < min_val:
                return False
            if max_val is not None and num > max_val:
                return False
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """检查是否为有效URL"""
        if not url:
            return False
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return bool(url_pattern.match(url))
    
    @staticmethod
    def is_valid_file_path(path: str) -> bool:
        """检查是否为有效的文件路径格式"""
        if not path:
            return False
        # 简单的路径格式检查
        invalid_chars = '<>"|?*'
        return not any(char in path for char in invalid_chars)
    
    @staticmethod
    def is_valid_json(json_string: str) -> bool:
        """检查是否为有效JSON"""
        import json
        try:
            json.loads(json_string)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_dict_structure(
        data: Dict,
        required_keys: List[str],
        optional_keys: List[str] = None
    ) -> Tuple[bool, List[str]]:
        """
        验证字典结构
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        # 检查必需键
        for key in required_keys:
            if key not in data:
                errors.append(f"缺少必需字段: {key}")
        
        # 检查是否有未定义的键
        all_keys = set(required_keys)
        if optional_keys:
            all_keys.update(optional_keys)
        
        for key in data.keys():
            if key not in all_keys:
                errors.append(f"未知字段: {key}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """清理文件名，移除非法字符"""
        # 移除或替换非法字符
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename.strip()
    
    @staticmethod
    def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
        """截断字符串"""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix

