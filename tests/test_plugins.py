"""v0.3.7 插件管理测试"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from app.claude.plugins_manager import PluginManager
from app.claude.schemas import Plugin


class TestPluginManager:
    """PluginManager 单元测试"""

    def test_load_enabled_plugins_empty(self):
        """测试加载空的已启用插件列表"""
        with patch.object(Path, "exists", return_value=False):
            manager = PluginManager()
            enabled = manager._load_enabled_plugins()
            assert enabled == set()

    def test_load_enabled_plugins_with_data(self, tmp_path):
        """测试加载已启用的插件列表"""
        # 创建目录结构
        config_dir = tmp_path / ".claude"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "plugins-config.json"
        config_data = {"enabled_plugins": ["plugin1", "plugin2"]}

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        with patch.object(PluginManager, "CONFIG_FILE", config_file):
            manager = PluginManager()
            enabled = manager._load_enabled_plugins()
            assert enabled == {"plugin1", "plugin2"}

    def test_save_enabled_plugins(self, tmp_path):
        """测试保存已启用的插件列表"""
        config_file = tmp_path / ".claude" / "plugins-config.json"

        with patch.object(PluginManager, "CONFIG_FILE", config_file):
            manager = PluginManager()
            enabled_plugins = {"plugin1", "plugin2"}
            manager._save_enabled_plugins(enabled_plugins)

            assert config_file.exists()

            with open(config_file) as f:
                data = json.load(f)
                assert set(data["enabled_plugins"]) == enabled_plugins


class TestPluginManagerEnableDisable:
    """启用/禁用插件测试"""

    def test_enable_plugin(self, tmp_path):
        """测试启用插件"""
        config_file = tmp_path / ".claude" / "plugins-config.json"

        with patch.object(PluginManager, "CONFIG_FILE", config_file):
            manager = PluginManager()

            # 确保配置为空
            manager._save_enabled_plugins(set())

            # 启用插件
            result = manager.enable_plugin("test-plugin")
            assert result is True

            # 验证插件已被添加到启用列表
            enabled = manager._load_enabled_plugins()
            assert "test-plugin" in enabled

    def test_enable_already_enabled_plugin(self, tmp_path):
        """测试启用已启用的插件"""
        config_file = tmp_path / ".claude" / "plugins-config.json"

        with patch.object(PluginManager, "CONFIG_FILE", config_file):
            manager = PluginManager()

            # 先启用插件
            manager._save_enabled_plugins({"test-plugin"})

            # 再次启用
            result = manager.enable_plugin("test-plugin")
            assert result is True

            # 验证仍然是启用状态
            enabled = manager._load_enabled_plugins()
            assert "test-plugin" in enabled

    def test_disable_plugin(self, tmp_path):
        """测试禁用插件"""
        config_file = tmp_path / ".claude" / "plugins-config.json"

        with patch.object(PluginManager, "CONFIG_FILE", config_file):
            manager = PluginManager()

            # 先启用插件
            manager._save_enabled_plugins({"test-plugin"})

            # 禁用插件
            result = manager.disable_plugin("test-plugin")
            assert result is True

            # 验证插件已从启用列表中移除
            enabled = manager._load_enabled_plugins()
            assert "test-plugin" not in enabled

    def test_disable_already_disabled_plugin(self, tmp_path):
        """测试禁用已禁用的插件"""
        config_file = tmp_path / ".claude" / "plugins-config.json"

        with patch.object(PluginManager, "CONFIG_FILE", config_file):
            manager = PluginManager()

            # 确保插件未启用
            manager._save_enabled_plugins(set())

            # 禁用插件
            result = manager.disable_plugin("test-plugin")
            assert result is True

            # 验证仍然是禁用状态
            enabled = manager._load_enabled_plugins()
            assert "test-plugin" not in enabled


class TestPluginManagerGetPlugins:
    """get_plugins 方法测试"""

    def test_get_plugins_empty_directory(self, tmp_path):
        """测试空插件目录"""
        plugins_dir = tmp_path / ".claude" / "plugins"

        with patch.object(PluginManager, "PLUGINS_DIR", plugins_dir):
            manager = PluginManager()
            plugins = manager.get_plugins()
            assert plugins == []

    def test_get_plugins_with_plugins(self, tmp_path):
        """测试扫描插件目录"""
        plugins_dir = tmp_path / ".claude" / "plugins"
        plugins_dir.mkdir(parents=True, exist_ok=True)

        # 创建插件目录
        plugin_dir = plugins_dir / "test-plugin"
        plugin_dir.mkdir()

        # 创建插件元数据文件
        metadata_file = plugin_dir / "plugin.md"
        metadata_file.write_text("""---
name: Test Plugin
description: A test plugin
version: 1.0.0
author: Test Author
---

# Test Plugin
""")

        with patch.object(PluginManager, "PLUGINS_DIR", plugins_dir):
            manager = PluginManager()
            plugins = manager.get_plugins()

            assert len(plugins) == 1
            assert plugins[0].id == "test-plugin"
            assert plugins[0].name == "Test Plugin"
            assert plugins[0].description == "A test plugin"
            assert plugins[0].version == "1.0.0"
            assert plugins[0].author == "Test Author"


class TestPluginsAPI:
    """插件管理 API 测试"""

    @pytest.fixture
    def client(self):
        from app.main import app

        return TestClient(app)

    @pytest.fixture
    def mock_plugin_manager(self):
        """Mock PluginManager"""
        mock_plugin = Plugin(
            id="test-plugin",
            name="Test Plugin",
            description="A test plugin",
            version="1.0.0",
            author="Test Author",
            is_enabled=False,
            is_builtin=False,
        )

        with patch("app.routers.claude.get_plugin_manager") as mock_manager:
            manager = MagicMock()
            manager.get_plugins.return_value = [mock_plugin]
            manager.get_plugin.return_value = mock_plugin
            manager.enable_plugin.return_value = True
            manager.disable_plugin.return_value = True
            mock_manager.return_value = manager
            yield mock_manager

    def test_get_plugins(self, client, mock_plugin_manager):
        """测试获取插件列表"""
        response = client.get("/api/claude/plugins")

        assert response.status_code == 200
        data = response.json()
        assert "plugins" in data
        assert "total" in data
        assert data["total"] == 1
        assert len(data["plugins"]) == 1
        assert data["plugins"][0]["id"] == "test-plugin"

    def test_get_plugin_detail(self, client, mock_plugin_manager):
        """测试获取插件详情"""
        response = client.get("/api/claude/plugins/test-plugin")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-plugin"
        assert data["name"] == "Test Plugin"

    def test_get_plugin_not_found(self, client, mock_plugin_manager):
        """测试获取不存在的插件"""
        mock_plugin_manager.return_value.get_plugin.return_value = None

        response = client.get("/api/claude/plugins/nonexistent")

        assert response.status_code == 404

    def test_enable_plugin(self, client, mock_plugin_manager):
        """测试启用插件"""
        response = client.post("/api/claude/plugins/test-plugin/enable")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "已启用" in data["message"]

    def test_disable_plugin(self, client, mock_plugin_manager):
        """测试禁用插件"""
        response = client.post("/api/claude/plugins/test-plugin/disable")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "已禁用" in data["message"]

    def test_enable_nonexistent_plugin(self, client, mock_plugin_manager):
        """测试启用不存在的插件"""
        mock_plugin_manager.return_value.enable_plugin.return_value = False

        response = client.post("/api/claude/plugins/nonexistent/enable")

        assert response.status_code == 404
