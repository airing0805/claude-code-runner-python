"""技能管理器 - 负责扫描和管理 Claude Code 技能"""

import json
import re
from pathlib import Path
from typing import Any, Optional

from app.skills.schemas import (
    Skill,
    SkillCategory,
    SkillConfig,
    SkillDetail,
    SkillListResponse,
    SkillParameter,
)


class SkillManager:
    """技能管理器"""

    # 用户级 skills 目录
    USER_SKILLS_DIR = Path.home() / ".claude" / "skills"
    CONFIG_FILE = Path.home() / ".claude" / "skills-config.json"

    # 技能元数据文件名
    METADATA_FILES = ["skill.md", "SKILL.md", "README.md", "README.MD"]

    # 分类映射
    CATEGORY_MAP = {
        "document": "文档处理",
        "pdf": "文档处理",
        "word": "文档处理",
        "code": "代码开发",
        "git": "版本控制",
        "database": "数据库",
        "db": "数据库",
        "testing": "测试",
        "test": "测试",
        "deployment": "部署",
        "docker": "容器",
        "security": "安全",
        "api": "API",
        "frontend": "前端",
        "backend": "后端",
        "ai": "AI工具",
        "ml": "机器学习",
        "default": "其他",
    }

    def __init__(self, project_path: str | Path | None = None):
        """
        初始化技能管理器

        Args:
            project_path: 项目路径，用于定位项目级 .claude/skills/ 目录
        """
        # 先设置项目路径
        if project_path:
            self._project_path = Path(project_path).resolve()
        else:
            self._project_path = None

        self._ensure_config_dir()
        self._skills_cache: list[Skill] = []
        self._categories_cache: list[SkillCategory] = []

    def set_project_path(self, project_path: str | Path | None) -> None:
        """设置项目路径"""
        if project_path:
            self._project_path = Path(project_path).resolve()
        else:
            self._project_path = None

    def get_project_skills_dir(self) -> Path | None:
        """获取项目级 skills 目录"""
        if self._project_path:
            return self._project_path / ".claude" / "skills"
        return None

    def _ensure_config_dir(self):
        """确保配置目录存在"""
        self.USER_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        if self._project_path:
            project_skills_dir = self._project_path / ".claude" / "skills"
            project_skills_dir.mkdir(parents=True, exist_ok=True)
        self.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    def _load_user_config(self) -> SkillConfig:
        """加载用户配置"""
        if not self.CONFIG_FILE.exists():
            return SkillConfig()

        try:
            with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return SkillConfig(**data)
        except (json.JSONDecodeError, IOError):
            return SkillConfig()

    def _save_user_config(self, config: SkillConfig) -> None:
        """保存用户配置"""
        data = config.model_dump()
        with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _parse_metadata(self, skill_dir: Path) -> Skill | None:
        """解析技能元数据"""
        metadata_file = None
        for filename in self.METADATA_FILES:
            candidate = skill_dir / filename
            if candidate.exists():
                metadata_file = candidate
                break

        if not metadata_file:
            return None

        try:
            content = metadata_file.read_text(encoding="utf-8")
        except (IOError, UnicodeDecodeError):
            return None

        # 从文件内容中提取元数据
        skill_id = skill_dir.name

        # 尝试从 frontmatter 提取
        name = skill_id
        description = ""
        category = "其他"
        version = "1.0.0"
        author = "Unknown"
        tags: list[str] = []
        parameters: list[SkillParameter] = []
        examples: list[dict[str, str]] = []
        permissions: list[str] = []

        # 尝试从 frontmatter 提取
        name = skill_id
        description = ""
        category = "其他"
        version = "1.0.0"
        author = "Unknown"
        tags: list[str] = []
        parameters: list[SkillParameter] = []
        examples: list[dict[str, str]] = []
        permissions: list[str] = []

        # 解析简单的 YAML frontmatter（不使用外部库）
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter_text = parts[1]
                # 简单解析 key: value 格式
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
                        elif key == "category":
                            category = value
                        elif key == "version":
                            version = value
                        elif key == "author":
                            author = value
                        elif key == "tags":
                            # 解析列表 [a, b, c] 或 - a\n- b 格式
                            if value.startswith("["):
                                tags = [t.strip() for t in value[1:-1].split(",") if t.strip()]
                            elif value.startswith("-"):
                                tags = [t.strip().lstrip("- ").strip() for t in value.split("\n") if t.strip()]
                        elif key == "permissions":
                            if value.startswith("["):
                                permissions = [p.strip() for p in value[1:-1].split(",") if p.strip()]
                            elif value.startswith("-"):
                                permissions = [p.strip().lstrip("- ").strip() for p in value.split("\n") if p.strip()]

                content = parts[2] if len(parts) > 2 else ""
            else:
                # 没有有效的 frontmatter
                name = self._extract_title(content) or skill_id
                description = self._extract_description(content)
        else:
            # 没有 frontmatter，从内容提取
            name = self._extract_title(content) or skill_id
            description = self._extract_description(content)

        # 自动判断分类
        if category == "其他":
            category = self._auto_detect_category(skill_id, description, tags)

        return Skill(
            skill_id=skill_id,
            name=name,
            description=description,
            category=category,
            version=version,
            author=author,
            tags=tags,
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

            # 跳过代码块
            if line.startswith("```"):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                continue

            # 跳过标题
            if line.startswith("#"):
                continue

            # 跳过空行
            if not line:
                continue

            # 收集段落文本
            if not line.startswith("- ") and not line.startswith("* "):
                description_lines.append(line)

            if len(description_lines) >= 3:
                break

        description = " ".join(description_lines)
        # 截断过长的描述
        if len(description) > 200:
            description = description[:200] + "..."
        return description

    def _auto_detect_category(
        self, skill_id: str, description: str, tags: list[str]
    ) -> str:
        """自动检测分类"""
        text = f"{skill_id} {description} {' '.join(tags)}".lower()

        for keyword, category in self.CATEGORY_MAP.items():
            if keyword in text:
                return category

        return "其他"

    def _scan_skills_dir(self, skills_dir: Path) -> list[Skill]:
        """扫描指定目录下的 skills"""
        skills: list[Skill] = []
        if not skills_dir.exists():
            return skills

        for item in skills_dir.iterdir():
            if not item.is_dir():
                continue

            skill = self._parse_metadata(item)
            if skill:
                skills.append(skill)

        return skills

    def get_skills(
        self, category: Optional[str] = None, enabled_only: bool = False
    ) -> SkillListResponse:
        """获取技能列表"""
        config = self._load_user_config()
        enabled_skills = set(config.enabled_skills)

        # 扫描技能目录（用户级 + 项目级）
        skills: list[Skill] = []
        categories_set: set[str] = set()

        # 扫描用户级 skills
        user_skills = self._scan_skills_dir(self.USER_SKILLS_DIR)
        skills.extend(user_skills)

        # 扫描项目级 skills
        project_skills_dir = self.get_project_skills_dir()
        project_skills = self._scan_skills_dir(project_skills_dir) if project_skills_dir else []
        # 合并，去重（项目级优先）
        existing_ids = {s.skill_id for s in skills}
        for skill in project_skills:
            if skill.skill_id not in existing_ids:
                skills.append(skill)

        if not skills:
            return SkillListResponse(skills=[], categories=[], total=0)

        # 应用用户配置并收集分类
        for skill in skills:
            skill.is_enabled = skill.skill_id in enabled_skills
            categories_set.add(skill.category)

        # 预先计算所有分类的计数（不过滤）
        all_category_counts: dict[str, int] = {}
        for skill in skills:
            all_category_counts[skill.category] = all_category_counts.get(skill.category, 0) + 1

        # 过滤
        if category:
            skills = [s for s in skills if s.category == category]

        if enabled_only:
            skills = [s for s in skills if s.is_enabled]

        # 构建分类列表 - 使用所有分类的计数，而不是过滤后的
        categories = []
        for cat_name in sorted(categories_set):
            categories.append(
                SkillCategory(name=cat_name, count=all_category_counts.get(cat_name, 0))
            )

        return SkillListResponse(
            skills=skills,
            categories=categories,
            total=len(skills),
        )

    def get_skill(self, skill_id: str) -> Optional[SkillDetail]:
        """获取技能详情"""
        # 先检查项目级，再检查用户级
        project_skills_dir = self.get_project_skills_dir()
        if project_skills_dir:
            skill_dir = project_skills_dir / skill_id
        else:
            skill_dir = None

        if not skill_dir or not skill_dir.exists():
            skill_dir = self.USER_SKILLS_DIR / skill_id

        if not skill_dir or not skill_dir.exists():
            return None

        skill = self._parse_metadata(skill_dir)
        if not skill:
            return None

        # 加载用户配置
        config = self._load_user_config()
        skill.is_enabled = skill_id in config.enabled_skills

        # 获取文件内容作为详细信息
        metadata_file = None
        for filename in self.METADATA_FILES:
            candidate = skill_dir / filename
            if candidate.exists():
                metadata_file = candidate
                break

        content = ""
        if metadata_file:
            try:
                content = metadata_file.read_text(encoding="utf-8")
            except (IOError, UnicodeDecodeError):
                content = ""

        # 从文件内容中提取更多信息
        examples = self._extract_examples(content)
        permissions = self._extract_permissions(content)

        return SkillDetail(
            **skill.model_dump(),
            file_path=str(skill_dir),
            examples=examples,
            permissions=permissions,
        )

    def _extract_examples(self, content: str) -> list[dict[str, str]]:
        """提取使用示例"""
        examples: list[dict[str, str]] = []

        # 简单实现：查找代码块作为示例
        lines = content.split("\n")
        current_example: dict[str, str] = {}
        in_example = False

        for line in lines:
            line = line.strip()

            if line.startswith("### Example") or line.startswith("## Example"):
                if current_example:
                    examples.append(current_example)
                current_example = {"description": line, "code": ""}
                in_example = True
            elif in_example and line.startswith("```"):
                in_example = False
            elif in_example:
                current_example["code"] += line + "\n"

        if current_example:
            examples.append(current_example)

        return examples[:5]  # 最多5个示例

    def _extract_permissions(self, content: str) -> list[str]:
        """提取所需权限"""
        permissions: list[str] = []

        # 查找 permissions 相关内容
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "permission" in line.lower():
                # 尝试提取接下来的列表
                for j in range(i + 1, min(i + 5, len(lines))):
                    next_line = lines[j].strip()
                    if next_line.startswith("- ") or next_line.startswith("* "):
                        perm = next_line[2:].strip()
                        if perm:
                            permissions.append(perm)
                    elif next_line.startswith("#"):
                        break

        return permissions

    def enable_skill(self, skill_id: str) -> bool:
        """启用技能"""
        config = self._load_user_config()

        if skill_id not in config.enabled_skills:
            config.enabled_skills.append(skill_id)

        self._save_user_config(config)
        return True

    def disable_skill(self, skill_id: str) -> bool:
        """禁用技能"""
        config = self._load_user_config()

        if skill_id in config.enabled_skills:
            config.enabled_skills.remove(skill_id)

        self._save_user_config(config)
        return True

    def get_config(self) -> SkillConfig:
        """获取用户配置"""
        return self._load_user_config()

    def update_config(self, config: SkillConfig) -> SkillConfig:
        """更新用户配置"""
        self._save_user_config(config)
        return config


# 全局管理器实例
_skill_manager: Optional[SkillManager] = None


def get_skill_manager(project_path: str | Path | None = None) -> SkillManager:
    """
    获取技能管理器单例

    Args:
        project_path: 项目路径，用于定位项目级 .claude/skills/ 目录
    """
    global _skill_manager
    if _skill_manager is None:
        _skill_manager = SkillManager(project_path)
    elif project_path is not None:
        # 如果传入了新的项目路径，更新它
        _skill_manager.set_project_path(project_path)
    return _skill_manager


def reset_skill_manager() -> None:
    """重置技能管理器单例"""
    global _skill_manager
    _skill_manager = None
