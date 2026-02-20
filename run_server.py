"""启动脚本"""
import os
import signal
import socket
import site
import subprocess
import sys
from pathlib import Path


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
    try:
        # 使用 netstat 查找占用端口的进程 PID
        result = subprocess.run(
            f'netstat -ano | findstr "127.0.0.1:{port}" | findstr "LISTENING"',
            shell=True,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            # 提取 PID（最后一列）
            for line in result.stdout.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 5:
                    pid = int(parts[-1])
                    if pid != 0:
                        # 终止进程
                        subprocess.run(
                            ["taskkill", "/F", "/PID", str(pid)],
                            capture_output=True,
                        )
                        print(f"已关闭占用端口 {port} 的进程 (PID: {pid})")
                        return True
        return False
    except Exception as e:
        print(f"关闭端口 {port} 进程时出错: {e}")
        return False


def ensure_port_available(port: int) -> None:
    """确保端口可用，如果被占用则关闭占用进程"""
    if is_port_in_use(port):
        print(f"端口 {port} 已被占用，正在关闭...")
        if kill_process_on_port(port):
            # 等待端口释放
            import time
            time.sleep(1)
            if is_port_in_use(port):
                print(f"警告: 端口 {port} 仍然被占用")


# 添加 venv site-packages
venv_site = Path(__file__).parent / ".venv" / "Lib" / "site-packages"
site.addsitedir(str(venv_site))

# 启动服务
import uvicorn
from app.main import app

if __name__ == "__main__":
    # 确保端口可用
    ensure_port_available(8000)

    uvicorn.run(app, host="0.0.0.0", port=8000)
