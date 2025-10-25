# 🎨 Stable Diffusion 人物一致性完整指南

## 📌 概述

本指南详细介绍如何使用本地Stable Diffusion在导演页面生成保持人物一致性的分镜图片。通过结合文生图、图生图、固定种子等技术，确保同一人物在不同镜头中保持外观一致。

## 🚀 快速开始

### 1. 启动SD WebUI
```bash
# Windows
cd your_stable_diffusion_webui_folder
set COMMANDLINE_ARGS=--api --xformers --no-half-vae
webui-user.bat

# 确保看到：Running on local URL: http://127.0.0.1:7860
```

### 2. 配置项目
1. 在"设置"页面选择"本地 Stable Diffusion"
2. 确保API地址为 `http://localhost:7860`
3. 测试连接成功

### 3. 使用导演功能
1. 生成剧本和分镜
2. 编辑人物一致性设定
3. 点击"生成SD参考图片"（新功能）
4. 生成分镜图片

## 💡 核心技术

### 1. **人物参考图片生成**
首先为每个人物生成高质量的参考图片：

```python
# 提示词结构
"{age} {gender}, {face_shape}, {skin_tone} skin, {hair_description}, 
{outfit}, portrait, centered, looking at viewer, professional photography, 
soft lighting, high quality, detailed face, sharp focus"

# 示例
"28 years old male, oval face, fair skin, black short straight hair, 
wearing blue checkered shirt, portrait, centered, looking at viewer, 
professional photography, soft lighting, high quality, detailed face"
```

### 2. **图生图保持一致性**
使用参考图片作为基础，通过图生图生成不同场景：

```python
# 关键参数
denoising_strength: 0.6  # 保留40%原始特征
cfg_scale: 7.5          # 适中的提示词权重
sampler: "DPM++ 2M Karras"  # 稳定的采样器
```

### 3. **固定种子技术**
为每个人物分配固定种子，确保特征稳定：

```python
# 基于人物名称生成固定种子
import hashlib
seed = int(hashlib.md5(character_name.encode()).hexdigest()[:8], 16)
```

## 📝 提示词编写技巧

### 1. **人物描述层次**
```
基础层：年龄 + 性别 + 种族
├── 脸部：脸型 + 肤色 + 五官特征
├── 发型：颜色 + 长度 + 风格 + 特殊处理
├── 身材：身高体型 + 体态特征
└── 服装：上装 + 下装 + 配饰 + 风格
```

### 2. **镜头类型提示词**

| 镜头类型 | 英文 | 构图提示词 | 推荐尺寸 |
|---------|------|-----------|---------|
| 宽景 | Wide Shot | wide angle view, full scene visible, environmental shot | 768×512 |
| 中景 | Medium Shot | waist up view, medium distance, half body shot | 512×768 |
| 特写 | Close-up | face focus, close up shot, facial expression | 512×512 |
| 极特写 | Extreme Close-up | extreme close up, detail focus, macro shot | 512×512 |

### 3. **质量控制标签**
```
必备正面标签：
masterpiece, best quality, high resolution, sharp focus, 
professional photography, detailed face, perfect lighting

必备负面标签：
nsfw, lowres, bad anatomy, bad hands, text, error, 
missing fingers, extra digit, fewer digits, cropped, 
worst quality, low quality, normal quality, jpeg artifacts
```

## 🔧 高级技巧

### 1. **多人物场景处理**
```python
# 主体人物放前面，配角放后面
"main character: {detailed description}, 
in the background: {secondary character description},
interaction between characters, eye contact"
```

### 2. **表情变化保持一致性**
```python
# 基础描述不变，只改变表情部分
base_prompt = "28yo male, black hair, blue shirt"
expressions = ["smiling", "serious", "surprised", "thinking"]

for expr in expressions:
    prompt = f"{base_prompt}, {expr} expression, portrait"
```

### 3. **服装变化处理**
```python
# 保持人物特征，只更换服装描述
character_base = "28yo male, oval face, black hair"
outfits = {
    "work": "wearing formal business suit",
    "casual": "wearing t-shirt and jeans",
    "sport": "wearing sports wear"
}
```

