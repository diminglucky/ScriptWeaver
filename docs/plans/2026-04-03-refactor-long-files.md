# Refactor Long Files Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 拆分5个超长文件（1000+行），消除跨文件重复代码，改善模块架构。

**Architecture:** 采用自底向上策略：先提取公共工具函数（无依赖），再拆分各大文件为职责单一的子模块，最后清理跨文件共性重复。每次重构后运行测试验证不破坏现有功能。

**Tech Stack:** Python, tkinter, mixin pattern

---

## Phase 1: 提取公共工具（无破坏性，最安全）

### Task 1: 提取 `env_utils.py` — 环境变量读取工具

**Files:**
- Create: `src/gui/utils/env_utils.py`
- Modify: `src/gui/modern_app.py`

**Step 1: 创建工具模块**

```python
# src/gui/utils/env_utils.py
import os

def read_env_text(key: str, default: str = "") -> str:
    return os.environ.get(key, default)

def read_env_int(key: str, default: int = 0) -> int:
    try:
        return int(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default

def read_env_float(key: str, default: float = 0.0) -> float:
    try:
        return float(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default

def read_env_bool(key: str, default: bool = False) -> bool:
    val = os.environ.get(key)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes", "on")
```

**Step 2: 在 `modern_app.py` 中替换静态方法**

找到 `modern_app.py` 中的4个 `_read_env_*` 静态方法（约318-344行），在文件顶部添加：
```python
from src.gui.utils.env_utils import read_env_text, read_env_int, read_env_float, read_env_bool
```
然后将所有 `self._read_env_text(...)` / `cls._read_env_text(...)` 调用替换为直接调用 `read_env_text(...)`，最后删除4个静态方法定义。

**Step 3: 运行测试**

Run: `cd /Volumes/F/code/play/Zhihu_short_stories && python -m pytest tests/ -v 2>&1 | tail -20`
Expected: 所有测试通过或与之前相同

**Step 4: Commit**

```bash
git add src/gui/utils/env_utils.py src/gui/modern_app.py
git commit -m "refactor: extract env_utils.py from modern_app static methods"
```

---

### Task 2: 提取通用异步任务包装器

**Files:**
- Create: `src/gui/utils/async_task.py`

**Step 1: 创建异步任务工具**

```python
# src/gui/utils/async_task.py
import threading
import traceback
import tkinter as tk
from typing import Callable, Optional

def run_async_task(
    task_fn: Callable,
    on_done: Optional[Callable] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
    daemon: bool = True,
) -> threading.Thread:
    """在后台线程运行task_fn，完成后在主线程回调on_done/on_error。"""
    def _wrapper():
        try:
            result = task_fn()
            if on_done:
                on_done(result)
        except Exception as e:
            traceback.print_exc()
            if on_error:
                on_error(e)

    t = threading.Thread(target=_wrapper, daemon=daemon)
    t.start()
    return t
```

**Step 2: 运行测试**

Run: `python -m pytest tests/ -v 2>&1 | tail -20`
Expected: 所有测试通过

**Step 3: Commit**

```bash
git add src/gui/utils/async_task.py
git commit -m "refactor: add async_task utility for background thread pattern"
```

---

## Phase 2: 拆分 `char_photo.py`（1054行）

### Task 3: 提取图片 API 解析器

**Files:**
- Create: `src/gui/mixins/image_modules/img_api_resolver.py`
- Modify: `src/gui/mixins/image_modules/char_photo.py`

**Step 1: 读取 char_photo.py 中 API 解析相关代码**

阅读 `char_photo.py` 第176-213行（`_resolve_img_runtime` 内嵌函数）和第915-929行。

**Step 2: 创建解析器模块**

提取以下方法到新文件（保持与原有接口兼容，作为 mixin 方法或独立函数）：
- `_get_img_api_config(self)` — 读取 img_api_key, img_base_url, img_model
- `_is_safety_block_error(self, err_msg: str) -> bool`
- `_is_retryable_model_error(self, err_msg: str) -> bool`

**Step 3: 在 char_photo.py 中替换内嵌 API 读取逻辑**

将 `_on_generate_character_photo` 和 `_on_generate_turnaround_sheet` 中重复的 API 读取代码替换为调用 `self._get_img_api_config()`。

**Step 4: 运行测试**

Run: `python -m pytest tests/ -v 2>&1 | tail -20`

**Step 5: Commit**

```bash
git add src/gui/mixins/image_modules/img_api_resolver.py src/gui/mixins/image_modules/char_photo.py
git commit -m "refactor: extract img_api_resolver from char_photo.py"
```

