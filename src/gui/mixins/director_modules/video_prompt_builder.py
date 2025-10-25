"""
视频提示词构建器 - 为即梦AI/视频平台生成提示词
"""

from typing import List, Dict


class VideoPromptBuilderMixin:
	"""视频提示词生成功能"""
	
	def build_jimeng_ai_prompt(self, shots: List[Dict]) -> str:
		"""
		为即梦AI构建视频生成提示词
		
		即梦AI特性：
		- 支持图片序列转视频
		- 支持自然转场
		- 支持背景音乐和配音
		- 支持5s-60s视频
		
		Args:
			shots: 分镜头列表
			
		Returns:
			即梦AI格式的提示词
		"""
		
		prompt = "创建一个令人惊艳的5秒短视频：\n\n"
		
		# 添加镜头转场信息
		transitions = []
		for i, shot in enumerate(shots, 1):
			shot_type = shot.get('shot_type', 'Medium Shot')
			description = shot.get('scene_description', '')
			atmosphere = shot.get('atmosphere', '')
			
			# 基于镜头类型推荐转场
			transition = self._suggest_transition(shot_type, i == 1)
			
			shot_prompt = f"""
镜头 {i}（约1秒）：
【视觉】{description}
【氛围】{atmosphere}
【转场】{transition}
"""
			transitions.append(shot_prompt)
		
		prompt += "".join(transitions)
		
		# 添加整体建议
		prompt += """
【视频效果建议】
- 使用自然平滑的转场
- 保持一致的色彩风格
- 添加微妙的动态感
- 突出人物的情感表现

【时间节奏】
- 总长5秒
- 每个镜头约1秒
- 转场时间0.1-0.3秒

【音乐氛围】
- 背景音乐应该温暖、舒缓
- 音乐与画面节奏一致
"""
		
		return prompt
	
	def build_capcut_template(self, shots: List[Dict]) -> str:
		"""
		为CapCut/剪映生成编辑模板说明
		"""
		
		template = "剪映编辑指南：\n\n"
		
		for i, shot in enumerate(shots, 1):
			template += f"""
【第 {i} 个视频片段】
文件名：shot_{i:02d}.mp4
时长：1秒
转场：{self._suggest_capcut_transition(i == 1)}
滤镜：保持原色
文字：无
特效：微妙缩放
"""
		
		template += """
【整体设置】
- 视频比例：16:9（用于社媒分享）或 1:1（用于短视频平台）
- 帧率：30fps
- 分辨率：1080p
- 音乐：从库中选择"温暖"、"舒缓"类别
- 字幕：无

【导出设置】
- 格式：MP4
- 比特率：中等
- 优化：为社交媒体优化
"""
		
		return template
	
	def build_image_to_video_guide(self, shots: List[Dict]) -> str:
		"""
		生成将静态图片转为视频的指南
		
		方案：
		1. 使用Runway ML的Motion Brush
		2. 使用D-ID视频生成
		3. 使用即梦AI的图片升级视频
		4. 使用Synthesia的视频合成
		"""
		
		guide = """
# 将分镜头图片转换为视频的3种方案

## 方案1：即梦AI网页版（推荐，免费额度）

### 🌐 使用地址
https://jimeng.jianying.com （剪映旗下，有免费额度）

### 📝 详细步骤：

1. **准备工作**
   - 确保所有分镜图片已生成（shot_001.png, shot_002.png...）
   - 打开即梦AI网页版

2. **创建视频**
   - 点击「图生视频」功能
   - 上传第一张分镜图片

3. **设置参数**
   - 生成时长：5秒
   - 运动幅度：中等（适合故事叙述）
   - 镜头运动：自动

4. **批量处理建议**
   - 可以一次上传多张图片
   - 选择「智能转场」
   - 让AI自动处理镜头切换

5. **分镜提示词**（复制到对应镜头）：
"""
		
		# 为每个镜头生成网页版专用提示词
		for i, shot in enumerate(shots[:5], 1):  # 5秒视频，最多5个镜头
			prompt = self._build_single_shot_video_prompt(shot, i)
			guide += f"\n**镜头{i}（第{i}秒）：**\n"
			guide += f"图片文件：shot_{i:03d}.png\n"
			guide += f"提示词：{prompt}\n"
			guide += f"运动建议：{self._suggest_camera_motion(shot.get('shot_type', ''))}\n\n"
		
		guide += """
### 💡 使用技巧

1. **免费额度使用**
   - 新用户有免费额度
   - 建议先用低质量测试效果
   - 满意后再用高质量生成

2. **提高生成质量**
   - 确保图片分辨率统一（建议1024x1024）
   - 保持人物服装一致性
   - 使用相似的光线和色调

3. **后期处理**
   - 下载生成的视频
   - 使用剪映添加音乐和字幕
   - 调整转场效果

**生成的视频用途：**
- 作为基础素材进行剪辑

---

## 方案2：Runway ML（推荐，需付费）

**步骤：**
1. 访问 runway.com
2. 创建新项目
3. 使用 Motion Brush 工具：
   - 上传分镜头图片
   - 在关键部分画出运动轨迹
   - AI将生成平滑的视频转换
4. 导出视频

---

## 方案3：本地方案（免费）

**使用 Stable Diffusion Deforum 扩展：**

```python
# 配置参数
{
  "animation_mode": "2D",
  "max_frames": 30,  # 1秒 = 30帧（30fps）
  "motion_scale": 0.5,
  "zoom": 1.01,  # 微妙的推进
  "angle": 0,
  "translation_x": 0,
  "translation_y": 0
}
```

**步骤：**
1. 在本地SD中安装 Deforum 扩展
2. 导入分镜头图片
3. 设置上述参数
4. 生成动画
5. 导出视频

---

## 视频合成完整流程

1. 生成所有分镜头图片（已完成）
2. 选择合适的转换方案将图片转为视频
3. 使用剪映/CapCut进行编辑：
   - 添加转场效果
   - 调整音乐和节奏
   - 添加配音
4. 导出最终视频

---

## 即梦AI提示词生成规则

对于每个镜头，提示词应包含：

```
[主体描述], [动作/变化], [镜头移动], [光线效果], [氛围]

示例：
"一个穿着黑色校服的男生，低头沉思，画面轻微推进，
温暖的朝阳照亮他的侧脸，气氛压抑而深沉"
```

## 推荐的视频生成工具对比

| 工具 | 成本 | 质量 | 易用性 | 时间 |
|------|------|------|--------|------|
| 即梦AI | $$ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 快 |
| Runway ML | $$ | ⭐⭐⭐⭐ | ⭐⭐⭐ | 中 |
| 本地Deforum | 免费 | ⭐⭐⭐ | ⭐ | 慢 |
| D-ID | $$$ | ⭐⭐⭐⭐ | ⭐⭐ | 快 |

"""
		
		return guide
	
	def _suggest_camera_motion(self, shot_type: str) -> str:
		"""根据镜头类型推荐相机运动"""
		motions = {
			"Wide Shot": "缓慢横移，展现全景",
			"宽景": "缓慢横移，展现全景",
			"Medium Shot": "轻微推进，聚焦人物",
			"中景": "轻微推进，聚焦人物",
			"Close-up": "微妙晃动，强调情绪",
			"特写": "微妙晃动，强调情绪",
			"Extreme Close-up": "静止或极缓慢推进",
			"极特写": "静止或极缓慢推进",
			"Tracking": "跟随主体移动",
			"跟镜": "跟随主体移动"
		}
		
		for key, motion in motions.items():
			if key in shot_type:
				return motion
		
		return "轻微推拉，保持动态感"
	
	def _build_single_shot_video_prompt(self, shot: Dict, shot_num: int) -> str:
		"""为单个镜头生成视频提示词"""
		
		description = shot.get('scene_description', '')
		action = shot.get('action', '')
		atmosphere = shot.get('atmosphere', '')
		lighting = shot.get('lighting', '')
		
		prompt = f"{description}, {action}, {lighting}, {atmosphere}"
		
		# 根据镜头类型添加运动建议
		shot_type = shot.get('shot_type', '')
		if '特写' in shot_type or 'Close' in shot_type:
			prompt += ", 画面轻微推进"
		elif '宽景' in shot_type or 'Wide' in shot_type:
			prompt += ", 缓慢平移扫过"
		
		return prompt
	
	def _suggest_transition(self, shot_type: str, is_first: bool) -> str:
		"""推荐转场效果"""
		
		if is_first:
			return "淡入"
		
		if '特写' in shot_type or 'Close' in shot_type:
			return "缓慢淡出 → 淡入"
		elif '宽景' in shot_type or 'Wide' in shot_type:
			return "推进转场"
		else:
			return "中性淡出"
	
	def _suggest_capcut_transition(self, is_first: bool) -> str:
		"""为剪映推荐转场"""
		
		if is_first:
			return "无转场（开始）"
		else:
			return "淡出 (0.2s)"
