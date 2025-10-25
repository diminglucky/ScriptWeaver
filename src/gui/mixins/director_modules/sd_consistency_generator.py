"""
Stable Diffusion 人物一致性生成器
专门用于导演页面的分镜图片生成，确保人物在多个镜头中保持一致
"""

import os
import json
import base64
from typing import Dict, List, Optional, Tuple
from PIL import Image
from io import BytesIO
import tkinter as tk
from tkinter import ttk, messagebox

from src.clients.sd_client import StableDiffusionClient
from .sd_prompt_optimizer import SDPromptOptimizer


class SDConsistencyGenerator:
    """SD人物一致性生成器"""
    
    def __init__(self, base_url: str = "http://localhost:7860"):
        self.sd_client = StableDiffusionClient(base_url)
        self.character_seeds = {}  # 存储每个人物的种子
        self.character_refs = {}   # 存储每个人物的参考图片
        
    def generate_character_reference(self, character_name: str, character_info: Dict) -> Optional[Image.Image]:
        """
        为人物生成参考图片
        
        Args:
            character_name: 人物名称
            character_info: 人物信息（来自一致性设定）
            
        Returns:
            生成的参考图片
        """
        # 构建人物描述提示词
        prompt = self._build_character_prompt(character_name, character_info)
        
        # 生成参考图片
        images = self.sd_client.txt2img(
            prompt=prompt,
            negative_prompt=self._get_portrait_negative_prompt(),
            width=512,
            height=768,  # 肖像比例
            steps=30,     # 更多步数确保质量
            cfg_scale=7.5,
            sampler_name="DPM++ 2M Karras",
            seed=-1       # 随机种子，之后会保存
        )
        
        if images and len(images) > 0:
            # 保存种子以便后续使用
            # 注意：需要从SD API响应中获取实际使用的种子
            self.character_refs[character_name] = images[0]
            return images[0]
        
        return None
    
    def generate_shot_with_consistency(
        self, 
        shot: Dict, 
        shot_num: int,
        consistency_data: Dict,
        use_img2img: bool = True,
        batch_size: int = 4
    ) -> List[Image.Image]:
        """
        生成保持人物一致性的分镜图片
        
        Args:
            shot: 分镜信息
            shot_num: 镜头号
            consistency_data: 一致性设定数据
            use_img2img: 是否使用图生图模式
            batch_size: 批量生成数量（用于选择最佳结果）
            
        Returns:
            生成的图片列表
        """
        # 获取镜头中的人物
        characters = shot.get('characters', [])
        scene_desc = shot.get('scene_description', '')
        action = shot.get('action', '')
        shot_type = shot.get('shot_type', '')
        
        # 构建基础提示词
        base_prompt = self._build_shot_prompt(shot, consistency_data)
        
        # 根据镜头类型设置图片尺寸
        width, height = self._get_shot_dimensions(shot_type)
        
        generated_images = []
        
        # 如果有人物且有参考图片，使用图生图
        if characters and use_img2img:
            for char_name in characters:
                if char_name in self.character_refs:
                    ref_image = self.character_refs[char_name]
                    
                    # 图生图模式 - 保持人物特征
                    images = self.sd_client.img2img(
                        init_image=ref_image,
                        prompt=base_prompt,
                        negative_prompt=self._get_scene_negative_prompt(),
                        denoising_strength=0.6,  # 保留更多原始特征
                        width=width,
                        height=height,
                        steps=25,
                        cfg_scale=7.5,
                        sampler_name="DPM++ 2M Karras",
                        batch_size=batch_size
                    )
                    
                    if images:
                        generated_images.extend(images)
                        break  # 使用第一个找到的参考图片
        
        # 如果没有参考图片或不使用图生图，使用文生图
        if not generated_images:
            # 使用固定种子确保人物一致性
            seed = self._get_or_create_seed(characters[0] if characters else "scene")
            
            images = self.sd_client.txt2img(
                prompt=base_prompt,
                negative_prompt=self._get_scene_negative_prompt(),
                width=width,
                height=height,
                steps=25,
                cfg_scale=7.5,
                sampler_name="DPM++ 2M Karras",
                seed=seed,
                batch_size=batch_size
            )
            
            if images:
                generated_images.extend(images)
        
        return generated_images
    
    def _build_character_prompt(self, character_name: str, character_info: Dict) -> str:
        """构建人物参考图片的提示词"""
        # 准备优化器需要的数据格式
        char_desc = {
            'age': character_info.get('basic_info', {}).get('age', ''),
            'gender': character_info.get('basic_info', {}).get('gender', ''),
            'face_shape': character_info.get('appearance', {}).get('face', {}).get('shape', ''),
            'skin_tone': character_info.get('appearance', {}).get('face', {}).get('skin_tone', ''),
        }
        
        # 构建发型描述
        hair = character_info.get('appearance', {}).get('hair', {})
        hair_parts = []
        if hair.get('color'):
            hair_parts.append(hair['color'])
        if hair.get('length'):
            hair_parts.append(hair['length'])
        if hair.get('style'):
            hair_parts.append(hair['style'])
        if hair_parts:
            char_desc['hair'] = ''.join(hair_parts)
        
        # 构建服装描述
        default_outfit = character_info.get('outfits', {}).get('default', {})
        outfit_parts = []
        if default_outfit.get('top'):
            outfit_parts.append(default_outfit['top'])
        if default_outfit.get('bottom'):
            outfit_parts.append(default_outfit['bottom'])
        if outfit_parts:
            char_desc['outfit'] = '和'.join(outfit_parts)
        
        # 使用优化器生成英文提示词
        optimized_prompt = SDPromptOptimizer.optimize_character_prompt(char_desc)
        
        # 添加肖像专用标签
        portrait_tags = [
            "portrait", "centered", "looking at viewer",
            "professional photography", "soft lighting",
            "high quality", "detailed face", "sharp focus",
            "beautiful detailed eyes", "realistic"
        ]
        
        return f"{optimized_prompt}, {', '.join(portrait_tags)}"
    
    def _build_shot_prompt(self, shot: Dict, consistency_data: Dict) -> str:
        """构建分镜提示词，整合一致性设定"""
        parts = []
        
        # 场景描述
        scene_desc = shot.get('scene_description', '')
        if scene_desc:
            parts.append(scene_desc)
        
        # 添加人物描述
        characters = shot.get('characters', [])
        character_details = shot.get('character_details', {})
        
        for char_name in characters:
            # 从一致性设定中获取人物信息
            if char_name in consistency_data.get('characters', {}):
                char_data = consistency_data['characters'][char_name]
                char_prompt = self._build_character_prompt(char_name, char_data)
                parts.append(char_prompt)
            elif char_name in character_details:
                parts.append(character_details[char_name])
        
        # 动作描述
        action = shot.get('action', '')
        if action:
            parts.append(action)
        
        # 光线和氛围
        lighting = shot.get('lighting', '')
        if lighting:
            parts.append(lighting)
        
        atmosphere = shot.get('atmosphere', '')
        if atmosphere:
            parts.append(f"{atmosphere} atmosphere")
        
        # 镜头类型相关的构图
        shot_type = shot.get('shot_type', '')
        composition = self._get_shot_composition(shot_type)
        if composition:
            parts.append(composition)
        
        # 添加质量标签
        parts.extend([
            "cinematic", "professional", "high quality",
            "detailed", "sharp focus", "8k resolution"
        ])
        
        return ", ".join(parts)
    
    def _get_shot_dimensions(self, shot_type: str) -> Tuple[int, int]:
        """根据镜头类型返回合适的图片尺寸"""
        dimensions = {
            # 宽镜头 - 横向
            "Wide Shot": (768, 512),
            "宽景": (768, 512),
            
            # 中景 - 标准
            "Medium Shot": (512, 768),
            "中景": (512, 768),
            
            # 特写 - 方形或竖向
            "Close-up": (512, 512),
            "特写": (512, 512),
            
            # 极特写 - 方形
            "Extreme Close-up": (512, 512),
            "极特写": (512, 512),
            
            # 默认
            "default": (512, 768)
        }
        
        for key, dims in dimensions.items():
            if key in shot_type:
                return dims
        
        return dimensions["default"]
    
    def _get_shot_composition(self, shot_type: str) -> str:
        """根据镜头类型返回构图描述"""
        compositions = {
            "Wide Shot": "wide angle view, full scene visible",
            "宽景": "wide angle view, full scene visible",
            
            "Medium Shot": "medium shot, waist up view",
            "中景": "medium shot, waist up view",
            
            "Close-up": "close up shot, face focus",
            "特写": "close up shot, face focus",
            
            "Extreme Close-up": "extreme close up, detail focus",
            "极特写": "extreme close up, detail focus"
        }
        
        for key, comp in compositions.items():
            if key in shot_type:
                return comp
        
        return ""
    
    def _get_portrait_negative_prompt(self) -> str:
        """获取人物肖像的负面提示词"""
        return (
            "nsfw, nude, naked, explicit, "
            "deformed, ugly, bad anatomy, bad proportions, "
            "extra limbs, extra fingers, mutated hands, "
            "poorly drawn face, mutation, deformed face, "
            "blurry, dehydrated, bad quality, low quality, "
            "text, watermark, signature, username, "
            "multiple people, crowd, group"
        )
    
    def _get_scene_negative_prompt(self) -> str:
        """获取场景的负面提示词"""
        return (
            "nsfw, nude, naked, explicit, "
            "ugly, deformed, noisy, blurry, distorted, "
            "out of focus, bad anatomy, extra limbs, "
            "poorly drawn face, poorly drawn hands, "
            "missing fingers, low quality, worst quality, "
            "text, watermark, signature, username, "
            "anime, cartoon, graphic, abstract"
        )
    
    def _get_or_create_seed(self, identifier: str) -> int:
        """获取或创建固定种子，确保同一标识符使用相同种子"""
        if identifier not in self.character_seeds:
            # 基于标识符生成固定种子
            import hashlib
            hash_value = hashlib.md5(identifier.encode()).hexdigest()
            seed = int(hash_value[:8], 16) % 2147483647  # 确保在有效范围内
            self.character_seeds[identifier] = seed
        
        return self.character_seeds[identifier]
    
    def save_character_reference(self, character_name: str, image: Image.Image, save_dir: str):
        """保存人物参考图片"""
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, f"{character_name}_reference.png")
        image.save(save_path)
        return save_path
    
    def load_character_reference(self, character_name: str, image_path: str):
        """加载人物参考图片"""
        if os.path.exists(image_path):
            image = Image.open(image_path)
            self.character_refs[character_name] = image
            return True
        return False