---

### Task 4: 拆分 `char_photo.py` — 保存逻辑

**Files:**
- Create: `src/gui/mixins/image_modules/char_photo_save_mixin.py`
- Modify: `src/gui/mixins/image_modules/char_photo.py`

**Step 1: 读取保存相关方法**

阅读 `char_photo.py` 第664-814行（`_auto_save_character_photo`、`_auto_save_character_photo_with_name`、`_on_save_character_photo`）。

**Step 2: 合并重复保存逻辑**

发现 `_auto_save_character_photo`（664-747行）是 `_auto_save_character_photo_with_name` 的超集。重构为：
```python
def _auto_save_character_photo_with_name(self, char_name, filename, img_data): ...
def _auto_save_character_photo(self, char_name, img_data):
    filename = self._generate_photo_filename(char_name)
    return self._auto_save_character_photo_with_name(char_name, filename, img_data)
```

**Step 3: 移动到新 mixin**

创建 `CharPhotoSaveMixin` 类，将3个保存方法移入。在 `char_photo.py` 的 `CharacterPhotoMixin` 中改为继承 `CharPhotoSaveMixin`。

**Step 4: 运行测试**

Run: `python -m pytest tests/ -v 2>&1 | tail -20`

**Step 5: Commit**

```bash
git add src/gui/mixins/image_modules/char_photo_save_mixin.py src/gui/mixins/image_modules/char_photo.py
git commit -m "refactor: extract CharPhotoSaveMixin, merge duplicate save logic"
```

---

### Task 5: 拆分 `char_photo.py` — 三视图逻辑

**Files:**
- Create: `src/gui/mixins/image_modules/char_turnaround_mixin.py`
- Modify: `src/gui/mixins/image_modules/char_photo.py`

**Step 1: 移动三视图方法**

将 `_on_generate_turnaround_sheet`（816-1009行）和 `_build_turnaround_prompt`（1011-1050行）移入新文件 `CharTurnaroundMixin`。

**Step 2: 更新 char_photo.py**

`CharacterPhotoMixin` 改为继承 `CharPhotoSaveMixin, CharTurnaroundMixin, ImgApiResolverMixin`。

**Step 3: 运行测试**

Run: `python -m pytest tests/ -v 2>&1 | tail -20`

**Step 4: Commit**

```bash
git add src/gui/mixins/image_modules/char_turnaround_mixin.py src/gui/mixins/image_modules/char_photo.py
git commit -m "refactor: extract CharTurnaroundMixin from char_photo.py"
```

---

## Phase 3: 拆分 `prompt_builder_mixin.py`（1026行）

### Task 6: 提取大纲对齐模块

**Files:**
- Create: `src/gui/mixins/story_modules/outline_alignment_mixin.py`
- Modify: `src/gui/mixins/story_modules/prompt_builder_mixin.py`

**Step 1: 识别大纲对齐方法**

以下方法移入 `OutlineAlignmentMixin`（约300行）：
- `_score_requirement_for_category` (118-127)
- `_infer_category_from_requirement` (129-145)
- `_resolve_effective_story_category` (147-162)
- `_extract_requirement_anchors` (164-188)
- `_build_requirement_alignment_block` (190-209)
- `_collect_outline_titles` (211-224)
- `_is_generic_outline_title` (226-244)
- `_evaluate_outline_alignment` (246-308)
- `_build_outline_realign_prompt` (310-336)
- `_derive_outline_must_tokens` (338-377)
- `_repair_outline_for_alignment` (379-419)

**Step 2: 创建新文件**

```python
# src/gui/mixins/story_modules/outline_alignment_mixin.py
class OutlineAlignmentMixin:
    # 以上11个方法
    ...
```

**Step 3: 在 prompt_builder_mixin.py 中继承**

```python
from .outline_alignment_mixin import OutlineAlignmentMixin

class StoryPromptBuilderMixin(OutlineAlignmentMixin, ...):
    ...
```

**Step 4: 运行测试**

Run: `python -m pytest tests/ -v 2>&1 | tail -20`

**Step 5: Commit**

```bash
git add src/gui/mixins/story_modules/outline_alignment_mixin.py src/gui/mixins/story_modules/prompt_builder_mixin.py
git commit -m "refactor: extract OutlineAlignmentMixin from prompt_builder_mixin.py"
```

---

### Task 7: 提取模型加载器模块

**Files:**
- Create: `src/gui/mixins/story_modules/model_loader_mixin.py`
- Modify: `src/gui/mixins/story_modules/prompt_builder_mixin.py`

