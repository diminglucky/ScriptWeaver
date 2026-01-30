"""
综合增强功能模块
包含：进度显示、快捷键、历史记录、缓存、API状态监控等
"""

import os
import json
import time
import base64
import hashlib
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, Dict, List, Any
from functools import wraps

# 可选依赖：cryptography（用于API Key加密）
try:
    from cryptography.fernet import Fernet
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False
    Fernet = None


# ==================== 1. 进度显示组件 ====================

class ProgressDialog:
    """现代化进度对话框"""
    
    def __init__(self, parent, title: str = "处理中", message: str = "请稍候..."):
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 窗口居中
        width, height = 400, 180
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        self.dialog.resizable(False, False)
        
        # 样式
        self.dialog.configure(bg="#1e1e1e")
        
        # 消息标签
        self.message_var = tk.StringVar(value=message)
        tk.Label(
            self.dialog, textvariable=self.message_var,
            bg="#1e1e1e", fg="#ffffff", font=("", 12)
        ).pack(pady=(30, 15))
        
        # 进度条
        self.progress = ttk.Progressbar(
            self.dialog, mode='determinate', length=300
        )
        self.progress.pack(pady=10)
        
        # 百分比标签
        self.percent_var = tk.StringVar(value="0%")
        tk.Label(
            self.dialog, textvariable=self.percent_var,
            bg="#1e1e1e", fg="#9CA3AF", font=("", 10)
        ).pack(pady=5)
        
        # 详情标签
        self.detail_var = tk.StringVar(value="")
        tk.Label(
            self.dialog, textvariable=self.detail_var,
            bg="#1e1e1e", fg="#6B7280", font=("", 9)
        ).pack(pady=5)
        
        # 禁止关闭
        self.dialog.protocol("WM_DELETE_WINDOW", lambda: None)
    
    def update(self, value: float, message: str = None, detail: str = None):
        """更新进度"""
        self.progress['value'] = value
        self.percent_var.set(f"{int(value)}%")
        if message:
            self.message_var.set(message)
        if detail:
            self.detail_var.set(detail)
        self.dialog.update()
    
    def set_indeterminate(self, message: str = "处理中..."):
        """设置为不确定模式"""
        self.progress.configure(mode='indeterminate')
        self.progress.start(10)
        self.message_var.set(message)
        self.percent_var.set("")
        self.dialog.update()
    
    def close(self):
        """关闭对话框"""
        try:
            self.progress.stop()
            self.dialog.destroy()
        except Exception:
            pass


class ProgressMixin:
    """进度显示Mixin - 提供统一的进度显示功能"""
    
    def show_progress(self, title: str = "处理中", message: str = "请稍候...") -> ProgressDialog:
        """显示进度对话框"""
        return ProgressDialog(self, title, message)
    
    def run_with_progress(self, func: Callable, title: str = "处理中", 
                          message: str = "请稍候...", callback: Callable = None):
        """在后台线程运行任务并显示进度"""
        progress = self.show_progress(title, message)
        progress.set_indeterminate()
        
        def worker():
            try:
                result = func()
                self.after(0, lambda: self._on_task_complete(progress, result, callback))
            except Exception as e:
                self.after(0, lambda: self._on_task_error(progress, e))
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return progress
    
    def _on_task_complete(self, progress: ProgressDialog, result, callback: Callable):
        """任务完成处理"""
        progress.close()
        if callback:
            callback(result)
    
    def _on_task_error(self, progress: ProgressDialog, error: Exception):
        """任务错误处理"""
        progress.close()
        messagebox.showerror("错误", f"操作失败: {str(error)}")


# ==================== 2. 快捷键系统 ====================