### 4. **背景一致性**
```python
# 使用场景种子确保背景风格统一
scene_settings = {
    "lighting": "soft natural light from window",
    "atmosphere": "calm and peaceful",
    "color_tone": "warm colors, golden hour"
}
```

## 📊 最佳实践工作流

### 步骤1：生成人物参考图（每个人物4-8张）
```
目的：找到最佳的人物形象
- 正面照
- 侧面照（可选）
- 不同表情
- 不同光线
```

### 步骤2：选择最佳参考图
```
标准：
- 五官清晰
- 特征明显
- 符合设定
- 易于识别
```

### 步骤3：批量生成分镜
```
技巧：
- 每个镜头生成4张，选最佳
- 保存替代版本
- 记录使用的种子
```

### 步骤4：后期筛选
```
检查点：
- 人物是否一致
- 场景是否合理
- 动作是否自然
- 光线是否统一
```

## 🛠️ 推荐模型和设置

### 1. **写实人物模型**
- **Deliberate v2**: 适合写实人物，细节丰富
- **Realistic Vision**: 真实感强，适合现代场景
- **ChilloutMix**: 亚洲人物表现优秀

### 2. **最佳参数设置**
```json
{
  "采样方法": "DPM++ 2M Karras",
  "采样步数": 25-30,
  "CFG Scale": 7-8,
  "图片尺寸": "512x768 (人物) / 768x512 (场景)",
  "高清修复": "开启，放大倍数1.5",
  "面部修复": "开启 (使用CodeFormer)"
}
```

### 3. **VAE推荐**
- **vae-ft-mse-840000**: 提升色彩和细节
- 确保在设置中选择正确的VAE

## ⚠️ 常见问题解决

### 1. **人物特征不稳定**
- 增加人物描述的具体性
- 使用更低的denoising_strength（0.4-0.6）
- 确保种子固定

### 2. **表情僵硬**
- 添加情绪描述：natural expression, relaxed face
- 使用LoRA模型增强表情
- 参考真实照片的表情

### 3. **服装细节丢失**
- 提高分辨率到768或1024
- 使用高清修复
- 详细描述服装材质和颜色

### 4. **多人物混淆**
- 使用区域提示词：on the left/right
- 明确人物大小：in foreground/background
- 考虑分开生成后合成

## 📚 提示词模板库

### 人物基础模板
```
# 年轻女性
"25 years old chinese woman, oval face, fair skin, long black straight hair, 
brown eyes, natural makeup, gentle smile"

# 中年男性
"40 years old asian man, square face, tan skin, short black hair with gray, 
wearing glasses, professional appearance"

# 老年人物
"65 years old elderly chinese man, wrinkled face, gray hair, kind eyes, 
wearing traditional clothing"
```

### 表情模板
```
# 基础表情
neutral, smiling, laughing, serious, thinking, surprised, angry, sad

# 细微表情
slight smile, gentle expression, contemplating, concerned look, 
determined face, tired eyes, hopeful expression
```

### 动作模板
```
# 站姿
standing straight, leaning against wall, arms crossed, hands in pockets

# 坐姿
sitting on chair, relaxed posture, leaning forward, crossed legs

# 互动
shaking hands, having conversation, looking at each other, gesturing
```

## 🎯 项目集成使用

### 1. 在导演页面的工作流
1. **编辑一致性设定** → 详细设定每个人物特征
2. **生成SD参考图片** → 为每个人物生成参考图
3. **生成分镜图片** → 自动应用一致性技术
4. **选择最佳结果** → 从多个候选中选择

### 2. 文件组织结构
```
project_name/
├── director/
│   ├── character_refs/     # 人物参考图片
│   │   ├── 张三_reference.png
│   │   └── 李四_reference.png
│   ├── shots/             # 分镜图片
│   │   ├── shot_001.png
│   │   ├── shot_001_alt1.png  # 替代版本
│   │   └── shot_002.png
│   └── consistency.json   # 一致性设定
```

### 3. 批量优化建议
- 一次生成所有人物参考图
- 使用批处理生成多个候选
- 保存所有版本供后期选择
- 记录成功的参数组合

通过以上技术和方法，你可以在本地SD中实现专业级的人物一致性，为即梦AI视频制作提供高质量的分镜素材！
