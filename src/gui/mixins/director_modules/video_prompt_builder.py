"""
视频提示词构建器 - 为AI视频生成平台构建提示词
"""

from tkinter import messagebox


class VideoPromptBuilderMixin:
    """视频提示词构建器 Mixin"""
    
    def _on_generate_video_prompts(self):
        """生成视频提示词"""
        if not hasattr(self, 'current_shots') or not self.current_shots:
            messagebox.showwarning("提示", "请先生成分镜")
            return
        
        # 构建即梦AI格式的提示词
        prompts = []
        for shot in self.current_shots:
            # 跳过非字典元素
            if not isinstance(shot, dict):
                continue
            prompt = self._build_jimeng_prompt_for_shot(shot)
            prompts.append(prompt)
        
        # 显示结果
        result = "\n\n".join([f"【分镜{i+1}】\n{p}" for i, p in enumerate(prompts)])
        
        if hasattr(self, 'video_prompt_text'):
            self.video_prompt_text.config(state="normal")
            self.video_prompt_text.delete("1.0", "end")
            self.video_prompt_text.insert("end", result)
            self.video_prompt_text.config(state="disabled")
    
    def _build_jimeng_prompt_for_shot(self, shot: dict) -> str:
        """为单个分镜构建即梦AI提示词"""
        visual = shot.get('visual_description', '')
        action = shot.get('action', '')
        
        prompt = f"{visual}\n\n{action}"
        return prompt[:500]  # 即梦AI通常限制长度

