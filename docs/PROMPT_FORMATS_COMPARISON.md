# 图片生成API提示词格式对比

## 概述

本项目支持三种图片生成API，每种API使用**不同的提示词格式**。理解这些差异对于获得最佳生成效果至关重要。

## 三种API对比表

| API类型 | 提示词格式 | 语言 | 字数限制 | 负向提示词 | 适用场景 |
|--------|----------|------|---------|-----------|---------|
| **Stable Diffusion (SD)** | 标签式 (Tag-based) | 英文 | ~1000字符 | ✅ 支持 (详细) | 精细控制、批量生成 |
| **腾讯混元 (Hunyuan)** | 自然语言 | 中文 | 256字符 | ✅ 支持 (简单) | 中国风、写实风格 |
| **OpenAI DALL-E** | 自然语言 | 英文 | ~1000字符 | ❌ 不支持 | 创意风格、复杂场景 |

---

## 1. Stable Diffusion (本地SD)

### 提示词格式
**标签式 (Tag-based)** - 使用逗号分隔的关键词标签

### 特点
- ✅ 使用英文关键词
- ✅ 逗号分隔，无需完整句子
- ✅ 支持权重控制：`(tag:1.5)` 或 `((tag))`
- ✅ 需要详细的负向提示词
- ✅ 顺序很重要：前面的标签权重更高

### 示例

**人物描述**：
```
小远，男孩，约10岁。圆脸，大眼睛，皮肤白皙。短发，深棕色。穿着蓝白连帽卫衣，牛仔裤。
```

**SD标签式提示词**：
```
(((solo))), (((1person))), (solo:2.0), (1person:2.0), only one person, single person portrait,
masterpiece, best quality, ultra detailed, 8k,
1boy, 10 years old, boy, male child, child, young boy, male, not female,
Chinese, East Asian, asian,
black hair, short hair,
t-shirt, hoodie, jeans, casual wear,
full body, standing straight, standing figure, full shot,
front view,
neutral expression,
simple background, white background, plain background,
professional photography, studio lighting, sharp focus, highly detailed,
photorealistic, high resolution,
looking at viewer, centered composition, clear face, detailed face,
perfect anatomy, realistic proportions, standing, upright, feet on ground
```

**SD负向提示词** (详细)：
```
low quality, worst quality, blurry, jpeg artifacts, watermark,
bad anatomy, bad hands, bad proportions, deformed, mutated,
extra limbs, missing limbs, fused fingers,
ugly face, bad eyes, crossed eyes,
(multiple people:2.0), (two people:2.0), (crowd:1.8),
((multiple people)), ((two people)), duplicate person,
lying down, lying, sitting, kneeling, crouching,
不自然的姿势, twisted body, unnatural pose,
girl, female, woman, 女性, 女孩
```

### 关键点
1. **单人约束**：使用极高权重 `(((solo)))` 和 `(solo:2.0)`
2. **质量标签**：`masterpiece`, `best quality` 等
3. **年龄性别**：明确 `1boy`, `10 years old`
4. **负向约束**：详细列出不要的内容

---

## 2. 腾讯混元 (Hunyuan)

### 提示词格式
**中文自然语言** - 使用完整的中文句子描述

### 特点
- ✅ 使用中文描述
- ✅ 自然流畅的句子
- ⚠️ **严格限制256字符**
- ✅ 支持简单的负向提示词
- ✅ 理解中文语义，不需要标签

### 示例

**人物描述**（同上）：
```
小远，男孩，约10岁。圆脸，大眼睛，皮肤白皙。短发，深棕色。穿着蓝白连帽卫衣，牛仔裤。
```

**腾讯混元中文自然语言提示词** (优化后≤256字符)：
```
单人照片，仅一个人，全身照，一个约10岁的男孩，中国人，圆脸，大眼睛，皮肤白皙，短发，深棕色，穿着蓝白连帽卫衣，牛仔裤，中性表情，正面，站立姿势，高清专业摄影，细节清晰，纯色背景
```

**腾讯混元负向提示词** (简单)：
```
两个人，多个人，多人，一群人，couple，two people，multiple people，坐着，躺着，lying，sitting，模糊，低质量，blurry，low quality
```

### 关键点
1. **字数限制**：严格控制在256字符内
2. **单人约束**：开头明确"单人照片，仅一个人"
3. **智能截断**：优先保留关键约束词
4. **中文表达**：使用自然的中文描述

### 优化策略
由于256字符限制，系统会：
1. 识别关键约束词（如"单人"、"仅一个人"）
2. 优先保留这些约束
3. 智能提取核心视觉特征
4. 截断次要信息

---

## 3. OpenAI DALL-E

