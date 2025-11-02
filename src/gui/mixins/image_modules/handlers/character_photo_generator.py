"""
人物照片生成器 - 从char_photo.py重构出来
负责人物照片的生成逻辑
"""
import base64
from io import BytesIO
from typing import Dict, List, Tuple, Optional
from PIL import Image

from src.clients.hunyuan_image_client import HunyuanImageClient
from src.clients.image_client import OpenAIImageClient
from src.clients.sd_client import StableDiffusionClient
from ....helpers.character_prompt_builder import CharacterPromptBuilder
from src.core.logging_config import get_logger

logger = get_logger(__name__)


class CharacterPhotoGenerator:
    """人物照片生成器 - 负责人物照片的生成逻辑"""
    
    @staticmethod
    def generate_photo(
        mixin_instance,
        character: Dict,
        angle: str,
        angle_name: str,
        expression: str,
        expression_name: str,
        style: str,
        extra_desc: str,
        variant_value: str,
        variant_mode: str,
        consistency_level: str,
        batch_type: str,
        generated_photos: List,
        current_index: int,
        total_count: int
    ) -> Optional[Image.Image]:
        """
        生成单张人物照片
        
        Args:
            mixin_instance: CharacterPhotoMixin实例
            character: 人物信息字典
            angle: 视角（front/side/back）
            angle_name: 视角名称（正面/侧面/背面）
            expression: 表情（neutral/happy/sad等）
            expression_name: 表情名称
            style: 图片风格
            extra_desc: 额外描述
            variant_value: 变体值
            variant_mode: 变体模式
            consistency_level: 一致性级别
            batch_type: 批量类型
            generated_photos: 已生成的照片列表
            current_index: 当前索引
            total_count: 总数量
            
        Returns:
            生成的图片对象，失败返回None
        """
        try:
            character_name = character.get("name", "")
            description = character.get("description", "")
            
            # 检查API配置
            img_api_type = mixin_instance.img_api_type.get() if hasattr(mixin_instance, 'img_api_type') else "openai"
            logger.info(f"图片API类型: {img_api_type}")
            
            if img_api_type == "hunyuan":
                return CharacterPhotoGenerator._generate_with_hunyuan(
                    mixin_instance, description, style, angle, angle_name,
                    expression, expression_name, extra_desc, variant_value,
                    variant_mode, consistency_level, batch_type
                )
            else:
                # 检查provider
                current_preset = mixin_instance.img_api_preset.get() if hasattr(mixin_instance, 'img_api_preset') else ""
                provider = mixin_instance.img_api_presets.get(current_preset, {}).get("provider", "openai") if hasattr(mixin_instance, 'img_api_presets') else "openai"
                
                if provider == "sd":
                    return CharacterPhotoGenerator._generate_with_sd(
                        mixin_instance, description, style, angle, angle_name,
                        expression, expression_name, extra_desc, variant_value,
                        variant_mode, consistency_level, batch_type,
                        generated_photos, current_index, character_name
                    )
                else:
                    return CharacterPhotoGenerator._generate_with_openai(
                        mixin_instance, description, style, angle, angle_name,
                        expression, expression_name, extra_desc, variant_value,
                        variant_mode, consistency_level, batch_type, provider
                    )
                    
        except Exception as e:
            logger.error(f"生成照片失败: {e}", exc_info=True)
            return None
    
    @staticmethod
    def _generate_with_hunyuan(
        mixin_instance,
        description: str,
        style: str,
        angle: str,
        angle_name: str,
        expression: str,
        expression_name: str,
        extra_desc: str,
        variant_value: str,
        variant_mode: str,
        consistency_level: str,
        batch_type: str
    ) -> Optional[Image.Image]:
        """使用腾讯混元API生成"""
        try:
            secret_id = mixin_instance.hunyuan_secret_id.get() if hasattr(mixin_instance, 'hunyuan_secret_id') else ""
            secret_key = mixin_instance.hunyuan_secret_key.get() if hasattr(mixin_instance, 'hunyuan_secret_key') else ""
            
            if not secret_id or not secret_key:
                logger.error("腾讯混元API密钥未配置")
                return None
            
            composition = "upper_body" if style == "证件照" else "full_body"
            
            full_prompt = CharacterPromptBuilder.build_character_photo_prompt(
                description=description,
                style=style,
                view_angle=angle,
                expression=expression,
                composition=composition,
                extra_details=extra_desc,
                language="zh",
                default_nationality="chinese",
                variant=variant_value,
                variant_mode=variant_mode,
                consistency_level=consistency_level,
                batch_type=batch_type
            )
            
            full_prompt = CharacterPromptBuilder.optimize_for_api(full_prompt, "hunyuan", 256)
            logger.info(f"腾讯混元提示词 ({angle_name}+{expression_name}): {full_prompt}")
            
            client = HunyuanImageClient(secret_id=secret_id, secret_key=secret_key)
            result = client.generate(
                prompt=full_prompt,
                resolution="1024:1024",
                style="201"
            )
            
            img_base64 = result["ResultImage"]
            img_data = base64.b64decode(img_base64)
            img = Image.open(BytesIO(img_data))
            return img
            
        except Exception as e:
            logger.error(f"腾讯混元生成失败: {e}", exc_info=True)
            return None
    
    @staticmethod
    def _generate_with_sd(
        mixin_instance,
        description: str,
        style: str,
        angle: str,
        angle_name: str,
        expression: str,
        expression_name: str,
        extra_desc: str,
        variant_value: str,
        variant_mode: str,
        consistency_level: str,
        batch_type: str,
        generated_photos: List,
        current_index: int,
        character_name: str
    ) -> Optional[Image.Image]:
        """使用本地Stable Diffusion生成"""
        try:
            base_url = mixin_instance.img_base_url.get() if hasattr(mixin_instance, 'img_base_url') and mixin_instance.img_base_url.get() else None
            sd_base_url = base_url or "http://localhost:7860"
            
            # 检查是否使用img2img
            reference_image = None
            use_img2img = False
            
            if current_index > 1 and generated_photos and len(generated_photos) > 0:
                try:
                    reference_image = generated_photos[0].get("image")
                    if reference_image:
                        use_img2img = True
                        logger.info("使用第一张图片作为参考（强制一致性）")
                except (IndexError, KeyError) as e:
                    logger.warning(f"无法访问参考图: {e}，使用 txt2img")
            
            composition = "upper_body" if style == "证件照" else "full_body"
            
            if use_img2img:
                full_prompt = CharacterPromptBuilder.build_character_photo_prompt(
                    description="",
                    style=style,
                    view_angle=angle,
                    expression=expression,
                    composition=composition,
                    extra_details=f"{angle_name} view, {expression_name} expression",
                    language="en",
                    default_nationality="chinese",
                    variant="",
                    variant_mode="none",
                    consistency_level="high",
                    batch_type=batch_type
                )
            else:
                full_prompt = CharacterPromptBuilder.build_character_photo_prompt(
                    description=description,
                    style=style,
                    view_angle=angle,
                    expression=expression,
                    composition=composition,
                    extra_details=extra_desc,
                    language="en",
                    default_nationality="chinese",
                    variant=variant_value,
                    variant_mode=variant_mode,
                    consistency_level=consistency_level,
                    batch_type=batch_type,
                    api_type="sd"
                )
            
            full_prompt = CharacterPromptBuilder.optimize_for_api(full_prompt, "sd", 1000)
            logger.info(f"SD标签式提示词 ({angle_name}+{expression_name}): {full_prompt[:200]}...")
            
            sd_client = StableDiffusionClient(base_url=sd_base_url)
            negative_prompt = CharacterPromptBuilder.get_negative_prompt_for_character("sd")
            
            if use_img2img:
                consistency_negative = [
                    "different clothing", "clothing change", "different outfit", "wardrobe change",
                    "different hairstyle", "hair change", "different hair color", "haircut",
                    "different accessories", "different style", "style change",
                    "different person", "another character", "face swap", "body swap"
                ]
                negative_prompt = negative_prompt + ", " + ", ".join(consistency_negative)
            
            if use_img2img:
                logger.info("使用 img2img 模式（denoising_strength=0.4）")
                images = sd_client.img2img(
                    init_image=reference_image,
                    prompt=full_prompt,
                    negative_prompt=negative_prompt,
                    denoising_strength=0.4,
                    width=1024,
                    height=1024,
                    steps=25,
                    cfg_scale=8.5,
                    sampler_name="Euler a"
                )
            else:
                logger.info("使用 txt2img 模式（生成基准图）")
                import hashlib
                seed = int(hashlib.md5(character_name.encode()).hexdigest()[:8], 16)
                logger.info(f"固定 seed: {seed}")
                
                images = sd_client.txt2img(
                    prompt=full_prompt,
                    negative_prompt=negative_prompt,
                    width=1024,
                    height=1024,
                    steps=20,
                    cfg_scale=7.5,
                    sampler_name="Euler a",
                    seed=seed
                )
            
            if images:
                return images[0]
            else:
                raise RuntimeError("SD生成失败")
                
        except Exception as e:
            logger.error(f"SD生成失败: {e}", exc_info=True)
            return None
    
    @staticmethod
    def _generate_with_openai(
        mixin_instance,
        description: str,
        style: str,
        angle: str,
        angle_name: str,
        expression: str,
        expression_name: str,
        extra_desc: str,
        variant_value: str,
        variant_mode: str,
        consistency_level: str,
        batch_type: str,
        provider: str
    ) -> Optional[Image.Image]:
        """使用OpenAI或兼容API生成"""
        try:
            api_key = mixin_instance.img_api_key.get()
            base_url = mixin_instance.img_base_url.get() if hasattr(mixin_instance, 'img_base_url') and mixin_instance.img_base_url.get() else None
            model = mixin_instance.img_model.get() if hasattr(mixin_instance, 'img_model') else "dall-e-3"
            
            if not api_key:
                logger.error("图片API密钥未配置")
                return None
            
            composition = "upper_body" if style == "证件照" else "full_body"
            
            # 根据provider确定api_type
            if "hunyuan" in provider.lower():
                current_api_type = "hunyuan"
            elif "openai" in provider.lower() or "dalle" in provider.lower():
                current_api_type = "openai"
            else:
                current_api_type = "openai"
            
            full_prompt = CharacterPromptBuilder.build_character_photo_prompt(
                description=description,
                style=style,
                view_angle=angle,
                expression=expression,
                composition=composition,
                extra_details=extra_desc,
                language="en",
                default_nationality="chinese",
                variant=variant_value,
                variant_mode=variant_mode,
                consistency_level=consistency_level,
                batch_type=batch_type,
                api_type=current_api_type
            )
            
            full_prompt = CharacterPromptBuilder.optimize_for_api(full_prompt, current_api_type, 1000)
            logger.info(f"{current_api_type.upper()}自然语言提示词 ({angle_name}+{expression_name}): {full_prompt[:200]}...")
            
            client = OpenAIImageClient(api_key=api_key, base_url=base_url, model=model)
            results = client.generate(full_prompt, size="1024x1024")
            
            if results:
                return results[0].image
            else:
                raise RuntimeError("API未返回任何图片")
                
        except Exception as e:
            logger.error(f"OpenAI API生成失败: {e}", exc_info=True)
            return None

