"""
Narrator Engine - 存档管理 API

处理游戏的存档和读档（用户隔离）：
  - 列出当前用户的所有存档
  - 创建存档（关联 user_id）
  - 自动存档（slot 101-103 循环，按用户隔离）
  - 加载存档（所有权校验）
  - 删除存档（所有权校验）
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import get_current_user
from app.models import GameSession, AffectionState, SaveSlot, DialogueLog, User
from app.schemas.schemas import (
    SaveCreateRequest,
    AutoSaveRequest,
    SaveSlotResponse,
    SaveLoadRequest,
    MessageResponse,
)

router = APIRouter()

# 自动存档使用的 slot 编号（循环覆盖）
AUTO_SAVE_SLOTS = [101, 102, 103]


def _build_state_snapshot(session: GameSession, characters_state: list[dict]) -> dict:
    """构建游戏状态快照"""
    return {
        "template_ids": {
            "world": session.world_template_id,
            "scenario": session.scenario_template_id,
        },
        "player_name": session.player_name,
        "player_data": session.player_data,
        "chapter": session.chapter,
        "current_scene": session.current_scene,
        "world_state": session.world_state,
        "characters_state": characters_state,
    }


async def _get_characters_state(db: AsyncSession, session_id: str) -> list[dict]:
    """获取角色好感度状态快照"""
    aff_stmt = select(AffectionState).where(AffectionState.session_id == session_id)
    aff_result = await db.execute(aff_stmt)
    characters_state = []
    for aff in aff_result.scalars().all():
        characters_state.append({
            "character_id": aff.character_id,
            "character_name": aff.character_name,
            "intimacy": aff.intimacy,
            "trust": aff.trust,
            "respect": aff.respect,
            "curiosity": aff.curiosity,
            "fear": aff.fear,
            "current_rank": aff.current_rank,
        })
    return characters_state


def _check_session_ownership(session: GameSession, user: User):
    """校验游戏会话所有权"""
    if session.user_id and session.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问此游戏会话")


def _check_save_ownership(save: SaveSlot, user: User):
    """校验存档所有权"""
    if save.user_id and save.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问此存档")


@router.get("", response_model=list[SaveSlotResponse], summary="获取存档列表")
async def list_saves(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的所有存档位信息（含自动存档）"""
    stmt = (
        select(SaveSlot)
        .where(SaveSlot.user_id == current_user.id)
        .order_by(SaveSlot.slot_number)
    )
    result = await db.execute(stmt)
    saves = result.scalars().all()
    return [
        SaveSlotResponse(
            id=s.id,
            slot_number=s.slot_number,
            auto_save=s.auto_save,
            title=s.title,
            description=s.description,
            session_id=s.session_id,
            created_at=s.created_at,
        )
        for s in saves
    ]


