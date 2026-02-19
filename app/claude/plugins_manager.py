"""插件管理器 - 负责扫描和管理 Claude Code 插件"""

import json
from pathlib import Path
from typing import Optional

from app.claude.schemas import Plugin


class PluginManager:
    """插件管理器"""

    PLUGINS_DIR = Path.home() / ".claude" / "plugins"
    CONFIG_FILE = Path.home() / ".claude" / "plugins-config.json"

    # 插件元数据文件名
    METADATA_FILES = ["plugin.md", "PLUGIN.md", "README.md", "README.MD"]

    def __init__(self):
        self._ensure_config_dir()
        self._plugins_cache: list[Plugin] = []

    def _ensure_config_dir(self):
        """确保配置目录存在"""
        self.PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
        self.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    def _load_enabled_plugins(self) -> set[str]:
        """加载已启用的插件列表"""
        if not self.CONFIG_FILE.exists():
            return set()

        try:
            with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("enabled_plugins", []))
        except (json.JSONDecodeError, IOError):
            return set()

    def _save_enabled_plugins(self, enabled_plugins: set[str]) -> None:
        """保存已启用的插件列表"""
        data = {"enabled_plugins": list(enabled_plugins)}
        with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _parse_metadata(self, plugin_dir: Path) -> Optional[Plugin]:
        """解析插件元数据"""
        metadata_file = None
        for filename in self.METADATA_FILES:
            candidate = plugin_dir / filename
            if candidate.exists():
                metadata_file = candidate
                break

        if not metadata_file:
            return None

        try:
            content = metadata_file.read_text(encoding="utf-8")
        except (IOError, UnicodeDecodeError):
            return None

        plugin_id = plugin_dir.name

        # 默认值
        name = plugin_id
        description = ""
        version = "1.0.0"
        author = "Unknown"

        # 解析 frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter_text = parts[1]
                for line in frontmatter_text.split("\n"):
                    line = line.strip()
                    if ":" in line:
                        key, value = line.split(":", 1)
                        key = key.strip()
                        value = value.strip()

                        if key == "name":
                            name = value
                        elif key == "description":
                            description = value
                        elif key == "version":
                            version = value
                        elif key == "author":
                            author = value
        else:
            # 没有 frontmatter，从内容提取
            name = self._extract_title(content) or plugin_id
            description = self._extract_description(content)

        return Plugin(
            id=plugin_id,
            name=name,
            description=description,
            version=version,
            author=author,
            is_enabled=True,
            is_builtin=True,
        )

    def _extract_title(self, content: str) -> Optional[str]:
        """从内容中提取标题"""
        lines = content.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return None

    def _extract_description(self, content: str) -> str:
        """从内容中提取描述"""
        lines = content.strip().split("\n")
        description_lines = []
        in_code_block = False

        for line in lines:
            line = line.strip()

            if line.startswith("```"):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                continue

            if line.startswith("#"):
                continue

            if not line:
                continue

            if not line.startswith("- ") and not line.startswith("* "):
                description_lines.append(line)

            if len(description_lines) >= 3:
                break

        description = " ".join(description_lines)
        if len(description) > 200:
            description = description[:200] + "..."
        return description

    def get_plugins(self) -> list[Plugin]:
        """获取插件列表"""
        enabled_plugins = self._load_enabled_plugins()

        if not self.PLUGINS_DIR.exists():
            return []

        plugins: list[Plugin] = []

        for item in self.PLUGINS_DIR.iterdir():
            if not item.is_dir():
                continue

            plugin = self._parse_metadata(item)
            if plugin:
                # 应用用户配置
                plugin.is_enabled = plugin.id in enabled_plugins
                plugins.append(plugin)

        # 按名称排序
        plugins.sort(key=lambda p: p.name)

        return plugins

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """获取插件详情"""
        plugin_dir = self.PLUGINS_DIR / plugin_id
        if not plugin_dir.exists():
            return None

        plugin = self._parse_metadata(plugin_dir)
        if not plugin:
            return None

        # 应用用户配置
        enabled_plugins = self._load_enabled_plugins()
        plugin.is_enabled = plugin.id in enabled_plugins

        return plugin

    def enable_plugin(self, plugin_id: str) -> bool:
        """启用插件"""
        enabled_plugins = self._load_enabled_plugins()

        if plugin_id not in enabled_plugins:
            enabled_plugins.add(plugin_id)
            self._save_enabled_plugins(enabled_plugins)

        return True

    def disable_plugin(self, plugin_id: str) -> bool:
        """禁用插件"""
        enabled_plugins = self._load_enabled_plugins()

        if plugin_id in enabled_plugins:
            enabled_plugins.remove(plugin_id)
            self._save_enabled_plugins(enabled_plugins)

        return True


# 全局管理器实例
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """获取插件管理器单例"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager
