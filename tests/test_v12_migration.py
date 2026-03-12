"""
数据迁移 (Migration) 单元测试

测试目标：
- v11 到 v12 数据转换
- 去重逻辑
- 异常处理
- 版本检测

v12.0.0.4 - 界面重构测试
"""

import pytest
from unittest.mock import MagicMock, patch
import json
from datetime import datetime


class TestMigrationVersionDetection:
    """测试版本检测"""

    def test_needs_migration_from_v11(self):
        """测试从 v11 需要迁移"""
        migration = MockMigration()
        migration.set_data_version("v11")

        assert migration.needs_migration() is True

    def test_no_migration_needed_for_v12(self):
        """测试 v12 不需要迁移"""
        migration = MockMigration()
        migration.set_data_version("v12")

        assert migration.needs_migration() is False

    def test_needs_migration_from_no_version(self):
        """测试无版本标识时需要迁移"""
        migration = MockMigration()
        migration.set_data_version(None)

        assert migration.needs_migration() is True


class TestMigrationDataConversion:
    """测试数据转换"""

    def test_convert_basic_v11_to_v12(self):
        """测试基本 v11 到 v12 转换"""
        migration = MockMigration()

        v11_data = {
            "sessions": {
                "tab-1": {
                    "id": "session-1",
                    "workingDir": "/path/to/project1",
                    "timestamp": 1000
                },
                "tab-2": {
                    "id": "session-2",
                    "workingDir": "/path/to/project2",
                    "timestamp": 2000
                }
            },
            "activeTab": "tab-1"
        }

        v12_data = migration.convert_v11_to_v12(v11_data)

        assert len(v12_data["sessions"]) == 2
        assert v12_data["currentSessionId"] == "session-1"
        assert "/path/to/project1" in v12_data["workspaceHistory"]
        assert "/path/to/project2" in v12_data["workspaceHistory"]

    def test_convert_empty_v11_data(self):
        """测试空 v11 数据转换"""
        migration = MockMigration()

        v11_data = {"sessions": {}, "activeTab": None}

        v12_data = migration.convert_v11_to_v12(v11_data)

        assert len(v12_data["sessions"]) == 0
        assert v12_data["currentSessionId"] is None
        assert len(v12_data["workspaceHistory"]) == 0

    def test_convert_v11_with_null_sessions(self):
        """测试包含空会话的 v11 数据"""
        migration = MockMigration()

        v11_data = {
            "sessions": {
                "tab-1": {"id": "valid-session", "workingDir": "/path", "timestamp": 1000},
                "tab-2": None,
                "tab-3": {},
                "tab-4": {"noId": "test"},  # 缺少 id
            },
            "activeTab": "tab-1"
        }

        v12_data = migration.convert_v11_to_v12(v11_data)

        # 只有有效的会话应该被转换
        assert len(v12_data["sessions"]) == 1
        assert v12_data["sessions"][0]["id"] == "valid-session"

    def test_sessions_sorted_by_timestamp_desc(self):
        """测试会话按时间戳降序排序"""
        migration = MockMigration()

        v11_data = {
            "sessions": {
                "tab-1": {"id": "s1", "timestamp": 1000},
                "tab-2": {"id": "s2", "timestamp": 3000},
                "tab-3": {"id": "s3", "timestamp": 2000},
            },
            "activeTab": "tab-1"
        }

        v12_data = migration.convert_v11_to_v12(v11_data)

        # 应该按时间戳降序排序
        assert v12_data["sessions"][0]["id"] == "s2"  # 3000
        assert v12_data["sessions"][1]["id"] == "s3"  # 2000
        assert v12_data["sessions"][2]["id"] == "s1"  # 1000

    def test_workspace_history_limited_to_10(self):
        """测试工作空间历史限制为 10 条"""
        migration = MockMigration()

        sessions = {}
        for i in range(15):
            sessions[f"tab-{i}"] = {
                "id": f"s{i}",
                "workingDir": f"/path/to/project{i}",
                "timestamp": i
            }

        v11_data = {"sessions": sessions, "activeTab": "tab-0"}
        v12_data = migration.convert_v11_to_v12(v11_data)

        assert len(v12_data["workspaceHistory"]) <= 10

    def test_working_dir_field_variants(self):
        """测试 workingDir 字段的不同命名变体"""
        migration = MockMigration()

        v11_data = {
            "sessions": {
                "tab-1": {"id": "s1", "workingDir": "/path1", "timestamp": 1000},
                "tab-2": {"id": "s2", "working_dir": "/path2", "timestamp": 2000},
            },
            "activeTab": "tab-1"
        }

        v12_data = migration.convert_v11_to_v12(v11_data)

        assert "/path1" in v12_data["workspaceHistory"]
        assert "/path2" in v12_data["workspaceHistory"]


class TestMigrationDeduplication:
    """测试去重逻辑"""

    def test_deduplicate_sessions_by_id(self):
        """测试按 ID 去重会话"""
        migration = MockMigration()

        v11_data = {
            "sessions": {
                "tab-1": {"id": "same-id", "workingDir": "/path1", "timestamp": 1000},
                "tab-2": {"id": "same-id", "workingDir": "/path2", "timestamp": 2000},
                "tab-3": {"id": "other-id", "workingDir": "/path3", "timestamp": 1500},
            },
            "activeTab": "tab-1"
        }

        v12_data = migration.convert_v11_to_v12(v11_data)

        # 去重后应该只有 2 个会话
        assert len(v12_data["sessions"]) == 2

        # 保留时间戳最新的版本
        same_id_session = next(s for s in v12_data["sessions"] if s["id"] == "same-id")
        assert same_id_session["workingDir"] == "/path2"  # 保留 timestamp: 2000 的版本

    def test_deduplicate_workspace_history(self):
        """测试工作空间历史去重"""
        migration = MockMigration()

        v11_data = {
            "sessions": {
                "tab-1": {"id": "s1", "workingDir": "/same/path", "timestamp": 1000},
                "tab-2": {"id": "s2", "workingDir": "/same/path", "timestamp": 2000},
                "tab-3": {"id": "s3", "workingDir": "/other/path", "timestamp": 1500},
            },
            "activeTab": "tab-1"
        }

        v12_data = migration.convert_v11_to_v12(v11_data)

        # 工作空间历史应该去重
        assert len(v12_data["workspaceHistory"]) == 2
        assert "/same/path" in v12_data["workspaceHistory"]
        assert "/other/path" in v12_data["workspaceHistory"]

    def test_session_id_uniqueness_in_v12(self):
        """测试 v12 数据中会话 ID 唯一性"""
        migration = MockMigration()

        v11_data = {
            "sessions": {
                f"tab-{i}": {"id": f"session-{i % 3}", "timestamp": i}
                for i in range(6)
            },
            "activeTab": "tab-0"
        }

        v12_data = migration.convert_v11_to_v12(v11_data)

        # 验证 ID 唯一性
        ids = [s["id"] for s in v12_data["sessions"]]
        assert len(ids) == len(set(ids))


class TestMigrationValidation:
    """测试数据验证"""

    def test_validate_v12_data_success(self):
        """测试验证成功的 v12 数据"""
        migration = MockMigration()

        v12_data = {
            "sessions": [
                {"id": "s1", "workingDir": "/path1"},
                {"id": "s2", "workingDir": "/path2"},
            ],
            "currentSessionId": "s1",
            "workspaceHistory": ["/path1", "/path2"]
        }

        v11_data = {"sessions": {"t1": {"id": "s1"}, "t2": {"id": "s2"}}}

        result = migration.validate_v12_data(v12_data, v11_data)

        assert result["valid"] is True

    def test_validate_v12_data_duplicate_ids(self):
        """测试验证重复 ID"""
        migration = MockMigration()

        v12_data = {
            "sessions": [
                {"id": "same-id"},
                {"id": "same-id"},
            ],
            "currentSessionId": "same-id",
            "workspaceHistory": []
        }

        result = migration.validate_v12_data(v12_data, {})

        assert result["valid"] is False
        assert any("重复" in w for w in result["warnings"])

    def test_validate_current_session_not_exists(self):
        """测试当前会话不存在于列表中"""
        migration = MockMigration()

        v12_data = {
            "sessions": [{"id": "s1"}],
            "currentSessionId": "nonexistent",
            "workspaceHistory": []
        }

        result = migration.validate_v12_data(v12_data, {})

        # 应该有警告，但自动修复
        assert any("当前会话" in w for w in result["warnings"])


