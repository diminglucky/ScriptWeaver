"""
测试配置文件
"""
import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 测试配置
@pytest.fixture(scope="session")
def project_root_path():
    """返回项目根目录路径"""
    return project_root

@pytest.fixture(scope="session")
def test_data_dir(project_root_path):
    """返回测试数据目录"""
    test_dir = project_root_path / "tests" / "data"
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir

@pytest.fixture(scope="session")
def test_projects_dir(project_root_path):
    """返回测试项目目录"""
    test_dir = project_root_path / "tests" / "test_projects"
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir

@pytest.fixture(autouse=True)
def setup_logging():
    """为每个测试设置日志"""
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )

