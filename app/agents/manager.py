"""Agent 管理器 - 管理子代理的生命周期"""

from datetime import datetime
from enum import Enum
from typing import AsyncIterator

from pydantic import BaseModel


class AgentStatus(str, Enum):
    """代理状态枚举"""
    RUNNING = "running"
    COMPLETED = "completed"
    TERMINATED = "terminated"
    FAILED = "failed"


class Agent(BaseModel):
    """代理数据模型"""
    id: str
    parent_task_id: str
    status: AgentStatus
    prompt: str
    started_at: datetime
    ended_at: datetime | None = None
    progress: int = 0
    tools_used: list[str] = []
    files_changed: list[str] = []
    logs: list[str] = []


class AgentManager:
    """子代理管理器"""

    def __init__(self):
        self.agents: dict[str, Agent] = {}

    def create_agent(self, agent_id: str, parent_task_id: str, prompt: str) -> Agent:
        """创建子代理"""
        agent = Agent(
            id=agent_id,
            parent_task_id=parent_task_id,
            status=AgentStatus.RUNNING,
            prompt=prompt,
            started_at=datetime.now(),
        )
        self.agents[agent_id] = agent
        return agent

    def get_agent(self, agent_id: str) -> Agent | None:
        """获取代理"""
        return self.agents.get(agent_id)

    def get_all_agents(
        self,
        status: AgentStatus | None = None,
        parent_task_id: str | None = None,
        limit: int = 50,
    ) -> list[Agent]:
        """获取代理列表"""
        agents = list(self.agents.values())

        # 按状态过滤
        if status:
            agents = [a for a in agents if a.status == status]

        # 按父任务过滤
        if parent_task_id:
            agents = [a for a in agents if a.parent_task_id == parent_task_id]

        # 按开始时间倒序排序
        agents.sort(key=lambda a: a.started_at, reverse=True)

        # 限制数量
        return agents[:limit]

    def get_running_count(self) -> int:
        """获取运行中的代理数量"""
        return sum(1 for a in self.agents.values() if a.status == AgentStatus.RUNNING)

    def update_status(self, agent_id: str, status: AgentStatus, progress: int | None = None):
        """更新代理状态"""
        agent = self.agents.get(agent_id)
        if agent:
            agent.status = status
            if progress is not None:
                agent.progress = progress
            if status != AgentStatus.RUNNING:
                agent.ended_at = datetime.now()

    def add_tool_use(self, agent_id: str, tool_name: str):
        """添加工具使用记录"""
        agent = self.agents.get(agent_id)
        if agent and tool_name not in agent.tools_used:
            agent.tools_used.append(tool_name)

    def add_file_change(self, agent_id: str, file_path: str):
        """添加文件变更记录"""
        agent = self.agents.get(agent_id)
        if agent and file_path not in agent.files_changed:
            agent.files_changed.append(file_path)

    def add_log(self, agent_id: str, log: str):
        """添加日志"""
        agent = self.agents.get(agent_id)
        if agent:
            agent.logs.append(log)

    def terminate(self, agent_id: str) -> bool:
        """终止代理"""
        agent = self.agents.get(agent_id)
        if agent and agent.status == AgentStatus.RUNNING:
            agent.status = AgentStatus.TERMINATED
            agent.ended_at = datetime.now()
            return True
        return False

    def stream_logs(self, agent_id: str) -> AsyncIterator[str]:
        """流式获取日志"""
        agent = self.agents.get(agent_id)
        if agent:
            for log in agent.logs:
                yield log


# 全局单例
agent_manager = AgentManager()
