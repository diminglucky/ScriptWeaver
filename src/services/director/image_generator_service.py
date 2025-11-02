"""
图片生成服务 - 负责调用各种图片生成API
"""

from typing import Optional, Dict, Any
from pathlib import Path
import os

try:
    from src.gui.mixins.director_modules.models.shot import Shot
    from src.gui.mixins.director_modules.models.character import Character
    from .prompt_builder_service import PromptBuilderService
except ImportError:
    from ...gui.mixins.director_modules.models.shot import Shot
    from ...gui.mixins.director_modules.models.character import Character
    from .prompt_builder_service import PromptBuilderService


class ImageGeneratorService:
    """图片生成服务"""
    
    def __init__(self):
        self.prompt_builder = PromptBuilderService()
    
    def generate_shot_image(
        self,
        shot: Shot,
        shot_variant: int,
        output_dir: Path,
        api_config: Dict[str, Any],
        characters_data: Dict[str, Character] = None,
        seed_offset: int = 0
    ) -> Optional[str]:
        """
        生成分镜图片
        
        Args:
            shot: 分镜对象
            shot_variant: 变体编号
            output_dir: 输出目录
            api_config: API配置
            characters_data: 人物数据
            seed_offset: 种子偏移
        
        Returns:
            生成的图片路径，失败返回None
        """
        try:
            provider = api_config.get("provider", "openai")
            
            if provider == "sd":
                return self._generate_with_sd(
                    shot, shot_variant, output_dir, api_config,
                    characters_data, seed_offset
                )
            else:
                return self._generate_with_openai_compatible(
                    shot, shot_variant, output_dir, api_config,
                    characters_data
                )
        
        except Exception as e:
            print(f"生成图片失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _generate_with_sd(
        self,
        shot: Shot,
        shot_variant: int,
        output_dir: Path,
        api_config: Dict[str, Any],
        characters_data: Dict[str, Character] = None,
        seed_offset: int = 0
    ) -> Optional[str]:
        """使用Stable Diffusion生成图片"""
        from src.clients.sd_client import StableDiffusionClient
        from PIL import Image as PILImage
        import os
        
        # 构建提示词
        positive_prompt, negative_prompt = self.prompt_builder.build_shot_prompt(
            shot, "sd", characters_data
        )
        
        # 强化一致性与单人约束，避免人物被替换
        strong_negative = (
            ", multiple people, two persons, three persons, crowd, group,"
            " different person, changing appearance, inconsistent clothing,"
            " inconsistent face, inconsistent hair"
        )
        negative_prompt = (negative_prompt + strong_negative).strip()
        
        # 创建客户端
        sd_base_url = api_config.get("base_url", "http://localhost:7860")
        client = StableDiffusionClient(base_url=sd_base_url)
        
        # 计算种子
        base_seed = 42
        if shot.characters and len(shot.characters) > 0:
            main_char = shot.characters[0]
            base_seed = self.prompt_builder.generate_character_seed(main_char)
        
        seed = base_seed + seed_offset * 10
        
        # 如果有参考人物肖像，优先使用图生图保持一致性
        reference_image_path: Optional[str] = None
        if characters_data and shot.characters:
            for name in shot.characters:
                ch = characters_data.get(name)
                if ch and getattr(ch, "portrait_image", None):
                    img_path = ch.portrait_image
                    if isinstance(img_path, str) and os.path.exists(img_path):
                        reference_image_path = img_path
                        break
        
        # 输出尺寸（可根据分镜类型调整，这里保持与原逻辑一致）
        width, height = 768, 512
        
        print(f"\n=== SD图片生成 ===")
        print(f"正向提示词: {positive_prompt[:200]}...")
        print(f"负向提示词: {negative_prompt[:100]}...")
        print(f"种子: {seed}")
        
        # 计算动态去噪强度（根据镜头类型和一致性模式）
        denoising_strength = self.prompt_builder.get_denoising_strength(shot)
        
        # 生成图片：优先img2img，其次txt2img
        images = None
        if reference_image_path:
            try:
                ref_img = PILImage.open(reference_image_path).convert("RGB")
                images = client.img2img(
                    init_image=ref_img,
                    prompt=positive_prompt,
                    negative_prompt=negative_prompt,
                    denoising_strength=denoising_strength,  # 动态计算，根据镜头类型和一致性模式
                    width=width,
                    height=height,
                    steps=30,
                    cfg_scale=8.0,
                    sampler_name="DPM++ 2M Karras",
                    seed=seed
                )
                print(f"使用人物参考图进行img2img，去噪强度: {denoising_strength:.2f}")
            except Exception as _e:
                print(f"参考图加载失败，回退至txt2img: {_e}")
                images = None
        
        if not images:
            images = client.txt2img(
                prompt=positive_prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                steps=35,
                cfg_scale=8.5,
                sampler_name="DPM++ 2M Karras",
                seed=seed
            )
        
        if images:
            # 保存图片
            image_path = output_dir / f"shot_{shot.shot_number:03d}_v{shot_variant}.png"
            images[0].save(str(image_path))
            print(f"✅ 已保存: {image_path}")
            return str(image_path)
        
        return None
    
    def _generate_with_openai_compatible(
        self,
        shot: Shot,
        shot_variant: int,
        output_dir: Path,
        api_config: Dict[str, Any],
        characters_data: Dict[str, Character] = None
    ) -> Optional[str]:
        """使用OpenAI兼容API生成图片"""
        from src.clients.image_client import OpenAIImageClient
        import requests
        import base64
        
        # 构建提示词
        prompt, _ = self.prompt_builder.build_shot_prompt(
            shot, "openai", characters_data
        )
        
        print(f"\n=== OpenAI图片生成 ===")
        print(f"提示词: {prompt[:200]}...")
        
        # 创建客户端
        client = OpenAIImageClient(
            api_key=api_config.get("key", ""),
            base_url=api_config.get("base_url", ""),
            model=api_config.get("model", "")
        )
        
        # 生成图片
        image_data = client.generate(
            prompt=prompt,
            size="1024x1024"
        )
        
        if image_data:
            # 保存图片
            image_path = output_dir / f"shot_{shot.shot_number:03d}_v{shot_variant}.png"
            
            if isinstance(image_data, str) and image_data.startswith("http"):
                # URL形式
                response = requests.get(image_data)
                with open(image_path, 'wb') as f:
                    f.write(response.content)
            else:
                # Base64形式
                with open(image_path, 'wb') as f:
                    f.write(base64.b64decode(image_data))
            
            print(f"✅ 已保存: {image_path}")
            return str(image_path)
        
        return None
    
    def batch_generate_shots(
        self,
        shots: list,
        output_dir: Path,
        api_config: Dict[str, Any],
        characters_data: Dict[str, Character] = None,
        num_variants: int = 3,
        progress_callback: callable = None
    ) -> Dict[int, list]:
        """
        批量生成分镜图片
        
        Args:
            shots: 分镜列表
            output_dir: 输出目录
            api_config: API配置
            characters_data: 人物数据
            num_variants: 每个分镜的变体数量
            progress_callback: 进度回调函数
        
        Returns:
            {shot_number: [image_paths]}
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = {}
        total = len(shots) * num_variants
        current = 0
        
        for shot in shots:
            shot_images = []
            
            for variant in range(num_variants):
                current += 1
                
                if progress_callback:
                    progress_callback(current, total, shot.shot_number, variant + 1)
                
                image_path = self.generate_shot_image(
                    shot=shot,
                    shot_variant=variant + 1,
                    output_dir=output_dir,
                    api_config=api_config,
                    characters_data=characters_data,
                    seed_offset=variant
                )
                
                if image_path:
                    shot_images.append(image_path)
            
            results[shot.shot_number] = shot_images
        
        return results

