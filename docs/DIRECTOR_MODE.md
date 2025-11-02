# 导演模式模块详细技术文档

## 📋 目录

1. [模块概述](#模块概述)
2. [文件结构](#文件结构)
3. [核心组件详解](#核心组件详解)
4. [工作流程详解](#工作流程详解)
5. [数据模型](#数据模型)

---

## 模块概述

### 功能定位

导演模式模块负责将故事转换为视频制作所需的完整资源：

1. **剧本生成**：将故事转换为专业电影剧本
2. **分镜生成**：将剧本分解为详细的分镜列表
3. **人物提取**：从剧本中提取人物信息
4. **分镜图片生成**：为每个分镜生成图片
5. **视频提示词生成**：生成AI视频平台的提示词
6. **项目持久化**：保存和加载导演模式数据

### 模块位置

```
src/gui/mixins/director_modules/
├── __init__.py
├── director_mixin.py              # 主Mixin类（整合所有功能）
├── director_controller.py          # 控制器（协调服务层）
├── script_generator.py             # 剧本生成器
├── shot_list_generator.py          # 分镜列表生成器
├── video_prompt_builder.py        # 视频提示词构建器
├── sd_consistency_generator.py    # SD一致性生成器
├── sd_prompt_builder.py           # SD提示词构建器
├── jimeng_prompt_generator.py      # 即梦提示词生成器
├── enhanced_shot_prompt_builder.py # 增强分镜提示词
├── shot_viewer.py                 # 分镜查看器
├── prompt_adapter.py              # 提示词适配器
├── project_persistence.py         # 项目持久化
├── image_preview_methods.py       # 图片预览方法
├── advanced_consistency.py        # 高级一致性系统
├── commercial_grade_tips.py        # 商业级提示
│
├── handlers/                      # 事件处理器
│   ├── __init__.py
│   ├── image_generation_handler.py  # 图片生成处理
│   ├── project_handler.py            # 项目加载/保存处理
│   └── jimeng_handler.py             # 即梦提示词处理
│
├── models/                        # 数据模型
│   ├── __init__.py
│   ├── shot.py                      # 分镜模型
│   ├── character.py                 # 人物模型
│   └── project.py                   # 项目模型
│
└── ui/                            # UI构建
    └── director_ui_builder.py       # UI构建器
```

### 模块依赖关系

```
DirectorMixin
├── ScriptGeneratorMixin          # 剧本生成
├── ShotListGeneratorMixin        # 分镜生成
├── VideoPromptBuilderMixin       # 视频提示词
├── ProjectPersistenceMixin       # 项目持久化
├── SDConsistencyMixin            # SD一致性生成
└── ShotViewerMixin               # 分镜查看
```

---

## 文件结构

### 1. director_mixin.py

**职责**: 主Mixin类，整合所有导演模式功能

**主要类**:
- `DirectorMixin`: 导演模式主类（通过多重继承组合多个Mixin）

**关键方法**:
- `_build_director_page()`: 构建导演页面UI
- `_refresh_shot_combo()`: 刷新分镜下拉框
- `_on_generate_selected_shot()`: 生成选中分镜图片
- `_view_character_gallery()`: 查看人物图片库

**文件大小**: 约800行

### 2. script_generator.py

**职责**: 将故事转换为专业电影剧本

**主要类**:
- `ScriptGeneratorMixin`: 剧本生成器Mixin

**关键方法**:
- `_on_story_to_script()`: 生成剧本

**文件大小**: 约450行

### 3. shot_list_generator.py

**职责**: 将剧本分解为详细的分镜列表

**主要类**:
- `ShotListGeneratorMixin`: 分镜生成器Mixin

**关键方法**:
- `_on_script_to_shots()`: 生成分镜列表
- `_split_script_by_scenes()`: 智能分割剧本

**文件大小**: 约450行

### 4. video_prompt_builder.py

**职责**: 构建AI视频平台的提示词

**主要类**:
- `VideoPromptBuilderMixin`: 视频提示词构建器Mixin

**关键方法**:
- `_on_generate_video_prompts()`: 生成视频提示词
- `_build_jimeng_prompt_for_shot()`: 构建即梦AI提示词

**文件大小**: 约50行

---

## 核心组件详解

### 1. ScriptGeneratorMixin类

#### 类定义

```python
class ScriptGeneratorMixin:
    """剧本生成器 Mixin - 专业级故事到剧本转换"""
    
    def _on_story_to_script(self):
        """生成剧本 - 从故事文本转换为专业电影剧本"""
```

#### `_on_story_to_script()` 详解

```python
def _on_story_to_script(self):
    """
    生成剧本 - 从故事文本转换为专业电影剧本
    
    流程:
        1. 获取故事内容
        2. 验证API配置
        3. 构建专业级提示词
        4. 调用AI生成剧本
        5. 显示到UI
        6. 自动保存到项目
    """
    # 步骤1: 获取故事内容
    story_text = self.output.get("1.0", END).strip()
    if not story_text:
        messagebox.showwarning("提示", "请先生成或粘贴故事内容")
        return
    
    # 步骤2: 验证API配置
    api_key = self.api_key.get()
    base_url = self.base_url.get() or "https://api.deepseek.com"
    model = self.model.get() or "deepseek-chat"
    
    if not api_key:
        messagebox.showerror("错误", "请先配置 API Key")
        return
    
    # 步骤3: 构建专业级提示词
    system_prompt = """你是奥斯卡级别的电影编剧，曾为《肖申克的救赎》《盗梦空间》《阿凡达》等大片编写剧本。你擅长：
1. 将故事完整转换为极具画面感的详细剧本
2. 保持人物外貌、服装的一致性描述
3. 动作分解细致，每个细节都可视化
4. 场景过渡自然流畅，连贯性强
5. 对话真实，符合人物性格"""
    
    user_prompt = f"""请将以下故事**完整、详细、连贯**地转换为专业电影剧本。

【核心要求】
1. **完整性（最重要）**：
   - 故事中的**所有情节、人物、对话**都要体现
   - **绝对不能省略、不能跳过、不能简化**任何内容
   - 每个场景都要完整展现，从开始到结束
   - 宁可篇幅长，也不要遗漏细节
   
2. **连贯性**：场景过渡自然流畅，时间线清晰，因果关系明确

3. **详细性**：
   - 环境描述200-300字
   - 人物外貌、服装、动作都要具体描述
   - 每个时间点的动作、对话、情绪都要写清楚
   - 可直接指导拍摄
   
4. **一致性**：人物外貌、服装在整个剧本中必须保持一致

【剧本格式】

═══════════════════════════════════════
【场景X】INT/EXT - 具体地点 - 时间段
═══════════════════════════════════════

【环境描述】（200-300字）
- 空间布局：房间大小、结构、家具摆放、重点道具位置
- 光线氛围：主光源位置、光线强度、明暗分布、色温（冷/暖）
- 视觉细节：墙面装饰、地面材质、窗外景色、远近景物
- 环境音效：背景声音（如风声、车声、音乐）
- 情绪基调：整体氛围感受（温馨/压抑/紧张/轻松等）

【人物登场】
人物1：[姓名]
  - 外貌特征（固定）：年龄段、身高体型、脸型、五官特点
  - 发型发色（固定）：长度、造型、颜色
  - 服装造型（固定）：上衣、下装、鞋子、配饰
  - 初始状态：进入场景时的表情、姿态、位置、正在做什么

【剧情展开】（按时间顺序，动作细致分解）

[时间点 00:00] 场景建立
动作：镜头如何展现环境，观众首先看到什么
描述：用具体的视觉语言描述画面

[时间点 00:05] [人物名]的动作
动作：[人物]具体做什么
  - 身体动作：站/坐/走，移动方向，动作幅度
  - 手部动作：拿/放/指/握，左右手分别做什么
  - 面部表情：眉毛、眼神、嘴角
  - 姿态细节：身体朝向、重心、肢体语言
对话：（如有）"对话内容"
  - 语气：平静/激动/低沉/颤抖/讽刺等
  - 音量：耳语/正常/提高/喊叫
  - 节奏：快速/缓慢/停顿
情绪：[人物]的内心情绪
  - 主情绪：焦虑/喜悦/恐惧/愤怒/悲伤等
  - 强度：轻微/明显/强烈/爆发
  - 变化：情绪如何发展

【镜头建议】
- 主镜头：Wide Shot（全景）/Medium Shot（中景）/Close-up（特写）
- 拍摄角度：平视/俯视15°/俯视45°/仰视15°/仰视45°
- 镜头运动：固定/推进/拉远/横摇/纵摇/跟随/环绕
- 重点捕捉：需要特写的细节（如：手部动作、眼神交流、道具特写）
- 拍摄要点：光线运用、景深控制、构图方式

【场景结尾】
- 持续时长：建议XX秒 - XX秒
- 转场方式：切（硬切）/淡入淡出/叠化/划像/其他特效
- 下一场景：简要说明下一场景的时间、地点，确保连贯

═══════════════════════════════════════

故事内容：
{story_text}"""
    
    # 步骤4: 调用AI生成（后台线程）
    def task():
        client = DeepSeekClient(api_key=api_key, base_url=base_url, model=model)
        
        response = client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            stream=True
        )
        
        # 流式显示结果
        script_text = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                script_text += chunk.choices[0].delta.content
                self.after(0, lambda text=script_text: self._update_script_text(text))
        
        # 步骤5: 保存到项目
        self.after(0, lambda: self._auto_save_script_to_project(script_text))
    
    threading.Thread(target=task, daemon=True).start()
```

**关键点**:
- **完整性优先**: 强调不能省略、跳过、简化任何内容
- **专业格式**: 使用标准的电影剧本格式
- **人物一致性**: 强调人物外貌、服装在整个剧本中保持一致
- **详细描述**: 环境描述200-300字，动作分解细致

### 2. ShotListGeneratorMixin类

#### 类定义

```python
class ShotListGeneratorMixin:
    """分镜生成器 Mixin - 支持分段生成"""
    
    def _on_script_to_shots(self):
        """生成分镜 - 支持分段生成"""
    
    def _split_script_by_scenes(self, script_text: str, max_length: int = 1500) -> list:
        """智能分割剧本为多个场景段落"""
```

#### `_split_script_by_scenes()` 详解

```python
def _split_script_by_scenes(self, script_text: str, max_length: int = 1500) -> list:
    """
    智能分割剧本为多个场景段落
    
    流程:
        1. 按行遍历剧本
        2. 检测场景分隔符（【场景】、场景、##、---）
        3. 如果当前段落超过max_length，或遇到场景标记，就分段
        4. 返回场景列表
    
    参数:
        script_text: 完整剧本文本
        max_length: 每段最大长度（默认1500字符）
    
    返回:
        场景段落列表
    """
    scenes = []
    current_scene = []
    current_length = 0
    
    lines = script_text.split('\n')
    
    for line in lines:
        line_stripped = line.strip()
        
        # 检测场景分隔符
        is_scene_marker = (
            line_stripped.startswith('【场景') or 
            line_stripped.startswith('场景') or
            line_stripped.startswith('##') or
            '---' in line_stripped
        )
        
        # 如果当前段落太长，或遇到场景标记，就分段
        if is_scene_marker and current_scene and current_length > 500:
            scenes.append('\n'.join(current_scene))
            current_scene = [line]
            current_length = len(line)
        elif current_length + len(line) > max_length and current_scene:
            scenes.append('\n'.join(current_scene))
            current_scene = [line]
            current_length = len(line)
        else:
            current_scene.append(line)
            current_length += len(line)
    
    # 添加最后一段
    if current_scene:
        scenes.append('\n'.join(current_scene))
    
    return scenes if scenes else [script_text]
```

**关键点**:
- **智能分割**: 自动检测场景分隔符，避免硬性分割
- **长度控制**: 每段不超过max_length，避免API限制
- **完整性**: 确保每个场景段落完整

#### `_on_script_to_shots()` 详解

```python
def _on_script_to_shots(self):
    """
    生成分镜 - 支持分段生成
    
    流程:
        1. 获取剧本内容
        2. 智能分割剧本为多个场景段落
        3. 逐段生成分镜（保持人物一致性）
        4. 合并所有分镜
        5. 显示到UI
        6. 自动保存到项目
    """
    # 步骤1: 获取剧本内容
    script_text = self.script_text.get("1.0", END).strip()
    if not script_text:
        messagebox.showwarning("提示", "请先生成剧本")
        return
    
    # 步骤2: 智能分割
    scenes = self._split_script_by_scenes(script_text)
    total_scenes = len(scenes)
    
    # 步骤3: 逐段生成分镜
    def task():
        client = DeepSeekClient(api_key=api_key, base_url=base_url, model=model)
        
        all_shots = []
        shot_counter = 1
        
        for scene_idx, scene_text in enumerate(scenes, 1):
            # 上文人物信息（用于保持一致性）
            character_context = ""
            if all_shots:
                last_shot = all_shots[-1]
                if 'character_details' in last_shot:
                    character_context = f"\n\n【重要】之前已出现的人物，外貌和服装必须完全一致：\n{json.dumps(last_shot['character_details'], ensure_ascii=False, indent=2)}"
            
            # 构建提示词
            system_prompt = """你是奥斯卡金像奖级别的分镜设计大师，专注于创作极其详细的分镜头脚本。

【核心能力】
1. 超细致的视觉描述（每个画面300-500字，可直接作为绘画指令）
2. 人物一致性专家（同一人物外貌、服装100%一致）
3. 故事叙事精准（通过图片序列完整展现故事）
4. 情感传达大师（善用构图、光线、表情传达情感）

【工作标准】
- 人物一致性是第一优先级，绝不能改变同一人物的外貌、发型、服装
- 每个分镜描述要达到800-1200字总量
- 描述要具体到可以画出来，避免抽象概念
- 确保JSON格式完整正确，从{开始到}结尾
- 只输出JSON，不要任何其他文字"""
            
            user_prompt = f"""将以下剧本片段分解为**极其详细**的分镜JSON，每个分镜都要能独立讲述故事片段。

【核心目标】
通过图片序列就能完整理解故事情节，每张图都是故事的关键节点。

格式：
{{
  "shots": [
    {{
      "shot_number": {shot_counter},
      "shot_type": "Wide Shot（全景）/Medium Shot（中景）/Close-up（特写）/Extreme Close-up（大特写）",
      "location": "精确位置：室内/室外+具体地点+方位",
      
      "visual_description": "**画面详细描述（300-500字）**：
        - 【画面构图】前景有什么、中景有什么、背景有什么，画面重心在哪里
        - 【空间布局】物品摆放、人物位置关系、距离远近
        - 【光线效果】主光源位置、光线强度、阴影方向、明暗对比、色温
        - 【色彩基调】主色调、辅助色、画面整体色彩情绪
        - 【视觉焦点】观众第一眼会看到什么，引导视线的元素
        - 【环境氛围】给人的整体感受（温馨/压抑/紧张/轻松等）
        ⚠️ 描述要具体到可以直接作为绘画指令",
      
      "characters": ["人物名"],
      "character_details": {{
        "人物名": {{
          "appearance": "外貌（固定，所有分镜必须一致）：
            - 年龄：XX岁
            - 身高体型：XXXcm，体型特征
            - 脸型：圆脸/方脸/瓜子脸/长脸
            - 眼睛：大小、形状、眼神特点
            - 鼻子：高低、形状
            - 嘴唇：厚薄、颜色
            - 肤色：白皙/健康/古铜等
            - 特殊标记：痣/疤痕/酒窝等",
          
          "hair": "发型（固定）：
            - 长度：长发/中长发/短发/超短发
            - 造型：直发/卷发/波浪/马尾/丸子头等
            - 颜色：黑色/棕色/金色等
            - 刘海：有无、样式
            - 发质：柔顺/蓬松/油亮等",
          
          "clothing": "服装（固定，除非剧情换装）：
            - 上衣：款式、颜色、材质、细节（纽扣/拉链/图案/logo）
            - 下装：款式、颜色、长度
            - 鞋子：类型、颜色、款式
            - 配饰：眼镜/项链/手表/包包/帽子等",
          
          "expression": "此分镜中的表情：
            - 眉毛：皱/扬/平/挑
            - 眼神：锐利/温柔/迷茫/惊恐/专注
            - 嘴角：上扬/下垂/紧抿/微张
            - 整体神态：严肃/放松/紧张/开心/悲伤",
          
          "posture": "此分镜中的姿态：
            - 身体朝向：正面/侧面/背面/45度角
            - 身体重心：左/右/居中
            - 手臂位置：自然下垂/交叉/抬手/插兜
            - 腿部姿态：站立/坐下/行走/跑步",
          
          "action": "此分镜中的动作：
            - 具体动作：做什么（如：伸手拿杯子、转身离开、低头看手机）
            - 动作幅度：大/中/小
            - 动作节奏：快速/缓慢/停顿
            - 动作方向：左/右/前/后/上/下"
        }}
      }},
      
      "action": "此分镜中的主要动作和剧情发展",
      "emotion": "此分镜要传达的情绪和氛围",
      "lighting": "光线描述：主光源位置、光线强度、阴影、色温",
      "atmosphere": "氛围描述：整体感受、情绪基调",
      "props": ["道具列表"],
      "camera": {{
        "movement": "固定/推进/拉远/横摇/纵摇/跟随/环绕",
        "angle": "平视/俯视15°/俯视45°/仰视15°/仰视45°",
        "lens": "广角/标准/长焦/微距"
      }},
      "duration": "建议时长：XX秒",
      "transition": "转场方式：切/淡入淡出/叠化/划像"
    }}
  ]
}}

【重要要求】
1. **人物一致性**：如果人物在之前的分镜中出现过，外貌、发型、服装必须**完全一致**
2. **详细性**：visual_description要达到300-500字，可以直接作为绘画指令
3. **完整性**：每个分镜都要能独立讲述故事片段
4. **连贯性**：分镜之间要有逻辑关联，时间线清晰

剧本片段：
{scene_text}
{character_context}"""
            
            # 调用AI生成
            response = client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                stream=False
            )
            
            # 解析JSON
            result_text = response.choices[0].message.content.strip()
            
            # 提取JSON（可能包含markdown代码块）
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result_json = json.loads(json_match.group())
                shots = result_json.get('shots', [])
                
                # 更新shot_number
                for shot in shots:
                    shot['shot_number'] = shot_counter
                    shot_counter += 1
                
                all_shots.extend(shots)
            else:
                logger.error(f"无法解析JSON: {result_text[:200]}")
        
        # 步骤4: 合并所有分镜
        self.current_shots = all_shots
        
        # 步骤5: 显示到UI
        self.after(0, lambda: self._update_shots_display())
        
        # 步骤6: 自动保存
        self.after(0, lambda: self._auto_save_shots_to_project())
    
    threading.Thread(target=task, daemon=True).start()
```

**关键点**:
- **分段生成**: 支持长剧本的分段生成，避免API限制
- **人物一致性**: 每次生成时传递上文人物信息，确保一致性
- **详细描述**: visual_description要求300-500字，可直接作为绘画指令
- **JSON格式**: 严格遵循JSON格式，便于后续处理

### 3. VideoPromptBuilderMixin类

#### 类定义

```python
class VideoPromptBuilderMixin:
    """视频提示词构建器 Mixin"""
    
    def _on_generate_video_prompts(self):
        """生成视频提示词"""
    
    def _build_jimeng_prompt_for_shot(self, shot: dict) -> str:
        """为单个分镜构建即梦AI提示词"""
```

#### `_on_generate_video_prompts()` 详解

```python
def _on_generate_video_prompts(self):
    """
    生成视频提示词
    
    流程:
        1. 检查分镜数据
        2. 遍历所有分镜
        3. 为每个分镜构建提示词
        4. 显示到UI
    """
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
```

#### `_build_jimeng_prompt_for_shot()` 详解

```python
def _build_jimeng_prompt_for_shot(self, shot: dict) -> str:
    """
    为单个分镜构建即梦AI提示词
    
    流程:
        1. 提取visual_description和action
        2. 组合成提示词
        3. 限制长度（500字符）
    
    参数:
        shot: 分镜字典
    
    返回:
        提示词字符串
    """
    visual = shot.get('visual_description', '')
    action = shot.get('action', '')
    
    prompt = f"{visual}\n\n{action}"
    return prompt[:500]  # 即梦AI通常限制长度
```

**关键点**:
- **简单组合**: 直接将visual_description和action组合
- **长度限制**: 限制在500字符以内，符合即梦AI要求

---

## 工作流程详解

### 完整工作流程

```
用户操作
  │
  ├─→ 步骤1: 生成剧本
  │   └─→ ScriptGeneratorMixin._on_story_to_script()
  │       │
  │       ├─→ 获取故事内容
  │       ├─→ 验证API配置
  │       ├─→ 构建专业级提示词
  │       ├─→ 调用AI生成剧本
  │       ├─→ 显示到script_text文本框
  │       └─→ 自动保存到project/director/script.txt
  │
  ├─→ 步骤2: 生成分镜列表
  │   └─→ ShotListGeneratorMixin._on_script_to_shots()
  │       │
  │       ├─→ 获取剧本内容
  │       ├─→ 智能分割剧本（_split_script_by_scenes）
  │       ├─→ 逐段生成分镜（保持人物一致性）
  │       ├─→ 合并所有分镜
  │       ├─→ 显示到shots_text文本框
  │       ├─→ 刷新分镜下拉框（_refresh_shot_combo）
  │       └─→ 自动保存到project/director/shots.json
  │
  ├─→ 步骤3: 提取人物信息（可选）
  │   └─→ 从分镜中提取人物信息
  │       └─→ 保存到project/characters/characters_info.json
  │
  ├─→ 步骤4: 生成分镜图片
  │   └─→ ImageGenerationHandler.handle_generate_selected_shot()
  │       │
  │       ├─→ 选择生成模式（全部/单个）
  │       ├─→ 循环生成每个分镜的图片
  │       │   └─→ SDConsistencyMixin._generate_single_shot_image()
  │       │       ├─→ 构建提示词（包含人物一致性信息）
  │       │       ├─→ 调用SD API生成图片
  │       │       └─→ 保存到project/director/shots/
  │       └─→ 刷新图片预览（_refresh_preview_images）
  │
  └─→ 步骤5: 生成视频提示词
      └─→ VideoPromptBuilderMixin._on_generate_video_prompts()
          │
          ├─→ 遍历所有分镜
          ├─→ 为每个分镜构建提示词
          ├─→ 显示到video_prompt_text文本框
          └─→ 保存到project/director/jimeng_prompts.txt
```

### 人物一致性工作流程

```
分镜生成阶段
  │
  ├─→ 第一段：生成分镜1-N
  │   └─→ 记录人物信息到character_details
  │
  ├─→ 第二段：生成分镜N+1-M
  │   └─→ 传递上文人物信息（character_context）
  │       └─→ AI根据character_context保持一致性
  │
  └─→ 后续段：继续传递人物信息
      └─→ 确保所有分镜中人物外貌、服装一致

图片生成阶段
  │
  ├─→ 第一个分镜：txt2img生成基准图
  │   └─→ 使用固定seed（基于人物名称）
  │
  ├─→ 后续分镜：img2img生成
  │   └─→ 使用第一个分镜的图片作为参考
  │       └─→ denoising_strength=0.4（保持一致性）
  │
  └─→ 人物一致性提示词
      └─→ 包含character_details中的外貌、服装信息
```

---

## 数据模型

### 1. Shot模型

#### 类定义

```python
@dataclass
class Shot:
    """分镜数据模型"""
    shot_number: int
    scene_id: str = ""
    location: str = ""
    time: str = ""
    shot_type: str = ""
    visual_description: str = ""
    scene_description: str = ""
    lighting: str = ""
    atmosphere: str = ""
    characters: List[str] = field(default_factory=list)
    character_details: Dict[str, ShotCharacterDetail] = field(default_factory=dict)
    action: str = ""
    emotion: str = ""
    props: List[str] = field(default_factory=list)
    camera: Optional[ShotCamera] = None
    continuity: str = ""
    duration: str = ""
    transition: str = ""
```

#### 字段说明

- **shot_number**: 分镜编号（从1开始）
- **scene_id**: 场景ID
- **location**: 精确位置（室内/室外+具体地点+方位）
- **time**: 时间段
- **shot_type**: 镜头类型（Wide Shot/Medium Shot/Close-up等）
- **visual_description**: 画面详细描述（300-500字）
- **scene_description**: 场景描述
- **lighting**: 光线描述
- **atmosphere**: 氛围描述
- **characters**: 人物列表（姓名列表）
- **character_details**: 人物详细信息（字典，key为人物名）
- **action**: 主要动作和剧情发展
- **emotion**: 要传达的情绪和氛围
- **props**: 道具列表
- **camera**: 相机参数（ShotCamera对象）
- **continuity**: 连贯性说明
- **duration**: 建议时长
- **transition**: 转场方式

### 2. ShotCharacterDetail模型

#### 类定义

```python
@dataclass
class ShotCharacterDetail:
    """分镜中人物的详细信息"""
    name: str
    appearance: str = ""
    clothing: str = ""
    expression: str = ""
    posture: str = ""
    action: str = ""
```

#### 字段说明

- **name**: 人物姓名
- **appearance**: 外貌（固定，所有分镜必须一致）
- **clothing**: 服装（固定，除非剧情换装）
- **expression**: 此分镜中的表情
- **posture**: 此分镜中的姿态
- **action**: 此分镜中的动作

### 3. Character模型

#### 类定义

```python
@dataclass
class Character:
    """人物数据模型"""
    name: str
    appearance: CharacterAppearance = field(default_factory=CharacterAppearance)
    outfit: CharacterOutfit = field(default_factory=CharacterOutfit)
    personality: str = ""
    background: str = ""
    role: str = ""
```

#### 字段说明

- **name**: 人物姓名
- **appearance**: 外观（CharacterAppearance对象，包含face、hair、body）
- **outfit**: 服装（CharacterOutfit对象，包含top、bottom、shoes、accessories）
- **personality**: 性格特点
- **background**: 背景故事
- **role**: 角色定位

---

## 总结

导演模式模块提供了完整的故事到视频制作工作流：

1. **剧本生成**: 专业级电影剧本格式，强调完整性和一致性
2. **分镜生成**: 支持分段生成，保持人物一致性
3. **图片生成**: 支持SD一致性生成，确保人物形象一致
4. **视频提示词**: 自动生成AI视频平台的提示词
5. **项目持久化**: 自动保存和加载所有数据

所有功能都经过精心设计，确保专业性和一致性。