class SDConsistencyMixin:
    """SD人物一致性混入类，用于导演页面"""
    
    def _init_sd_consistency(self):
        """初始化SD一致性生成器"""
        base_url = getattr(self, 'sd_base_url', "http://localhost:7860")
        self.sd_consistency = SDConsistencyGenerator(base_url)
        
    def _generate_character_references(self):
        """为所有人物生成参考图片"""
        if not hasattr(self, 'consistency_data') or not self.consistency_data:
            messagebox.showwarning("提示", "请先设定人物一致性")
            return
        
        characters = self.consistency_data.get('characters', {})
        if not characters:
            messagebox.showwarning("提示", "没有找到人物设定")
            return
        
        # 创建进度窗口
        progress_window = tk.Toplevel(self)
        progress_window.title("生成人物参考图片")
        progress_window.geometry("400x200")
        
        progress_label = tk.Label(progress_window, text="正在生成...")
        progress_label.pack(pady=20)
        
        progress_bar = ttk.Progressbar(progress_window, length=300, mode='determinate')
        progress_bar.pack(pady=20)
        
        total = len(characters)
        progress_bar['maximum'] = total
        
        # 保存路径 - 兼容不同项目对象类型
        if hasattr(self.current_project, 'project_dir'):
            project_path = str(self.current_project.project_dir)
        elif isinstance(self.current_project, dict):
            project_path = self.current_project.get('path', '')
        else:
            project_path = str(self.current_project)
        
        ref_dir = os.path.join(project_path, 'director', 'character_refs')
        os.makedirs(ref_dir, exist_ok=True)
        
        def generate():
            for i, (char_name, char_info) in enumerate(characters.items()):
                progress_label.config(text=f"生成 {char_name} 的参考图片...")
                progress_bar['value'] = i
                progress_window.update()
                
                # 生成参考图片
                ref_image = self.sd_consistency.generate_character_reference(char_name, char_info)
                
                if ref_image:
                    # 保存参考图片
                    save_path = self.sd_consistency.save_character_reference(
                        char_name, ref_image, ref_dir
                    )
                    print(f"✅ 已生成 {char_name} 的参考图片: {save_path}")
            
            progress_bar['value'] = total
            progress_label.config(text="✅ 所有参考图片生成完成！")
            progress_window.after(1000, progress_window.destroy)
        
        # 在后台线程运行
        import threading
        threading.Thread(target=generate, daemon=True).start()
    
    def _generate_shot_with_sd_consistency(self, shot: Dict, shot_num: int, output_dir: str, 
                                            shot_variant: int = 1) -> Optional[str]:
        """使用SD一致性生成器生成分镜图片
        
        Args:
            shot: 分镜信息
            shot_num: 镜头号
            output_dir: 输出目录
            shot_variant: 变体编号（用于文件命名）
        """
        try:
            if not hasattr(self, 'sd_consistency'):
                self._init_sd_consistency()
            
            # 加载已有的参考图片 - 优先使用一致性设定中的portrait_image
            consistency_data = getattr(self, 'consistency_data', {})
            characters_data = consistency_data.get('characters', {})
            
            # 优先从一致性设定中加载人物形象
            for char_name in shot.get('characters', []):
                char_data = characters_data.get(char_name, {})
                portrait_path = char_data.get('portrait_image')
                
                if portrait_path and os.path.exists(portrait_path):
                    print(f"🎨 加载人物 '{char_name}' 的标准形象: {portrait_path}")
                    self.sd_consistency.load_character_reference(char_name, portrait_path)
                    continue
                
                # 如果没有portrait_image，尝试加载旧的参考图片
                if hasattr(self.current_project, 'project_dir'):
                    project_path = str(self.current_project.project_dir)
                elif isinstance(self.current_project, dict):
                    project_path = self.current_project.get('path', '')
                else:
                    project_path = str(self.current_project)
                
                ref_dir = os.path.join(project_path, 'director', 'character_refs')
                ref_path = os.path.join(ref_dir, f"{char_name}_reference.png")
                if os.path.exists(ref_path):
                    print(f"📂 加载人物 '{char_name}' 的旧参考图: {ref_path}")
                    self.sd_consistency.load_character_reference(char_name, ref_path)
            
            # 生成单张一致性图片（不是批量）
            images = self.sd_consistency.generate_shot_with_consistency(
                shot=shot,
                shot_num=shot_num,
                consistency_data=getattr(self, 'consistency_data', {}),
                use_img2img=True,  # 优先使用图生图
                batch_size=1       # 生成1张
            )
            
            if images:
                # 保存图片（带变体编号）
                output_path = os.path.join(output_dir, f"shot_{shot_num:03d}_v{shot_variant}.png")
                images[0].save(output_path)
                print(f"✅ SD一致性生成成功: {output_path}")
                return output_path
            
        except Exception as e:
            print(f"SD一致性生成失败: {str(e)}")
            import traceback
            traceback.print_exc()
            
        return None
