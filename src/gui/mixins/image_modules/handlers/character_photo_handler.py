"""
人物照片事件处理器 - 从char_photo.py重构出来
负责人物照片相关的事件处理
"""
import threading
from typing import List, Dict, Tuple
from tkinter import messagebox, END, DISABLED, NORMAL
from PIL import Image

from .character_photo_generator import CharacterPhotoGenerator
from .character_photo_saver import CharacterPhotoSaver
from .character_photo_preview import CharacterPhotoPreview
from src.core.logging_config import get_logger

logger = get_logger(__name__)


class CharacterPhotoHandler:
    """人物照片事件处理器 - 负责人物照片相关的事件处理"""
    
    @staticmethod
    def handle_generate_photo(mixin_instance) -> None:
        """
        处理生成人物照片的事件
        
        Args:
            mixin_instance: CharacterPhotoMixin实例
        """
        # 获取选中的人物索引（兼容Combobox）
        index = mixin_instance.char_combobox.current()
        
        if index < 0:
            messagebox.showwarning("提示", "请先从下拉框中选择一个人物！")
            return
        
        # 边界检查
        if index < 0 or index >= len(mixin_instance.character_list):
            messagebox.showerror("错误", "人物索引无效，请重新选择人物")
            return
        
        character = mixin_instance.character_list[index]
        character_name = character.get("name", "")
        
        if not character_name:
            messagebox.showerror("错误", "人物信息不完整")
            return
        
        # 获取人物描述（优先从character字典获取，因为文本框是DISABLED状态）
        description = character.get("description", "")
        
        # 如果字典中没有描述，尝试从UI获取（虽然文本框是DISABLED，但可能有遗留数据）
        if not description:
            ui_description = mixin_instance.char_txt_desc.get("1.0", END).strip()
            if ui_description and not ui_description.startswith("尚未生成特征描述"):
                description = ui_description
        
        # 重要：更新character字典中的描述，确保使用最新的描述
        character["description"] = description
        
        # 记录日志，确保使用正确的人物描述
        logger.info(f"准备生成人物照片：{character_name}")
        logger.info(f"人物描述长度：{len(description)} 字符")
        if description:
            logger.info(f"人物描述预览：{description[:100]}...")
        
        if not description or len(description.strip()) < 10:
            messagebox.showwarning("提示", f"请先生成\"{character_name}\"的人物特征描述！\n\n描述太短或为空，无法生成照片。")
            return
        
        # 验证当前选中的人物是否仍然是生成开始时的人物
        # 防止在生成过程中用户切换了人物
        current_index = mixin_instance.char_combobox.current()
        if current_index != index:
            logger.warning(f"人物选择已更改，当前索引：{current_index}，原索引：{index}")
            # 不中断生成，但记录警告
        
        # 检查当前项目
        if not mixin_instance.current_project:
            messagebox.showwarning("提示", "请先创建或打开一个项目，人物照片需要保存到项目中！")
            return
        
        # 获取UI配置
        config = CharacterPhotoHandler._get_generation_config(mixin_instance)
        
        # 确定要生成的角度和表情列表
        angles_to_generate, expressions_to_generate = CharacterPhotoHandler._determine_generation_list(
            config['batch_generate'],
            config['batch_expressions'],
            config['view_angle'],
            config['expression']
        )
        
        total_count = len(angles_to_generate) * len(expressions_to_generate)
        
        # 禁用按钮
        mixin_instance.char_btn_gen_photo.config(state=DISABLED)
        mixin_instance.status.set(f"🎨 正在生成\"{character_name}\"的照片 (共{total_count}张)...")
        if hasattr(mixin_instance, 'update_header_status'):
            mixin_instance.update_header_status(f"生成人物照片...", "🎨")
        
        # 在后台线程中生成
        def generate_photo_thread():
            try:
                generated_photos = []
                current_index = 0
                
                for angle, angle_name in angles_to_generate:
                    for expr, expr_name in expressions_to_generate:
                        current_index += 1
                        
                        logger.info(f"[{current_index}/{total_count}] 正在生成：{angle_name}视图 + {expr_name}表情")
                        
                        # 锁定当前人物的描述，防止在生成过程中人物切换导致的问题
                        # 使用生成开始时获取的描述，而不是每次从UI获取
                        # 因为UI可能在生成过程中被用户改变
                        current_description = character.get("description", "")
                        
                        # 验证描述有效性
                        if not current_description or len(current_description.strip()) < 10:
                            logger.error(f"[{current_index}/{total_count}] 人物\"{character_name}\"的描述无效（长度：{len(current_description)}）")
                            continue  # 跳过这张图片，继续下一张
                        
                        logger.info(f"[{current_index}/{total_count}] 人物：{character_name}，描述长度：{len(current_description)}")
                        logger.debug(f"人物描述：{current_description[:200]}...")
                        
                        # 更新状态
                        mixin_instance.after(0, lambda i=current_index, a=angle_name, e=expr_name: mixin_instance.status.set(
                            f"🎨 [{i}/{total_count}] 正在生成\"{character_name}\"的{a}照片（{e}）..."
                        ))
                        
                        # 生成照片
                        img = CharacterPhotoGenerator.generate_photo(
                            mixin_instance,
                            character,  # 确保包含最新的描述
                            angle,
                            angle_name,
                            expr,
                            expr_name,
                            config['style'],
                            config['extra_desc'],
                            config['variant_value'],
                            config['variant_mode'],
                            config['consistency_level'],
                            config['batch_type'],
                            generated_photos,
                            current_index,
                            total_count
                        )
                        
                        if img:
                            # 保存照片
                            mixin_instance.character_last_image = img
                            
                            # 构建文件名
                            filename = CharacterPhotoHandler._build_filename(
                                character_name,
                                angle_name,
                                angle,
                                expr_name,
                                expr,
                                config['batch_generate'],
                                config['batch_expressions'],
                                config['variant_mode'],
                                config['variant_value']
                            )
                            
                            saved_path = CharacterPhotoSaver.auto_save_photo_with_name(
                                mixin_instance,
                                img,
                                character_name,
                                filename
                            )
                            
                            if saved_path:
                                generated_photos.append({
                                    "angle": angle,
                                    "angle_name": angle_name,
                                    "expression": expr,
                                    "expression_name": expr_name,
                                    "path": saved_path,
                                    "image": img
                                })
                                logger.info(f"✅ [{current_index}/{total_count}] {angle_name}+{expr_name}照片生成成功")
                            else:
                                logger.warning(f"⚠️ [{current_index}/{total_count}] 照片保存失败")
                        else:
                            logger.error(f"❌ [{current_index}/{total_count}] 照片生成失败")
                
                # 更新UI
                mixin_instance.after(0, lambda: CharacterPhotoHandler._update_ui_after_generation(
                    mixin_instance,
                    generated_photos,
                    character_name,
                    total_count
                ))
                
            except Exception as e:
                logger.error(f"生成照片失败: {e}", exc_info=True)
                mixin_instance.after(0, lambda: (
                    messagebox.showerror("生成失败", f"生成照片时发生错误: {str(e)}"),
                    mixin_instance.status.set("❌ 生成照片失败"),
                    mixin_instance.char_btn_gen_photo.config(state=NORMAL)
                ))
        
        threading.Thread(target=generate_photo_thread, daemon=True).start()
    
    @staticmethod
    def _get_generation_config(mixin_instance) -> Dict:
        """获取生成配置"""
        style = mixin_instance.char_img_style.get()
        extra_desc = mixin_instance.char_txt_extra.get("1.0", END).strip()
        gen_type = mixin_instance.char_gen_type.get() if hasattr(mixin_instance, 'char_gen_type') else "standard"
        
        # 根据生成类型设定批量选项
        if gen_type == "standard":
            batch_generate = False
            batch_expressions = False
        elif gen_type == "expressions":
            batch_generate = False
            batch_expressions = True
        elif gen_type == "angles":
            batch_generate = True
            batch_expressions = False
        elif gen_type == "full":
            batch_generate = True
            batch_expressions = True
        else:
            batch_generate = False
            batch_expressions = False
        
        view_angle = mixin_instance.char_view_angle.get() if hasattr(mixin_instance, 'char_view_angle') else "front"
        expression = mixin_instance.char_expression.get() if hasattr(mixin_instance, 'char_expression') else "neutral"
        
        variant_mode = mixin_instance.char_variant_mode.get() if hasattr(mixin_instance, 'char_variant_mode') else "none"
        variant_preset = mixin_instance.char_variant_preset.get() if hasattr(mixin_instance, 'char_variant_preset') else "casual"
        variant_custom = mixin_instance.char_variant_custom.get() if hasattr(mixin_instance, 'char_variant_custom') else ""
        
        if variant_mode == "preset":
            variant_value = variant_preset
        elif variant_mode == "custom":
            variant_value = variant_custom
        else:
            variant_value = ""
        
        consistency_level = mixin_instance.char_consistency_level.get() if hasattr(mixin_instance, 'char_consistency_level') else "high"
        
        batch_type = "none"
        if batch_generate and batch_expressions:
            batch_type = "angle+expression"
        elif batch_generate:
            batch_type = "angle"
        elif batch_expressions:
            batch_type = "expression"
        elif variant_mode != "none":
            batch_type = "variant"
        
        return {
            'style': style,
            'extra_desc': extra_desc,
            'batch_generate': batch_generate,
            'batch_expressions': batch_expressions,
            'view_angle': view_angle,
            'expression': expression,
            'variant_mode': variant_mode,
            'variant_value': variant_value,
            'consistency_level': consistency_level,
            'batch_type': batch_type
        }
    
    @staticmethod
    def _determine_generation_list(
        batch_generate: bool,
        batch_expressions: bool,
        view_angle: str,
        expression: str
    ) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
        """确定要生成的角度和表情列表"""
        angle_names = {
            "front": "正面",
            "side": "侧面",
            "back": "背面",
            "three-quarter": "斜侧"
        }
        
        expression_names = {
            "neutral": "中性",
            "happy": "开心",
            "sad": "难过",
            "angry": "愤怒",
            "surprised": "惊讶",
            "scared": "害怕",
            "smile": "微笑"
        }
        
        if batch_generate:
            angles_to_generate = [("front", "正面"), ("side", "侧面"), ("back", "背面")]
        else:
            angle_name = angle_names.get(view_angle, "正面")
            angles_to_generate = [(view_angle, angle_name)]
        
        if batch_expressions:
            expressions_to_generate = [
                ("neutral", "中性"), ("happy", "开心"), ("sad", "难过"),
                ("angry", "愤怒"), ("surprised", "惊讶"), ("scared", "害怕"),
                ("smile", "微笑")
            ]
        else:
            expression_name = expression_names.get(expression, "中性")
            expressions_to_generate = [(expression, expression_name)]
        
        return angles_to_generate, expressions_to_generate
    
    @staticmethod
    def _build_filename(
        character_name: str,
        angle_name: str,
        angle: str,
        expression_name: str,
        expression: str,
        batch_generate: bool,
        batch_expressions: bool,
        variant_mode: str,
        variant_value: str
    ) -> str:
        """构建文件名"""
        filename_parts = [character_name]
        
        if batch_generate or angle != "front":
            filename_parts.append(angle_name)
        
        if batch_expressions or expression != "neutral":
            filename_parts.append(expression_name)
        
        if variant_mode == "preset" and variant_value:
            variant_name_map = {
                "formal": "正装",
                "casual": "休闲",
                "sport": "运动",
                "traditional": "古装",
                "artistic": "艺术",
                "professional": "职业"
            }
            variant_name = variant_name_map.get(variant_value, variant_value)
            filename_parts.append(variant_name)
        elif variant_mode == "custom" and variant_value and not variant_value.startswith("例如"):
            variant_short = variant_value[:10].replace(" ", "_")
            filename_parts.append(variant_short)
        
        return "_".join(filename_parts)
    
    @staticmethod
    def _update_ui_after_generation(
        mixin_instance,
        generated_photos: List,
        character_name: str,
        total_count: int
    ) -> None:
        """生成完成后更新UI"""
        try:
            # 更新预览（显示最后一张）
            if generated_photos:
                last_photo = generated_photos[-1]
                CharacterPhotoPreview.update_preview(mixin_instance, last_photo["image"])
            
            # 获取项目名称
            if mixin_instance.current_project:
                project_name = mixin_instance.current_project.metadata.get("name", "未命名项目")
            else:
                project_name = "未知项目"
            
            # 根据生成数量显示不同的消息
            if len(generated_photos) > 1:
                photo_desc_list = []
                for p in generated_photos:
                    desc_parts = []
                    if p["angle_name"]:
                        desc_parts.append(p["angle_name"])
                    if p.get("expression_name") and p["expression_name"] != "中性":
                        desc_parts.append(p["expression_name"])
                    photo_desc_list.append("+".join(desc_parts) if desc_parts else "照片")
                
                photo_list_str = "、".join(photo_desc_list)
                mixin_instance.status.set(f"✅ 成功生成{len(generated_photos)}张照片（{photo_list_str}）并保存到项目 [{project_name}]")
                
                detail_list = "\n".join([f"• {desc}" for desc in photo_desc_list])
                messagebox.showinfo("成功", f"已成功生成并保存 {len(generated_photos)} 张照片！\n\n{detail_list}\n\n保存位置：项目/characters/{character_name}_xxx.png")
            else:
                photo = generated_photos[0] if generated_photos else None
                if photo:
                    desc_parts = [photo["angle_name"]]
                    if photo.get("expression_name") and photo["expression_name"] != "中性":
                        desc_parts.append(photo["expression_name"])
                    desc = "+".join(desc_parts)
                    mixin_instance.status.set(f"✅ 成功生成并保存\"{character_name}\"的{desc}照片到项目 [{project_name}]")
            
            if not generated_photos:
                mixin_instance.status.set(f"❌ 照片生成失败或未保存")
            
            # 启用保存按钮
            mixin_instance.char_btn_save_photo.config(state=NORMAL)
            
            # 更新参考人物列表
            if hasattr(mixin_instance, '_update_reference_character_list'):
                mixin_instance._update_reference_character_list()
            
            # 更新顶部状态
            if hasattr(mixin_instance, 'update_header_status'):
                mixin_instance.update_header_status("照片生成完成", "✅")
            
            # 恢复生成按钮
            mixin_instance.char_btn_gen_photo.config(state=NORMAL)
            
        except Exception as e:
            logger.error(f"更新UI失败: {e}", exc_info=True)
            mixin_instance.char_btn_gen_photo.config(state=NORMAL)

