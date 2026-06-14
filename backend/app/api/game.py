"""
Narrator Engine - 游戏流程 API

处理游戏的核心流程：
  - 开始新游戏
  - 获取游戏状态
  - 推进剧情
"""

import traceback

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database import get_db
from app.engine.narrator import narrator
from app.auth import get_current_user, get_optional_user
from app.models import User
from app.schemas.schemas import (
    GameStartRequest,
    GameStartResponse,
    GameStateResponse,
    DialogueAdvanceRequest,
    DialogueAdvanceResponse,
)

router = APIRouter()


@router.post("/start", response_model=GameStartResponse, summary="开始新游戏")
async def start_game(
    request: GameStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建一个新的游戏会话并开始冒险。需要登录。

    流程:
      1. 加载世界观和剧本模板
      2. 初始化角色和好感度
      3. 生成开场叙事
      4. 返回开场内容和选项
    """
    try:
        result = await narrator.start_game(
            db=db,
            world_template_id=request.world_template_id,
            scenario_template_id=request.scenario_template_id,
            player_name=request.player_name,
            player_data=request.player_data,
            character_template_ids=request.character_template_ids,
            user_id=current_user.id,
        )
        return GameStartResponse(**result)
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"游戏初始化失败: {type(e).__name__}: {e}\n{tb}")
        raise HTTPException(status_code=500, detail=f"游戏初始化失败: {str(e)}")


@router.get("/{session_id}/state", response_model=GameStateResponse, summary="获取游戏状态")
async def get_game_state(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取当前游戏会话的完整状态信息。
    包括章节进度、场景、世界状态等。
    """
    from sqlalchemy import select
    from app.models import GameSession

    stmt = select(GameSession).where(GameSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="游戏会话不存在")

    # 所有权校验
    if session.user_id and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此游戏会话")

    from app.models import AffectionState, DialogueLog

    # 统计角色数
    char_stmt = select(AffectionState).where(AffectionState.session_id == session_id)
    char_result = await db.execute(char_stmt)
    char_count = len(char_result.scalars().all())

    # 统计对话轮次
    dlg_stmt = select(DialogueLog).where(DialogueLog.session_id == session_id)
    dlg_result = await db.execute(dlg_stmt)
    dlg_count = len(dlg_result.scalars().all())

    return GameStateResponse(
        session_id=session.id,
        player_name=session.player_name,
        chapter=session.chapter,
        total_chapters=session.total_chapters,
        current_scene=session.current_scene,
        world_state=session.world_state,
        character_count=char_count,
        dialogue_count=dlg_count,
        total_turns=session.total_turns,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.post("/{session_id}/advance", response_model=DialogueAdvanceResponse, summary="推进剧情")
async def advance_game(
    session_id: str,
    request: DialogueAdvanceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    推进一轮游戏剧情。

    玩家可以:
      - 选择一个 AI 给出的选项 (input_type="choice")
      - 自由输入想说的话 (input_type="free")

    返回 AI 生成的叙事文本、角色台词、新选项和好感度变化。
    """
    try:
        result = await narrator.advance(
            db=db,
            session_id=session_id,
            input_type=request.input_type,
            content=request.content,
        )
        return DialogueAdvanceResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"剧情推进失败: {str(e)}")
