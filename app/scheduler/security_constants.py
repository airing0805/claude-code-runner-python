"""安全验证模块常量定义"""

import re

# ============= 常量定义 =============

# 有效的工具名称白名单
# 参考 Claude Code 官方文档的工具列表
VALID_TOOLS: set[str] = {
    # 文件操作
    "Read",        # 读取文件内容
    "Write",       # 写入文件内容
    "Edit",        # 编辑文件内容
    "Glob",        # 文件路径匹配
    "Grep",        # 文本搜索
    "Bash",        # 执行 shell 命令

    # 任务管理
    "Task",        # 创建子任务
    "TodoWrite",   # 写入 TODO 列表

    # 网络操作
    "WebFetch",    # 获取网页内容
    "WebSearch",   # 网络搜索

    # 其他
    "NotebookEdit",  # Jupyter notebook 编辑
    "NotebookRead",  # Jupyter notebook 读取
    "Mcp",          # MCP 工具调用

    # 代理工具 (MCP 扩展)
    "mcp__filesystem__read_file",
    "mcp__filesystem__write_file",
    "mcp__filesystem__read_text_file",
    "mcp__filesystem__write_text_file",
    "mcp__filesystem__list_directory",
    "mcp__filesystem__create_directory",
    "mcp__filesystem__move_file",
    "mcp__filesystem__search_files",
    "mcp__filesystem__get_file_info",
    "mcp__filesystem__directory_tree",
    "mcp__filesystem__edit_file",
    "mcp__filesystem__read_multiple_files",
    "mcp__filesystem__read_media_file",
    "mcp__chrome-devtools__take_snapshot",
    "mcp__chrome-devtools__navigate_page",
    "mcp__chrome-devtools__click",
    "mcp__chrome-devtools__fill",
    "mcp__chrome-devtools__fill_form",
    "mcp__chrome-devtools__type_text",
    "mcp__chrome-devtools__press_key",
    "mcp__chrome-devtools__take_screenshot",
    "mcp__chrome-devtools__hover",
    "mcp__chrome-devtools__evaluate_script",
    "mcp__chrome-devtools__wait_for",
    "mcp__chrome-devtools__list_pages",
    "mcp__chrome-devtools__select_page",
    "mcp__chrome-devtools__new_page",
    "mcp__chrome-devtools__close_page",
    "mcp__chrome-devtools__list_network_requests",
    "mcp__chrome-devtools__get_network_request",
    "mcp__chrome-devtools__list_console_messages",
    "mcp__chrome-devtools__get_console_message",
    "mcp__playwright__browser_navigate",
    "mcp__playwright__browser_snapshot",
    "mcp__playwright__browser_click",
    "mcp__playwright__browser_type",
    "mcp__playwright__browser_take_screenshot",
    "mcp__playwright__browser_hover",
    "mcp__playwright__browser_evaluate",
    "mcp__playwright__browser_fill_form",
    "mcp__playwright__browser_select_option",
    "mcp__playwright__browser_press_key",
    "mcp__playwright__browser_wait_for",
    "mcp__playwright__browser_tabs",
    "mcp__playwright__browser_close",
    "mcp__playwright__browser_file_upload",
    "mcp__playwright__browser_drag",
    "mcp__playwright__browser_handle_dialog",
    "mcp__playwright__browser_console_messages",
    "mcp__playwright__browser_network_requests",
    "mcp__playwright__browser_resize",
    "mcp__playwright__browser_run_code",
    "mcp__github__create_issue",
    "mcp__github__get_issue",
    "mcp__github__list_issues",
    "mcp__github__update_issue",
    "mcp__github__add_issue_comment",
    "mcp__github__create_pull_request",
    "mcp__github__get_pull_request",
    "mcp__github__list_pull_requests",
    "mcp__github__get_pull_request_files",
    "mcp__github__get_pull_request_status",
    "mcp__github__get_pull_request_reviews",
    "mcp__github__get_pull_request_comments",
    "mcp__github__merge_pull_request",
    "mcp__github__create_pull_request_review",
    "mcp__github__update_pull_request_branch",
    "mcp__github__create_branch",
    "mcp__github__get_file_contents",
    "mcp__github__create_or_update_file",
    "mcp__github__push_files",
    "mcp__github__search_code",
    "mcp__github__search_issues",
    "mcp__github__search_repositories",
    "mcp__github__search_users",
    "mcp__github__list_commits",
    "mcp__github__fork_repository",
    "mcp__github__create_repository",
    "mcp__memory__create_entities",
    "mcp__memory__create_relations",
    "mcp__memory__add_observations",
    "mcp__memory__delete_entities",
    "mcp__memory__delete_observations",
    "mcp__memory__delete_relations",
    "mcp__memory__read_graph",
    "mcp__memory__search_nodes",
    "mcp__memory__open_nodes",
    "mcp__sequential-thinking__sequentialthinking",
    "mcp__web_reader__webReader",
    "mcp__4_5v_mcp__analyze_image",
}

# 禁止访问的系统目录
FORBIDDEN_DIRS: list[str] = [
    # Unix/Linux
    "/etc",
    "/root",
    "/var/log",
    "/usr/bin",
    "/bin",
    "/sbin",
    "/boot",
    "/dev",
    "/proc",
    "/sys",

    # Windows
    "C:\\Windows",
    "C:\\System32",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
]

# 路径遍历危险字符模式
PATH_TRAVERSAL_PATTERNS = [
    "..",           # 父目录引用
    "~",            # 用户主目录
    "\\\\",         # UNC 路径 (Windows)
]

# 任务名称验证模式
VALID_NAME_PATTERN = re.compile(r'^[\w\u4e00-\u9fff\- ]+$')

# 验证限制
MAX_PROMPT_LENGTH = 10000
MAX_NAME_LENGTH = 100
MIN_TIMEOUT = 1         # 1 秒
MAX_TIMEOUT = 3600     # 1 小时