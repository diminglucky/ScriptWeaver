"""
标签提取模块 - 从prompt_adapter.py重构出来
负责从文本中提取各种类型的标签
"""
from typing import List


class TagExtractor:
    """标签提取器 - 从文本中提取各种类型的标签"""
    
    @staticmethod
    def extract_character_tags(description: str) -> List[str]:
        """提取人物特征标签"""
        tags = []
        desc_lower = description.lower()
        
        # 年龄
        if '16岁' in description or '16 years old' in desc_lower:
            tags.append("teenage")
        if '17岁' in description or '17 years old' in desc_lower:
            tags.append("teenage")
        if '18岁' in description or '18 years old' in desc_lower:
            tags.append("teenage")
        
        # 性别
        if '男' in description or 'male' in desc_lower or 'boy' in desc_lower:
            tags.append("male")
        elif '女' in description or 'female' in desc_lower or 'girl' in desc_lower:
            tags.append("female")
        
        # 发型
        if '黑发' in description or 'black hair' in desc_lower:
            tags.append("black hair")
        if '短发' in description or 'short hair' in desc_lower:
            tags.append("short hair")
        elif '长发' in description or 'long hair' in desc_lower:
            tags.append("long hair")
        
        # 脸型
        if '国字脸' in description or 'square jaw' in desc_lower:
            tags.append("square jaw")
        elif '瓜子脸' in description or 'oval face' in desc_lower:
            tags.append("oval face")
        
        # 眼睛
        if '大眼' in description or 'large eyes' in desc_lower:
            tags.append("large eyes")
        if '眼镜' in description or 'glasses' in desc_lower:
            if '黑框' in description or 'black frame' in desc_lower:
                tags.append("black framed glasses")
            else:
                tags.append("glasses")
        
        # 服装
        if '白衬衫' in description or 'white shirt' in desc_lower:
            tags.append("white shirt")
        elif '蓝色连衣裙' in description or 'blue dress' in desc_lower:
            tags.append("blue dress")
        elif '校服' in description or 'school uniform' in desc_lower:
            tags.append("school uniform")
        
        return tags
    
    @staticmethod
    def extract_action_tags(action: str) -> List[str]:
        """提取动作标签"""
        tags = []
        action_lower = action.lower()
        
        action_map = {
            ('坐', 'sitting', 'sit'): 'sitting',
            ('站', 'standing', 'stand'): 'standing',
            ('走', 'walking', 'walk'): 'walking',
            ('跑', 'running'): 'running',
            ('看书', 'reading'): 'reading book',
            ('写', 'writing'): 'writing',
            ('说话', 'talking'): 'talking'
        }
        
        for keywords, tag in action_map.items():
            if any(kw in action or kw in action_lower for kw in keywords):
                tags.append(tag)
        
        return tags
    
    @staticmethod
    def extract_scene_tags(scene_desc: str) -> List[str]:
        """提取场景标签"""
        tags = []
        scene_lower = scene_desc.lower()
        
        # 地点
        location_map = {
            ('教室', 'classroom'): ['classroom', 'indoors'],
            ('走廊', 'hallway', 'corridor'): ['hallway', 'indoors'],
            ('操场', 'playground'): ['playground', 'outdoors']
        }
        
        for keywords, tag_list in location_map.items():
            if any(kw in scene_desc or kw in scene_lower for kw in keywords):
                tags.extend(tag_list)
        
        # 光线
        lighting_map = {
            ('阳光', 'sunlight'): 'sunlight',
            ('明亮', 'bright'): 'bright lighting',
            ('昏暗', 'dim'): 'dim lighting'
        }
        
        for keywords, tag in lighting_map.items():
            if any(kw in scene_desc or kw in scene_lower for kw in keywords):
                tags.append(tag)
        
        # 物品
        item_map = {
            ('书', 'book'): 'books',
            ('桌子', 'desk'): 'desk',
            ('黑板', 'blackboard'): 'blackboard'
        }
        
        for keywords, tag in item_map.items():
            if any(kw in scene_desc or kw in scene_lower for kw in keywords):
                tags.append(tag)
        
        return tags
    
    @staticmethod
    def extract_emotion_tags(emotion: str) -> List[str]:
        """提取情感标签"""
        tags = []
        emotion_lower = emotion.lower()
        
        emotion_map = {
            ('开心', '微笑', 'smile', 'happy'): 'smile',
            ('悲伤', '哭', 'sad', 'crying'): 'sad',
            ('生气', '愤怒', 'angry'): 'angry',
            ('惊讶', 'surprised'): 'surprised',
            ('认真', 'serious'): 'serious'
        }
        
        for keywords, tag in emotion_map.items():
            if any(kw in emotion or kw in emotion_lower for kw in keywords):
                tags.append(tag)
        
        return tags