### 提示词格式
**英文自然语言** - 使用完整的英文句子描述

### 特点
- ✅ 使用英文描述
- ✅ 理解复杂语义
- ✅ 支持较长提示词 (~1000字符)
- ❌ 不支持负向提示词
- ✅ 创意理解能力强

### 示例

**人物描述**（同上）：
```
小远，男孩，约10岁。圆脸，大眼睛，皮肤白皙。短发，深棕色。穿着蓝白连帽卫衣，牛仔裤。
```

**OpenAI英文自然语言提示词**：
```
Single person portrait photo, only one person, full body photo of one 10-year-old boy, Chinese, 
round face, big eyes, fair skin, short hair, dark brown color, wearing blue and white hooded 
sweatshirt, jeans, neutral expression, front view, standing pose, high quality professional 
photography, detailed, plain background
```

### 关键点
1. **单人约束**：开头明确"Single person portrait photo, only one person"
2. **完整句子**：使用自然的英文句子
3. **详细描述**：可以更详细，支持长提示词
4. **无负向提示**：通过正向描述来引导

---

## 代码实现

### 提示词构建流程

```python
# src/gui/helpers/character_prompt_builder.py

def build_character_photo_prompt(
    description: str,
    api_type: str = "openai",  # 关键参数！
    language: str = "zh",
    ...
) -> str:
    """根据api_type选择提示词格式"""
    
    if api_type == "sd":
        # ✅ Stable Diffusion: 标签式提示词
        return _build_sd_style_prompt(...)
    else:
        # ✅ OpenAI/Hunyuan: 自然语言提示词
        return _build_natural_language_prompt(...)
```

### 三个独立的生成函数

```python
# src/gui/mixins/image_modules/handlers/character_photo_generator.py

def _generate_with_hunyuan(...):
    """腾讯混元生成"""
    full_prompt = CharacterPromptBuilder.build_character_photo_prompt(
        api_type="hunyuan",  # ✅ 中文自然语言
        language="zh",
        ...
    )
    full_prompt = optimize_for_api(full_prompt, "hunyuan", 256)  # 256字符限制

def _generate_with_sd(...):
    """SD生成"""
    full_prompt = CharacterPromptBuilder.build_character_photo_prompt(
        api_type="sd",  # ✅ 英文标签式
        language="en",
        ...
    )
    negative_prompt = get_negative_prompt_for_character("sd", description)  # 详细负向

def _generate_with_openai(...):
    """OpenAI生成"""
    full_prompt = CharacterPromptBuilder.build_character_photo_prompt(
        api_type="openai",  # ✅ 英文自然语言
        language="en",
        ...
    )
    # 无负向提示词
```

---

## 提示词对比示例

### 场景：生成"小远"（10岁男孩）的全身照

#### 原始描述
```
小远，男孩，约10岁。圆脸，大眼睛，皮肤白皙。短发，深棕色。
身材瘦弱纤细。穿着蓝白连帽卫衣，T恤，牛仔裤，白色运动鞋。
```

---

#### Stable Diffusion (标签式)

**正向提示词**：
```
(((solo))), (((1person))), (solo:2.0), only one person,
masterpiece, best quality, ultra detailed, 8k, photorealistic,
1boy, 10 years old, boy, male child, child, male, not female,
Chinese, East Asian, asian,
round face, big eyes, fair skin,
black hair, short hair,
slim, slender, thin,
hoodie, blue and white, t-shirt, jeans, sneakers, casual wear,
full body, standing straight, standing figure, vertical stance,
front view, neutral expression,
simple background, white background, plain background,
professional photography, studio lighting, sharp focus,
looking at viewer, centered composition, clear face, detailed face,
perfect anatomy, realistic proportions, standing, upright
```

**负向提示词**：
```
low quality, worst quality, blurry, watermark, bad anatomy,
(multiple people:2.0), (two people:2.0), ((multiple people)),
duplicate person, extra person, two persons, three persons,
lying down, lying, sitting, kneeling, crouching,
girl, female, woman, 女性, 女孩, not male,
bad face, ugly face, bad eyes, bad hands,
unnatural pose, twisted body
```

**特点**：
- ✅ 关键词密集，权重明确
- ✅ 详细的负向约束
- ✅ 适合精细控制

---

#### 腾讯混元 (中文自然语言)

**正向提示词** (256字符以内)：
```
单人照片，仅一个人，全身照，一个约10岁的男孩，中国人，圆脸，大眼睛，皮肤白皙，短发，深棕色，瘦弱纤细，穿着蓝白连帽卫衣，T恤，牛仔裤，白色运动鞋，中性表情，正面，站立姿势，高清专业摄影，细节清晰，纯色背景
```

