"""
Narrator Engine - 存档管理 API

处理游戏的存档和读档：
  - 列出所有存档
  - 创建存档
  - 自动存档（slot 101-103 循环）
  - 加载存档
  - 删除存档
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import GameSession, AffectionState, SaveSlot
from app.schemas.schemas import (
    SaveCreateRequest,
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


@router.get("", response_model=list[SaveSlotResponse], summary="获取存档列表")
async def list_saves(db: AsyncSession = Depends(get_db)):
    """获取所有存档位的信息（含自动存档）"""
    stmt = select(SaveSlot).order_by(SaveSlot.slot_number)
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
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    自动存档：使用 slot 101-103 循环覆盖。
    
    每次调用会找到最旧的自动存档位并覆盖，保证最多保留 3 个自动存档。
    """
    # 获取当前游戏会话
    stmt = select(GameSession).where(GameSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalars().first()

    if not session:
        raise HTTPException(status_code=404, detail="游戏会话不存在")

    characters_state = await _get_characters_state(db, session_id)
    state_snapshot = _build_state_snapshot(session, characters_state)

    # 查找现有的自动存档
    auto_stmt = (
        select(SaveSlot)
        .where(SaveSlot.auto_save == True)
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
            session_id=session.id,
            slot_number=target_slot,
            auto_save=True,
            title=f"[自动存档] 第{session.chapter}章",
            description=session.current_scene,
            state_snapshot=state_snapshot,
        )
        db.add(save)

    await db.flush()

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
):
    """
    为当前游戏会话创建一个存档。

    存档会序列化完整的游戏状态快照，包括:
      - 游戏进度（章节、场景、世界状态）
      - 所有角色的好感度
      - 玩家画像
      - 记忆系统指针
    """
    # 获取当前游戏会话
    stmt = select(GameSession).where(GameSession.id == request.session_id if hasattr(request, 'session_id') else True)
    result = await db.execute(stmt)
    session = result.scalars().first()

    if not session:
        raise HTTPException(status_code=404, detail="游戏会话不存在")

    characters_state = await _get_characters_state(db, session.id)
    state_snapshot = _build_state_snapshot(session, characters_state)

    # 检查是否已有存档占用此位
    existing_stmt = select(SaveSlot).where(SaveSlot.slot_number == request.slot_number)
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
        session_id=session.id,
        slot_number=request.slot_number,
        auto_save=False,
        title=request.title or f"第{session.chapter}章 存档",
        description=session.current_scene,
        state_snapshot=state_snapshot,
    )
    db.add(save)
    await db.flush()

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
):
    """
    从存档恢复游戏状态。

    流程:
      1. 读取存档的状态快照
      2. 更新对应游戏会话的状态
      3. 恢复角色好感度
    """
    # 获取存档
    stmt = select(SaveSlot).where(SaveSlot.id == request.save_id)
    result = await db.execute(stmt)
    save = result.scalar_one_or_none()

    if not save:
        raise HTTPException(status_code=404, detail="存档不存在")

    snapshot = save.state_snapshot

    # 获取并更新游戏会话
    session_stmt = select(GameSession).where(GameSession.id == save.session_id)
    session_result = await db.execute(session_stmt)
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="存档关联的游戏会话不存在")

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

    return MessageResponse(
        success=True,
        message=f"存档已加载: {save.title}",
        data={"session_id": session.id, "chapter": session.chapter},
    )


@router.delete("/{save_id}", response_model=MessageResponse, summary="删除存档")
async def delete_save(
    save_id: str,
    db: AsyncSession = Depends(get_db),
):
    """删除指定的存档"""
    stmt = select(SaveSlot).where(SaveSlot.id == save_id)
    result = await db.execute(stmt)
    save = result.scalar_one_or_none()

    if not save:
        raise HTTPException(status_code=404, detail="存档不存在")

    await db.delete(save)
    await db.flush()

    return MessageResponse(success=True, message=f"存档已删除: {save.title}")
