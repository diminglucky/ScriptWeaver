#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动现代化UI版本 - ScriptWeaver
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

# 设置Windows控制台UTF-8编码
if sys.platform == "win32":
    import io
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 禁用不必要的警告
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("USE_TF", "0")

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent
os.chdir(project_root)
sys.path.insert(0, str(project_root))


def _can_import_tkinter(py_bin: str) -> bool:
    """Lightweight probe to avoid hard-failing on broken/partial runtimes."""
    try:
        probe = subprocess.run(
            [
                py_bin,
                "-c",
                "import tkinter",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=8,
            check=False,
        )
    except Exception:
        return False
    return probe.returncode == 0


def _find_safe_macos_python() -> str:
    """Prefer Python 3.11 runtimes on macOS for Tk stability."""
    candidates = []
    env_override = os.getenv("STORY_PYTHON", "").strip()
    if env_override:
        candidates.append(env_override)
    candidates.extend(
        [
            "/opt/homebrew/bin/python3.11",
            "/usr/local/bin/python3.11",
        ]
    )
    which_311 = shutil.which("python3.11")
    if which_311:
        candidates.append(which_311)

    seen = set()
    current_exe = str(Path(sys.executable).resolve())
    for raw in candidates:
        if not raw:
            continue
        resolved = str(Path(raw).expanduser())
        if not Path(resolved).exists():
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        try:
            resolved_real = str(Path(resolved).resolve())
        except Exception:
            resolved_real = resolved
        if resolved_real == current_exe:
            continue
        if _can_import_tkinter(resolved):
            return resolved
    return ""


def _maybe_reexec_safe_python_on_macos() -> None:
    """Avoid known macOS Tk crashes with Python 3.12 by re-execing into 3.11."""
    if sys.platform != "darwin":
        return
    if os.getenv("STORY_LAUNCHER_REEXEC_DONE", "") == "1":
        return
    # Observed unstable Tk runtime combinations on macOS with 3.12
    if sys.version_info < (3, 12):
        return

    safe_py = _find_safe_macos_python()
    if not safe_py:
        print(
            "[WARN] 检测到 Python 3.12，且未找到可用的 Python 3.11(Tk) 运行时；"
            "可能出现窗口闪退。建议安装/指定 Python 3.11。"
        )
        return

    print(f"[INFO] macOS 启动保护：从 Python {sys.version.split()[0]} 切换到 {safe_py}")
    env = os.environ.copy()
    env["STORY_LAUNCHER_REEXEC_DONE"] = "1"
    os.execve(safe_py, [safe_py, str(Path(__file__).resolve()), *sys.argv[1:]], env)

def main():
    """主函数"""
    _maybe_reexec_safe_python_on_macos()
    try:
        # 尝试导入现代化UI
        from src.gui.modern_app import ModernApp
        print("[INFO] 启动 ScriptWeaver (现代化UI版本)...")
        app = ModernApp()
        app.mainloop()
    except Exception as e:
        print(f"[WARN] 无法加载现代化UI: {e}")
        print("[INFO] 正在回退到经典版本...")
        
        # 回退到经典版本
        from src.gui_app import App
        app = App()
        app.mainloop()

if __name__ == "__main__":
    main()
