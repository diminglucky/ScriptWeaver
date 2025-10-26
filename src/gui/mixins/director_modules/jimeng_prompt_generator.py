"""
即梦AI视频提示词生成器
专门为图生视频优化，结合故事、分镜和人物信息
"""


class JimengPromptGenerator:
    """即梦AI提示词生成器"""
    
    @staticmethod
    def generate_video_prompt(
        shot: dict,
        character_details: dict = None,
        story_context: str = ""
    ) -> str:
        """
        为单个分镜生成即梦AI视频提示词
        
        Args:
            shot: 分镜信息字典
            character_details: 人物详细信息
            story_context: 故事背景
            
        Returns:
            优化的视频提示词
        """
        prompt_parts = []
        
        # 1. 场景和时间
        location = shot.get('location', '')
        time = shot.get('time', '')
        if time and location:
            prompt_parts.append(f"{time}的{location}中")
        elif location:
            prompt_parts.append(f"在{location}中")
        
        # 2. 环境描述（光线、氛围）
        visual_desc = shot.get('visual_description', '')
        if visual_desc:
            # 提取环境关键词
            env_keywords = JimengPromptGenerator._extract_environment_keywords(visual_desc)
            if env_keywords:
                prompt_parts.append(f"，{env_keywords}")
        
        # 3. 人物主体描述（外貌、服装）
        characters = shot.get('characters', [])
        if characters and character_details:
            char_descs = []
            for char_name in characters:
                char_info = character_details.get(char_name, {})
                if char_info:
                    # 提取关键特征
                    appearance = JimengPromptGenerator._extract_character_appearance(
                        char_name, 
                        char_info.get('description', '') or char_info.get('appearance', '')
                    )
                    char_descs.append(appearance)
            
            if char_descs:
                if len(char_descs) == 1:
                    prompt_parts.append(f"，{char_descs[0]}")
                else:
                    prompt_parts.append(f"，{' 和 '.join(char_descs)}")
        
        # 4. 核心动作（最重要）
        action = shot.get('action', '')
        if action:
            # 优化动作描述，使其更自然流畅
            action_optimized = JimengPromptGenerator._optimize_action_description(action)
            prompt_parts.append(f"{action_optimized}")
        
        # 5. 表情和情感
        emotion = shot.get('emotion', '')
        if emotion:
            emotion_desc = JimengPromptGenerator._extract_emotion_description(emotion)
            if emotion_desc:
                prompt_parts.append(f"，{emotion_desc}")
        
        # 6. 对话（如果有）
        dialogue = shot.get('dialogue')
        if dialogue:
            prompt_parts.append(f"。{dialogue}")
        
        # 7. 镜头运动
        camera = shot.get('camera', {})
        if camera:
            camera_movement = JimengPromptGenerator._describe_camera_movement(camera)
            if camera_movement:
                prompt_parts.append(f"。{camera_movement}")
        
        # 8. 镜头类型和构图
        shot_type = shot.get('shot_type', '')
        if shot_type:
            shot_desc = JimengPromptGenerator._describe_shot_type(shot_type)
            if shot_desc:
                prompt_parts.append(f"。{shot_desc}")
        
        # 9. 氛围和风格
        prompt_parts.append("。电影级画面质量，自然流畅的动作")
        
        # 组合成完整提示词
        full_prompt = "".join(prompt_parts)
        
        # 清理格式
        full_prompt = full_prompt.replace("，，", "，").replace("。，", "，").replace("。。", "。")
        full_prompt = full_prompt.strip("，。")
        
        return full_prompt
    
    @staticmethod
    def _extract_environment_keywords(visual_desc: str) -> str:
        """提取环境关键词"""
        keywords = []
        
        # 光线
        if '阳光' in visual_desc or '日光' in visual_desc:
            keywords.append('阳光透过窗户洒进来')
        elif '昏暗' in visual_desc:
            keywords.append('光线昏暗')
        elif '明亮' in visual_desc:
            keywords.append('明亮的光线')
        
        # 天气
        if '雨' in visual_desc:
            keywords.append('雨水打在窗上')
        elif '雪' in visual_desc:
            keywords.append('雪花飘落')
        elif '风' in visual_desc:
            keywords.append('微风轻拂')
        
        # 氛围
        if '温馨' in visual_desc:
            keywords.append('温馨的氛围')
        elif '紧张' in visual_desc:
            keywords.append('紧张的气氛')
        
        return '，'.join(keywords)
    
    @staticmethod
    def _extract_character_appearance(name: str, description: str) -> str:
        """提取人物外貌关键特征"""
        features = [name]
        
        # 性别和年龄
        if '男' in description:
            if '18岁' in description or '17岁' in description:
                features.append('一位高中男生')
            elif '中年' in description:
                features.append('一位中年男子')
        elif '女' in description:
            if '18岁' in description or '17岁' in description:
                features.append('一位高中女生')
            elif '中年' in description:
                features.append('一位中年女子')
        
        # 发型
        if '短发' in description:
            features.append('短发')
        elif '长发' in description:
            features.append('长发')
        if '马尾' in description:
            features.append('扎着马尾')
        
        # 眼镜
        if '眼镜' in description:
            if '黑框' in description:
                features.append('戴着黑框眼镜')
            else:
                features.append('戴着眼镜')
        
        # 服装
        if '白衬衫' in description:
            features.append('穿着白色衬衫')
        elif '校服' in description:
            features.append('穿着校服')
        elif '蓝色连衣裙' in description:
            features.append('穿着蓝色连衣裙')
        elif 'T恤' in description:
            features.append('穿着T恤')
        
        return '，'.join(features[:4])  # 最多4个特征，避免过长
    
    @staticmethod
    def _optimize_action_description(action: str) -> str:
        """优化动作描述，使其更适合视频生成"""
        # 确保动作描述流畅自然
        action = action.strip()
        
        # 添加动作细节
        if '坐' in action and '看书' in action:
            return '正坐在座位上专注地翻看书本'
        elif '站' in action and '说话' in action:
            return '站立着与对方交谈'
        elif '走' in action:
            return '缓缓走动，步伐自然'
        elif '跑' in action:
            return '快速奔跑'
        elif '转头' in action:
            return '慢慢转过头'
        elif '抬头' in action:
            return '缓缓抬起头'
        elif '低头' in action:
            return '低下头'
        elif '微笑' in action:
            return '露出微笑'
        else:
            # 保持原样
            return action
    
    @staticmethod
    def _extract_emotion_description(emotion: str) -> str:
        """提取情感描述"""
        if '开心' in emotion or '微笑' in emotion:
            return '脸上带着温暖的笑容'
        elif '悲伤' in emotion or '难过' in emotion:
            return '神情略显忧伤'
        elif '生气' in emotion or '愤怒' in emotion:
            return '眉头紧皱，表情严肃'
        elif '惊讶' in emotion:
            return '露出惊讶的表情'
        elif '认真' in emotion or '专注' in emotion:
            return '神情专注认真'
        elif '紧张' in emotion:
            return '略显紧张'
        elif '期待' in emotion:
            return '眼神中充满期待'
        return ''
    
    @staticmethod
    def _describe_camera_movement(camera: dict) -> str:
        """描述镜头运动"""
        movement = camera.get('movement', '')
        angle = camera.get('angle', '')
        
        desc_parts = []
        
        # 运动方式
        if '推进' in movement or 'push' in movement.lower():
            desc_parts.append('镜头缓缓推进')
        elif '拉远' in movement or 'pull' in movement.lower():
            desc_parts.append('镜头缓缓拉远')
        elif '跟随' in movement or 'follow' in movement.lower():
            desc_parts.append('镜头跟随移动')
        elif '环绕' in movement:
            desc_parts.append('镜头环绕拍摄')
        elif '摇' in movement or 'pan' in movement.lower():
            desc_parts.append('镜头左右摇动')
        elif '固定' in movement:
            desc_parts.append('镜头保持固定')
        
        # 角度
        if '俯视' in angle:
            desc_parts.append('从上往下俯视')
        elif '仰视' in angle:
            desc_parts.append('从下往上仰视')
        elif '侧面' in angle:
            desc_parts.append('侧面角度')
        
        return '，'.join(desc_parts)
    
    @staticmethod
    def _describe_shot_type(shot_type: str) -> str:
        """描述镜头类型和构图"""
        if '特写' in shot_type or 'close' in shot_type.lower():
            return '面部特写镜头，聚焦表情细节'
        elif '中景' in shot_type or 'medium' in shot_type.lower():
            return '中景镜头，展现人物上半身'
        elif '全景' in shot_type or 'wide' in shot_type.lower():
            return '全景镜头，展现整体环境'
        elif '双人' in shot_type:
            return '双人镜头，展现两人互动'
        return ''
    
    @staticmethod
    def generate_batch_prompts(
        shots: list,
        character_details: dict = None,
        story_context: str = ""
    ) -> dict:
        """
        批量生成所有分镜的即梦AI提示词
        
        Returns:
            {shot_number: prompt} 字典
        """
        prompts = {}
        
        for shot in shots:
            shot_num = shot.get('shot_number', 0)
            prompt = JimengPromptGenerator.generate_video_prompt(
                shot, character_details, story_context
            )
            prompts[shot_num] = prompt
        
        return prompts
    
    @staticmethod
    def format_prompts_for_display(prompts: dict) -> str:
        """格式化提示词用于显示"""
        lines = []
        lines.append("="*80)
        lines.append("即梦AI视频生成提示词")
        lines.append("="*80)
        lines.append("")
        lines.append("使用方法：")
        lines.append("1. 访问 https://jimeng.jianying.com/ai-tool/image/generate")
        lines.append("2. 上传对应分镜的图片")
        lines.append("3. 复制下方提示词到输入框")
        lines.append("4. 点击生成视频")
        lines.append("")
        lines.append("="*80)
        lines.append("")
        
        for shot_num in sorted(prompts.keys()):
            prompt = prompts[shot_num]
            lines.append(f"【分镜 {shot_num}】")
            lines.append("-" * 80)
            lines.append(prompt)
            lines.append("")
            lines.append("")
        
        return "\n".join(lines)

