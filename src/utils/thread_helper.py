"""线程安全工具"""

from __future__ import annotations

import threading
from typing import Callable, Any, Optional, TypeVar
import tkinter as tk

T = TypeVar('T')


class ThreadSafeExecutor:
    """线程安全的任务执行器
    
    用于在后台线程执行耗时任务，并在主线程安全地更新UI
    """
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self._lock = threading.Lock()
        self._active_threads = []
    
    def run_async(
        self,
        task: Callable[[], T],
        on_success: Optional[Callable[[T], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        on_finally: Optional[Callable[[], None]] = None
    ) -> threading.Thread:
        """在后台线程执行任务，在主线程处理结果
        
        Args:
            task: 要执行的任务函数
            on_success: 成功回调（在主线程执行）
            on_error: 错误回调（在主线程执行）
            on_finally: 最终回调（在主线程执行）
        
        Returns:
            创建的线程对象
        
        Example:
            executor.run_async(
                task=lambda: expensive_operation(),
                on_success=lambda result: self.display_result(result),
                on_error=lambda e: messagebox.showerror("错误", str(e))
            )
        """
        def worker():
            try:
                result = task()
                if on_success:
                    self.root.after(0, lambda: on_success(result))
            except Exception as e:
                if on_error:
                    self.root.after(0, lambda: on_error(e))
            finally:
                if on_finally:
                    self.root.after(0, on_finally)
                # 清理线程引用
                with self._lock:
                    if thread in self._active_threads:
                        self._active_threads.remove(thread)
        
        thread = threading.Thread(target=worker, daemon=True)
        
        with self._lock:
            self._active_threads.append(thread)
        
        thread.start()
        return thread
    
    def wait_all(self, timeout: Optional[float] = None):
        """等待所有活动线程完成"""
        with self._lock:
            threads = list(self._active_threads)
        
        for thread in threads:
            thread.join(timeout=timeout)
    
    def active_count(self) -> int:
        """获取活动线程数量"""
        with self._lock:
            return len(self._active_threads)


def run_in_thread(func: Callable) -> Callable:
    """装饰器：在后台线程执行函数
    
    注意：被装饰的函数不应直接操作UI
    
    Example:
        @run_in_thread
        def load_data(self):
            data = expensive_operation()
            # 使用 after() 更新UI
            self.after(0, lambda: self.update_ui(data))
    """
    def wrapper(*args, **kwargs):
        thread = threading.Thread(
            target=lambda: func(*args, **kwargs),
            daemon=True
        )
        thread.start()
        return thread
    return wrapper