**Step 1: 移动模型加载方法**

将以下方法移入 `ModelLoaderMixin`（约150行）：
- `_canonical_story_preset_name` (850-881)
- `_normalize_story_preset_names` (883-899)
- `_resolve_model_fetch_api_config` (901-929)
- `_load_available_models` (931-994)
- `_set_default_models` (996-1026)

**Step 2: 提取 `_safe_get_var` 辅助方法**

```python
def _safe_get_var(self, attr_name: str, default: str = "") -> str:
    var = getattr(self, attr_name, None)
    if var is None:
        return default
    try:
        return var.get()
    except Exception:
        return default
```
替换6处 `_get_story_template_strategy`、`_get_story_creativity_mode` 等方法中的重复模式。

**Step 3: 运行测试**

Run: `python -m pytest tests/ -v 2>&1 | tail -20`

**Step 4: Commit**

```bash
git add src/gui/mixins/story_modules/model_loader_mixin.py src/gui/mixins/story_modules/prompt_builder_mixin.py
git commit -m "refactor: extract ModelLoaderMixin, add _safe_get_var helper"
```

---

## Phase 4: 拆分 `settings_mixin.py`（1174行）

### Task 8: 提取 API 设置 UI 构建器

**Files:**
- Create: `src/gui/mixins/settings_modules/settings_api_ui_builder.py`
- Modify: `src/gui/mixins/settings_mixin.py`

**Step 1: 阅读对称的 story/image API 构建方法**

阅读 `settings_mixin.py` 第630-848行（8个 `_build_story_api_*` 和 `_build_image_api_*` 方法）。

**Step 2: 合并对称方法**

将8个对称方法合并为4个通用方法：
```python
def _build_api_provider_row(self, parent, context: str):  # context = "story"/"image"
def _build_api_model_row(self, parent, context: str):
def _build_api_credentials_rows(self, parent, context: str):
def _build_api_buttons(self, parent, context: str):
```
context 参数用于选择对应的变量名和标签文字。

**Step 3: 移动到新文件**

创建 `SettingsApiUiBuilder` mixin，包含上述4个方法和辅助方法。

**Step 4: 运行测试**

Run: `python -m pytest tests/ -v 2>&1 | tail -20`

**Step 5: Commit**

```bash
git add src/gui/mixins/settings_modules/settings_api_ui_builder.py src/gui/mixins/settings_mixin.py
git commit -m "refactor: extract SettingsApiUiBuilder, merge symmetric story/image API UI methods"
```

---

### Task 9: 提取参数/模版 UI 构建器

**Files:**
- Create: `src/gui/mixins/settings_modules/settings_params_ui_builder.py`
- Modify: `src/gui/mixins/settings_mixin.py`

**Step 1: 提取通用选择器方法**

将 `_build_story_template_selector`、`_build_story_template_strategy_selector`、`_build_story_creativity_selector`（281-422行）三个相同模式的方法重构为：
```python
def _build_selector_row(self, parent, label: str, items: list, var_attr: str,
                        on_change: Callable, update_desc_fn: Callable, desc_texts: dict):
    # 通用：Combobox + 描述Label
    ...
```

**Step 2: 移动知识库/生成参数/模版方法到新文件**

`SettingsParamsUiBuilder` mixin 包含：
- `_build_kb_config_section`
- `_build_generation_params_section`
- `_build_basic_generation_params_row`
- `_build_story_template_controls` 及其3个子方法
- `_build_story_quality_controls`

**Step 3: 运行测试**

Run: `python -m pytest tests/ -v 2>&1 | tail -20`

**Step 4: Commit**

```bash
git add src/gui/mixins/settings_modules/settings_params_ui_builder.py src/gui/mixins/settings_mixin.py
git commit -m "refactor: extract SettingsParamsUiBuilder, unify selector row pattern"
```

---

## Phase 5: 拆分 `shot_manager.py`（1224行）

### Task 10: 提取导演包生成模块

**Files:**
- Create: `src/gui/mixins/image_modules/director_package_mixin.py`
- Modify: `src/gui/mixins/image_modules/shot_manager.py`

**Step 1: 移动导演包相关方法**

将以下方法移入 `DirectorPackageMixin`（约217行）：
- `_build_director_package_instruction` (57-132)
- `_on_generate_director_package` (134-235)
- `_apply_director_package_to_ui` (237-276)
- `_sync_characters_from_director_package` (278-351)
- `_save_director_package_markdown` (353-377)

**Step 2: 提取 `_get_text_api_config` 辅助方法**

