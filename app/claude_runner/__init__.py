"""Claude Agent Runner - 通过 Web API 调用 Claude Agent 执行任务"""

from .client import ClaudeCodeClient, TaskResult

__all__ = ["ClaudeCodeClient", "TaskResult"]
__version__ = "0.1.0"
