"""任务调度配置常量

定义数据文件路径、超时、轮询间隔等配置。
"""

from enum import Enum
from pathlib import Path

# 数据文件目录
DATA_DIR = Path("data")

# 数据文件路径
QUEUE_FILE = DATA_DIR / "queue.json"
SCHEDULED_FILE = DATA_DIR / "scheduled.json"
RUNNING_FILE = DATA_DIR / "running.json"
COMPLETED_FILE = DATA_DIR / "completed.json"
FAILED_FILE = DATA_DIR / "failed.json"

# 默认超时时间（毫秒）
DEFAULT_TIMEOUT = 600000  # 10 分钟

# 最小/最大超时时间（毫秒）
MIN_TIMEOUT = 1000  # 1 秒
MAX_TIMEOUT = 3600000  # 1 小时

# 轮询间隔（秒）
POLL_INTERVAL = 10

# 最大重试次数
MAX_RETRIES = 2

# 历史记录最大数量
MAX_HISTORY = 1000

# 分页默认值
DEFAULT_PAGE = 1
DEFAULT_LIMIT = 20
MAX_LIMIT = 100

# 文件锁配置
LOCK_TIMEOUT = 5  # 锁获取超时时间（秒）
LOCK_RETRY_INTERVAL = 0.1  # 重试间隔（秒）
MAX_LOCK_RETRIES = 50  # 最大重试次数

# 调度器状态
class SchedulerStatus(str, Enum):
    """调度器状态"""

    STOPPED = "stopped"  # 已停止
    RUNNING = "running"  # 运行中
    STARTING = "starting"  # 启动中
    STOPPING = "stopping"  # 停止中


def get_data_dir() -> Path:
    """获取数据目录路径"""
    return DATA_DIR


def ensure_data_dir() -> None:
    """确保数据目录存在"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