class KeyboardShortcuts:
    """快捷键管理器"""
    
    DEFAULT_SHORTCUTS = {
        # 文件操作
        '<Control-n>': ('new_project', '新建项目'),
        '<Control-o>': ('open_project', '打开项目'),
        '<Control-s>': ('save_project', '保存项目'),
        '<Control-Shift-s>': ('save_as', '另存为'),
        '<Control-e>': ('export_project', '导出项目'),
        '<Control-i>': ('import_project', '导入项目'),
        
        # 编辑操作
        '<Control-z>': ('undo', '撤销'),
        '<Control-Shift-z>': ('redo', '重做'),
        '<Control-y>': ('redo', '重做'),
        
        # 生成操作
        '<Control-g>': ('generate_outline', '生成大纲'),
        '<Control-Shift-g>': ('generate_story', '生成故事'),
        '<F5>': ('generate_selected', '生成选中章节'),
        
        # 视图操作
        '<Control-1>': ('goto_project', '切换到项目页'),
        '<Control-2>': ('goto_story', '切换到故事页'),
        '<Control-3>': ('goto_image', '切换到图片页'),
        '<Control-4>': ('goto_settings', '切换到设置页'),
        '<Control-t>': ('toggle_theme', '切换主题'),
        
        # 其他
        '<F1>': ('show_help', '显示帮助'),
        '<Control-comma>': ('open_settings', '打开设置'),
    }
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.shortcuts = {}
        self.handlers = {}
        self._load_shortcuts()
    
    def _load_shortcuts(self):
        """加载快捷键配置"""
        config_path = Path("config/shortcuts.json")
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    self.shortcuts = json.load(f)
            except Exception:
                self.shortcuts = dict(self.DEFAULT_SHORTCUTS)
        else:
            self.shortcuts = dict(self.DEFAULT_SHORTCUTS)
    
    def save_shortcuts(self):
        """保存快捷键配置"""
        config_path = Path("config/shortcuts.json")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(self.shortcuts, f, indent=2)
    
    def register(self, action: str, handler: Callable):
        """注册快捷键处理器"""
        self.handlers[action] = handler
    
    def bind_all(self):
        """绑定所有快捷键"""
        for key, (action, _) in self.shortcuts.items():
            self._bind_key(key, action)
    
    def _bind_key(self, key: str, action: str):
        """绑定单个快捷键"""
        def handler(event):
            if action in self.handlers:
                try:
                    self.handlers[action]()
                except Exception as e:
                    print(f"快捷键处理错误 [{action}]: {e}")
            return "break"
        
        try:
            self.root.bind_all(key, handler)
        except Exception:
            pass
    
    def get_shortcut_list(self) -> List[tuple]:
        """获取快捷键列表"""
        return [(key, action, desc) for key, (action, desc) in self.shortcuts.items()]