```python
def _get_text_api_config(self, task_key: str) -> dict:
    fallback_provider = getattr(self, 'story_api_provider_var', None)
    fallback_model = getattr(self, 'story_model_var', None)
    return self._resolve_task_api(
        task_key,
        fallback_provider=fallback_provider.get() if fallback_provider else "",
        fallback_model=fallback_model.get() if fallback_model else "",
    )
```
替换 `shot_manager.py` 中5处重复的 API 配置读取代码。

**Step 3: 运行测试**

Run: `python -m pytest tests/ -v 2>&1 | tail -20`

**Step 4: Commit**

```bash
git add src/gui/mixins/image_modules/director_package_mixin.py src/gui/mixins/image_modules/shot_manager.py
git commit -m "refactor: extract DirectorPackageMixin, add _get_text_api_config helper"
```

---

### Task 11: 提取分镜提取模块

**Files:**
- Create: `src/gui/mixins/image_modules/shot_extraction_mixin.py`
- Modify: `src/gui/mixins/image_modules/shot_manager.py`

**Step 1: 移动分镜提取相关方法**

将以下方法移入 `ShotExtractionMixin`（约290行）：
- `_parse_shot_response` (28-44)
- `_estimate_director_shot_range` (46-55)
- `_on_recommend_video_mode` (379-464)
- `_on_img_extract_shots` (466-653)
- `_on_shot_listbox_selected` (656-676)
- `_on_shot_selected` (679-682)

**Step 2: 提取分镜指令构建方法**

```python
def _build_shot_extraction_instruction(self, mode: str, n: int) -> str:
    # mode: "brief"/"normal"/"detailed"/"video"
    # 统一处理4种模式
    ...
```
替换 `_on_img_extract_shots` 中4段重复的 `inst` 字符串构建代码。

**Step 3: 运行测试**

Run: `python -m pytest tests/ -v 2>&1 | tail -20`

**Step 4: Commit**

```bash
git add src/gui/mixins/image_modules/shot_extraction_mixin.py src/gui/mixins/image_modules/shot_manager.py
git commit -m "refactor: extract ShotExtractionMixin, unify shot instruction builder"
```

---

### Task 12: 提取图片批量生成模块

**Files:**
- Create: `src/gui/mixins/image_modules/batch_generation_mixin.py`
- Modify: `src/gui/mixins/image_modules/shot_manager.py`

**Step 1: 移动批量生成方法**

将以下方法移入 `BatchGenerationMixin`（约256行）：
- `_on_img_prompt_from_current_shot` (685-967)
- `_on_batch_generate_all_shots` (970-1095)
- `_generate_shot_description_sync` (1097-1136)
- `_generate_shot_image_sync` (1138-1157)
- `_cancel_batch_generation` (1159-1162)
- `_on_img_prompt_from_shots` (1164-1222)

**Step 2: `shot_manager.py` 变为聚合类**

```python
from .director_package_mixin import DirectorPackageMixin
from .shot_extraction_mixin import ShotExtractionMixin
from .batch_generation_mixin import BatchGenerationMixin

class ShotManagerMixin(DirectorPackageMixin, ShotExtractionMixin, BatchGenerationMixin):
    pass
```

**Step 3: 运行测试**

Run: `python -m pytest tests/ -v 2>&1 | tail -20`

**Step 4: Commit**

```bash
git add src/gui/mixins/image_modules/batch_generation_mixin.py src/gui/mixins/image_modules/shot_manager.py
git commit -m "refactor: extract BatchGenerationMixin, ShotManagerMixin now aggregates sub-mixins"
```

---

## Phase 6: 拆分 `modern_app.py`（1354行）

### Task 13: 提取主题应用器

**Files:**
- Create: `src/gui/theme_applicator.py`
- Modify: `src/gui/modern_app.py`

**Step 1: 移动主题相关方法**

将以下方法移入 `ThemeApplicator` 类（约500行）：
- `_setup_modern_styles` (667-679)
- 所有 `_configure_*_styles` 方法 (681-841)
- `_apply_modern_theme` (1026-1041)
- `_apply_theme_to_children` (1043-1054)
- `_should_skip_theme_widget_class` (1056-1066)
- `_apply_theme_to_child_widgets` (1068-1070)
- `_apply_theme_to_single_widget` (1072-1092)
- 所有 `_apply_theme_to_*` 专项方法 (1094-1165)

**Step 2: 合并6个 `_apply_theme_to_*` 方法**