@router.post("/auto", response_model=SaveSlotResponse, summary="自动存档")
async def auto_save(
    request: AutoSaveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    自动存档：使用 slot 101-103 循环覆盖（按用户隔离）。

    每次调用会找到当前用户最旧的自动存档位并覆盖，保证每用户最多保留 3 个自动存档。
    """
    # 获取当前游戏会话
    session_id = request.session_id
    stmt = select(GameSession).where(GameSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalars().first()

    if not session:
        raise HTTPException(status_code=404, detail="游戏会话不存在")

    _check_session_ownership(session, current_user)

    characters_state = await _get_characters_state(db, session_id)
    state_snapshot = _build_state_snapshot(session, characters_state)

    # 查找当前用户的自动存档
    auto_stmt = (
        select(SaveSlot)
        .where(SaveSlot.auto_save == True, SaveSlot.user_id == current_user.id)
        .order_by(SaveSlot.created_at.asc())
    )
    auto_result = await db.execute(auto_stmt)
    existing_auto_saves = auto_result.scalars().all()

    # 决定使用哪个 slot：如果已有 3 个自动存档，覆盖最旧的
    if len(existing_auto_saves) >= len(AUTO_SAVE_SLOTS):
        # 覆盖最旧的
        save = existing_auto_saves[0]
        save.session_id = session.id
        save.state_snapshot = state_snapshot
        save.title = f"[自动存档] 第{session.chapter}章"
        save.description = session.current_scene
    else:
        # 使用下一个可用 slot
        used_slots = {s.slot_number for s in existing_auto_saves}
        target_slot = next(
            (s for s in AUTO_SAVE_SLOTS if s not in used_slots),
            AUTO_SAVE_SLOTS[0],
        )
        save = SaveSlot(
            user_id=current_user.id,
            session_id=session.id,
            slot_number=target_slot,
            auto_save=True,
            title=f"[自动存档] 第{session.chapter}章",
            description=session.current_scene,
            state_snapshot=state_snapshot,
        )
        db.add(save)

    await db.flush()
    await db.refresh(save)

    return SaveSlotResponse(
        id=save.id,
        slot_number=save.slot_number,
        auto_save=save.auto_save,
        title=save.title,
        description=save.description,
        session_id=save.session_id,
        created_at=save.created_at,
    )


@router.post("", response_model=SaveSlotResponse, summary="创建存档")
async def create_save(
    request: SaveCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    为当前游戏会话创建一个存档（关联当前用户）。

    存档会序列化完整的游戏状态快照，包括:
      - 游戏进度（章节、场景、世界状态）
      - 所有角色的好感度
      - 玩家画像
      - 记忆系统指针
    """
    # 获取当前游戏会话
    stmt = select(GameSession).where(GameSession.id == request.session_id)
    result = await db.execute(stmt)
    session = result.scalars().first()

    if not session:
        raise HTTPException(status_code=404, detail="游戏会话不存在")

    _check_session_ownership(session, current_user)

    characters_state = await _get_characters_state(db, session.id)
    state_snapshot = _build_state_snapshot(session, characters_state)

    # 检查当前用户是否已有存档占用此位
    existing_stmt = select(SaveSlot).where(
        SaveSlot.slot_number == request.slot_number,
        SaveSlot.user_id == current_user.id,
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()
    if existing:
        # 覆盖旧存档
        existing.session_id = session.id
        existing.state_snapshot = state_snapshot
        existing.title = request.title or f"第{session.chapter}章 存档"
        existing.description = session.current_scene
        await db.flush()
        return SaveSlotResponse(
            id=existing.id,
            slot_number=existing.slot_number,
            auto_save=existing.auto_save,
            title=existing.title,
            description=existing.description,
            session_id=existing.session_id,
            created_at=existing.created_at,
        )

    # 创建新存档
    save = SaveSlot(
        user_id=current_user.id,
        session_id=session.id,
        slot_number=request.slot_number,
        auto_save=False,
        title=request.title or f"第{session.chapter}章 存档",
        description=session.current_scene,
        state_snapshot=state_snapshot,
    )
    db.add(save)
    await db.flush()
    await db.refresh(save)

    return SaveSlotResponse(
        id=save.id,
        slot_number=save.slot_number,
        auto_save=save.auto_save,
        title=save.title,
        description=save.description,
        session_id=save.session_id,
        created_at=save.created_at,
    )


@router.post("/load", response_model=MessageResponse, summary="加载存档")
async def load_save(
    request: SaveLoadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    从存档恢复游戏状态（所有权校验）。

    流程:
      1. 校验存档所有权
      2. 读取存档的状态快照
      3. 更新对应游戏会话的状态
      4. 恢复角色好感度
    """
    # 获取存档
    stmt = select(SaveSlot).where(SaveSlot.id == request.save_id)
    result = await db.execute(stmt)
    save = result.scalar_one_or_none()

    if not save:
        raise HTTPException(status_code=404, detail="存档不存在")

    _check_save_ownership(save, current_user)

    snapshot = save.state_snapshot

    # 获取并更新游戏会话
    session_stmt = select(GameSession).where(GameSession.id == save.session_id)
    session_result = await db.execute(session_stmt)
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="存档关联的游戏会话不存在")

    _check_session_ownership(session, current_user)

    session.chapter = snapshot.get("chapter", session.chapter)
    session.current_scene = snapshot.get("current_scene", session.current_scene)
    session.world_state = snapshot.get("world_state", session.world_state)

    # 恢复角色好感度
    for char_state in snapshot.get("characters_state", []):
        aff_stmt = select(AffectionState).where(
            AffectionState.session_id == session.id,
            AffectionState.character_id == char_state["character_id"],
        )
        aff_result = await db.execute(aff_stmt)
        aff = aff_result.scalar_one_or_none()
        if aff:
            aff.intimacy = char_state.get("intimacy", aff.intimacy)
            aff.trust = char_state.get("trust", aff.trust)
            aff.respect = char_state.get("respect", aff.respect)
            aff.curiosity = char_state.get("curiosity", aff.curiosity)
            aff.fear = char_state.get("fear", aff.fear)
            aff.current_rank = char_state.get("current_rank", aff.current_rank)

    await db.flush()

    # 获取恢复后的角色好感度状态
    characters_state = await _get_characters_state(db, session.id)

    # 获取最近 20 条对话记录
    dialogue_stmt = (
        select(DialogueLog)
        .where(DialogueLog.session_id == session.id)
        .order_by(DialogueLog.turn_number.desc())
        .limit(20)
    )
    dialogue_result = await db.execute(dialogue_stmt)
    recent_logs = list(reversed(dialogue_result.scalars().all()))

    recent_dialogues = [
        {
            "turn_number": log.turn_number,
            "speaker": log.speaker,
            "content": log.content,
            "emotion": log.emotion,
            "action": log.action,
        }
        for log in recent_logs
    ]

    return MessageResponse(
        success=True,
        message=f"存档已加载: {save.title}",
        data={
            "session_id": session.id,
            "chapter": session.chapter,
            "current_scene": session.current_scene,
            "world_state": session.world_state,
            "characters_state": characters_state,
            "recent_dialogues": recent_dialogues,
        },
    )


@router.delete("/{save_id}", response_model=MessageResponse, summary="删除存档")
async def delete_save(
    save_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除指定的存档（所有权校验）"""
    stmt = select(SaveSlot).where(SaveSlot.id == save_id)
    result = await db.execute(stmt)
    save = result.scalar_one_or_none()

    if not save:
        raise HTTPException(status_code=404, detail="存档不存在")

    _check_save_ownership(save, current_user)

    await db.delete(save)
    await db.flush()

    return MessageResponse(success=True, message=f"存档已删除: {save.title}")
