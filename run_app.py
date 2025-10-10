#!/usr/bin/env python3
"""
启动脚本 - 创作知乎故事应用
"""
import os
import sys
from pathlib import Path

# 禁用Transformers的TensorFlow集成，避免Keras兼容性问题
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("USE_TF", "0")

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入并运行GUI应用
if __name__ == "__main__":
    from src.gui_app import App
    app = App()
    app.mainloop()

