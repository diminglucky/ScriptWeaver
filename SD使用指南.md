# 本地Stable Diffusion使用指南

## ✅ 集成状态：已完成

本项目已成功集成本地Stable Diffusion WebUI，可以完全免费、私密地生成图片。

---

## 🚀 快速开始

### 步骤1: 启动Stable Diffusion WebUI

在SD的目录下运行：

```bash
# Windows
python launch.py --api

# Linux/Mac
./webui.sh --api
```

**重要**: 必须添加 `--api` 参数才能启用API接口！

### 步骤2: 配置环境变量

编辑项目根目录的 `.env` 文件：

```ini
# 本地SD地址 (默认)
SD_BASE_URL=http://localhost:7860
```

如果SD运行在其他端口，修改为对应地址，例如：
- `http://localhost:7861`
- `http://192.168.1.100:7860`

### 步骤3: 启动本应用

```bash
python run_modern_app.py
```

### 步骤4: 在应用中选择SD

1. 进入 **"🎨 图片生成"** 标签页
2. 点击 **"⚙️ 配置"** 子标签
3. 在 **"API预设"** 下拉框中选择 **"本地 Stable Diffusion"**
4. 点击 **"✅ 保存配置"**

### 步骤5: 开始生成图片

1. 返回 **"🎨 图片创作"** 子标签
2. 填写图片描述（中文）
3. 选择图片类型（写实照片、数字绘画、动漫风格等）
4. 点击 **"🎨 生成图片"**

---

## 🎯 支持的功能

### ✅ 文生图 (txt2img)
- 直接从文字描述生成图片
- 自动将中文翻译为英文提示词
- 支持所有图片类型和风格

### ✅ 图生图 (img2img)
- 使用参考图片生成新图片
- 保持人物特征
- 适合生成人物的不同姿态和场景

### ✅ 人物一致性
- 上传人物照片作为参考
- 生成该人物的不同场景图片
- 保持人物外观一致

---

## ⚙️ 生成参数

当前使用的默认参数：

```python
{
    "steps": 20,           # 采样步数
    "cfg_scale": 7.0,      # CFG系数
    "sampler_name": "Euler a",  # 采样器
    "denoising_strength": 0.75,  # 图生图去噪强度
}
```

支持的尺寸（从配置页面选择）：
- 512x512
- 768x768
- 1024x1024
- 1024x1792 (竖版)
- 1792x1024 (横版)

---

## 📝 使用示例

### 示例1: 生成写实照片

1. 选择SD预设
2. 图片类型选择 **"写实照片"**
3. 输入描述：
   ```
   一位年轻女性，长发飘飘，穿着白色连衣裙，
   站在樱花树下，阳光洒在她的脸上，微笑着
   ```
4. 点击生成

### 示例2: 使用人物照片生成场景

1. 在 **"人物管理"** 中添加人物并上传照片
2. 在图片生成页面勾选该人物
3. 输入场景描述：
   ```
   在咖啡馆里，坐在窗边，手里拿着一杯咖啡，
   看着窗外的雨景，表情平静
   ```
4. 点击生成（自动使用图生图模式）

### 示例3: 从分镜生成

1. 先在 **"📖 故事创作"** 生成故事
2. 提取分镜
3. 在 **"🎨 图片生成"** 中点击 **"✨ 从当前分镜生成"**
4. 自动填充描述并生成

---

## 🔧 故障排除

### 问题1: 连接失败

**错误**: `Connection refused` 或 `Failed to connect to SD API`

**解决**:
1. 确认SD已启动且使用了 `--api` 参数
2. 检查SD控制台输出，确认API已启用
3. 访问 `http://localhost:7860` 确认SD正常运行
4. 检查 `.env` 中的 `SD_BASE_URL` 是否正确

### 问题2: 生成速度慢

**原因**: SD生成需要大量GPU计算

**优化建议**:
1. 降低图片尺寸（使用512x512）
2. 减少采样步数（修改sd_client.py中的steps参数）
3. 使用更快的采样器（Euler a已经比较快）
4. 确保SD使用GPU而非CPU运行

### 问题3: 显存不足

**错误**: `CUDA out of memory` 或 `RuntimeError: out of memory`

**解决**:
1. 降低图片尺寸
2. 在SD启动时添加 `--medvram` 或 `--lowvram` 参数：
   ```bash
   python launch.py --api --medvram
   ```
3. 关闭其他占用显存的程序

### 问题4: 图片质量不理想

**优化建议**:
1. 增加采样步数（修改sd_client.py中的steps，如改为30）
2. 尝试不同的模型（在SD中切换模型）
3. 调整CFG系数（增加到9-11可能更符合提示词）
4. 使用更详细的描述

---

## 🎨 模型推荐

### 写实照片
- **Realistic Vision V5.1**
- **ChilloutMix**
- **Deliberate V2**

### 动漫风格
- **Anything V5**
- **AbyssOrangeMix3**
- **CounterfeitV3**

### 数字绘画
- **Dreamshaper**
- **ReV Animated**

在Stable Diffusion WebUI的界面上切换模型，无需修改本应用配置。

---

## 💡 高级技巧

### 技巧1: 使用负面提示词

负面提示词已内置，包括：
```
nsfw, lowres, bad anatomy, bad hands, text, error, 
missing fingers, extra digit, fewer digits, cropped, 
worst quality, low quality, normal quality, jpeg artifacts, 
signature, watermark, username, blurry
```

如需自定义，修改 `src/gui/mixins/image_modules/image_generator.py` 中的 `negative_prompt` 变量。

### 技巧2: 多次生成选择最佳

每次生成的结果都可能不同，可以：
1. 多生成几次
2. 选择最满意的保存

### 技巧3: 参考图片的使用

- 人物照片：使用证件照风格的正面照效果最好
- 场景参考：使用类似构图的图片作为参考
- 去噪强度：0.75是平衡值，0.5更接近原图，0.9更自由

---

## 📊 对比：SD vs API

| 特性 | 本地SD | 在线API |
|------|--------|---------|
| 费用 | ✅ 免费 | ❌ 付费 |
| 速度 | ⚡ 快（有好GPU） | 🐌 取决于网络 |
| 隐私 | ✅ 完全私密 | ❌ 上传到服务器 |
| 质量 | 🎨 取决于模型 | 🎨 固定 |
| 自定义 | ✅ 自由选择模型 | ❌ 受限 |
| 门槛 | 💻 需要GPU | 💰 需要API Key |

---

## 🔗 相关文件

- **SD客户端**: `src/clients/sd_client.py`
- **集成逻辑**: `src/gui/mixins/image_modules/image_generator.py`
- **配置界面**: `src/gui/mixins/image_modules/ui_setup.py`
- **详细文档**: `docs/本地SD绘图集成说明.md`

---

## ✨ 总结

本地SD集成完整，功能齐全，可以：
- ✅ 完全免费使用
- ✅ 保护隐私
- ✅ 自由选择模型
- ✅ 支持文生图和图生图
- ✅ 与现有功能无缝配合

立即开始使用本地SD，享受免费、私密、自由的AI绘图体验！

---

*最后更新: 2025-10-19*