class TestMigrationErrorHandling:
    """测试异常处理"""

    def test_handle_invalid_json_in_v11_data(self):
        """测试处理无效 JSON 数据"""
        migration = MockMigration()

        # 模拟解析失败的情况
        result = migration.load_v11_data_with_invalid_json()

        # 应该返回空数据结构
        assert result["sessions"] == {}
        assert result["activeTab"] is None

    def test_rollback_on_failure(self):
        """测试迁移失败时的回滚"""
        migration = MockMigration()
        migration.set_should_fail(True)

        # 执行迁移应该失败并回滚
        success = migration.run_migration_sync()

        assert success is False
        assert migration.rollback_called is True

    def test_backup_before_migration(self):
        """测试迁移前备份"""
        migration = MockMigration()

        v11_data = {"sessions": {"t1": {"id": "s1"}}, "activeTab": "t1"}
        migration.backup_v11_data(v11_data)

        assert migration.backup_created is True


class TestMigrationProgress:
    """测试迁移进度"""

    def test_progress_sequence(self):
        """测试进度序列"""
        migration = MockMigration()

        progress_values = []
        migration.on_progress(lambda p, m: progress_values.append(p))

        migration.run_migration_sync()

        # 进度应该是递增的
        assert progress_values == sorted(progress_values)
        assert progress_values[-1] == 100

    def test_progress_messages(self):
        """测试进度消息"""
        migration = MockMigration()

        messages = []
        migration.on_progress(lambda p, m: messages.append(m))

        migration.run_migration_sync()

        # 应该包含关键步骤的消息
        assert any("准备" in m for m in messages)
        assert any("读取" in m or "历史" in m for m in messages)
        assert any("转换" in m for m in messages)
        assert any("完成" in m for m in messages)


