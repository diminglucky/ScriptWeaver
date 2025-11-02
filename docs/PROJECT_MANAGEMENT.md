# 项目管理模块详细技术文档

## 📋 目录

1. [模块概述](#模块概述)
2. [文件结构](#文件结构)
3. [核心组件详解](#核心组件详解)
4. [项目数据结构](#项目数据结构)
5. [完整执行流程](#完整执行流程)

---

## 模块概述

### 功能定位

项目管理模块负责：

1. **项目创建**：创建新的创作项目
2. **项目加载**：加载已有项目
3. **项目保存**：保存故事、图片、配置等所有内容
4. **项目列表**：列出所有项目
5. **项目删除**：安全删除项目
6. **自动备份**：保存时自动创建备份文件

### 模块位置

```
src/
├── project_manager.py          # 项目管理器核心类
└── gui/mixins/
    ├── project_mixin.py         # 项目管理UI和逻辑
    └── project_modules/
        └── enhanced_manager.py # 增强管理器
```

### 模块依赖关系

```
ProjectMixin
├── ProjectManager               # 项目管理器
│   └── Project                  # 单个项目类
└── EnhancedProjectManager      # 增强管理器（如果使用）
```

---

## 文件结构

### 1. project_manager.py

**职责**: 项目管理器的核心实现

**主要类**:
- `Project`: 单个创作项目类
- `ProjectManager`: 项目管理器类

**文件大小**: 186行

### 2. project_mixin.py

**职责**: 项目管理UI和逻辑

**主要类**:
- `ProjectMixin`: 项目管理功能

**主要方法**:
- `on_new_project()`: 创建新项目
- `on_load_project()`: 加载项目
- `on_save_story()`: 保存故事
- `on_save_all()`: 保存所有内容
- `on_delete_project()`: 删除项目
- `on_refresh_project_list()`: 刷新项目列表

**文件大小**: 约300-500行（估计）

### 3. enhanced_manager.py

**职责**: 增强的项目管理功能

**主要类**:
- `EnhancedProjectManager`: 增强管理器

**文件大小**: 约100-200行（估计）

---

## 核心组件详解

### 1. Project类

#### 类定义

```python
class Project:
    """单个创作项目"""
    
    def __init__(self, project_dir: Path):
        """
        初始化项目
        
        参数:
            project_dir: 项目目录路径
        
        创建的文件结构:
            project_dir/
            ├── project.json        # 项目元数据
            ├── story.txt           # 故事内容
            ├── story.txt.bak       # 故事备份
            ├── images/             # 图片目录
            ├── characters/         # 人物目录（导演模式）
            └── director/            # 导演模式数据
                ├── script.txt
                ├── shots.json
                └── shots/
        """
        self.project_dir = Path(project_dir)
        self.project_dir.mkdir(parents=True, exist_ok=True)
        
        # 定义文件路径
        self.meta_file = self.project_dir / "project.json"
        self.story_file = self.project_dir / "story.txt"
        self.images_dir = self.project_dir / "images"
        self.images_dir.mkdir(exist_ok=True)
        
        # 加载元数据
        self.metadata: dict[str, Any] = self._load_metadata()
```

#### `_load_metadata()` 详解

```python
def _load_metadata(self) -> dict[str, Any]:
    """
    加载项目元数据
    
    返回:
        项目元数据字典
    
    元数据字段:
        - name: 项目名称
        - created_at: 创建时间（ISO格式）
        - updated_at: 更新时间（ISO格式）
        - category: 故事类型
        - requirement: 创作需求
        - style: 风格设置
        - target_chars: 目标字数
    """
    if self.meta_file.exists():
        try:
            with open(self.meta_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"加载项目元数据失败: {e}，使用默认值")
    
    # 默认元数据
    return {
        "name": self.project_dir.name,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "category": "",
        "requirement": "",
        "style": "",
        "target_chars": 1800,
    }
```

#### `save_story()` 详解

```python
def save_story(self, content: str, **params) -> None:
    """
    保存故事内容
    
    参数:
        content: 故事内容
        **params: 其他参数（会更新到元数据）
            - category: 故事类型
            - requirement: 创作需求
            - style: 风格设置
            - target_chars: 目标字数
    
    流程:
        1. 创建备份（如果已存在）
        2. 保存故事内容
        3. 更新元数据
    """
    try:
        # 步骤1: 创建备份（如果已存在）
        if self.story_file.exists():
            backup_file = self.project_dir / "story.txt.bak"
            shutil.copy2(self.story_file, backup_file)
            # copy2 会复制文件内容和元数据（时间戳等）
        
        # 步骤2: 保存故事内容
        with open(self.story_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        # 步骤3: 更新元数据
        for key, value in params.items():
            self.metadata[key] = value
        self._save_metadata()
        
    except Exception as e:
        logger.error(f"保存故事失败: {e}", exc_info=True)
        raise
```

#### `load_story()` 详解

```python
def load_story(self) -> str:
    """
    加载故事内容
    
    返回:
        故事内容（字符串）
    
    如果文件不存在，返回空字符串
    """
    if self.story_file.exists():
        with open(self.story_file, "r", encoding="utf-8") as f:
            return f.read()
    return ""
```

#### `save_image()` 详解

```python
def save_image(self, image_path: Path | str, name: str | None = None) -> Path:
    """
    保存图片到项目
    
    参数:
        image_path: 源图片路径
        name: 保存的文件名（如果为None，自动生成）
    
    返回:
        保存后的图片路径
    
    流程:
        1. 检查源文件是否存在
        2. 生成目标文件名（如果未指定）
        3. 复制文件到images目录
    """
    src = Path(image_path)
    if not src.exists():
        raise FileNotFoundError(f"图片不存在: {src}")
    
    # 生成文件名（如果未指定）
    if name is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"img_{timestamp}{src.suffix}"
    
    # 保存到images目录
    dst = self.images_dir / name
    shutil.copy2(src, dst)
    return dst
```

#### `list_images()` 详解

```python
def list_images(self) -> list[Path]:
    """
    列出项目中的所有图片
    
    返回:
        图片路径列表（按文件名排序）
    
    支持的格式:
        - .png
        - .jpg
        - .jpeg
        - .webp
    """
    if not self.images_dir.exists():
        return []
    
    images: list[Path] = []
    # Path.glob 不支持大括号扩展，需逐个模式匹配
    for pattern in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
        images.extend(self.images_dir.glob(pattern))
    
    return sorted(images)
```

#### `get_info()` 详解

```python
def get_info(self) -> dict[str, Any]:
    """
    获取项目信息摘要
    
    返回:
        项目信息字典
    
    信息字段:
        - name: 项目名称
        - created_at: 创建时间
        - updated_at: 更新时间
        - category: 故事类型
        - story_length: 故事字数
        - image_count: 图片数量
    """
    story_length = len(self.load_story())
    image_count = len(list(self.images_dir.glob("*.*"))) if self.images_dir.exists() else 0
    
    return {
        "name": self.metadata.get("name", self.project_dir.name),
        "created_at": self.metadata.get("created_at", ""),
        "updated_at": self.metadata.get("updated_at", ""),
        "category": self.metadata.get("category", ""),
        "story_length": story_length,
        "image_count": image_count,
    }
```

### 2. ProjectManager类

#### 类定义

```python
class ProjectManager:
    """项目管理器：管理多个项目"""
    
    def __init__(self, workspace: Path | str = "projects"):
        """
        初始化项目管理器
        
        参数:
            workspace: 工作空间目录（默认"projects"）
        
        工作空间结构:
            projects/
            ├── {project_name}_{timestamp}/
            │   ├── project.json
            │   ├── story.txt
            │   └── images/
            └── ...
        """
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
```

#### `create_project()` 详解

```python
def create_project(self, name: str) -> Project:
    """
    创建新项目
    
    参数:
        name: 项目名称
    
    返回:
        Project实例
    
    流程:
        1. 生成安全的文件夹名
        2. 添加时间戳
        3. 创建项目目录
        4. 初始化项目
        5. 保存元数据
    """
    # 步骤1: 生成安全的文件夹名
    safe_name = "".join(
        c if c.isalnum() or c in ("-", "_") else "_" 
        for c in name
    )
    # 例如: "我的故事" → "我的故事"
    # 例如: "故事/测试" → "故事_测试"
    
    # 步骤2: 添加时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 例如: "20251027_171224"
    
    # 步骤3: 创建项目目录
    project_dir = self.workspace / f"{safe_name}_{timestamp}"
    # 例如: "projects/我的故事_20251027_171224"
    
    # 步骤4: 初始化项目
    project = Project(project_dir)
    project.metadata["name"] = name
    project._save_metadata()
    
    return project
```

**示例**:

```python
# 创建项目
manager = ProjectManager()
project = manager.create_project("我的第一个故事")

# 结果
# projects/我的第一个故事_20251027_171224/
# ├── project.json
# ├── story.txt
# └── images/
```

#### `load_project()` 详解

```python
def load_project(self, project_dir: Path | str) -> Project:
    """
    加载已有项目
    
    参数:
        project_dir: 项目目录路径
    
    返回:
        Project实例
    
    流程:
        1. 创建Project实例
        2. 自动加载元数据和故事内容
    """
    return Project(project_dir)
```

#### `list_projects()` 详解

```python
def list_projects(self) -> list[dict[str, Any]]:
    """
    列出所有项目
    
    返回:
        项目信息列表（按更新时间倒序）
    
    流程:
        1. 扫描工作空间目录
        2. 查找有效的项目目录（包含project.json）
        3. 加载项目信息
        4. 按更新时间排序
    """
    projects = []
    
    # 遍历工作空间目录
    for item in self.workspace.iterdir():
        if item.is_dir() and (item / "project.json").exists():
            try:
                # 加载项目
                project = Project(item)
                info = project.get_info()
                info["path"] = str(item)
                projects.append(info)
            except Exception:
                # 跳过无效项目
                continue
    
    # 按更新时间倒序排列
    projects.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return projects
```

**返回格式**:

```python
[
    {
        "name": "我的第一个故事",
        "created_at": "2025-10-27T17:12:24",
        "updated_at": "2025-10-27T18:30:15",
        "category": "爱情",
        "story_length": 2345,
        "image_count": 3,
        "path": "projects/我的第一个故事_20251027_171224"
    },
    # ... 更多项目
]
```

#### `delete_project()` 详解

```python
def delete_project(self, project_dir: Path | str) -> None:
    """
    删除项目
    
    参数:
        project_dir: 项目目录路径
    
    流程:
        1. 安全检查：确保要删除的是workspace内的项目
        2. 验证项目有效性
        3. 删除项目目录
    """
    project_path = Path(project_dir)
    
    # 步骤1: 安全检查
    try:
        project_path = project_path.resolve()
        workspace_path = self.workspace.resolve()
        
        # 检查路径是否在workspace内
        if not str(project_path).startswith(str(workspace_path)):
            raise ValueError(f"不能删除workspace外的目录: {project_path}")
        
        # 步骤2: 验证项目有效性
        if not (project_path / "project.json").exists():
            raise ValueError(f"不是有效的项目目录: {project_path}")
        
        # 步骤3: 删除项目
        if project_path.exists() and project_path.is_dir():
            shutil.rmtree(project_path)
            logger.info(f"已删除项目: {project_path.name}")
            
    except Exception as e:
        logger.error(f"删除项目失败: {e}", exc_info=True)
        raise
```

**安全检查**:
- 确保要删除的目录在workspace内
- 确保是有效的项目目录（包含project.json）
- 防止误删其他目录

---

## 项目数据结构

### 项目目录结构

```
projects/
└── {project_name}_{timestamp}/    # 项目目录
    ├── project.json                # 项目元数据
    ├── story.txt                    # 故事内容
    ├── story.txt.bak                # 故事备份
    ├── images/                      # 图片目录
    │   ├── img_20251027_171224.png
    │   └── ...
    ├── characters/                 # 人物目录（导演模式）
    │   ├── characters_info.json
    │   ├── 小雨_中性.png
    │   ├── 小雨_开心.png
    │   └── ...
    └── director/                    # 导演模式数据
        ├── script.txt               # 剧本
        ├── shots.json              # 分镜列表
        ├── jimeng_prompts.txt      # 即梦提示词
        └── shots/                   # 分镜图片
            ├── shot_1.png
            └── ...
```

### project.json 格式

```json
{
  "name": "我的第一个故事",
  "created_at": "2025-10-27T17:12:24.123456",
  "updated_at": "2025-10-27T18:30:15.654321",
  "category": "爱情",
  "requirement": "写一个关于初恋的故事",
  "style": "情感起伏/反转/细节描写/有画面感/口语化",
  "target_chars": 1800
}
```

**字段说明**:
- **name**: 项目名称（用户输入）
- **created_at**: 创建时间（ISO格式，自动生成）
- **updated_at**: 更新时间（ISO格式，每次保存时更新）
- **category**: 故事类型（爱情/悬疑/职场等）
- **requirement**: 创作需求（用户输入）
- **style**: 风格设置（用户输入）
- **target_chars**: 目标字数（用户设置）

---

## 完整执行流程

### 创建项目流程

```
用户操作
  │
  ├─→ 点击"新建项目"按钮
  │   └─→ ProjectMixin.on_new_project()
  │       │
  │       ├─→ 步骤1: 弹出输入对话框
  │       │   └─→ simpledialog.askstring("新建项目", "请输入项目名称")
  │       │
  │       ├─→ 步骤2: 验证项目名称
  │       │   └─→ 检查是否为空
  │       │
  │       ├─→ 步骤3: 创建项目
  │       │   └─→ ProjectManager.create_project(name)
  │       │       ├─→ 生成安全的文件夹名
  │       │       ├─→ 添加时间戳
  │       │       ├─→ 创建项目目录
  │       │       └─→ 初始化Project实例
  │       │
  │       ├─→ 步骤4: 设置为当前项目
  │       │   └─→ self.current_project = project
  │       │
  │       ├─→ 步骤5: 刷新项目列表
  │       │   └─→ self._refresh_project_list()
  │       │
  │       └─→ 步骤6: 更新UI状态
  │           └─→ self.lbl_current_project.config(text=project.metadata["name"])
```

### 加载项目流程

```
用户操作
  │
  ├─→ 从项目列表选择项目
  │   └─→ ProjectMixin.on_load_project()
  │       │
  │       ├─→ 步骤1: 获取选中的项目路径
  │       │   └─→ 从列表获取项目路径
  │       │
  │       ├─→ 步骤2: 加载项目
  │       │   └─→ ProjectManager.load_project(project_path)
  │       │       └─→ Project(project_dir)
  │       │
  │       ├─→ 步骤3: 加载故事内容
  │       │   └─→ project.load_story()
  │       │       └─→ 显示到输出区域
  │       │
  │       ├─→ 步骤4: 恢复项目参数
  │       │   ├─→ self.category.set(project.metadata["category"])
  │       │   ├─→ self.target_chars.set(project.metadata["target_chars"])
  │       │   └─→ self.style.set(project.metadata["style"])
  │       │
  │       ├─→ 步骤5: 设置为当前项目
  │       │   └─→ self.current_project = project
  │       │
  │       └─→ 步骤6: 更新UI状态
  │           └─→ self.lbl_current_project.config(text=project.metadata["name"])
```

### 保存故事流程

```
用户操作
  │
  ├─→ 点击"保存故事"按钮
  │   └─→ ProjectMixin.on_save_story()
  │       │
  │       ├─→ 步骤1: 检查是否有当前项目
  │       │   └─→ if not self.current_project: 提示创建项目
  │       │
  │       ├─→ 步骤2: 获取故事内容
  │       │   └─→ content = self.output.get("1.0", END).strip()
  │       │
  │       ├─→ 步骤3: 获取项目参数
  │       │   ├─→ category = self.category.get()
  │       │   ├─→ requirement = self._get_prompt_content()
  │       │   ├─→ style = self.style.get()
  │       │   └─→ target_chars = self.target_chars.get()
  │       │
  │       ├─→ 步骤4: 保存故事
  │       │   └─→ self.current_project.save_story(
  │       │           content,
  │       │           category=category,
  │       │           requirement=requirement,
  │       │           style=style,
  │       │           target_chars=target_chars
  │       │       )
  │       │       ├─→ 创建备份（如果已存在）
  │       │       ├─→ 保存故事内容
  │       │       └─→ 更新元数据
  │       │
  │       └─→ 步骤5: 显示成功消息
  │           └─→ messagebox.showinfo("成功", "故事已保存")
```

### 删除项目流程

```
用户操作
  │
  ├─→ 点击"删除项目"按钮
  │   └─→ ProjectMixin.on_delete_project()
  │       │
  │       ├─→ 步骤1: 确认删除
  │       │   └─→ messagebox.askyesno("确认删除", "确定要删除这个项目吗？")
  │       │
  │       ├─→ 步骤2: 获取项目路径
  │       │   └─→ project_path = self.current_project.project_dir
  │       │
  │       ├─→ 步骤3: 删除项目
  │       │   └─→ ProjectManager.delete_project(project_path)
  │       │       ├─→ 安全检查
  │       │       └─→ shutil.rmtree(project_path)
  │       │
  │       ├─→ 步骤4: 清空当前项目
  │       │   └─→ self.current_project = None
  │       │
  │       ├─→ 步骤5: 刷新项目列表
  │       │   └─→ self._refresh_project_list()
  │       │
  │       └─→ 步骤6: 更新UI状态
  │           ├─→ self.lbl_current_project.config(text="未选择项目")
  │           └─→ self.output.delete("1.0", END)
```

---

## 自动保存机制

### 自动保存触发

```python
# 在故事生成完成后自动保存
self.after(100, lambda: self._auto_save_to_project())

def _auto_save_to_project(self):
    """自动保存到当前项目"""
    if not self.current_project:
        return
    
    content = self.output.get("1.0", END).strip()
    if not content:
        return
    
    try:
        self.current_project.save_story(
            content,
            category=self.category.get(),
            requirement=self._get_prompt_content(),
            style=self.style.get(),
            target_chars=self.target_chars.get()
        )
        logger.info("已自动保存到项目")
    except Exception as e:
        logger.error(f"自动保存失败: {e}")
```

### 备份机制

每次保存时自动创建备份：

```python
# 在save_story()中
if self.story_file.exists():
    backup_file = self.project_dir / "story.txt.bak"
    shutil.copy2(self.story_file, backup_file)
```

**备份特点**:
- 保存前自动创建备份
- 备份文件名固定：`story.txt.bak`
- 使用`copy2`保持文件元数据

---

## 总结

项目管理模块提供了完整的项目生命周期管理：

1. **项目创建**：安全命名、时间戳、自动初始化
2. **项目加载**：加载故事、恢复参数、更新UI
3. **项目保存**：自动备份、更新元数据、保存所有内容
4. **项目列表**：按时间排序、显示信息摘要
5. **项目删除**：安全检查、防止误删

所有操作都经过精心设计，确保数据安全和用户体验。

