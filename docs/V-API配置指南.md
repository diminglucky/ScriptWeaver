# V-API 图片生成服务配置指南

## 简介

V-API (https://api.gpt.ge) 是一个提供多种AI图片生成服务的API平台，兼容OpenAI接口格式，支持多种图片生成模型。

## 配置步骤

### 1. 获取API密钥

1. 访问 V-API 网站注册账号
2. 在用户中心获取您的API密钥（Token）
3. 查看您的账户额度和可用模型

### 2. 修改配置文件

在 `custom_image_api_presets.json` 文件中，将 `"您的API密钥"` 替换为您实际的API Token：

```json
{
  "V-API图片生成": {
    "base_url": "https://api.gpt.ge/v1",
    "model": "dall-e-3",
    "key": "sk-xxxxxxxxxxxxxxxxxxxxxxxx"
  }
}
```

### 3. 在GUI中选择预设

1. 运行程序：`python run_app.py`
2. 在"图片生成"区域的"API预设"下拉框中选择：
   - `V-API图片生成` - 使用DALL-E-3模型（推荐，质量最高）
   - `V-API-DALL-E-2` - 使用DALL-E-2模型（更经济）
   - `V-API-GPT-Image` - 使用GPT-Image-1模型

## 支持的模型

### DALL-E-3（推荐）

- **模型名**: `dall-e-3`
- **特点**: 质量最高，理解力强，自动优化提示词
- **支持尺寸**: 
  - `1024x1024` (方形)
  - `1792x1024` (横向)
  - `1024x1792` (纵向)
- **生成数量**: 每次1张
- **价格**: 相对较高

### DALL-E-2

- **模型名**: `dall-e-2`
- **特点**: 速度快，价格实惠
- **支持尺寸**: 
  - `256x256`
  - `512x512`
  - `1024x1024`
- **生成数量**: 每次最多10张
- **价格**: 经济实惠

### GPT-Image-1

- **模型名**: `gpt-image-1`
- **特点**: V-API平台专有模型，支持图片编辑
- **支持尺寸**: `1024x1024` 等
- **功能**: 支持文生图和图片编辑

## 使用方法

### 方法1：通过GUI使用

1. 打开应用程序
2. 在"API预设"中选择 `V-API图片生成`
3. 填写图片描述
4. 选择图片类型（写实、动漫、古风等）
5. 点击"生成图片"按钮

### 方法2：自定义配置

如果您想使用其他高级配置，可以添加更多预设：

```json
{
  "V-API-高清横图": {
    "base_url": "https://api.gpt.ge/v1",
    "model": "dall-e-3",
    "key": "您的API密钥",
    "size": "1792x1024"
  },
  "V-API-快速生成": {
    "base_url": "https://api.gpt.ge/v1",
    "model": "dall-e-2",
    "key": "您的API密钥",
    "size": "512x512"
  }
}
```

## API请求示例

V-API使用标准的OpenAI格式，请求示例：

```bash
curl --location --request POST 'https://api.gpt.ge/v1/images/generations' \
--header 'Authorization: Bearer YOUR_API_KEY' \
--header 'Content-Type: application/json' \
--data-raw '{
    "model": "dall-e-3",
    "prompt": "一幅精美的中国古风山水画",
    "n": 1,
    "size": "1024x1024"
}'
```

## 价格与限额

### 查询账户信息

您可以使用以下API查询您的账户信息：

```bash
# 查询令牌用量
GET https://api.gpt.ge/v1/dashboard/billing/usage

# 查询令牌限额
GET https://api.gpt.ge/v1/dashboard/billing/subscription

# 查询账户信息
GET https://api.gpt.ge/v1/dashboard/billing/account
```

### 计费说明

- 按照生成的图片数量和尺寸计费
- DALL-E-3 价格较高但质量最好
- DALL-E-2 价格实惠适合批量生成
- 建议先小额充值测试效果

## 其他可用的图片生成模型

V-API还支持以下模型（需要查看文档了解具体配置）：

### 主流模型
- **Flux** - 高质量开源模型
- **Stable Diffusion** - 经典开源模型
- **Midjourney** - 艺术性强（通过Discord）

### 中国厂商模型
- **即梦AI** (Jimeng) - 中文优化
- **Qwen** (通义千问) - 阿里巴巴
- **可灵AI** (Kling) - 快手
- **Ideogram** - 文字渲染优秀

### 配置其他模型示例

```json
{
  "V-API-Flux": {
    "base_url": "https://api.gpt.ge/v1",
    "model": "flux-1-dev",
    "key": "您的API密钥"
  },
  "V-API-即梦": {
    "base_url": "https://api.gpt.ge/v1",
    "model": "jimeng-4.0",
    "key": "您的API密钥"
  }
}
```

**注意**: 不同模型的API端点和参数可能有所不同，使用前请查阅V-API官方文档。

## 优势与特点

### 相比直接使用OpenAI

1. **价格优势**: 通常比OpenAI官方价格更优惠
2. **国内访问**: 无需翻墙，访问速度快
3. **多模型支持**: 一个API密钥可使用多种模型
4. **兼容性好**: 使用OpenAI格式，无缝集成

### 相比单独使用各厂商API

1. **统一接口**: 一个密钥访问多个模型
2. **简化开发**: 不需要集成多个SDK
3. **灵活切换**: 轻松在不同模型间切换
4. **集中管理**: 统一的账户和计费

## 注意事项

### 1. API密钥安全

- 不要将API密钥提交到公开的Git仓库
- 建议使用环境变量存储密钥
- 定期更换密钥

### 2. 成本控制

- 建议先小额充值测试
- DALL-E-3生成成本较高，测试时可用DALL-E-2
- 监控API使用量，避免意外超支

### 3. 内容审核

- V-API会进行内容审核
- 避免生成违规内容
- 遵守中国法律法规和平台规则

### 4. 速率限制

- 注意API的速率限制（QPM/RPM）
- 高并发使用时需要实现重试机制
- 大批量生成建议分批次进行

## 故障排查

### 问题1: 401 Unauthorized

**原因**: API密钥错误或已过期

**解决**:
- 检查配置文件中的key是否正确
- 确认API密钥是否有效
- 登录V-API查看账户状态

### 问题2: 429 Too Many Requests

**原因**: 超过速率限制

**解决**:
- 降低请求频率
- 在代码中添加重试逻辑
- 联系V-API升级配额

### 问题3: 图片生成失败

**原因**: 提示词可能触发内容审核

**解决**:
- 检查提示词内容
- 避免敏感词汇
- 使用更温和的描述

### 问题4: 连接超时

**原因**: 网络问题或服务繁忙

**解决**:
- 检查网络连接
- 增加timeout参数
- 稍后重试

## 进阶配置

### 使用环境变量（推荐）

为了安全起见，建议使用环境变量存储API密钥：

1. 在系统中设置环境变量：
```bash
export VAPI_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
```

2. 修改配置文件使用变量：
```json
{
  "V-API图片生成": {
    "base_url": "https://api.gpt.ge/v1",
    "model": "dall-e-3",
    "key": "${VAPI_KEY}"
  }
}
```

3. 修改代码读取环境变量：
```python
import os
api_key = config.get("key")
if api_key.startswith("${") and api_key.endswith("}"):
    env_var = api_key[2:-1]
    api_key = os.getenv(env_var)
```

### 自定义超时时间

默认超时时间是120秒，您可以根据需要调整：

```python
client = OpenAIImageClient(
    api_key=your_key,
    base_url="https://api.gpt.ge/v1",
    model="dall-e-3",
    timeout_seconds=300  # 5分钟
)
```

## 参考链接

- V-API官方文档: https://api-gpt-ge.apifox.cn/
- V-API用户中心: https://api.gpt.ge/
- OpenAI图片生成API文档: https://platform.openai.com/docs/api-reference/images

## 技术说明

### 图片返回格式兼容性

本项目的 `OpenAIImageClient` 已经做了兼容性处理，同时支持两种返回格式：

1. **Base64格式** (OpenAI官方默认)
   - 优点：直接返回图片数据，不需要额外下载
   - 缺点：响应体积较大
   
2. **URL格式** (V-API默认)
   - 优点：响应速度快，适合高并发
   - 缺点：需要额外下载图片

代码会自动检测：
- 先尝试请求 base64 格式
- 如果不支持，自动切换为 URL 格式并下载图片
- 完全透明，无需手动配置

### 处理流程

```python
# 1. 尝试 base64 格式
response = client.images.generate(
    model="dall-e-3",
    prompt="...",
    response_format="b64_json"  # 请求 base64
)

# 2. 如果失败，自动切换为 URL 格式
response = client.images.generate(
    model="dall-e-3",
    prompt="..."  # 默认返回 URL
)
# 然后自动下载 URL 的图片
```

这样的设计保证了与各种API服务商的兼容性。

## 更新日期

2025-10-11

## 版本

v1.1.0 - 添加URL/Base64格式自动兼容  
v1.0.0 - V-API配置初始版本

