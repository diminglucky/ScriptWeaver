# 故事功能 Bug 修复说明

## 修复日期
2025-10-11

## 问题描述

### 错误信息
```
'_tkinter.tkapp' object has no attribute '_estimate_chars'
```

### 根本原因
在将代码重构为 Mixin 模式后，`_estimate_chars` 和 `_parse_outline_sections` 这两个辅助方法没有被迁移到 `StoryMixin` 类中，导致运行时找不到这些方法。

## 涉及的方法

### 1. `_estimate_chars(self, outline: str) -> int`
**功能：** 根据目录估算字数

**实现逻辑：**
- 解析目录中的章节数量
- 识别数字编号、中文编号（一、二、三...）、或符号（-、•、*）开头的行
- 按每章节约 350 字估算总字数
- 如果无法识别章节，默认估算 3-8 章

**用途：**
- 在生成目录后显示预估字数
- 帮助用户了解生成内容的大致长度

### 2. `_parse_outline_sections(self, outline: str) -> list[dict[str, str]]`
**功能：** 解析目录，提取章节信息

**实现逻辑：**
- 将目录文本按行分割
- 使用正则表达式识别章节标题：
  - 数字编号：`1.`、`1、`
  - 中文编号：`一、`、`二、`等
  - 符号标记：`-`、`•`、`*`开头
- 将每个章节及其子项目组织成字典
- 返回结构化的章节列表

**返回格式：**
```python
[
    {
        "title": "1. 章节标题",
        "items": ["子项1", "子项2"]
    },
    ...
]
```

**用途：**
- 支持分章节生成功能
- 更新章节选择器
- 实现章节导航

## 修复内容

### 1. 添加缺失的导入
在 `story_mixin.py` 文件顶部添加了 `re` 模块导入：
```python
import re
```

### 2. 添加辅助方法
在 `StoryMixin` 类的末尾添加了两个方法：

```python
def _estimate_chars(self, outline: str) -> int:
    """根据目录估算字数"""
    lines = [l.strip() for l in outline.splitlines() if l.strip()]
    count = 0
    for l in lines:
        if l[:2].isdigit() or l[:1] in {"-", "•", "*"} or l.startswith(("一、", "二、", "三、", "四、", "五、")):
            count += 1
    if count <= 0:
        count = max(3, min(8, len(lines)//2 or 4))
    return int(count * 350)

def _parse_outline_sections(self, outline: str) -> list[dict[str, str]]:
    """解析目录，提取章节信息"""
    if not outline:
        return []
    
    sections = []
    lines = outline.strip().splitlines()
    current_section = None
    current_items = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        
        # 检测是否为章节标题
        is_main_section = False
        if re.match(r'^\d+[.、]', stripped) or re.match(r'^[一二三四五六七八九十]+[.、]', stripped):
            is_main_section = True
        elif stripped[:1] in ("-", "•", "*") and not stripped[1:2].isdigit():
            is_main_section = True
        
        if is_main_section:
            if current_section:
                sections.append({
                    "title": current_section,
                    "items": current_items.copy()
                })
            current_section = stripped
            current_items = []
        else:
            if current_section:
                current_items.append(stripped)
    
    if current_section:
        sections.append({
            "title": current_section,
            "items": current_items
        })
    
    return sections
```

## 修复后的功能

### ✅ 恢复的功能
1. **目录生成** - 可以正常生成目录并显示预估字数
2. **章节解析** - 可以正确识别和解析章节结构
3. **分章节生成** - 支持按章节逐个生成故事内容
4. **字数估算** - 在生成目录后显示预估的总字数

### ✅ 支持的目录格式
```
✓ 数字编号
1. 章节一
2. 章节二

✓ 中文编号
一、章节一
二、章节二

✓ 符号标记
- 章节一
• 章节二
* 章节三
```

## 测试验证

### 测试步骤
1. 启动应用：`python run_modern_app.py`
2. 进入"故事生成"页面
3. 输入创作需求
4. 点击"生成目录"
5. 查看是否显示预估字数
6. 测试分章节生成功能

### 预期结果
- ✅ 目录生成成功
- ✅ 显示"目录（共X章，预估字数≈XXX字）"
- ✅ 章节选择器可以正常工作
- ✅ 可以选择章节并单独生成

## 技术说明

### 正则表达式详解

#### 数字编号匹配
```python
re.match(r'^\d+[.、]', stripped)
```
- `^\d+`：以一个或多个数字开头
- `[.、]`：后跟句点或中文顿号

#### 中文编号匹配
```python
re.match(r'^[一二三四五六七八九十]+[.、]', stripped)
```
- `^[一二三四五六七八九十]+`：以中文数字开头
- `[.、]`：后跟句点或中文顿号

### 字数估算算法
```python
# 每章节约350字
return int(count * 350)
```

根据经验值：
- 知乎风格故事每个章节平均 300-400 字
- 取中间值 350 字作为估算基准
- 如果用户设置了目标字数，实际生成会接近目标值

## 相关文件

### 修改的文件
- `src/gui/mixins/story_mixin.py`
  - 添加 `import re`
  - 添加 `_estimate_chars()` 方法
  - 添加 `_parse_outline_sections()` 方法

### 参考文件
- `src/gui_app_backup.py` - 原始实现参考
- `src/gui/modern_app.py` - 变量初始化位置

## 经验总结

### 问题根源
在代码重构过程中，将大型单文件拆分为多个 Mixin 类时，容易遗漏一些辅助方法。

### 防范措施
1. **代码审查**：重构后检查所有被调用的方法是否都已迁移
2. **单元测试**：为关键方法编写测试用例
3. **渐进式重构**：先测试每个 Mixin，再集成
4. **文档记录**：记录每个 Mixin 提供的方法

### 最佳实践
1. 使用 IDE 的"查找引用"功能检查方法调用
2. 在迁移代码时做清单记录
3. 保留原始文件作为参考
4. 逐个测试重构后的功能

## 后续建议
1. 考虑为这些辅助方法添加单元测试
2. 优化正则表达式以支持更多目录格式
3. 改进字数估算算法的准确性
4. 添加目录格式验证功能


