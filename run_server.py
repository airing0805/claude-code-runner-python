"""启动脚本"""
import logging
import os
import signal
import socket
import site
import subprocess
import sys
from pathlib import Path

# 配置日志输出到控制台
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)
logger = logging.getLogger(__name__)


def is_port_in_use(port: int) -> bool:
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return False
        except OSError:
            return True


def kill_process_on_port(port: int) -> bool:
    """关闭占用指定端口的进程"""
    killed = False
    killed_pids = set()

    try:
        # 使用 PowerShell 的 Get-NetTCPConnection 查找占用端口的进程
        # 这比 netstat 更可靠
        cmd = [
            "powershell",
            "-Command",
            f"Get-NetTCPConnection -LocalPort {port} -State Listen | "
            f"Select-Object -ExpandProperty OwningProcess | "
            f"Get-Unique",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.stdout.strip():
            pids = []
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if line.isdigit():
                    pids.append(int(line))

            # 终止所有占用该端口的进程
            for pid in pids:
                if pid == 0:
                    continue
                if pid in killed_pids:
                    continue

                # 获取进程名称用于日志
                try:
                    name_result = subprocess.run(
                        ["powershell", "-Command",
                         f"(Get-Process -Id {pid} -ErrorAction SilentlyContinue).ProcessName"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    process_name = name_result.stdout.strip() or f"PID:{pid}"
                except Exception:
                    process_name = f"PID:{pid}"

                # 终止进程
                kill_result = subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if kill_result.returncode == 0:
                    logger.info(f"已关闭占用端口 {port} 的进程: {process_name} (PID: {pid})")
                    killed = True
                    killed_pids.add(pid)
                else:
                    logger.warning(f"无法关闭进程 {process_name} (PID: {pid}): {kill_result.stderr or kill_result.stdout}")

    except subprocess.TimeoutExpired:
        logger.error(f"查找占用端口 {port} 的进程时超时")
    except Exception as e:
        logger.error(f"关闭端口 {port} 进程时出错: {e}")

    return killed


def ensure_port_available(port: int, max_retries: int = 3) -> None:
    """
    确保端口可用，如果被占用则关闭占用进程

    Args:
        port: 端口号
        max_retries: 最大重试次数
    """
    if is_port_in_use(port):
        logger.info(f"端口 {port} 已被占用，正在关闭...")

        for attempt in range(1, max_retries + 1):
            if kill_process_on_port(port):
                # 等待端口释放
                import time
                time.sleep(1)

                if not is_port_in_use(port):
                    logger.info(f"端口 {port} 已释放")
                    return

                if attempt < max_retries:
                    logger.warning(f"端口 {port} 仍然被占用，尝试第 {attempt + 1} 次关闭...")
                else:
                    logger.error(f"端口 {port} 在 {max_retries} 次尝试后仍然被占用")
                    raise RuntimeError(f"无法释放端口 {port}，请手动检查并关闭占用进程")
            else:
                logger.warning(f"第 {attempt} 次尝试关闭端口 {port} 失败")
                if attempt < max_retries:
                    import time
                    time.sleep(1)


# 添加 venv site-packages
venv_site = Path(__file__).parent / ".venv" / "Lib" / "site-packages"
site.addsitedir(str(venv_site))

# 启动服务
import uvicorn
from app.main import app

if __name__ == "__main__":
    # 确保端口可用
    ensure_port_available(8000)

    logger.info("启动 Claude Code Runner 服务...")
    logger.info("监听地址: 0.0.0.0:8000")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        log_config=None,  # 使用自定义日志配置
        access_log=True,  # 启用访问日志
    )
