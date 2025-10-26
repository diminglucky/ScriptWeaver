"""
商用级人物一致性实现提示
"""

COMMERCIAL_GRADE_TIPS = """
# 🎯 达到商用级人物一致性的方法

## 1. 安装必要组件

### ComfyUI工作流（推荐）
```bash
# 1. 安装ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI
cd ComfyUI
pip install -r requirements.txt

# 2. 安装关键插件
cd custom_nodes
git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus
git clone https://github.com/Fannovel16/comfyui_controlnet_aux
git clone https://github.com/ltdrdata/ComfyUI-Manager
```

### SD WebUI插件
```bash
# 在SD WebUI中安装：
- ControlNet
- Reactor (换脸)
- ADetailer (面部修复)
```

## 2. 训练角色LoRA

### 准备数据
- 每个角色准备15-30张高质量图片
- 不同角度、表情、光照
- 使用标注工具标注特征

### 训练命令
```bash
python train_network.py \
  --pretrained_model_name_or_path="runwayml/stable-diffusion-v1-5" \
  --train_data_dir="./character_images" \
  --output_dir="./character_lora" \
  --resolution=512,512 \
  --train_batch_size=1 \
  --max_train_steps=2000
```

## 3. 使用IPAdapter方案

```python
# 伪代码示例
def generate_consistent_character(reference_image, prompt):
    # 1. 提取面部特征
    face_embedding = extract_face_embedding(reference_image)
    
    # 2. 提取姿势
    pose = extract_pose(reference_image)
    
    # 3. 应用IPAdapter
    image = pipeline(
        prompt=prompt,
        ip_adapter_image=reference_image,
        ip_adapter_scale=0.8,  # 控制相似度
        controlnet_conditioning_image=pose,
        controlnet_conditioning_scale=0.7
    )
    
    # 4. 面部修复
    image = face_restoration(image, reference_face=reference_image)
    
    return image
```

## 4. 商业API集成示例

### Midjourney Character Reference
```
/imagine prompt: a boy reading a book --cref [URL] --cw 100
```

### Leonardo.AI
```python
import requests

response = requests.post(
    "https://api.leonardo.ai/v1/generations",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "prompt": "boy reading in classroom",
        "modelId": "character-consistency-model",
        "characterReference": base64_image,
        "consistency_weight": 0.85
    }
)
```

## 5. 工作流建议

1. **第一步：生成参考图**
   - 使用最高质量设置
   - 多次生成，选最佳
   - 保存多角度版本

2. **第二步：建立特征库**
   - 面部特征embedding
   - 服装模板
   - 常用姿势

3. **第三步：批量生成**
   - 使用统一seed
   - 固定模型和参数
   - 后期统一处理

## 6. 质量检查清单

- [ ] 面部特征一致性 > 95%
- [ ] 服装细节保持
- [ ] 体型比例不变
- [ ] 肤色统一
- [ ] 发型稳定

## 7. 推荐工具链

1. **生成**: ComfyUI + IPAdapter
2. **检查**: Face comparison API
3. **修复**: GFPGAN / CodeFormer
4. **管理**: Character sheet generator

记住：商用级一致性需要多种技术组合，
单一方法很难达到要求。
"""

def show_commercial_tips():
    """显示商用级提示"""
    print(COMMERCIAL_GRADE_TIPS)
    
    # 创建提示文件
    with open("COMMERCIAL_GRADE_CHARACTER_CONSISTENCY.txt", "w", encoding="utf-8") as f:
        f.write(COMMERCIAL_GRADE_TIPS)
    
    print("\n提示已保存到: COMMERCIAL_GRADE_CHARACTER_CONSISTENCY.txt")

if __name__ == "__main__":
    show_commercial_tips()
