"""
异步处理和批量生成优化模块
"""

import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import gc


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """任务定义"""
    id: str
    name: str
    func: Callable
    args: tuple = ()
    kwargs: dict = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = None
    progress: float = 0.0
    
    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}


class TaskQueue:
    """任务队列管理器"""
    
    def __init__(self, max_workers: int = 2):
        self.max_workers = max_workers
        self.tasks: Dict[str, Task] = {}
        self.queue = queue.Queue()
        self.workers: List[threading.Thread] = []
        self.running = False
        self.lock = threading.Lock()
        self._callbacks: Dict[str, List[Callable]] = {
            'on_task_start': [],
            'on_task_complete': [],
            'on_task_error': [],
            'on_progress': [],
            'on_queue_empty': [],
        }
    
    def add_task(self, task: Task) -> str:
        """添加任务到队列"""
        with self.lock:
            self.tasks[task.id] = task
        self.queue.put(task.id)
        return task.id
    
    def start(self):
        """启动工作线程"""
        if self.running:
            return
        
        self.running = True
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker, daemon=True)
            worker.start()
            self.workers.append(worker)
    
    def stop(self):
        """停止队列"""
        self.running = False
        # 发送停止信号
        for _ in self.workers:
            self.queue.put(None)
    
    def _worker(self):
        """工作线程"""
        while self.running:
            try:
                task_id = self.queue.get(timeout=1)
                
                if task_id is None:
                    break
                
                task = self.tasks.get(task_id)
                if not task:
                    continue
                
                if task.status == TaskStatus.CANCELLED:
                    continue
                
                # 开始执行
                task.status = TaskStatus.RUNNING
                self._notify('on_task_start', task)
                
                try:
                    # 执行任务
                    result = task.func(*task.args, **task.kwargs)
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                    task.progress = 100.0
                    self._notify('on_task_complete', task)
                except Exception as e:
                    task.error = str(e)
                    task.status = TaskStatus.FAILED
                    self._notify('on_task_error', task)
                
                # 检查队列是否为空
                if self.queue.empty():
                    self._notify('on_queue_empty', None)
                    
            except queue.Empty:
                continue
    
    def cancel_task(self, task_id: str):
        """取消任务"""
        task = self.tasks.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
    
    def cancel_all(self):
        """取消所有任务"""
        with self.lock:
            for task in self.tasks.values():
                if task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.CANCELLED
    
    def get_status(self) -> Dict:
        """获取队列状态"""
        with self.lock:
            total = len(self.tasks)
            pending = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING)
            running = sum(1 for t in self.tasks.values() if t.status == TaskStatus.RUNNING)
            completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
            failed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)
            
        return {
            'total': total,
            'pending': pending,
            'running': running,
            'completed': completed,
            'failed': failed,
            'queue_size': self.queue.qsize(),
        }
    
    def register_callback(self, event: str, callback: Callable):
        """注册回调"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def _notify(self, event: str, data):
        """通知回调"""
        for callback in self._callbacks.get(event, []):
            try:
                callback(data)
            except Exception:
                pass


class BatchGeneratorDialog:
    """批量生成对话框"""
    
    def __init__(self, parent, sections: List[Dict], generate_func: Callable):
        self.parent = parent
        self.sections = sections
        self.generate_func = generate_func
        self.cancelled = False
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("批量生成")
        self.dialog.geometry("600x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.dialog.configure(bg="#1e1e1e")
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self._build_ui()
        
        # 任务队列
        self.task_queue = TaskQueue(max_workers=1)  # 串行执行
        self.task_queue.register_callback('on_task_complete', self._on_task_complete)
        self.task_queue.register_callback('on_task_error', self._on_task_error)
        self.task_queue.register_callback('on_queue_empty', self._on_all_complete)
    
    def _build_ui(self):
        """构建UI"""
        # 标题
        tk.Label(self.dialog, text="📝 批量生成", bg="#1e1e1e", fg="#ffffff",
                 font=("", 16, "bold")).pack(pady=20)
        
        # 进度信息
        info_frame = tk.Frame(self.dialog, bg="#2b2b2b")
        info_frame.pack(fill="x", padx=20, pady=10)
        
        self.progress_label = tk.Label(info_frame, text="准备中...", bg="#2b2b2b", fg="#ffffff",
                                        font=("", 12))
        self.progress_label.pack(pady=10)
        
        # 总进度条
        self.total_progress = ttk.Progressbar(info_frame, mode='determinate', length=500)
        self.total_progress.pack(pady=5)
        
        self.total_percent = tk.Label(info_frame, text="0%", bg="#2b2b2b", fg="#9CA3AF")
        self.total_percent.pack(pady=5)
        
        # 当前任务
        self.current_label = tk.Label(info_frame, text="", bg="#2b2b2b", fg="#6B7280")
        self.current_label.pack(pady=5)
        
        # 任务列表
        list_frame = tk.Frame(self.dialog, bg="#1e1e1e")
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        scroll_y = tk.Scrollbar(list_frame, orient="vertical")
        scroll_y.pack(side="right", fill="y")
        
        self.task_listbox = tk.Listbox(list_frame, bg="#2b2b2b", fg="#d4d4d4",
                                        selectbackground="#3B82F6", selectforeground="#ffffff",
                                        yscrollcommand=scroll_y.set, font=("", 10))
        self.task_listbox.pack(fill="both", expand=True)
        scroll_y.config(command=self.task_listbox.yview)
        
        # 填充任务列表
        for i, section in enumerate(self.sections):
            title = section.get('title', f'章节 {i+1}')
            self.task_listbox.insert(tk.END, f"⏳ {title}")
        
        # 按钮
        btn_frame = tk.Frame(self.dialog, bg="#1e1e1e")
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        self.start_btn = tk.Button(btn_frame, text="▶️ 开始生成", command=self._start_generation,
                                    bg="#10B981", fg="#ffffff", relief=tk.FLAT, cursor="hand2",
                                    padx=20, pady=8)
        self.start_btn.pack(side="left", padx=5)
        
        self.cancel_btn = tk.Button(btn_frame, text="⏹️ 取消", command=self._cancel_generation,
                                     bg="#EF4444", fg="#ffffff", relief=tk.FLAT, cursor="hand2",
                                     padx=20, pady=8, state="disabled")
        self.cancel_btn.pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="关闭", command=self._on_close,
                  bg="#4B5563", fg="#ffffff", relief=tk.FLAT, cursor="hand2",
                  padx=20, pady=8).pack(side="right", padx=5)
    
    def _start_generation(self):
        """开始生成"""
        self.start_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.cancelled = False
        
        # 添加所有任务到队列
        for i, section in enumerate(self.sections):
            task = Task(
                id=f"section_{i}",
                name=section.get('title', f'章节 {i+1}'),
                func=self.generate_func,
                args=(section, i),
            )
            self.task_queue.add_task(task)
        
        # 启动队列
        self.task_queue.start()
        self._update_display()
    
    def _cancel_generation(self):
        """取消生成"""
        self.cancelled = True
        self.task_queue.cancel_all()
        self.progress_label.config(text="已取消")
        self.cancel_btn.config(state="disabled")
        self.start_btn.config(state="normal")
    
    def _on_task_complete(self, task: Task):
        """任务完成回调"""
        self.dialog.after(0, lambda: self._update_task_display(task, "✅"))
    
    def _on_task_error(self, task: Task):
        """任务错误回调"""
        self.dialog.after(0, lambda: self._update_task_display(task, "❌"))
    
    def _on_all_complete(self, _):
        """所有任务完成"""
        self.dialog.after(0, self._on_complete)
    
    def _update_task_display(self, task: Task, icon: str):
        """更新任务显示"""
        try:
            # 找到对应的列表项并更新
            for i, section in enumerate(self.sections):
                if f"section_{i}" == task.id:
                    title = section.get('title', f'章节 {i+1}')
                    self.task_listbox.delete(i)
                    self.task_listbox.insert(i, f"{icon} {title}")
                    break
            
            self._update_display()
        except Exception:
            pass
    
    def _update_display(self):
        """更新进度显示"""
        status = self.task_queue.get_status()
        total = status['total']
        completed = status['completed'] + status['failed']
        
        if total > 0:
            progress = (completed / total) * 100
            self.total_progress['value'] = progress
            self.total_percent.config(text=f"{int(progress)}%")
            self.progress_label.config(text=f"已完成 {completed}/{total} 个章节")
            
            # 当前任务
            for task in self.task_queue.tasks.values():
                if task.status == TaskStatus.RUNNING:
                    self.current_label.config(text=f"正在生成: {task.name}")
                    break
    
    def _on_complete(self):
        """完成回调"""
        status = self.task_queue.get_status()
        self.progress_label.config(text=f"完成! 成功: {status['completed']}, 失败: {status['failed']}")
        self.cancel_btn.config(state="disabled")
        self.start_btn.config(state="normal")
        
        if status['failed'] == 0:
            messagebox.showinfo("完成", f"已成功生成 {status['completed']} 个章节!")
    
    def _on_close(self):
        """关闭对话框"""
        if self.task_queue.running:
            if messagebox.askyesno("确认", "还有任务正在执行，确定要关闭吗？"):
                self.task_queue.stop()
                self.dialog.destroy()
        else:
            self.dialog.destroy()


class AsyncLoaderMixin:
    """异步加载Mixin"""
    
    def _init_async_loader(self):
        """初始化异步加载器"""
        self._loading_tasks = {}
    
    def load_async(self, key: str, func: Callable, callback: Callable = None, 
                   error_callback: Callable = None):
        """异步加载数据"""
        def worker():
            try:
                result = func()
                if callback:
                    self.after(0, lambda: callback(result))
            except Exception as e:
                if error_callback:
                    self.after(0, lambda: error_callback(e))
        
        thread = threading.Thread(target=worker, daemon=True)
        self._loading_tasks[key] = thread
        thread.start()
    
    def is_loading(self, key: str) -> bool:
        """检查是否正在加载"""
        thread = self._loading_tasks.get(key)
        return thread and thread.is_alive()


class MemoryOptimizer:
    """内存优化工具"""
    
    @staticmethod
    def cleanup():
        """清理内存"""
        gc.collect()
    
    @staticmethod
    def get_memory_usage() -> Dict:
        """获取内存使用情况"""
        import sys
        
        # 获取所有对象的大致大小
        all_objects = gc.get_objects()
        total_objects = len(all_objects)
        
        # 按类型统计
        type_counts = {}
        for obj in all_objects:
            type_name = type(obj).__name__
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        # 排序获取前10
        top_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_objects': total_objects,
            'top_types': top_types,
        }
    
    @staticmethod
    def optimize_images():
        """优化图片资源"""
        # 清理PIL缓存
        try:
            from PIL import Image
            Image.preinit()
        except Exception:
            pass


class BatchGeneratorMixin:
    """批量生成Mixin"""
    
    def open_batch_generator(self, sections: List[Dict] = None):
        """打开批量生成对话框"""
        if sections is None:
            sections = getattr(self, 'parsed_sections', [])
        
        if not sections:
            messagebox.showwarning("提示", "没有可生成的章节")
            return
        
        # 定义生成函数
        def generate_section(section: Dict, index: int):
            if hasattr(self, 'on_generate_single_section'):
                return self.on_generate_single_section(index)
            return None
        
        BatchGeneratorDialog(self, sections, generate_section)


class PerformanceMixin(AsyncLoaderMixin, BatchGeneratorMixin):
    """性能优化综合Mixin"""
    
    def _init_performance(self):
        """初始化性能优化"""
        self._init_async_loader()
        
        # 定期清理内存
        self._start_memory_cleanup()
    
    def _start_memory_cleanup(self, interval_ms: int = 60000):
        """定期清理内存"""
        def cleanup():
            MemoryOptimizer.cleanup()
            self.after(interval_ms, cleanup)
        
        self.after(interval_ms, cleanup)
    
    def show_memory_stats(self):
        """显示内存统计"""
        stats = MemoryOptimizer.get_memory_usage()
        
        msg = f"内存对象统计:\n总对象数: {stats['total_objects']}\n\n按类型排名:\n"
        for type_name, count in stats['top_types']:
            msg += f"  {type_name}: {count}\n"
        
        messagebox.showinfo("内存统计", msg)