class ShortcutsMixin:
    """快捷键Mixin"""
    
    def _setup_shortcuts(self):
        """设置快捷键"""
        self.shortcuts = KeyboardShortcuts(self)
        
        # 注册处理器
        self.shortcuts.register('new_project', self._shortcut_new_project)
        self.shortcuts.register('open_project', self._shortcut_open_project)
        self.shortcuts.register('save_project', self._shortcut_save_project)
        self.shortcuts.register('export_project', self._shortcut_export)
        self.shortcuts.register('import_project', self._shortcut_import)
        self.shortcuts.register('generate_outline', self._shortcut_generate_outline)
        self.shortcuts.register('generate_story', self._shortcut_generate_story)
        self.shortcuts.register('goto_project', lambda: self._goto_tab(0))
        self.shortcuts.register('goto_story', lambda: self._goto_tab(1))
        self.shortcuts.register('goto_image', lambda: self._goto_tab(2))
        self.shortcuts.register('goto_settings', lambda: self._goto_tab(3))
        self.shortcuts.register('toggle_theme', self._toggle_theme)
        self.shortcuts.register('show_help', self._show_shortcuts_help)
        
        # 绑定所有快捷键
        self.shortcuts.bind_all()
    
    def _goto_tab(self, index: int):
        """切换到指定标签页"""
        if hasattr(self, 'notebook'):
            tabs = self.notebook.tabs()
            if index < len(tabs):
                self.notebook.select(tabs[index])
    
    def _shortcut_new_project(self):
        if hasattr(self, '_on_new_project'):
            self._on_new_project()
    
    def _shortcut_open_project(self):
        if hasattr(self, '_on_load_project'):
            self._on_load_project()
    
    def _shortcut_save_project(self):
        if hasattr(self, '_auto_save_to_project'):
            self._auto_save_to_project()
        elif hasattr(self, '_on_save_story'):
            self._on_save_story()
    
    def _shortcut_export(self):
        if hasattr(self, 'export_project'):
            self.export_project()
    
    def _shortcut_import(self):
        if hasattr(self, 'import_project'):
            self.import_project()
    
    def _shortcut_generate_outline(self):
        if hasattr(self, 'on_generate_outline'):
            self.on_generate_outline()
    
    def _shortcut_generate_story(self):
        if hasattr(self, 'on_auto_generate_all'):
            self.on_auto_generate_all()
        elif hasattr(self, 'on_generate'):
            self.on_generate()
    
    def _toggle_theme(self):
        """切换主题"""
        from ..theme import theme_manager
        theme_manager.toggle()
        if hasattr(self, '_refresh_theme'):
            self._refresh_theme()
    
    def _show_shortcuts_help(self):
        """显示快捷键帮助"""
        help_text = "快捷键列表:\n\n"
        for key, action, desc in self.shortcuts.get_shortcut_list():
            key_display = key.replace('<', '').replace('>', '').replace('Control', 'Ctrl')
            help_text += f"  {key_display}: {desc}\n"
        
        messagebox.showinfo("快捷键帮助", help_text)


# ==================== 3. 历史记录管理 ====================

class HistoryManager:
    """历史记录管理器 - 支持撤销/重做"""
    
    def __init__(self, max_history: int = 50):
        self.max_history = max_history
        self.history: List[Dict] = []
        self.current_index = -1
    
    def add(self, action: str, data: Dict, undo_func: Callable = None, redo_func: Callable = None):
        """添加历史记录"""
        # 清除当前位置之后的历史
        if self.current_index < len(self.history) - 1:
            self.history = self.history[:self.current_index + 1]
        
        record = {
            'action': action,
            'data': data,
            'undo': undo_func,
            'redo': redo_func,
            'timestamp': datetime.now().isoformat()
        }
        
        self.history.append(record)
        self.current_index = len(self.history) - 1
        
        # 限制历史数量
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
            self.current_index = len(self.history) - 1
    
    def undo(self) -> Optional[Dict]:
        """撤销"""
        if self.current_index >= 0:
            record = self.history[self.current_index]
            if record.get('undo'):
                record['undo'](record['data'])
            self.current_index -= 1
            return record
        return None
    
    def redo(self) -> Optional[Dict]:
        """重做"""
        if self.current_index < len(self.history) - 1:
            self.current_index += 1
            record = self.history[self.current_index]
            if record.get('redo'):
                record['redo'](record['data'])
            return record
        return None
    
    def can_undo(self) -> bool:
        return self.current_index >= 0
    
    def can_redo(self) -> bool:
        return self.current_index < len(self.history) - 1
    
    def clear(self):
        """清除历史"""
        self.history = []
        self.current_index = -1
    
    def get_history_list(self) -> List[Dict]:
        """获取历史列表"""
        return self.history[:self.current_index + 1]


