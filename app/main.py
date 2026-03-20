"""FastAPI 主应用 - 提供 Web 界面和 API"""

import asyncio
import os
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import api_keys, admin, agents, auth, claude, files, mcp, scheduler, session, skills, status, task
from app.scheduler.scheduler import start_scheduler

# 配置日志 - 明确输出到控制台
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)

# 创建应用日志记录器
logger = logging.getLogger(__name__)

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


# ============== 会话超时清理 ==============

# 会话清理间隔（秒）- 每 60 秒检查一次
SESSION_CLEANUP_INTERVAL = 60

# 会话超时配置（秒）
# 根据需求文档 `当前会话-会话状态.md` 定义：
# - 单次答案超时: 300 秒 (5 分钟)
# - 会话总超时: 3600 秒 (1 小时)
# - 活动超时: 1800 秒 (30 分钟)
SESSION_MAX_AGE = 3600  # 会话总超时
SESSION_ACTIVITY_TIMEOUT = 1800  # 活动超时
SESSION_ANSWER_TIMEOUT = 300  # 答案等待超时


async def session_cleanup_loop():
    """会话超时清理循环

    根据需求文档 `当前会话-会话状态.md` 第 5.1 节定义的三种超时类型：
    - 单次答案超时: 300 秒 (5 分钟) - 等待用户回答超时
    - 会话总超时: 3600 秒 (1 小时) - 会话创建后的最大生命周期
    - 活动超时: 1800 秒 (30 分钟) - 无活动后的超时
    """
    from app.routers.session_manager import session_manager

    logger.info(
        f"会话超时清理循环配置: "
        f"interval={SESSION_CLEANUP_INTERVAL}s, "
        f"max_age={SESSION_MAX_AGE}s, "
        f"activity_timeout={SESSION_ACTIVITY_TIMEOUT}s, "
        f"answer_timeout={SESSION_ANSWER_TIMEOUT}s"
    )

    while True:
        try:
            await asyncio.sleep(SESSION_CLEANUP_INTERVAL)

            # 执行超时清理
            removed_sessions = await session_manager.cleanup_old_sessions(
                max_age_seconds=SESSION_MAX_AGE,
                activity_timeout=SESSION_ACTIVITY_TIMEOUT,
                answer_timeout=SESSION_ANSWER_TIMEOUT,
            )

            # 记录清理结果
            if removed_sessions:
                for info in removed_sessions:
                    logger.info(
                        f"会话已清理: session_id={info['session_id']}, "
                        f"reason={info['timeout_reason']}, "
                        f"session_age={info['session_age']:.0f}s, "
                        f"activity_age={info['activity_age']:.0f}s"
                    )

        except asyncio.CancelledError:
            logger.info("会话超时清理循环被取消")
            break
        except Exception as e:
            logger.error(f"会话超时清理循环错误: {e}", exc_info=True)
            # 继续运行清理循环，不因单次错误而中断
            await asyncio.sleep(SESSION_CLEANUP_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Claude Code Runner 启动")
    logger.info(f"工作目录: {WORKING_DIR}")

    # 启动任务调度器
    try:
        scheduler_started = await start_scheduler()
        if scheduler_started:
            logger.info("任务调度器已自动启动")
        else:
            logger.warning("任务调度器启动失败或已在运行")
    except Exception as e:
        logger.error(f"启动任务调度器时出错: {e}")

    # 启动会话超时清理后台任务
    session_cleanup_task = asyncio.create_task(session_cleanup_loop())
    logger.info("会话超时清理任务已启动")

    yield

    # 取消会话清理任务
    session_cleanup_task.cancel()
    try:
        await session_cleanup_task
    except asyncio.CancelledError:
        pass
    logger.info("会话超时清理任务已取消")

    logger.info("Claude Code Runner 关闭")


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
app.include_router(admin.router)
app.include_router(task.router)
app.include_router(session.router)
app.include_router(status.router)
app.include_router(api_keys.router)
app.include_router(claude.router)
app.include_router(mcp.router)
app.include_router(agents.router)
app.include_router(skills.router)
app.include_router(scheduler.router)
app.include_router(files.router)


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