**负向提示词**：
```
两个人，多个人，多人，一群人，坐着，躺着，模糊，低质量
```

**特点**：
- ✅ 中文流畅自然
- ⚠️ 严格字数限制
- ✅ 智能提取核心特征

---

#### OpenAI DALL-E (英文自然语言)

**正向提示词**：
```
Single person portrait photo, only one person, full body photo of one 10-year-old boy.
He is Chinese with a round face, big eyes, and fair skin. He has short dark brown hair.
His body is slim and slender. He is wearing a blue and white hooded sweatshirt, a t-shirt,
jeans, and white sneakers. Neutral expression, front view, standing pose.
High quality professional photography with detailed features and plain background.
```

**负向提示词**：
```
不支持
```

**特点**：
- ✅ 完整英文句子
- ✅ 语义理解能力强
- ❌ 无负向提示词支持

---

## 选择建议

### 使用Stable Diffusion，如果你需要：
- ✅ 精细控制每个细节
- ✅ 批量生成（速度快）
- ✅ 强大的负向约束
- ✅ 本地部署，无成本

### 使用腾讯混元，如果你需要：
- ✅ 中国风、东方美学
- ✅ 写实风格人像
- ✅ 快速生成单张
- ⚠️ 注意256字符限制

### 使用OpenAI DALL-E，如果你需要：
- ✅ 复杂创意场景
- ✅ 强大的语义理解
- ✅ 欧美风格
- ✅ 不想配置本地环境

---

## 常见问题

### Q1: 为什么同样的描述，SD和OpenAI生成的效果差别很大？

**原因**：提示词格式不同
- **SD**: 需要标签式关键词，对权重敏感
- **OpenAI**: 理解自然语言，侧重语义

**解决**：系统已自动针对不同API使用不同格式，无需手动调整

### Q2: 腾讯混元为什么总是生成多个人？

**原因**：
1. 描述过长被截断，"单人"约束丢失
2. 没有使用负向提示词

**解决**：
- ✅ 系统已优化，智能保留"单人"约束
- ✅ 已添加负向提示词
- ✅ 描述会智能提取核心特征（≤100字）

### Q3: SD生成的人物姿势总是躺着或坐着？

**原因**：没有明确姿势约束

**解决**：
- ✅ 正向提示词已添加：`standing, upright, feet on ground`
- ✅ 负向提示词已添加：`lying down, sitting, kneeling, crouching`

### Q4: 如何查看实际使用的提示词？

查看日志文件 `logs/app.log`：

```log
[INFO] === SD 标签式提示词（Tag-based Prompt）===
[INFO] 正向提示词 (前200字符): (((solo))), (((1person))), ...
[INFO] 负向提示词 (前100字符): low quality, worst quality, ...

[INFO] 腾讯混元中文自然语言提示词: 单人照片，仅一个人，全身照...

[INFO] OPENAI英文自然语言提示词: Single person portrait photo...
```

---

## 技术细节

### 智能提取核心描述

对于腾讯混元等有字数限制的API，系统会智能提取核心视觉特征：

**优先级**：
1. **第一优先级**: 年龄、性别（10岁、男孩）
2. **第二优先级**: 发型、发色（短发、深棕色）
3. **第三优先级**: 服装（卫衣、牛仔裤）
4. **第四优先级**: 体型（瘦弱、纤细）
5. **第五优先级**: 面部特征（圆脸、大眼睛）
6. **第六优先级**: 肤色（白皙）

### 智能截断策略

对于腾讯混元：
1. 识别关键约束词（"单人"、"仅一个人"）
2. 优先保留这些约束（不被截断）
3. 提取核心描述（≤100字）
4. 剩余空间填充其他信息
5. 最终确保≤256字符

---

## 总结

| 特性 | SD (标签式) | 腾讯混元 (中文) | OpenAI (英文) |
|-----|-----------|--------------|-------------|
| 格式 | 关键词标签 | 中文句子 | 英文句子 |
| 分隔符 | 逗号 | 逗号/顿号 | 空格/标点 |
| 语言 | 英文 | 中文 | 英文 |
| 长度 | ~1000字符 | 256字符 | ~1000字符 |
| 负向提示 | 详细 | 简单 | 不支持 |
| 权重控制 | 支持 | 不支持 | 不支持 |
| 适用场景 | 精细控制 | 中国风 | 创意场景 |
| 成本 | 免费(本地) | 付费 | 付费 |

**关键要点**：
- ✅ 系统已自动为每个API使用正确的提示词格式
- ✅ 无需手动调整，选择API即可
- ✅ 所有API都添加了单人约束
- ✅ 描述过长会智能提取核心特征

---

**更新日期**: 2025-11-02
**版本**: v2.0


