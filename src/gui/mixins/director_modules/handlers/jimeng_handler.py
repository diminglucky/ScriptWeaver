"""
即梦AI提示词事件处理器 - 从director_mixin.py重构出来
负责处理即梦AI提示词相关的事件
"""
from tkinter import messagebox, END
from typing import Optional, List, Dict

from ..jimeng_prompt_generator import JimengPromptGenerator
from src.core.logging_config import get_logger

logger = get_logger(__name__)


class JimengHandler:
    """即梦AI提示词事件处理器"""
    
    @staticmethod
    def generate_prompts_for_all_shots(mixin_instance, shots: Optional[List] = None) -> None:
        """为所有分镜生成即梦AI视频提示词（智能版）"""
        logger.debug("_generate_jimeng_prompts_for_all_shots 被调用")
        
        if shots is None:
            if not hasattr(mixin_instance, 'current_shots') or not mixin_instance.current_shots:
                messagebox.showwarning("提示", "请先生成分镜")
                return
            shots = mixin_instance.current_shots
        
        logger.debug(f"开始为 {len(shots)} 个分镜生成即梦AI提示词")
        
        # 加载人物详细信息
        character_details = JimengHandler._load_character_details(mixin_instance)
        
        # 获取故事背景
        story_context = JimengHandler._get_story_context(mixin_instance)
        
        # 使用新生成器生成提示词
        prompts_dict = JimengPromptGenerator.generate_batch_prompts(
            shots, character_details, story_context
        )
        
        # 格式化显示
        prompts_text = JimengPromptGenerator.format_prompts_for_display(prompts_dict)
        
        logger.debug(f"生成的提示词文本长度: {len(prompts_text)}")
        
        # 显示到UI
        if hasattr(mixin_instance, 'jimeng_prompts_text'):
            logger.debug("找到 jimeng_prompts_text，更新显示")
            mixin_instance.jimeng_prompts_text.config(state="normal")
            mixin_instance.jimeng_prompts_text.delete("1.0", "end")
            mixin_instance.jimeng_prompts_text.insert("end", prompts_text)
            mixin_instance.jimeng_prompts_text.config(state="disabled")
            logger.info("即梦AI提示词已生成并显示")
        else:
            logger.error("没有找到 jimeng_prompts_text")
    
    @staticmethod
    def extract_all_prompts(mixin_instance, show_message: bool = True) -> None:
        """提取所有分镜的即梦AI提示词（兼容旧方法）"""
        JimengHandler.generate_prompts_for_all_shots(mixin_instance)
        
        if show_message and hasattr(mixin_instance, 'current_shots'):
            messagebox.showinfo(
                "成功",
                f"已提取 {len(mixin_instance.current_shots)} 个分镜的即梦AI提示词"
            )
    
    @staticmethod
    def copy_all_prompts(mixin_instance) -> None:
        """复制所有即梦AI提示词"""
        if not hasattr(mixin_instance, 'jimeng_prompts_text'):
            messagebox.showwarning("提示", "请先生成即梦AI提示词")
            return
        
        text = mixin_instance.jimeng_prompts_text.get("1.0", END).strip()
        if not text:
            messagebox.showwarning("提示", "提示词为空")
            return
        
        mixin_instance.clipboard_clear()
        mixin_instance.clipboard_append(text)
        messagebox.showinfo("成功", "提示词已复制到剪贴板")
    
    @staticmethod
    def _load_character_details(mixin_instance) -> Dict:
        """加载人物详细信息"""
        character_details = {}
        
        if hasattr(mixin_instance, 'current_project') and mixin_instance.current_project:
            try:
                from pathlib import Path
                import json
                
                project_dir = Path(mixin_instance.current_project.project_dir)
                char_info_file = project_dir / "characters" / "characters_info.json"
                
                if char_info_file.exists():
                    with open(char_info_file, 'r', encoding='utf-8') as f:
                        char_data = json.load(f)
                        character_details = char_data.get('characters', {})
                        logger.info(f"加载了 {len(character_details)} 个人物信息")
            except Exception as e:
                logger.warning(f"加载人物信息失败: {e}")
        
        return character_details
    
    @staticmethod
    def _get_story_context(mixin_instance) -> str:
        """获取故事背景"""
        story_context = ""
        
        if hasattr(mixin_instance, 'story_text'):
            try:
                story_context = mixin_instance.story_text.get("1.0", END).strip()[:500]  # 前500字作为背景
            except Exception:
                pass
        
        return story_context

