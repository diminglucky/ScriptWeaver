# 本地 Stable Diffusion 完整使用指南

## 🚀 快速开始（5分钟）

### 1. 启动 Stable Diffusion WebUI

**Windows:**
```batch
cd your_stable_diffusion_webui_folder
set COMMANDLINE_ARGS=--api
webui-user.bat
```

**等待输出包含：**
```
Running on local URL:  http://127.0.0.1:7860
```

### 2. 打开应用并选择本地 SD

1. 运行 `python run_modern_app.py`
2. 切换到"图片生成"标签页
3. 在左上"图片API预设"选择：**"本地 Stable Diffusion"**
4. 点击"API测试" - 应该显示连接成功

### 3. 开始生成图片！

- **生成故事图片**：在"图片创建"标签页输入描述，点击"生成图片"
- **生成人物照片**：在"人物照片"标签页选择人物，点击"生成照片"
- **场景分镜**：在"分镜管理"标签页生成图片描述，然后生成图片

---

## ✨ 核心功能

### 1. 文本生成图片（txt2img）
```python
from src.clients.sd_client import StableDiffusionClient

sd = StableDiffusionClient(base_url="http://localhost:7860")

images = sd.txt2img(
    prompt="a beautiful chinese girl in ancient temple",
    negative_prompt="nsfw, lowres, bad anatomy",
    width=512,
    height=512,
    steps=20,
    cfg_scale=7.0
)

if images:
    images[0].save("output.png")
```

### 2. 图像编辑（img2img）
```python
from PIL import Image

ref_image = Image.open("reference.png").convert("RGB")

images = sd.img2img(
    init_image=ref_image,
    prompt="change expression to serious, add red dress",
    denoising_strength=0.5,
    steps=20
)
```

### 3. 故事场景生成
```python
story = """
清晨，张强推开教室的大门。他走到座位坐下，李明已经在那里。
下课铃声响起，学生们陆续涌出教室。
"""

# 自动从故事提取场景并生成图片
# 支持在应用UI中直接进行
```

### 4. 人物照片生成
- ✅ 单个视角（正面/侧面/背面）
- ✅ 多个表情（微笑/严肃/惊讶）
- ✅ 批量生成（所有组合）
- ✅ 一致性控制（保持同一人物特征）

---

## ⚙️ 高级配置

### 修改 Base URL
如果 SD WebUI 不在本地或使用不同端口：

1. 打开应用 → "图片生成" → "配置"
2. 修改 Base URL：`http://your_server_ip:your_port`
3. 点击"API测试"验证

### 调整图片生成参数

在应用中可以设置：
- **分辨率**：512x512, 768x768, 1024x1024（更大消耗更多显存）
- **采样步数**：15-40（更多步骤质量更好但速度慢）
- **CFG Scale**：5-15（控制遵循提示词的程度）

### 切换模型

```python
sd = StableDiffusionClient(base_url="http://localhost:7860")

# 获取可用模型
models = sd.get_models()
print(f"Available: {models}")

# 切换模型
sd.set_model("model_name")
```

### 选择采样器

常用采样器（应用中自动选择最优）：
- Euler a（推荐，平衡速度和质量）
- DPM++ 2M Karras（高质量）
- LCM（快速，质量略低）

---

## 🎯 常见场景

### 场景1：为故事生成配图

**步骤：**
1. 在"故事生成"标签页写好故事
2. 切换到"图片生成" → "图片创建"
3. 点击"从故事生成提示词" → 自动分析故事
4. 点击"生成图片" → 自动为故事生成图片

**提示词示例：**
```
清晨教室场景：清晨，阳光透过窗户洒进教室，一个学生坐在桌前，
光线柔和，细节清晰，8K质量
```

### 场景2：生成一致的人物照片

**步骤：**
1. "人物管理" → 新建人物
2. 输入人物描述：如"20岁的中国女孩，圆脸，黑色长发"
3. "生成人物照片"
4. 选择：视角（正/侧/背）、表情（笑/严肃/惊讶）
5. 点击"批量生成" → 自动生成所有组合

**一致性建议：**
- 首次生成时使用较低的步数(15-20)测试
- 满意后保存参考照片
- 后续生成时启用"参考人物"以保持一致性

### 场景3：修改已有图片

**步骤：**
1. 上传参考图片
2. 在提示词中描述修改：如"改变服装颜色为红色"
3. 设置 Denoising Strength：0.3-0.7
   - 0.3：保留大部分原样
   - 0.5：中等修改（推荐）
   - 0.7+：大幅改变

---

## 🐛 故障排除

### 问题1：连接失败（502 Error）

**检查清单：**
1. ✅ SD WebUI 是否已启动？
   ```bash
   # 检查是否运行在 http://localhost:7860
   # 浏览器打开：http://localhost:7860/
   ```

2. ✅ 是否添加了 `--api` 参数？
   ```batch
   set COMMANDLINE_ARGS=--api
   ```

3. ✅ 防火墙是否阻止了7860端口？
   ```cmd
   netstat -ano | findstr 7860
   ```

