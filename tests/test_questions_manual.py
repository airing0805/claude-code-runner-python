"""手动运行提问历史记录测试"""
import json
import tempfile
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, 'E:/workspaces_2026_python/claude-code-runner')

from app.services.questions import extract_question, mask_sensitive_info, _filter_ide_tags


def test_extract_question_from_valid_file():
    """测试从有效会话文件提取提问"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "projects" / "E--test-project"
        project_dir.mkdir(parents=True)

        session_id = "test-session-123"
        session_file = project_dir / f"{session_id}.jsonl"

        session_data = [
            {
                "type": "user",
                "sessionId": session_id,
                "uuid": "uuid-1",
                "timestamp": "2026-03-05T10:30:00.000Z",
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "帮我实现一个用户登录功能，需要包括邮箱和密码验证"
                        }
                    ]
                }
            }
        ]

        with open(session_file, "w", encoding="utf-8") as f:
            for line in session_data:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")

        result = extract_question(session_file)

        assert result is not None, "提取结果不应为 None"
        assert result["id"] == session_id, f"ID 不匹配: {result['id']} != {session_id}"
        assert "用户登录功能" in result["question_text"], "提问内容应包含原始文本"
        assert result["timestamp"] == "2026-03-05T10:30:00.000Z", "时间戳应匹配"
        print("[PASS] test_extract_question_from_valid_file")


def test_extract_question_filters_ide_tags():
    """测试过滤 IDE 标签"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "projects" / "E--test-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        session_id = "session-with-ide-tags"
        session_file = project_dir / f"{session_id}.jsonl"

        session_data = [
            {
                "type": "user",
                "sessionId": session_id,
                "uuid": "uuid-1",
                "timestamp": "2026-03-05T10:30:00.000Z",
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """<ide_selection>class User:
    def __init__(self):
        pass</ide_selection>
<ide_opened_file>src/models/user.py</ide_opened_file>
请帮我优化这个 User 类"""
                        }
                    ]
                }
            }
        ]

        with open(session_file, "w", encoding="utf-8") as f:
            for line in session_data:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")

        result = extract_question(session_file)

        assert result is not None, "提取结果不应为 None"
        assert "<ide_selection>" not in result["question_text"], "IDE selection 标签应被过滤"
        assert "<ide_opened_file>" not in result["question_text"], "IDE opened_file 标签应被过滤"
        assert "优化这个 User 类" in result["question_text"], "真实内容应保留"
        print("[PASS] test_extract_question_filters_ide_tags")


def test_mask_sensitive_info():
    """测试敏感信息脱敏"""
    # 测试 API Key
    text1 = "使用 sk-ant-api03-abc123-def456 作为 API key"
    result1 = mask_sensitive_info(text1)
    assert "[API_KEY]" in result1, "API Key 应被脱敏"
    assert "sk-ant-api03" not in result1, "原始 API Key 应被移除"

    # 测试 GitHub Token
    text2 = "ghp_abc123def456xyz7890abcdef1234567890"
    result2 = mask_sensitive_info(text2)
    assert "[GITHUB_TOKEN]" in result2, "GitHub Token 应被脱敏"

    # 测试 Password
    text3 = 'password="mySecretPass123"'
    result3 = mask_sensitive_info(text3)
    assert "[PASSWORD]" in result3, "Password 应被脱敏"

    # 测试 AWS Key
    text4 = "AKIAIOSFODNN7EXAMPLE"
    result4 = mask_sensitive_info(text4)
    assert "[AWS_ACCESS_KEY]" in result4, "AWS Key 应被脱敏"

    print("[PASS] test_mask_sensitive_info")


def test_filter_ide_tags():
    """测试 IDE 标签过滤函数"""
    text = """<ide_selection>代码</ide_selection>
    这里是正文内容
    <ide_opened_file>path/to/file.py</ide_opened_file>
    更多内容"""

    result = _filter_ide_tags(text)

    assert "<ide_selection>" not in result, "IDE selection 标签应被移除"
    assert "<ide_opened_file>" not in result, "IDE opened_file 标签应被移除"
    assert "这里是正文内容" in result, "正文内容应保留"
    print("[PASS] test_filter_ide_tags")


