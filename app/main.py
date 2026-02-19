"""FastAPI 主应用 - 提供 Web 界面和 API"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import api_keys, agents, auth, claude, mcp, session, skills, status, task

# 加载环境变量
load_dotenv()

# 配置
WORKING_DIR = os.getenv("WORKING_DIR", ".")
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

# 路径（前端文件已迁移到 web 目录）
BASE_DIR = Path(__file__).resolve().parent.parent  # 项目根目录
TEMPLATES_DIR = BASE_DIR / "web" / "templates"
STATIC_DIR = BASE_DIR / "web" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print(f"[INFO] Claude Code Runner 启动")
    print(f"[INFO] 工作目录: {WORKING_DIR}")
    yield
    print("[INFO] Claude Code Runner 关闭")


app = FastAPI(
    title="Claude Code Runner",
    description="通过 Web API 调用 Claude Code 执行任务",
    version="0.2.0",
    lifespan=lifespan,
)

# 挂载静态文件和模板
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# 注册路由
app.include_router(auth.router)
app.include_router(task.router)
app.include_router(session.router)
app.include_router(status.router)
app.include_router(api_keys.router)
app.include_router(claude.router)
app.include_router(mcp.router)
app.include_router(agents.router)
app.include_router(skills.router)


# ============== 页面路由 ==============

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页"""
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "working_dir": WORKING_DIR,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