class HistoryMixin:
    """历史记录Mixin"""
    
    def _init_history(self):
        """初始化历史管理"""
        self.history_manager = HistoryManager()
    
    def add_to_history(self, action: str, data: Dict, undo_func: Callable = None, redo_func: Callable = None):
        """添加到历史记录"""
        if hasattr(self, 'history_manager'):
            self.history_manager.add(action, data, undo_func, redo_func)
    
    def undo_action(self):
        """撤销操作"""
        if hasattr(self, 'history_manager') and self.history_manager.can_undo():
            record = self.history_manager.undo()
            if record:
                self.update_status(f"已撤销: {record['action']}")
    
    def redo_action(self):
        """重做操作"""
        if hasattr(self, 'history_manager') and self.history_manager.can_redo():
            record = self.history_manager.redo()
            if record:
                self.update_status(f"已重做: {record['action']}")
    
    def update_status(self, message: str):
        """更新状态（子类实现）"""
        if hasattr(self, 'status'):
            self.status.set(message)


# ==================== 4. API Key 加密存储 ====================

class SecureKeyStorage:
    """安全密钥存储"""
    
    def __init__(self, key_file: str = "config/.keyfile"):
        self.key_file = Path(key_file)
        self._fernet = None
        self._init_encryption()
    
    def _init_encryption(self):
        """初始化加密"""
        # 如果 cryptography 未安装，跳过加密
        if not HAS_CRYPTOGRAPHY:
            print("cryptography 未安装，API Key 将以明文存储")
            self._fernet = None
            return
        
        try:
            if self.key_file.exists():
                with open(self.key_file, 'rb') as f:
                    key = f.read()
            else:
                key = Fernet.generate_key()
                self.key_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.key_file, 'wb') as f:
                    f.write(key)
                # 设置文件权限（仅owner可读写）
                try:
                    import stat
                    os.chmod(self.key_file, stat.S_IRUSR | stat.S_IWUSR)
                except Exception:
                    pass
            
            self._fernet = Fernet(key)
        except Exception as e:
            print(f"加密初始化失败: {e}")
            self._fernet = None
    
    def encrypt(self, data: str) -> str:
        """加密数据"""
        if self._fernet and data:
            try:
                return self._fernet.encrypt(data.encode()).decode()
            except Exception:
                pass
        return data
    
    def decrypt(self, data: str) -> str:
        """解密数据"""
        if self._fernet and data:
            try:
                return self._fernet.decrypt(data.encode()).decode()
            except Exception:
                pass
        return data