4. ✅ Base URL 配置是否正确？
   - 本地：`http://localhost:7860` 或 `http://127.0.0.1:7860`
   - 远程：`http://your_ip:7860`

**解决方案：**
```batch
# 重新启动 SD WebUI
cd your_stable_diffusion_folder
set COMMANDLINE_ARGS=--api
webui-user.bat
```

### 问题2：生成很慢

**优化方案：**
1. 减少分辨率（512x512 替代 1024x1024）
2. 减少采样步数（15 替代 30）
3. 检查显卡使用率（任务管理器）
4. 更换更轻量的模型

### 问题3：CUDA 显存不足

**解决方案：**
1. 启用 Memory Optimization：
   ```batch
   set COMMANDLINE_ARGS=--api --medvram
   ```

2. 或使用 CPU（慢但可用）：
   ```batch
   set COMMANDLINE_ARGS=--api --cpu
   ```

### 问题4：生成的人物不一致

**解决方案：**
1. 使用"参考人物照片"功能
2. 在提示词中重复关键特征："20岁女孩，黑色长发，圆脸"
3. 启用"一致性优化"（应用中的高级选项）

---

## 📊 性能指标

|场景|分辨率|步数|耗时|显存需求|
|----|------|----|----|--------|
|快速草稿|512x512|15|10-15秒|4GB|
|标准生成|512x512|20|15-20秒|6GB|
|高质量|768x768|30|40-60秒|8GB|
|超高质量|1024x1024|40|2-3分钟|12GB+|

---

## 🔧 API 参考

### 连接 SD

```python
from src.clients.sd_client import StableDiffusionClient

sd = StableDiffusionClient(
    base_url="http://localhost:7860"  # 默认值
)
```

### 文本生成图片

```python
images = sd.txt2img(
    prompt="description",          # 必需
    negative_prompt="what not",   # 必需
    width=512,                     # 宽度
    height=512,                    # 高度
    steps=20,                      # 采样步数（越多越好但更慢）
    cfg_scale=7.0,                 # 提示词遵循程度
    sampler_name="Euler a"         # 采样器名称
)
```

### 图像编辑

```python
images = sd.img2img(
    init_image=pil_image,          # PIL Image 对象
    prompt="modifications",         # 修改描述
    negative_prompt="unwanted",
    denoising_strength=0.5,        # 0-1，越高改变越大
    width=512,
    height=512,
    steps=20,
    cfg_scale=7.0
)
```

### 查询信息

```python
# 获取所有模型
models = sd.get_models()

# 获取当前模型
current = sd.get_current_model()

# 切换模型
sd.set_model("model_name")

# 获取采样器
samplers = sd.get_samplers()

# 测试连接
sd.test_connection()  # 返回 True/False
```

---

## 📱 集成到你的应用

### 基础集成

```python
from src.clients.sd_client import StableDiffusionClient

class MyImageGenerator:
    def __init__(self):
        self.sd = StableDiffusionClient(base_url="http://localhost:7860")
    
    def generate_scene_image(self, scene_description: str):
        images = self.sd.txt2img(
            prompt=scene_description,
            negative_prompt="nsfw, bad quality",
            width=768,
            height=768,
            steps=25
        )
        return images[0] if images else None
```

### 结合 DeepSeek 进行智能翻译

```python
from src.clients.deepseek_client import DeepSeekClient
from src.clients.sd_client import StableDiffusionClient

def generate_from_story(story_cn: str):
    # 步骤1：提取关键场景
    deepseek = DeepSeekClient(api_key="your_key")
    scenes = deepseek.chat([
        {"role": "system", "content": "Extract 3-5 visual scenes"},
        {"role": "user", "content": f"Story: {story_cn}"}
    ])
    
    # 步骤2：为每个场景翻译为英文提示词
    sd = StableDiffusionClient()
    for scene in scenes:
        prompt = translate_to_english(scene)
        images = sd.txt2img(prompt=prompt)
        # 保存或处理图片
```

---

## 💡 最佳实践

1. **提示词质量**
   - 包含关键要素：主体、背景、光线、风格
   - 使用具体词汇而非抽象词汇
   - 示例：❌"漂亮的女孩" → ✅"beautiful 20yo chinese girl, soft lighting, detailed face, 8K"

2. **性能优化**
   - 开发时用 512x512 + 15 steps 快速迭代
   - 满意后升级到 768x768 + 25 steps
   - 最终版本用 1024x1024 + 35 steps

3. **一致性管理**
   - 保存参考照片
   - 在后续生成时参考它们
   - 在提示词中重复关键特征

4. **错误处理**
   ```python
   try:
       images = sd.txt2img(prompt=prompt)
   except ConnectionError:
       print("SD WebUI 未运行")
   except Exception as e:
       print(f"生成失败：{e}")
   ```

---

## 📚 更多资源

- [Stable Diffusion WebUI GitHub](https://github.com/AUTOMATIC1111/stable-diffusion-webui)
- [提示词工程指南](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Features)
- [模型下载站](https://huggingface.co/models)

---

**现在你已经准备好了！开始创建令人惊艳的 AI 生成图片吧！** 🎨✨