```python
_THEME_CONFIG_MAP = {
    "Label": {"bg": "bg", "fg": "fg"},
    "Text":  {"bg": "bg", "fg": "fg"},
    # ...
}

def _apply_theme_to_single_widget(self, widget, current_bg, colors):
    widget_class = type(widget).__name__
    cfg = self._THEME_CONFIG_MAP.get(widget_class)
    if cfg:
        widget.configure(**{k: colors[v] for k, v in cfg.items()})
```

**Step 3: 在 `modern_app.py` 中使用 ThemeApplicator**

```python
from src.gui.theme_applicator import ThemeApplicator
# ModernApp 继承或组合 ThemeApplicator
```

**Step 4: 运行测试**

Run: `python -m pytest tests/ -v 2>&1 | tail -20`

**Step 5: Commit**

```bash
git add src/gui/theme_applicator.py src/gui/modern_app.py
git commit -m "refactor: extract ThemeApplicator from modern_app.py, merge _apply_theme_to_* methods"
```

---

### Task 14: 提取 Provider 注册表

**Files:**
- Create: `src/gui/provider_registry.py`
- Modify: `src/gui/modern_app.py`

**Step 1: 移动 provider map 相关方法**

将以下方法移入 `ProviderRegistry` 类（约165行）：
- `_build_default_story_provider_map` (428-508)
- `_build_story_api_presets` (510-520)
- `_build_default_image_provider_map` (522-555)
- `_build_image_api_presets` (557-568)
- `_normalize_story_provider_map` (570-621)
- `_normalize_image_provider_map` (623-665)

**Step 2: 合并两个 `_normalize_*` 方法**

```python
def _normalize_provider_map(self, provider_map: dict, name_aliases: dict) -> dict:
    # 通用实现
    ...

def _normalize_story_provider_map(self):
    return self._normalize_provider_map(self.story_provider_map, STORY_NAME_ALIASES)

def _normalize_image_provider_map(self):
    return self._normalize_provider_map(self.image_provider_map, IMAGE_NAME_ALIASES)
```

**Step 3: 运行测试**

Run: `python -m pytest tests/ -v 2>&1 | tail -20`

**Step 4: Commit**

```bash
git add src/gui/provider_registry.py src/gui/modern_app.py
git commit -m "refactor: extract ProviderRegistry, merge duplicate normalize_provider_map methods"
```

---

### Task 15: 提取 Header/StatusBar 构建器

**Files:**
- Create: `src/gui/header_builder.py`
- Modify: `src/gui/modern_app.py`

**Step 1: 移动 Header 和 StatusBar 构建方法**

将以下方法移入 `HeaderBuilder` 类（约220行）：
- `_create_modern_header` (843-861)
- `_build_header_brand_area` (862-911)
- `_build_header_tools` (913-961)
- `_build_header_status_card` (963-991)
- `_build_header_user_card` (993-1019)
- `_build_header_separator` (1021-1024)
- `_create_modern_status_bar` (1167-1257)
- `_update_time` (1259-1267)
- `update_header_status` (1276-1320)

**Step 2: modern_app.py 精简为核心初始化**

`ModernApp.__init__` 委托给专门的构建器，文件减少到约400行（仅保留：变量初始化、启动加载配置、偏好持久化）。

**Step 3: 运行测试**

Run: `python -m pytest tests/ -v 2>&1 | tail -20`

**Step 4: Commit**

```bash
git add src/gui/header_builder.py src/gui/modern_app.py
git commit -m "refactor: extract HeaderBuilder from modern_app.py"
```

---

## Phase 7: 验证与清理

### Task 16: 全面验证

**Step 1: 运行所有测试**

Run: `python -m pytest tests/ -v`
Expected: 所有测试通过

**Step 2: 检查各文件行数**

Run: `find src -name "*.py" | xargs wc -l | sort -rn | head -20`
Expected: 没有文件超过600行

**Step 3: 检查循环导入**

Run: `python -c "from src.gui.modern_app import ModernApp; print('OK')" 2>&1`
Expected: 打印 "OK"，无导入错误

**Step 4: 最终 Commit**

```bash
git add -A
git commit -m "refactor: complete long-file refactoring, all files under 600 lines"
```

---

## 预期结果

| 文件 | 重构前 | 重构后 |
|---|---|---|
| `modern_app.py` | 1354行 | ~400行 |
| `shot_manager.py` | 1224行 | ~50行（聚合类） |
| `settings_mixin.py` | 1174行 | ~400行 |
| `prompt_builder_mixin.py` | 1026行 | ~400行 |
| `char_photo.py` | 1054行 | ~350行 |
| 新建文件数 | — | ~15个 |
| 消除重复 | — | ~200行重复代码 |
