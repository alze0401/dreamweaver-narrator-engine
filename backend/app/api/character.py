"""
Narrator Engine - 角色管理 API

处理角色的查询和管理：
  - 获取当前游戏的所有角色
  - 获取单个角色的详细信息（含好感度数值）
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.affection import AffectionState
from app.schemas.schemas import CharacterSummary, CharacterDetail

router = APIRouter()


@router.get(
    "/{session_id}/characters",
    response_model=list[CharacterSummary],
    summary="获取角色列表",
)
async def list_characters(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前游戏中所有角色的摘要信息。
    包含角色名、好感度等级和关系描述。
    不显示具体的好感度数值（除非用户在设置中开启）。
    """
    stmt = select(AffectionState).where(AffectionState.session_id == session_id)
    result = await db.execute(stmt)
    characters = result.scalars().all()

    if not characters:
        raise HTTPException(status_code=404, detail="该会话没有角色")

    return [
        CharacterSummary(
            character_id=c.character_id,
            character_name=c.character_name,
            current_rank=c.current_rank,
            relationship_label=c.relationship_label,
            overall_score=c.overall_score,
            intimacy=c.intimacy,
            trust=c.trust,
            respect=c.respect,
            curiosity=c.curiosity,
            fear=c.fear,
        )
        for c in characters
    ]


@router.get(
    "/{session_id}/characters/{character_id}",
    response_model=CharacterDetail,
    summary="获取角色详情",
)
async def get_character_detail(
    session_id: str,
    character_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取单个角色的详细信息，包括五维好感度数值。
    用于角色详情页面或调试用途。
    """
    stmt = select(AffectionState).where(
        AffectionState.session_id == session_id,
        AffectionState.character_id == character_id,
    )
    result = await db.execute(stmt)
    char = result.scalar_one_or_none()

    if not char:
        raise HTTPException(status_code=404, detail="角色不存在")

    return CharacterDetail(
        character_id=char.character_id,
        character_name=char.character_name,
        intimacy=char.intimacy,
        trust=char.trust,
        respect=char.respect,
        curiosity=char.curiosity,
        fear=char.fear,
        current_rank=char.current_rank,
        relationship_label=char.relationship_label,
        overall_score=char.overall_score,
        triggered_events=char.triggered_events,
        known_secrets=char.known_secrets,
    )