def test_extract_question_empty_content():
    """测试空内容"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "projects" / "E--test"
        project_dir.mkdir(parents=True)

        session_file = project_dir / "empty.jsonl"
        session_data = [
            {
                "type": "user",
                "sessionId": "empty-session",
                "uuid": "uuid-1",
                "timestamp": "2026-03-05T10:30:00.000Z",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": ""}
                    ]
                }
            }
        ]

        with open(session_file, "w", encoding="utf-8") as f:
            for line in session_data:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")

        result = extract_question(session_file)

        # 空内容应该返回 None
        assert result is None, "空内容应返回 None"
        print("[PASS] test_extract_question_empty_content")


def test_extract_question_with_tool_result():
    """测试跳过 tool_result 类型"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "projects" / "E--test"
        project_dir.mkdir(parents=True)

        session_id = "tool-result-test"
        session_file = project_dir / f"{session_id}.jsonl"

        # 第一条消息是 tool_result，应该被跳过
        session_data = [
            {
                "type": "user",
                "sessionId": session_id,
                "uuid": "uuid-1",
                "timestamp": "2026-03-05T10:30:00.000Z",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "tool-1", "content": "工具返回结果"}
                    ]
                }
            },
            {
                "type": "user",
                "sessionId": session_id,
                "uuid": "uuid-2",
                "timestamp": "2026-03-05T10:31:00.000Z",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "这是真正的用户提问"}
                    ]
                }
            }
        ]

        with open(session_file, "w", encoding="utf-8") as f:
            for line in session_data:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")

        result = extract_question(session_file)

        assert result is not None, "应能提取到真正的提问"
        assert "真正的用户提问" in result["question_text"], "应提取正确的提问"
        print("[PASS] test_extract_question_with_tool_result")


def test_extract_question_with_only_assistant_messages():
    """测试只有助手消息的文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "projects" / "E--test"
        project_dir.mkdir(parents=True)

        session_file = project_dir / "assistant-only.jsonl"
        session_data = [
            {
                "type": "assistant",
                "sessionId": "assistant-session",
                "uuid": "uuid-1",
                "message": {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "我来帮你"}
                    ]
                }
            }
        ]

        with open(session_file, "w", encoding="utf-8") as f:
            for line in session_data:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")

        result = extract_question(session_file)

        assert result is None, "没有用户消息应返回 None"
        print("[PASS] test_extract_question_with_only_assistant_messages")


def test_unicode_content():
    """测试 Unicode 内容处理"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "projects" / "E--unicode"
        project_dir.mkdir(parents=True)

        session_file = project_dir / "unicode.jsonl"
        session_data = [
            {
                "type": "user",
                "sessionId": "unicode-session",
                "timestamp": "2026-03-05T10:30:00.000Z",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "你好世界 Testing emojis"}
                    ]
                }
            }
        ]

        with open(session_file, "w", encoding="utf-8") as f:
            for line in session_data:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")

        result = extract_question(session_file)

        assert result is not None, "Unicode 内容应能正确提取"
        assert "你好世界" in result["question_text"], "中文应正确保留"
        print("[PASS] test_unicode_content")


if __name__ == "__main__":
    print("=" * 60)
    print("运行提问数据提取单元测试")
    print("=" * 60)

    test_extract_question_from_valid_file()
    test_extract_question_filters_ide_tags()
    test_mask_sensitive_info()
    test_filter_ide_tags()
    test_extract_question_empty_content()
    test_extract_question_with_tool_result()
    test_extract_question_with_only_assistant_messages()
    test_unicode_content()

    print("=" * 60)
    print("所有单元测试通过!")
    print("=" * 60)
