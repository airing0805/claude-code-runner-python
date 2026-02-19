"""钩子管理器 - 管理 Claude Code 钩子配置"""

import json
import uuid
from pathlib import Path

from app.claude.schemas import Hook, HookConfig, HookTypeDoc


class HookManager:
    """钩子管理器"""

    HOOKS_CONFIG_FILE = Path.home() / ".claude" / "hooks.json"

    # 钩子类型说明
    HOOK_TYPES = [
        HookTypeDoc(
            name="PreToolUse",
            description="工具执行前触发",
            example="在执行危险命令前进行检查",
        ),
        HookTypeDoc(
            name="PostToolUse",
            description="工具执行后触发",
            example="记录工具执行结果",
        ),
        HookTypeDoc(
            name="Stop",
            description="会话结束时触发",
            example="清理临时文件",
        ),
        HookTypeDoc(
            name="SessionStart",
            description="会话开始时触发",
            example="加载项目配置",
        ),
        HookTypeDoc(
            name="Notification",
            description="通知事件触发",
            example="发送任务完成通知",
        ),
    ]

    def get_hooks(self) -> list[Hook]:
        """获取钩子配置"""
        if not self.HOOKS_CONFIG_FILE.exists():
            return self._get_default_hooks()

        try:
            with open(self.HOOKS_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                hooks = []
                for hook_data in data.get("hooks", []):
                    config_data = hook_data.get("config", {})
                    hooks.append(
                        Hook(
                            id=hook_data.get("id", ""),
                            name=hook_data.get("name", ""),
                            type=hook_data.get("type", "PreToolUse"),
                            enabled=hook_data.get("enabled", True),
                            config=HookConfig(
                                tools=config_data.get("tools", []),
                                action=config_data.get("action", "allow"),
                                notification=config_data.get("notification", False),
                            ),
                        )
                    )
                return hooks
        except (json.JSONDecodeError, IOError):
            return self._get_default_hooks()

    def save_hooks(self, hooks: list[Hook]) -> bool:
        """保存钩子配置"""
        try:
            # 确保目录存在
            self.HOOKS_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "hooks": [
                    {
                        "id": hook.id or f"hook_{uuid.uuid4().hex[:8]}",
                        "name": hook.name,
                        "type": hook.type,
                        "enabled": hook.enabled,
                        "config": {
                            "tools": hook.config.tools,
                            "action": hook.config.action,
                            "notification": hook.config.notification,
                        },
                    }
                    for hook in hooks
                ]
            }

            with open(self.HOOKS_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return True
        except IOError:
            return False

    def get_hook_types(self) -> list[HookTypeDoc]:
        """获取钩子类型说明"""
        return self.HOOK_TYPES

    def _get_default_hooks(self) -> list[Hook]:
        """获取默认钩子配置（模拟数据）"""
        return [
            Hook(
                id="hook_demo_1",
                name="安全检查",
                type="PreToolUse",
                enabled=True,
                config=HookConfig(
                    tools=["Bash", "Write"],
                    action="block",
                    notification=True,
                ),
            ),
            Hook(
                id="hook_demo_2",
                name="操作日志",
                type="PostToolUse",
                enabled=True,
                config=HookConfig(
                    tools=[],
                    action="allow",
                    notification=False,
                ),
            ),
        ]


# 全局单例
_hook_manager: HookManager | None = None


def get_hook_manager() -> HookManager:
    """获取钩子管理器单例"""
    global _hook_manager
    if _hook_manager is None:
        _hook_manager = HookManager()
    return _hook_manager
