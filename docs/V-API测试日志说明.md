# V-API 测试日志功能说明

## 更新内容

为了方便查看API测试的详细信息，我们在**图片生成 → 配置**页面添加了专门的**测试日志**区域。

## 功能特性

### 1. 独立的日志显示区域

- **位置**: 图片生成 → 配置标签页 → 底部
- **样式**: 深色主题，易于阅读
- **滚动**: 支持滚动查看长日志
- **清空**: 一键清空日志按钮

### 2. 详细的测试信息

测试API时，日志会显示：

#### 测试开始
```
[2025-10-11 15:30:25] 开始测试图片生成API...

📋 测试参数:
  • Model: dall-e-2
  • API Key: ****************vLNNjUaq
```

#### 测试过程
```
🔍 尝试的Base URL:

[1/2] 测试: https://api.gpt.ge/v1
❌ 失败: Error code: 401 - {'error': {'message': 'Invalid API key', ...}}

[2/2] 测试: https://api.gpt.ge
❌ 失败: Error code: 404 - Not Found
```

#### 测试失败总结
```
============================================================
❌ 图片API测试失败（已尝试所有可能的base_url）
============================================================
base_url=https://api.gpt.ge/v1 -> FAIL: Error code: 401...
base_url=https://api.gpt.ge -> FAIL: Error code: 404...

💡 可能的原因:
  1. API密钥错误或已过期
  2. 账户余额不足
  3. Base URL不正确
  4. 网络连接问题
  5. 模型名称不支持

建议操作:
  • 检查API密钥是否正确
  • 登录服务商网站查看账户余额
  • 确认Base URL格式正确
```

#### 测试成功
```
[1/2] 测试: https://api.gpt.ge/v1
✅ 成功: 图片API测试成功 (返回URL格式，尺寸:512x512)

🎉 测试成功！已自动更新Base URL为: https://api.gpt.ge/v1
```

## 使用方法

### 步骤1: 打开配置页面
1. 运行应用：`python run_app.py`
2. 点击顶部 **🎨 图片生成** 标签
3. 点击 **配置** 子标签

### 步骤2: 配置API信息
1. 选择API预设（如：V-API-DALL-E-2）
2. 填写API Key
3. 确认Base URL和Model

### 步骤3: 测试API
1. 点击 **🔌 测试API** 按钮
2. 查看下方**测试日志**区域的详细信息
3. 根据日志提示排查问题

### 步骤4: 清空日志（可选）
- 点击日志区域右下角的 **清空日志** 按钮
- 每次测试会自动清空之前的日志

## 常见错误解读

### Error code: 401
```
❌ 失败: Error code: 401 - {'error': {'message': 'Invalid API key'}}
```
**原因**: API密钥错误或已失效  
**解决**: 
- 检查API Key是否完整复制
- 登录V-API网站查看密钥状态
- 重新生成新的密钥

### Error code: 403
```
❌ 失败: Error code: 403 - {'error': {'message': 'Insufficient quota'}}
```
**原因**: 账户余额不足  
**解决**: 
- 登录V-API网站充值
- 查看账户余额和消费记录

### Error code: 404
```
❌ 失败: Error code: 404 - Not Found
```
**原因**: Base URL不正确  
**解决**: 
- 确认Base URL是否为：`https://api.gpt.ge/v1`
- 检查是否有拼写错误
- 尝试从API预设重新选择

### Error code: 429
```
❌ 失败: Error code: 429 - {'error': {'message': 'Rate limit exceeded'}}
```
**原因**: 超过速率限制  
**解决**: 
- 等待几分钟后重试
- 降低请求频率
- 联系V-API升级配额

### Connection Error
```
❌ 失败: Connection error: [Errno 8] nodename nor servname provided...
```
**原因**: 网络连接问题  
**解决**: 
- 检查网络连接
- 确认可以访问 api.gpt.ge
- 检查防火墙/代理设置

### Invalid Model
```
❌ 失败: Error: model 'xxx' is not supported
```
**原因**: 模型名称不支持  
**解决**: 
- 使用支持的模型名称：`dall-e-2`, `dall-e-3`, `gpt-image-1`
- 查看V-API文档确认可用模型

## 优势

### 相比之前的方式

**之前**:
- ❌ 错误信息显示在"故事生成"页面
- ❌ 需要切换标签页查看日志
- ❌ 日志混在故事生成日志中
- ❌ 不够直观

**现在**:
- ✅ 错误信息显示在配置页面
- ✅ 无需切换标签，原地查看
- ✅ 专门的测试日志区域
- ✅ 格式化的错误提示
- ✅ 详细的排查建议

## 技术细节

### 代码位置
- **UI构建**: `src/gui/mixins/image_mixin.py` - `_build_image_setup_tab()`
- **测试逻辑**: `src/gui/mixins/config_mixin.py` - `on_test_image_api()`

### 日志控件
```python
self.img_test_log = tk.Text(
    grp_log, 
    height=10, 
    wrap="word",
    bg="#1e1e1e",  # 深色背景
    fg="#d4d4d4",  # 浅色文字
    font=("Consolas", 10)  # 等宽字体
)
```

### 智能回退
如果 `img_test_log` 控件不存在（向后兼容），日志会自动回退到 `self.output`：
```python
log_widget = getattr(self, 'img_test_log', self.output)
```

## 更新日期

2025-10-11

## 版本

v1.0.0 - 测试日志功能初始版本

