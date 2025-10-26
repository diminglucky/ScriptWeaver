"""
高级人物一致性系统 - 使用多种技术确保人物外观一致
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image
import hashlib

class AdvancedConsistencySystem:
    """高级人物一致性系统"""
    
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.char_dir = self.project_dir / "characters"
        self.reference_dir = self.char_dir / "references"
        self.reference_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载人物配置
        self.character_config = self._load_character_config()
        
    def _load_character_config(self) -> Dict:
        """加载人物配置"""
        config_file = self.char_dir / "consistency_config.json"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def generate_character_reference(self, character_name: str, sd_client) -> Optional[str]:
        """
        为人物生成参考图像（正面、高清、中性表情）
        这是确保一致性的关键步骤
        """
        print(f"\n=== 生成{character_name}的参考图像 ===")
        
        # 获取人物描述
        char_info = self._get_character_info(character_name)
        if not char_info:
            print(f"[ERROR] 未找到{character_name}的描述")
            return None
        
        # 构建参考图像提示词（极其详细）
        prompt_parts = []
        
        # 1. 人物数量和性别
        gender = char_info.get('gender', '').lower()
        if '男' in gender or 'male' in gender:
            prompt_parts.append("1boy, male focus, solo")
        else:
            prompt_parts.append("1girl, female focus, solo")
        
        # 2. 年龄
        age = char_info.get('age', '')
        if '18' in age:
            prompt_parts.append("18 years old, teenager")
        elif '17' in age:
            prompt_parts.append("17 years old, teenager")
        
        # 3. 面部特征（从描述中提取）
        desc = char_info.get('description', '')
        
        # 发型
        if '短发' in desc:
            prompt_parts.append("short hair")
        elif '长发' in desc:
            prompt_parts.append("long hair")
        if '马尾' in desc:
            prompt_parts.append("ponytail")
        
        # 眼镜
        if '眼镜' in desc or '戴眼镜' in desc:
            if '黑框' in desc:
                prompt_parts.append("black framed glasses")
            else:
                prompt_parts.append("glasses")
        
        # 服装
        if '白衬衫' in desc:
            prompt_parts.append("white shirt")
        elif '蓝色连衣裙' in desc:
            prompt_parts.append("blue dress")
        
        # 4. 参考图像专用设置
        prompt_parts.extend([
            "portrait", "facing viewer", "centered",
            "neutral expression", "looking at viewer",
            "simple background", "white background",
            "head and shoulders", "professional photo",
            "studio lighting", "high detail face"
        ])
        
        # 5. 质量标签
        prompt_parts.extend([
            "masterpiece", "best quality", "ultra detailed",
            "8k", "photorealistic", "professional photography"
        ])
        
        prompt = ", ".join(prompt_parts)
        
        # 负面提示词（确保单人、正面、清晰）
        negative = (
            "multiple people, side view, profile, back view, "
            "blurry face, covered face, hair over face, "
            "extreme expression, closed eyes, wink, "
            "low quality, bad anatomy, bad hands"
        )
        
        print(f"参考图像提示词: {prompt[:150]}...")
        
        # 使用固定种子生成
        char_seed = self._get_character_seed(character_name)
        
        try:
            images = sd_client.txt2img(
                prompt=prompt,
                negative_prompt=negative,
                width=512,
                height=768,  # 竖版更适合人物
                steps=30,     # 更多步数
                cfg_scale=7.0,
                sampler_name="DPM++ 2M Karras",
                seed=char_seed
            )
            
            if images and len(images) > 0:
                # 保存参考图像
                ref_path = self.reference_dir / f"{character_name}_reference.png"
                images[0].save(ref_path)
                print(f"[OK] 参考图像已保存: {ref_path}")
                
                # 更新配置
                if character_name not in self.character_config:
                    self.character_config[character_name] = {}
                self.character_config[character_name]['reference_image'] = str(ref_path)
                self.character_config[character_name]['seed'] = char_seed
                self._save_character_config()
                
                return str(ref_path)
            
        except Exception as e:
            print(f"[ERROR] 生成参考图像失败: {e}")
            
        return None
    
    def generate_consistent_shot(
        self, 
        shot_info: Dict,
        sd_client,
        shot_num: int,
        variant: int = 1
    ) -> Optional[str]:
        """
        使用img2img生成一致性分镜图片
        """
        characters = shot_info.get('characters', [])
        if not characters:
            print("[WARN] 分镜中没有人物")
            return None
        
        # 主角
        main_char = characters[0]
        
        # 检查是否有参考图像
        ref_image_path = self.character_config.get(main_char, {}).get('reference_image')
        if not ref_image_path or not os.path.exists(ref_image_path):
            print(f"[WARN] {main_char}没有参考图像，先生成")
            ref_image_path = self.generate_character_reference(main_char, sd_client)
            if not ref_image_path:
                print("[ERROR] 无法生成参考图像")
                return None
        
        # 加载参考图像
        ref_image = Image.open(ref_image_path)
        print(f"[OK] 使用参考图像: {ref_image_path}")
        
        # 构建img2img提示词
        prompt_parts = []
        
        # 1. 人物基础信息（与参考图像一致）
        char_info = self._get_character_info(main_char)
        gender = char_info.get('gender', '').lower()
        
        if len(characters) == 1:
            # 单人镜头
            if '男' in gender:
                prompt_parts.append("1boy, male focus, solo")
            else:
                prompt_parts.append("1girl, female focus, solo")
        else:
            # 多人镜头
            prompt_parts.append(f"{len(characters)} people")
            
        # 2. 保持的特征（从参考图像继承）
        desc = char_info.get('description', '')
        if '眼镜' in desc:
            prompt_parts.append("glasses")
        if '白衬衫' in desc:
            prompt_parts.append("white shirt")
        elif '蓝色连衣裙' in desc:
            prompt_parts.append("blue dress")
            
        # 3. 新的动作和场景
        action = shot_info.get('action', '')
        if 'sitting' in action or '坐' in action:
            prompt_parts.append("sitting")
        elif 'standing' in action or '站' in action:
            prompt_parts.append("standing")
        elif 'walking' in action or '走' in action:
            prompt_parts.append("walking")
            
        # 4. 场景描述
        location = shot_info.get('location', '')
        if 'classroom' in location or '教室' in location:
            prompt_parts.append("classroom, desks, blackboard")
            
        # 5. 镜头类型
        shot_type = shot_info.get('shot_type', '')
        if '特写' in shot_type:
            prompt_parts.append("close-up, face focus")
        elif '中景' in shot_type:
            prompt_parts.append("medium shot, upper body")
        elif '全景' in shot_type:
            prompt_parts.append("full body, wide shot")
            
        # 6. 视觉描述
        visual = shot_info.get('visual_description', '')
        if visual:
            # 简化中文描述为英文标签
            if '阳光' in visual:
                prompt_parts.append("sunlight, bright")
            if '微笑' in visual:
                prompt_parts.append("smile")
                
        # 7. 质量标签
        prompt_parts.extend([
            "masterpiece", "best quality", "ultra detailed",
            "photorealistic", "professional photography"
        ])
        
        prompt = ", ".join(prompt_parts)
        
        # 强负面提示词
        negative = (
            "different person, inconsistent appearance, "
            "changed clothes, different hairstyle, "
            "multiple faces, bad anatomy, low quality"
        )
        
        print(f"\n生成分镜{shot_num}-变体{variant}")
        print(f"提示词: {prompt[:150]}...")
        
        # 使用img2img保持一致性
        try:
            # 根据镜头类型调整去噪强度
            if '特写' in shot_type:
                denoising = 0.35  # 面部特写，低去噪
            elif '动作' in action:
                denoising = 0.55  # 有动作，中等去噪
            else:
                denoising = 0.45  # 默认
                
            print(f"去噪强度: {denoising}")
            
            images = sd_client.img2img(
                init_image=ref_image,
                prompt=prompt,
                negative_prompt=negative,
                denoising_strength=denoising,
                width=768,
                height=512,
                steps=25,
                cfg_scale=7.5,
                sampler_name="DPM++ 2M Karras",
                seed=self._get_character_seed(main_char) + variant
            )
            
            if images and len(images) > 0:
                # 保存分镜图片
                output_dir = self.project_dir / "director" / "shots"
                output_dir.mkdir(parents=True, exist_ok=True)
                
                output_path = output_dir / f"shot_{shot_num:03d}_v{variant}.png"
                images[0].save(output_path)
                print(f"[OK] 分镜已保存: {output_path}")
                
                return str(output_path)
                
        except Exception as e:
            print(f"[ERROR] img2img生成失败: {e}")
            import traceback
            traceback.print_exc()
            
        return None
    
    def _get_character_info(self, name: str) -> Dict:
        """获取人物信息"""
        char_file = self.char_dir / "characters_info.json"
        if char_file.exists():
            with open(char_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('characters', {}).get(name, {})
        return {}
    
    def _get_character_seed(self, name: str) -> int:
        """获取人物的固定种子"""
        # 如果已有种子，使用已有的
        if name in self.character_config:
            seed = self.character_config[name].get('seed')
            if seed:
                return seed
        
        # 否则生成固定种子
        hash_obj = hashlib.md5(name.encode('utf-8'))
        seed = int(hash_obj.hexdigest()[:8], 16) % 1000000
        return seed
    
    def _save_character_config(self):
        """保存人物配置"""
        config_file = self.char_dir / "consistency_config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(self.character_config, f, ensure_ascii=False, indent=2)


def generate_all_references(project_dir: str, character_list: List[str]):
    """为所有人物生成参考图像"""
    from src.clients.sd_client import StableDiffusionClient
    
    print("\n" + "="*60)
    print("生成人物参考图像")
    print("="*60)
    
    system = AdvancedConsistencySystem(project_dir)
    client = StableDiffusionClient()
    
    for char_name in character_list:
        print(f"\n处理人物: {char_name}")
        ref_path = system.generate_character_reference(char_name, client)
        if ref_path:
            print(f"✓ 成功生成参考图像")
        else:
            print(f"✗ 生成失败")
    
    print("\n参考图像生成完成！")
