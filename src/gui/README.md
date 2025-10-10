# GUI模块重构说明

## 目录结构

```
src/gui/
├── __init__.py          # 模块初始化
├── utils.py             # 工具函数
├── config_manager.py    # 配置管理
├── mixins/              # Mixin类（功能模块）
│   ├── __init__.py
│   ├── project_mixin.py # 项目管理
│   ├── story_mixin.py   # 故事生成
│   ├── image_mixin.py   # 图片生成
│   └── kb_mixin.py      # 知识库管理
└── main_window.py       # 主窗口类
```

## 设计模式

使用**Mixin模式**将功能模块化：
- `ProjectMixin`: 项目管理功能
- `StoryMixin`: 故事生成功能  
- `ImageMixin`: 图片生成功能
- `KBMixin`: 知识库管理功能

主窗口类继承所有Mixin，组合所有功能。

## 优点

1. **模块化**: 每个功能独立在一个文件中
2. **易维护**: 修改某个功能只需编辑对应的Mixin文件
3. **易测试**: 每个Mixin可以独立测试
4. **向后兼容**: API保持不变，现有代码无需修改