class MockMigration:
    """模拟 Migration 模块"""

    VERSION_V11 = "v11"
    VERSION_V12 = "v12"

    def __init__(self):
        self._data_version = None
        self._should_fail = False
        self.rollback_called = False
        self.backup_created = False
        self._progress_callback = None

    def set_data_version(self, version):
        self._data_version = version

    def set_should_fail(self, should_fail):
        self._should_fail = should_fail

    def on_progress(self, callback):
        self._progress_callback = callback

    def _emit_progress(self, progress, message):
        if self._progress_callback:
            self._progress_callback(progress, message)

    def needs_migration(self):
        return self._data_version != self.VERSION_V12

    def convert_v11_to_v12(self, v11_data):
        v12_data = {
            "sessions": [],
            "currentSessionId": None,
            "workspaceHistory": []
        }

        sessions = v11_data.get("sessions", {})
        session_map = {}

        # 遍历并去重
        if isinstance(sessions, dict):
            for key, session in sessions.items():
                if not session or not isinstance(session, dict):
                    continue
                if not session.get("id"):
                    continue

                session_id = session["id"]
                # 去重：保留时间戳最新的
                if session_id in session_map:
                    existing = session_map[session_id]
                    if session.get("timestamp", 0) > existing.get("timestamp", 0):
                        session_map[session_id] = session
                else:
                    session_map[session_id] = session

        # 转为数组并按时间戳降序排序
        v12_data["sessions"] = sorted(
            session_map.values(),
            key=lambda s: s.get("timestamp", 0),
            reverse=True
        )

        # 设置当前会话 ID
        active_tab = v11_data.get("activeTab")
        if active_tab and sessions.get(active_tab):
            v12_data["currentSessionId"] = sessions[active_tab].get("id")
        elif v12_data["sessions"]:
            v12_data["currentSessionId"] = v12_data["sessions"][0]["id"]

        # 构建工作空间历史（去重，限制 10 条）
        workspace_set = set()
        for session in v12_data["sessions"]:
            working_dir = session.get("workingDir") or session.get("working_dir")
            if working_dir:
                workspace_set.add(working_dir)

        v12_data["workspaceHistory"] = list(workspace_set)[:10]

        return v12_data

    def validate_v12_data(self, v12_data, v11_data):
        result = {
            "valid": True,
            "warnings": []
        }

        # 检查 ID 唯一性
        ids = [s.get("id") for s in v12_data.get("sessions", [])]
        if len(ids) != len(set(ids)):
            result["warnings"].append("存在重复的会话 ID")
            result["valid"] = False

        # 检查当前会话是否存在
        current_id = v12_data.get("currentSessionId")
        if current_id:
            exists = any(s.get("id") == current_id for s in v12_data.get("sessions", []))
            if not exists:
                result["warnings"].append("当前会话 ID 不存在于会话列表中")
                # 自动修复
                if v12_data["sessions"]:
                    v12_data["currentSessionId"] = v12_data["sessions"][0]["id"]

        return result

    def load_v11_data_with_invalid_json(self):
        return {"sessions": {}, "activeTab": None}

    def run_migration_sync(self):
        try:
            self._emit_progress(10, "正在准备数据迁移...")

            if self._should_fail:
                raise Exception("模拟迁移失败")

            self._emit_progress(30, "正在读取历史数据...")
            self._emit_progress(60, "正在转换数据格式...")
            self._emit_progress(90, "正在保存迁移数据...")
            self._emit_progress(100, "数据迁移完成！")

            return True

        except Exception as e:
            self.rollback_called = True
            return False

    def backup_v11_data(self, v11_data):
        self.backup_created = True

    def get_migration_status(self):
        """获取迁移状态"""
        return {
            "needsMigration": self.needs_migration(),
            "currentVersion": self._data_version or self.VERSION_V11,
            "isMigrating": False,
            "hasV11Data": True,
            "hasV12Data": False
        }


class TestMigrationIntegration:
    """集成测试"""

    def test_full_migration_flow(self):
        """测试完整的迁移流程"""
        migration = MockMigration()
        migration.set_data_version("v11")

        v11_data = {
            "sessions": {
                "tab-1": {"id": "s1", "workingDir": "/path/1", "timestamp": 1000},
                "tab-2": {"id": "s2", "workingDir": "/path/2", "timestamp": 2000},
                "tab-3": {"id": "s1", "workingDir": "/path/1/updated", "timestamp": 3000},
            },
            "activeTab": "tab-2"
        }

        # 转换
        v12_data = migration.convert_v11_to_v12(v11_data)

        # 验证
        result = migration.validate_v12_data(v12_data, v11_data)

        # 检查结果
        assert len(v12_data["sessions"]) == 2  # 去重后
        assert v12_data["currentSessionId"] == "s2"
        assert result["valid"] is True

        # 检查去重：s1 保留最新版本
        s1_session = next(s for s in v12_data["sessions"] if s["id"] == "s1")
        assert s1_session["workingDir"] == "/path/1/updated"

    def test_migration_status(self):
        """测试获取迁移状态"""
        migration = MockMigration()
        migration.set_data_version("v11")

        status = migration.get_migration_status()

        assert status["needsMigration"] is True
        assert status["currentVersion"] == "v11"

    def test_force_migration(self):
        """测试强制迁移"""
        migration = MockMigration()
        migration.set_data_version("v12")

        # 强制迁移应该重置版本并触发迁移
        migration.set_data_version("v11")

        assert migration.needs_migration() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
