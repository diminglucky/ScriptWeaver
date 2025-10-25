# 本地 Stable Diffusion 快速开始指南

## ⚡ 5分钟快速上手

### 步骤 1: 启动 SD WebUI（1分钟）

**Windows:**
```batch
@echo off
set COMMANDLINE_ARGS=--api --port 7860
call webui-user.bat
```

**Mac/Linux:**
```bash
export COMMANDLINE_ARGS="--api --port 7860"
./webui.sh
```

✅ 看到 `Running on http://0.0.0.0:7860` 即表示启动成功

### 步骤 2: 在应用中配置（2分钟）

1. 打开 **AI Story Creator Pro**
2. 进入 **图片生成** → **⚙️ 配置**
3. **API预设** 选择 → **"本地 Stable Diffusion"**
4. 点击 **🔌 API测试** 验证连接
5. 点击 **保存配置**

### 步骤 3: 生成你的第一张图片（2分钟）

1. 进入 **🎨 图片创作** 标签
2. 在 **图片描述** 框输入：
   ```
   A beautiful woman wearing a red silk dress in a classical garden, 
   photorealistic, 8K, professional photography
   ```
3. 选择 **图片类型**: 写实照片
4. 选择 **尺寸**: 768x768
5. 点击 **🎨 生成图片**
6. 等待完成，查看预览

**恭喜！你已成功使用本地 SD 生成图片！** 🎉

---

## 🎯 常用场景

### 场景1: 为故事生成分镜头

1. 在故事生成中创建故事并生成目录
2. 打开每一章的内容
3. 在图片生成中输入该章场景描述
4. 选择相应风格（根据故事类型）
5. 点击生成

### 场景2: 为人物生成照片

1. 进入 **人物生成** 标签
2. 点击 **🔍 提取故事人物**
3. 从列表选择一个人物
4. 点击 **✨ 生成特征描述**
5. 选择风格（如古风、仙侠、写实等）
6. 点击 **🎨 生成人物照片**

### 场景3: 用参考图片生成变体

1. 进入 **参考人物** 或 **参考图片** 
2. 选择或上传一张图片
3. 修改提示词（例如：改变服装、表情、姿态）
4. 点击 **🎨 生成图片**

---

## 📝 提示词技巧

### 基础模板

```
[主体描述]，[特征细节]，[场景]，[光线]，[风格]，[质量]
```

### 中文例子

```
一个年轻女性，长黑发，穿着红色旗袍，
站在古典园林中，阳光透过竹林洒落，
写实照片风格，高清细节，专业摄影
```

### 英文例子（效果更好）

```
A young woman with long black hair, wearing a red silk qipao,
standing in a classical Chinese garden with bamboo,
sunlight streaming through, photorealistic, 8K, sharp focus,
cinematic lighting, professional photography
```

### 质量词（复制-粘贴即用）

```
highly detailed, professional, 8K, sharp focus,
cinematic lighting, masterpiece, best quality
```

---

## ⚙️ 参数说明

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| 采样步数 (steps) | 20 | 10-50 | 越多越细致，越慢 |
| CFG Scale | 7.0 | 5-12 | 遵循提示的强度 |
| 采样器 | Euler a | - | 生成算法 |
| 尺寸 | 768x768 | 512-1024 | 分辨率 |

### 快速调整建议

- **生成太慢**: 降低分辨率到 512x512，步数到 15
- **质量不好**: 增加步数到 30，CFG 到 9
- **显存不足**: 开启 SD 的 `--lowvram` 参数

---

## 🔧 故障排查

| 问题 | 解决方案 |
|------|----------|
| **无法连接** | 检查 SD 是否启动，确保带 `--api` 参数 |
| **很慢** | 降低分辨率或步数 |
| **显存错误** | 添加 `--lowvram` 启动参数 |
| **质量差** | 修改提示词，增加质量词 |

---

## 💡 进阶技巧

### 1. 图生图变换

用参考图片作为基础，修改提示词进行创意变换：
- 改变风格（动漫→油画）
- 改变服装（红裙→蓝裙）
- 改变场景（室内→户外）

### 2. 批量生成

手动方式：
1. 生成第一张
2. 修改描述
3. 再次点击生成
4. 重复

### 3. 自定义负面提示词

编辑 `src/gui/mixins/image_modules/image_generator.py`，在 negative_prompt 中添加：
```python
+ ", distorted, ugly, deformed"
```

---

## 📚 进一步学习

- 查看 **本地SD高级配置指南** 获取深度参数调整
- 访问 https://lexica.art 查看高质量提示词示例
- 在 https://civitai.com 下载更多模型和 LoRA

---

## 🚀 下一步

1. ✅ 成功生成第一张图片
2. 📖 生成一个完整故事的分镜头图片
3. 👤 为故事人物生成专属照片
4. 🎨 尝试不同风格和参数组合

---

*提示: 所有生成的图片会自动保存到项目文件夹中！*

*需要帮助? 查看 docs 文件夹中的其他详细指南*
