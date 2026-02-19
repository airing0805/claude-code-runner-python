"""技能系统数据模型"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class SkillParameter(BaseModel):
    """技能参数定义"""
    name: str = Field(..., description="参数名称")
    type: str = Field(..., description="参数类型")
    default: Any = Field(None, description="默认值")
    description: str = Field(..., description="参数说明")
    required: bool = Field(False, description="是否必需")


class Skill(BaseModel):
    """技能基本信息"""
    skill_id: str = Field(..., description="技能 ID")
    name: str = Field(..., description="技能名称")
    description: str = Field(..., description="技能描述")
    category: str = Field(..., description="技能分类")
    version: str = Field("1.0.0", description="技能版本")
    author: str = Field("Unknown", description="作者")
    tags: list[str] = Field(default_factory=list, description="标签")
    is_enabled: bool = Field(True, description="是否启用")
    is_builtin: bool = Field(False, description="是否内置技能")


class SkillDetail(Skill):
    """技能详细信息"""
    parameters: list[SkillParameter] = Field(default_factory=list, description="参数列表")
    examples: list[dict[str, str]] = Field(default_factory=list, description="使用示例")
    permissions: list[str] = Field(default_factory=list, description="所需权限")
    file_path: str = Field(..., description="技能文件路径")


class SkillCategory(BaseModel):
    """技能分类"""
    name: str = Field(..., description="分类名称")
    count: int = Field(0, description="该分类下的技能数量")


class SkillListResponse(BaseModel):
    """技能列表响应"""
    skills: list[Skill] = Field(default_factory=list, description="技能列表")
    categories: list[SkillCategory] = Field(default_factory=list, description="分类列表")
    total: int = Field(0, description="总技能数")


class SkillConfig(BaseModel):
    """用户技能配置"""
    enabled_skills: list[str] = Field(default_factory=list, description="启用的技能列表")
    skill_settings: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="技能自定义设置"
    )


class SkillUpdateConfig(BaseModel):
    """更新技能配置请求"""
    enabled_skills: Optional[list[str]] = Field(None, description="启用的技能列表")
    skill_settings: Optional[dict[str, dict[str, Any]]] = Field(
        None, description="技能自定义设置"
    )


class SkillEnableResponse(BaseModel):
    """启用/禁用技能响应"""
    skill_id: str
    is_enabled: bool
    message: str
