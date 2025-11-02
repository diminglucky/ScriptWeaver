"""
SD一致性生成器 - 使用Stable Diffusion生成保持人物一致性的图片
"""

from tkinter import messagebox


class SDConsistencyMixin:
    """SD一致性生成器 Mixin - 处理人物一致性图片生成"""
    
    # ❌ 移除 __init__，避免多重继承冲突
    # 改为在需要时惰性初始化
    
    def _get_character_seed(self, character_name: str) -> int:
        """获取或生成人物的固定seed"""
        # 惰性初始化
        if not hasattr(self, 'character_seed_map'):
            self.character_seed_map = {}
        
        if character_name not in self.character_seed_map:
            # 🔥 修复：统一种子生成算法，与director_mixin.py保持一致
            # 使用 % 1000000 而不是 % 2147483647，确保种子范围一致
            import hashlib
            seed = int(hashlib.md5(character_name.encode('utf-8')).hexdigest()[:8], 16) % 1000000
            self.character_seed_map[character_name] = seed
        
        return self.character_seed_map[character_name]

