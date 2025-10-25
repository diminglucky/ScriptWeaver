"""
智能图片选择器 - 根据分镜描述自动选择最合适的人物图片
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import re


class SmartImageSelector:
    """智能图片选择器"""
    
    # 表情关键词映射
    EMOTION_KEYWORDS = {
        "开心": ["笑", "高兴", "喜悦", "开心", "欢乐", "愉快", "兴奋", "得意", "满意", "微笑"],
        "难过": ["哭", "悲伤", "难过", "失落", "伤心", "痛苦", "沮丧", "流泪", "悲痛"],
        "愤怒": ["怒", "生气", "愤怒", "暴怒", "发火", "恼火", "气愤", "愤恨", "狂怒"],
        "惊讶": ["惊", "震惊", "意外", "吃惊", "惊讶", "惊愕", "诧异", "惊呆", "目瞪口呆"],
        "害怕": ["怕", "恐惧", "害怕", "惊恐", "畏惧", "恐慌", "胆怯", "颤抖", "惊慌"],
        "微笑": ["微笑", "浅笑", "淡笑", "轻笑", "笑容"],
        "中性": ["平静", "冷静", "淡定", "沉着", "镇定", "严肃"]
    }
    
    # 角度关键词映射
    ANGLE_KEYWORDS = {
        "侧面": ["侧面", "侧身", "转身", "侧脸", "斜视", "歪头"],
        "背面": ["背面", "背影", "转过身", "背对", "离开", "走开"],
        "正面": ["正面", "面对", "直视", "注视", "看向", "迎面"]
    }
    
    @classmethod
    def select_character_image(cls, 
                               character_name: str, 
                               shot_description: str,
                               characters_dir: Path,
                               prefer_expression: bool = True) -> Optional[str]:
        """
        根据分镜描述智能选择最合适的人物图片
        
        Args:
            character_name: 人物名称
            shot_description: 分镜描述
            characters_dir: 人物图片目录
            prefer_expression: 是否优先考虑表情（True则先选表情再选角度）
            
        Returns:
            图片路径，如果没有找到则返回None
        """
        if not characters_dir.exists():
            print(f"⚠️ 人物目录不存在: {characters_dir}")
            return None
        
        # 清理人物名称
        clean_name = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', character_name)
        
        # 查找该人物的所有图片
        all_images = list(characters_dir.glob(f"{clean_name}*.png"))
        
        if not all_images:
            print(f"⚠️ 未找到人物 '{character_name}' 的图片")
            return None
        
        print(f"\n🔍 为 '{character_name}' 选择图片...")
        print(f"📝 分镜描述: {shot_description[:100]}...")
        print(f"📁 可用图片: {len(all_images)} 张")
        
        # 分析分镜描述，提取关键信息
        detected_emotion = cls._detect_emotion(shot_description)
        detected_angle = cls._detect_angle(shot_description)
        
        print(f"🎭 检测到的表情: {detected_emotion or '无'}")
        print(f"📐 检测到的角度: {detected_angle or '无'}")
        
        # 根据优先级选择图片
        selected_image = None
        
        if prefer_expression:
            # 优先考虑表情
            if detected_emotion:
                selected_image = cls._find_image_by_emotion(
                    all_images, clean_name, detected_emotion, detected_angle
                )
            
            # 如果没找到特定表情，尝试角度
            if not selected_image and detected_angle:
                selected_image = cls._find_image_by_angle(
                    all_images, clean_name, detected_angle
                )
        else:
            # 优先考虑角度
            if detected_angle:
                selected_image = cls._find_image_by_angle(
                    all_images, clean_name, detected_angle, detected_emotion
                )
            
            # 如果没找到特定角度，尝试表情
            if not selected_image and detected_emotion:
                selected_image = cls._find_image_by_emotion(
                    all_images, clean_name, detected_emotion
                )
        
        # 如果仍然没找到，使用标准形象或第一张
        if not selected_image:
            # 优先使用标准形象
            standard_image = characters_dir / f"{clean_name}_标准.png"
            if standard_image.exists():
                selected_image = str(standard_image)
                print(f"✅ 使用标准形象")
            elif all_images:
                selected_image = str(all_images[0])
                print(f"✅ 使用默认图片: {all_images[0].name}")
        
        if selected_image:
            print(f"🎨 最终选择: {Path(selected_image).name}")
        
        return selected_image
    
    @classmethod
    def _detect_emotion(cls, description: str) -> Optional[str]:
        """检测描述中的情感"""
        description_lower = description.lower()
        
        # 统计每种情感的匹配度
        emotion_scores = {}
        for emotion, keywords in cls.EMOTION_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in description)
            if score > 0:
                emotion_scores[emotion] = score
        
        if emotion_scores:
            # 返回得分最高的情感
            best_emotion = max(emotion_scores.items(), key=lambda x: x[1])
            return best_emotion[0]
        
        return None
    
    @classmethod
    def _detect_angle(cls, description: str) -> Optional[str]:
        """检测描述中的角度"""
        description_lower = description.lower()
        
        # 统计每种角度的匹配度
        angle_scores = {}
        for angle, keywords in cls.ANGLE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in description)
            if score > 0:
                angle_scores[angle] = score
        
        if angle_scores:
            # 返回得分最高的角度
            best_angle = max(angle_scores.items(), key=lambda x: x[1])
            return best_angle[0]
        
        return None
    
    @classmethod
    def _find_image_by_emotion(cls, 
                                all_images: List[Path], 
                                clean_name: str, 
                                emotion: str,
                                angle: Optional[str] = None) -> Optional[str]:
        """根据表情查找图片"""
        # 如果同时有角度要求，尝试找同时满足的
        if angle:
            combined_pattern = f"{clean_name}_{emotion}_{angle}.png"
            for img in all_images:
                if combined_pattern in img.name or f"{clean_name}_{angle}_{emotion}.png" in img.name:
                    print(f"✅ 找到精确匹配: {img.name}")
                    return str(img)
        
        # 只按表情查找
        emotion_pattern = f"{clean_name}_{emotion}.png"
        for img in all_images:
            if emotion_pattern in img.name:
                print(f"✅ 找到表情匹配: {img.name}")
                return str(img)
        
        return None
    
    @classmethod
    def _find_image_by_angle(cls, 
                             all_images: List[Path], 
                             clean_name: str, 
                             angle: str,
                             emotion: Optional[str] = None) -> Optional[str]:
        """根据角度查找图片"""
        # 如果同时有表情要求，尝试找同时满足的
        if emotion:
            combined_pattern = f"{clean_name}_{angle}_{emotion}.png"
            for img in all_images:
                if combined_pattern in img.name or f"{clean_name}_{emotion}_{angle}.png" in img.name:
                    print(f"✅ 找到精确匹配: {img.name}")
                    return str(img)
        
        # 只按角度查找
        angle_pattern = f"{clean_name}_{angle}.png"
        for img in all_images:
            if angle_pattern in img.name:
                print(f"✅ 找到角度匹配: {img.name}")
                return str(img)
        
        return None
    
    @classmethod
    def batch_select_images(cls, 
                           shots: List[Dict],
                           characters_dir: Path) -> Dict[str, Dict[int, str]]:
        """
        批量为所有分镜选择人物图片
        
        Args:
            shots: 分镜列表
            characters_dir: 人物图片目录
            
        Returns:
            {character_name: {shot_index: image_path}}
        """
        results = {}
        
        for idx, shot in enumerate(shots):
            characters = shot.get('characters', [])
            description = shot.get('visual_description', '') or shot.get('action', '')
            
            for char_name in characters:
                if char_name not in results:
                    results[char_name] = {}
                
                image_path = cls.select_character_image(
                    char_name,
                    description,
                    characters_dir
                )
                
                if image_path:
                    results[char_name][idx] = image_path
        
        return results
    
    @classmethod
    def get_character_image_stats(cls, characters_dir: Path) -> Dict[str, Dict[str, int]]:
        """
        获取人物图片统计信息
        
        Returns:
            {character_name: {"total": 11, "expressions": 7, "angles": 3, "standard": 1}}
        """
        if not characters_dir.exists():
            return {}
        
        stats = {}
        all_images = list(characters_dir.glob("*.png"))
        
        # 按人物分组
        char_images = {}
        for img in all_images:
            # 提取人物名称（第一个下划线之前的部分）
            name_parts = img.stem.split('_')
            if name_parts:
                char_name = name_parts[0]
                if char_name not in char_images:
                    char_images[char_name] = []
                char_images[char_name].append(img.name)
        
        # 统计每个人物的图片类型
        for char_name, images in char_images.items():
            stats[char_name] = {
                "total": len(images),
                "expressions": 0,
                "angles": 0,
                "standard": 0,
                "other": 0
            }
            
            for img_name in images:
                if "标准" in img_name:
                    stats[char_name]["standard"] += 1
                elif any(emotion in img_name for emotion in cls.EMOTION_KEYWORDS.keys()):
                    stats[char_name]["expressions"] += 1
                elif any(angle in img_name for angle in ["正面", "侧面", "背面"]):
                    stats[char_name]["angles"] += 1
                else:
                    stats[char_name]["other"] += 1
        
        return stats

