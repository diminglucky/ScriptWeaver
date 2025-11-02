"""
话题提取器 - 从zhihu_publisher.py重构出来
负责从文章内容中提取话题标签
"""
import re
from typing import List

from src.core.logging_config import get_logger

logger = get_logger(__name__)


class TopicExtractor:
    """话题提取器 - 从文章内容中提取话题标签"""
    
    @staticmethod
    def extract_topics_from_content(title: str, content: str) -> List[str]:
        """
        从标题和内容中提取话题标签
        
        Args:
            title: 文章标题
            content: 文章内容
            
        Returns:
            话题标签列表
        """
        # 常见的话题关键词
        topic_keywords = {
            '故事': ['故事', '小说', '叙事', '情节', '剧情'],
            '短篇小说': ['短篇', '短故事', '小故事'],
            '悬疑': ['悬疑', '推理', '谜题', '案件', '侦探'],
            '爱情': ['爱情', '恋爱', '浪漫', '情感'],
            '科幻': ['科幻', '未来', '科技', '宇宙', '外星'],
            '恐怖': ['恐怖', '惊悚', '鬼', '灵异', '诡异'],
            '职场': ['职场', '工作', '公司', '办公室', '职业'],
            '校园': ['校园', '学校', '学生', '青春', '校园生活'],
            '都市': ['都市', '城市', '现代', '生活'],
            '古风': ['古风', '古代', '历史', '古代', '传统'],
        }
        
        # 合并标题和内容
        full_text = f"{title} {content}"
        
        # 提取话题
        found_topics = []
        for topic, keywords in topic_keywords.items():
            for keyword in keywords:
                if keyword in full_text:
                    found_topics.append(topic)
                    break
        
        # 如果找到话题，返回前3个
        if found_topics:
            return found_topics[:3]
        
        # 如果没有找到，返回默认话题
        logger.info("未找到合适的话题，使用默认话题")
        return ['故事', '短篇小说']