class SecureConfigMixin:
    """安全配置Mixin - 提供加密API Key存储"""
    
    def _init_secure_storage(self):
        """初始化安全存储"""
        try:
            self.secure_storage = SecureKeyStorage()
        except ImportError:
            # cryptography未安装时使用简单的base64编码
            self.secure_storage = None
    
    def save_encrypted_config(self, config: Dict, path: str = "config/api_config.json"):
        """保存加密配置"""
        config_path = Path(path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 加密敏感字段
        encrypted_config = dict(config)
        if self.secure_storage:
            for key in ['api_key', 'key', 'secret']:
                if key in encrypted_config and encrypted_config[key]:
                    encrypted_config[key] = self.secure_storage.encrypt(encrypted_config[key])
                    encrypted_config[f'{key}_encrypted'] = True
        
        with open(config_path, 'w') as f:
            json.dump(encrypted_config, f, indent=2)
    
    def load_encrypted_config(self, path: str = "config/api_config.json") -> Dict:
        """加载并解密配置"""
        config_path = Path(path)
        if not config_path.exists():
            return {}
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # 解密敏感字段
        if self.secure_storage:
            for key in ['api_key', 'key', 'secret']:
                if config.get(f'{key}_encrypted') and key in config:
                    config[key] = self.secure_storage.decrypt(config[key])
        
        return config


# ==================== 5. API状态监控 ====================

class APIStatusMonitor:
    """API状态监控器"""
    
    def __init__(self):
        self.status_cache: Dict[str, Dict] = {}
        self.check_interval = 60  # 秒
        self._running = False
        self._thread = None
    
    def check_api(self, name: str, base_url: str, api_key: str, model: str = None) -> Dict:
        """检查单个API状态"""
        from src.utils.text import try_chat_api
        
        start_time = time.time()
        try:
            ok, msg = try_chat_api(api_key, base_url, model or "test")
            latency = (time.time() - start_time) * 1000
            
            status = {
                'name': name,
                'status': 'online' if ok else 'error',
                'message': msg,
                'latency': latency,
                'last_check': datetime.now().isoformat()
            }
        except Exception as e:
            status = {
                'name': name,
                'status': 'error',
                'message': str(e),
                'latency': -1,
                'last_check': datetime.now().isoformat()
            }
        
        self.status_cache[name] = status
        return status
    
    def get_status(self, name: str) -> Optional[Dict]:
        """获取缓存的状态"""
        return self.status_cache.get(name)
    
    def get_all_status(self) -> Dict[str, Dict]:
        """获取所有状态"""
        return dict(self.status_cache)


class APIMonitorMixin:
    """API监控Mixin"""
    
    def _init_api_monitor(self):
        """初始化API监控"""
        self.api_monitor = APIStatusMonitor()
    
    def check_api_status(self, name: str, base_url: str, api_key: str, model: str = None):
        """检查API状态（异步）"""
        def check():
            return self.api_monitor.check_api(name, base_url, api_key, model)
        
        def on_complete(result):
            self._update_api_status_display(result)
        
        if hasattr(self, 'run_with_progress'):
            thread = threading.Thread(target=lambda: on_complete(check()), daemon=True)
            thread.start()
        else:
            result = check()
            self._update_api_status_display(result)
    
    def _update_api_status_display(self, status: Dict):
        """更新API状态显示"""
        # 子类可以重写此方法
        pass


# ==================== 6. 配置导入导出 ====================

class ConfigExportMixin:
    """配置导入导出Mixin"""
    
    def export_config(self, include_keys: bool = False):
        """导出配置"""
        config = {
            'version': '2.0',
            'export_time': datetime.now().isoformat(),
            'settings': {
                'temperature': self.temperature.get() if hasattr(self, 'temperature') else 0.7,
                'top_k': self.top_k.get() if hasattr(self, 'top_k') else 6,
                'target_chars': self.target_chars.get() if hasattr(self, 'target_chars') else 1800,
            },
            'api_providers': {},
            'img_api_providers': {},
        }
        
        # 导出API配置
        if hasattr(self, 'api_providers'):
            for name, provider in self.api_providers.items():
                config['api_providers'][name] = {
                    'base_url': provider.get('base_url', ''),
                    'models': provider.get('models', []),
                }
                if include_keys:
                    config['api_providers'][name]['key'] = provider.get('key', '')
        
        if hasattr(self, 'img_api_providers'):
            for name, provider in self.img_api_providers.items():
                config['img_api_providers'][name] = {
                    'base_url': provider.get('base_url', ''),
                    'models': provider.get('models', []),
                }
                if include_keys:
                    config['img_api_providers'][name]['key'] = provider.get('key', '')
        
        # 选择保存位置
        file_path = filedialog.asksaveasfilename(
            title="导出配置",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            initialname=f"config_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("成功", f"配置已导出到:\n{file_path}")
    
    def import_config(self):
        """导入配置"""
        file_path = filedialog.askopenfilename(
            title="导入配置",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 验证配置版本
            if config.get('version', '1.0') < '2.0':
                messagebox.showwarning("警告", "配置文件版本较旧，部分设置可能无法导入")
            
            # 导入设置
            if 'settings' in config:
                settings = config['settings']
                if hasattr(self, 'temperature'):
                    self.temperature.set(settings.get('temperature', 0.7))
                if hasattr(self, 'top_k'):
                    self.top_k.set(settings.get('top_k', 6))
                if hasattr(self, 'target_chars'):
                    self.target_chars.set(settings.get('target_chars', 1800))
            
            # 导入API配置
            if 'api_providers' in config and hasattr(self, 'api_providers'):
                for name, provider in config['api_providers'].items():
                    if name in self.api_providers:
                        if provider.get('base_url'):
                            self.api_providers[name]['base_url'] = provider['base_url']
                        if provider.get('key'):
                            self.api_providers[name]['key'] = provider['key']
            
            if 'img_api_providers' in config and hasattr(self, 'img_api_providers'):
                for name, provider in config['img_api_providers'].items():
                    if name in self.img_api_providers:
                        if provider.get('base_url'):
                            self.img_api_providers[name]['base_url'] = provider['base_url']
                        if provider.get('key'):
                            self.img_api_providers[name]['key'] = provider['key']
            
            messagebox.showinfo("成功", "配置导入成功！")
            
            # 刷新界面
            if hasattr(self, '_load_settings_values'):
                self._load_settings_values()
                
        except Exception as e:
            messagebox.showerror("错误", f"导入配置失败:\n{str(e)}")


# ==================== 7. 缓存系统 ====================

class CacheManager:
    """缓存管理器"""
    
    def __init__(self, cache_dir: str = "cache", max_size_mb: int = 100):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size = max_size_mb * 1024 * 1024
        self.index_file = self.cache_dir / "index.json"
        self._load_index()
    
    def _load_index(self):
        """加载缓存索引"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    self.index = json.load(f)
            except Exception:
                self.index = {}
        else:
            self.index = {}
    
    def _save_index(self):
        """保存缓存索引"""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f)
    
    def _get_key(self, key: str) -> str:
        """生成缓存键"""
        return hashlib.md5(key.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        cache_key = self._get_key(key)
        if cache_key in self.index:
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    # 更新访问时间
                    self.index[cache_key]['last_access'] = time.time()
                    self._save_index()
                    return data.get('value')
                except Exception:
                    pass
        return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """设置缓存"""
        cache_key = self._get_key(key)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        data = {
            'key': key,
            'value': value,
            'created': time.time(),
            'ttl': ttl
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        
        self.index[cache_key] = {
            'key': key,
            'created': time.time(),
            'last_access': time.time(),
            'ttl': ttl,
            'size': cache_file.stat().st_size
        }
        self._save_index()
        
        # 检查缓存大小
        self._cleanup_if_needed()
    
    def delete(self, key: str):
        """删除缓存"""
        cache_key = self._get_key(key)
        if cache_key in self.index:
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                cache_file.unlink()
            del self.index[cache_key]
            self._save_index()
    
    def clear(self):
        """清除所有缓存"""
        for cache_key in list(self.index.keys()):
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                cache_file.unlink()
        self.index = {}
        self._save_index()
    
    def _cleanup_if_needed(self):
        """必要时清理缓存"""
        total_size = sum(item.get('size', 0) for item in self.index.values())
        
        if total_size > self.max_size:
            # 按访问时间排序，删除最旧的
            sorted_items = sorted(
                self.index.items(),
                key=lambda x: x[1].get('last_access', 0)
            )
            
            while total_size > self.max_size * 0.8 and sorted_items:
                cache_key, item = sorted_items.pop(0)
                self.delete(item['key'])
                total_size -= item.get('size', 0)


class CacheMixin:
    """缓存Mixin"""
    
    def _init_cache(self):
        """初始化缓存"""
        self.cache = CacheManager()
    
    def get_cached(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        if hasattr(self, 'cache'):
            return self.cache.get(key)
        return None
    
    def set_cached(self, key: str, value: Any, ttl: int = 3600):
        """设置缓存数据"""
        if hasattr(self, 'cache'):
            self.cache.set(key, value, ttl)
    
    def clear_cache(self):
        """清除缓存"""
        if hasattr(self, 'cache'):
            self.cache.clear()
            messagebox.showinfo("成功", "缓存已清除")


# ==================== 8. 项目导入导出 ====================

class ProjectExportMixin:
    """项目导入导出Mixin"""
    
    def export_project(self):
        """导出当前项目为zip包"""
        import zipfile
        import shutil
        
        if not hasattr(self, 'current_project') or not self.current_project:
            messagebox.showwarning("提示", "请先选择一个项目")
            return
        
        project = self.current_project
        project_dir = Path("projects") / project.get('name', 'unnamed')
        
        if not project_dir.exists():
            messagebox.showerror("错误", "项目目录不存在")
            return
        
        # 选择导出位置
        file_path = filedialog.asksaveasfilename(
            title="导出项目",
            defaultextension=".zip",
            filetypes=[("ZIP文件", "*.zip"), ("所有文件", "*.*")],
            initialname=f"{project.get('name', 'project')}_{datetime.now().strftime('%Y%m%d')}.zip"
        )
        
        if not file_path:
            return
        
        try:
            # 创建zip包
            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in project_dir.rglob('*'):
                    if file.is_file():
                        arcname = file.relative_to(project_dir.parent)
                        zipf.write(file, arcname)
                
                # 添加项目元数据
                metadata = {
                    'name': project.get('name'),
                    'export_time': datetime.now().isoformat(),
                    'version': '2.0'
                }
                zipf.writestr('metadata.json', json.dumps(metadata, indent=2))
            
            messagebox.showinfo("成功", f"项目已导出到:\n{file_path}")
            
        except Exception as e:
            messagebox.showerror("错误", f"导出项目失败:\n{str(e)}")
    
    def import_project(self):
        """从zip包导入项目"""
        import zipfile
        
        file_path = filedialog.askopenfilename(
            title="导入项目",
            filetypes=[("ZIP文件", "*.zip"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zipf:
                # 读取元数据
                try:
                    metadata = json.loads(zipf.read('metadata.json'))
                    project_name = metadata.get('name', 'imported_project')
                except Exception:
                    project_name = Path(file_path).stem
                
                # 检查是否已存在同名项目
                target_dir = Path("projects") / project_name
                if target_dir.exists():
                    if not messagebox.askyesno("确认", f"项目 '{project_name}' 已存在，是否覆盖？"):
                        return
                
                # 解压
                target_dir.mkdir(parents=True, exist_ok=True)
                for file_info in zipf.infolist():
                    if file_info.filename != 'metadata.json':
                        # 调整路径
                        parts = Path(file_info.filename).parts
                        if len(parts) > 1:
                            new_path = target_dir / '/'.join(parts[1:])
                        else:
                            new_path = target_dir / file_info.filename
                        
                        if file_info.is_dir():
                            new_path.mkdir(parents=True, exist_ok=True)
                        else:
                            new_path.parent.mkdir(parents=True, exist_ok=True)
                            with open(new_path, 'wb') as f:
                                f.write(zipf.read(file_info.filename))
            
            messagebox.showinfo("成功", f"项目 '{project_name}' 导入成功！")
            
            # 刷新项目列表
            if hasattr(self, 'refresh_projects'):
                self.refresh_projects()
            
        except Exception as e:
            messagebox.showerror("错误", f"导入项目失败:\n{str(e)}")


# ==================== 综合增强Mixin ====================

class EnhancementsMixin(ProgressMixin, ShortcutsMixin, HistoryMixin, 
                        SecureConfigMixin, APIMonitorMixin, ConfigExportMixin,
                        CacheMixin, ProjectExportMixin):
    """综合增强Mixin - 整合所有增强功能"""
    
    def _init_enhancements(self):
        """初始化所有增强功能"""
        # 初始化各个组件
        self._init_history()
        self._init_secure_storage()
        self._init_api_monitor()
        self._init_cache()
        
        # 设置快捷键（需要在UI构建后调用）
        self.after(100, self._setup_shortcuts)
    
    def _refresh_theme(self):
        """刷新主题（在主题切换后调用）"""
        # 子类可以重写此方法实现主题刷新
        messagebox.showinfo("提示", "主题已切换，部分更改需要重启应用后生效")
