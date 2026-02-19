"""技能系统管理 API"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.skills import get_skill_manager
from app.skills.schemas import (
    SkillConfig,
    SkillDetail,
    SkillEnableResponse,
    SkillListResponse,
    SkillUpdateConfig,
)

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("", response_model=SkillListResponse)
async def get_skills(
    category: Optional[str] = Query(None, description="按分类筛选"),
    enabled_only: bool = Query(False, description="仅返回已启用的技能"),
):
    """获取技能列表"""
    manager = get_skill_manager()
    return manager.get_skills(category=category, enabled_only=enabled_only)


@router.get("/{skill_id}", response_model=SkillDetail)
async def get_skill(skill_id: str):
    """获取技能详情"""
    manager = get_skill_manager()
    skill = manager.get_skill(skill_id)

    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    return skill


@router.post("/{skill_id}/enable", response_model=SkillEnableResponse)
async def enable_skill(skill_id: str):
    """启用技能"""
    manager = get_skill_manager()

    # 检查技能是否存在
    skill = manager.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    success = manager.enable_skill(skill_id)
    if not success:
        raise HTTPException(status_code=500, detail="启用技能失败")

    return SkillEnableResponse(
        skill_id=skill_id,
        is_enabled=True,
        message="技能已启用",
    )


@router.post("/{skill_id}/disable", response_model=SkillEnableResponse)
async def disable_skill(skill_id: str):
    """禁用技能"""
    manager = get_skill_manager()

    # 检查技能是否存在
    skill = manager.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    success = manager.disable_skill(skill_id)
    if not success:
        raise HTTPException(status_code=500, detail="禁用技能失败")

    return SkillEnableResponse(
        skill_id=skill_id,
        is_enabled=False,
        message="技能已禁用",
    )


@router.get("/config", response_model=SkillConfig)
async def get_skill_config():
    """获取用户技能配置"""
    manager = get_skill_manager()
    return manager.get_config()


@router.put("/config", response_model=SkillConfig)
async def update_skill_config(config: SkillUpdateConfig):
    """更新用户技能配置"""
    manager = get_skill_manager()

    # 获取当前配置
    current_config = manager.get_config()

    # 更新配置
    if config.enabled_skills is not None:
        current_config.enabled_skills = config.enabled_skills

    if config.skill_settings is not None:
        current_config.skill_settings = config.skill_settings

    return manager.update_config(current_config)
