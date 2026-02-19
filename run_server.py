"""启动脚本"""
import site
import sys
from pathlib import Path

# 添加 venv site-packages
venv_site = Path(__file__).parent / ".venv" / "Lib" / "site-packages"
site.addsitedir(str(venv_site))

# 启动服务
import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
