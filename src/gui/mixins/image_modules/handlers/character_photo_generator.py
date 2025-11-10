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
            
            # 记录日志，确保使用正确的人物信息
            logger.info(f"=== 开始生成人物照片 ===")
            logger.info(f"人物名称：{character_name}")
            logger.info(f"描述长度：{len(description)} 字符")
            if description:
                logger.info(f"描述预览：{description[:150]}...")
            
            if not description or len(description.strip()) < 10:
                logger.error(f"人物\"{character_name}\"的描述为空或太短（长度：{len(description)}）！")
                return None
            
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
            
            # 腾讯混元使用中文自然语言提示词
            full_prompt = CharacterPromptBuilder.build_character_photo_prompt(
                description=description,
                style=style,
                view_angle=angle,
                expression=expression,
                composition=composition,
                extra_details=extra_desc,
                language="zh",  # 中文
                default_nationality="chinese",
                variant=variant_value,
                variant_mode=variant_mode,
                consistency_level=consistency_level,
                batch_type=batch_type,
                api_type="hunyuan"  # ✅ 明确指定API类型
            )
            
            full_prompt = CharacterPromptBuilder.optimize_for_api(full_prompt, "hunyuan", 256)
            logger.info(f"腾讯混元中文自然语言提示词 ({angle_name}+{expression_name}): {full_prompt}")
            
            # 构建负向提示词（防止多人、姿势问题、多余物体、背景等）
            negative_prompt = "两个人，多个人，多人，一群人，couple，two people，multiple people，坐着，躺着，lying，sitting，话筒，麦克风，道具，装饰物，翅膀，microphone，mic，props，objects，items，decorations，wings，accessories，holding objects，背景，场景，环境，background，scene，environment，室内，室外，房间，街道，建筑，indoor，outdoor，room，street，building，模糊，低质量，blurry，low quality"
            logger.info(f"腾讯混元负向提示词: {negative_prompt}")
            
            client = HunyuanImageClient(secret_id=secret_id, secret_key=secret_key)
            result = client.generate(
                prompt=full_prompt,
                negative_prompt=negative_prompt,  # 添加负向提示词
                resolution="1024:1024",
                style="201"  # 201是写实风格
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
            
            # 只有在批量生成多张图片时才使用img2img（保持一致性）
            # 第一张图片必须使用完整描述，不能用img2img
            if current_index > 1 and generated_photos and len(generated_photos) > 0:
                try:
                    reference_image = generated_photos[0].get("image")
                    if reference_image:
                        use_img2img = True
                        logger.info(f"使用第一张图片作为参考（img2img模式，保持一致性）")
                except (IndexError, KeyError) as e:
                    logger.warning(f"无法访问参考图: {e}，使用 txt2img")
            
            # 记录使用的模式
            if use_img2img:
                logger.info("模式：img2img（基于第一张图片，保持一致性）")
            else:
                logger.info("模式：txt2img（使用完整人物描述生成）")
            
            composition = "upper_body" if style == "证件照" else "full_body"
            
            if use_img2img:
                # img2img模式：仍然需要包含人物描述，但权重较低
                # 这样可以确保即使有参考图，也能保持正确的人物特征
                full_prompt = CharacterPromptBuilder.build_character_photo_prompt(
                    description=description,  # 保留描述，确保正确的人物特征
                    style=style,
                    view_angle=angle,
                    expression=expression,
                    composition=composition,
                    extra_details=f"{angle_name} view, {expression_name} expression",
                    language="en",  # SD使用英文
                    default_nationality="chinese",
                    variant="",
                    variant_mode="none",
                    consistency_level="high",
                    batch_type=batch_type,
                    api_type="sd"  # ✅ SD使用标签式提示词
                )
            else:
                # txt2img模式：完整描述
                full_prompt = CharacterPromptBuilder.build_character_photo_prompt(
                    description=description,
                    style=style,
                    view_angle=angle,
                    expression=expression,
                    composition=composition,
                    extra_details=extra_desc,
                    language="en",  # SD使用英文
                    default_nationality="chinese",
                    variant=variant_value,
                    variant_mode=variant_mode,
                    consistency_level=consistency_level,
                    batch_type=batch_type,
                    api_type="sd"  # ✅ SD使用标签式提示词
                )
            
            full_prompt = CharacterPromptBuilder.optimize_for_api(full_prompt, "sd", 1000)
            
            # SD使用详细的负向提示词（防止质量问题、多人、错误姿势等）
            negative_prompt = CharacterPromptBuilder.get_negative_prompt_for_character("sd", description)
            
            # 记录提示词
            logger.info(f"=== SD 标签式提示词（Tag-based Prompt）===")
            logger.info(f"正向提示词 (前200字符): {full_prompt[:200]}...")
            logger.info(f"正向提示词长度: {len(full_prompt)} 字符")
            logger.info(f"负向提示词 (前100字符): {negative_prompt[:100]}...")
            logger.info(f"负向提示词长度: {len(negative_prompt)} 字符")
            logger.debug(f"完整正向提示词: {full_prompt}")
            logger.debug(f"完整负向提示词: {negative_prompt}")
            
            sd_client = StableDiffusionClient(base_url=sd_base_url)
            
            if use_img2img:
                consistency_negative = [
                    "different clothing", "clothing change", "different outfit", "wardrobe change",
                    "different hairstyle", "hair change", "different hair color", "haircut",
                    "different accessories", "different style", "style change",
                    "different person", "another character", "face swap", "body swap",
                    # 强化禁止多人（极高权重）
                    "(multiple people:2.0)", "(two people:2.0)", "(three people:2.0)", 
                    "(group:1.8)", "(crowd:1.8)",
                    "(pair:1.8)", "(duo:1.8)", "(couple:1.8)",
                    "((multiple people))", "((two people))", "((three people))",
                    "extra person", "duplicate person", "clone", "twin",
                    "another person", "second person", "third person",
                    "more than 1 person", "2 persons", "3 persons",
                    # 强化禁止不自然的姿势
                    "unnatural pose", "weird pose", "strange pose", "unrealistic pose",
                    "distorted pose", "twisted body", "bent body", "contorted",
                    "exaggerated pose", "dramatic pose", "extreme pose",
                    "awkward pose", "uncomfortable pose", "forced pose",
                    "unbalanced", "tilting", "leaning excessively",
                    "bent knees unnaturally", "twisted torso", "unnatural leg position",
                    "unnatural arm position", "distorted posture", "impossible stance",
                    # 强化禁止躺下、趴下
                    "lying down", "lying", "prone", "lying on ground", "lying position",
                    "reclining", "sitting", "kneeling", "crouching",
                    "not standing", "not upright"
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
                    steps=30,  # 提升步数，增加细节
                    cfg_scale=7.0,  # 降低CFG，避免过度强调导致3D效果
                    sampler_name="DPM++ 2M Karras",  # 更好的采样器
                    batch_size=1  # 明确设置为1，确保只生成一张图片
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
                    steps=35,  # 提升步数，增加细节和质量
                    cfg_scale=6.5,  # 降低CFG，避免过度强调导致3D效果和过度饱和
                    sampler_name="DPM++ 2M Karras",  # 更好的采样器，适合真实感
                    seed=seed,
                    batch_size=1  # 明确设置为1，确保只生成一张图片
                )
            
            if images:
                # 确保只返回第一张图片
                if len(images) > 1:
                    logger.warning(f"SD返回了{len(images)}张图片，只使用第一张")
                return images[0]
            else:
                raise RuntimeError("SD生成失败：未返回任何图片")
                
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
            
            # OpenAI系列使用英文自然语言提示词
            full_prompt = CharacterPromptBuilder.build_character_photo_prompt(
                description=description,
                style=style,
                view_angle=angle,
                expression=expression,
                composition=composition,
                extra_details=extra_desc,
                language="en",  # OpenAI使用英文
                default_nationality="chinese",
                variant=variant_value,
                variant_mode=variant_mode,
                consistency_level=consistency_level,
                batch_type=batch_type,
                api_type=current_api_type  # ✅ OpenAI使用自然语言
            )
            
            full_prompt = CharacterPromptBuilder.optimize_for_api(full_prompt, current_api_type, 1000)
            logger.info(f"{current_api_type.upper()}英文自然语言提示词 ({angle_name}+{expression_name}): {full_prompt[:200]}...")
            
            client = OpenAIImageClient(api_key=api_key, base_url=base_url, model=model)
            results = client.generate(full_prompt, size="1024x1024")
            
            if results:
                return results[0].image
            else:
                raise RuntimeError("API未返回任何图片")
                
        except Exception as e:
            logger.error(f"OpenAI API生成失败: {e}", exc_info=True)
            return None

