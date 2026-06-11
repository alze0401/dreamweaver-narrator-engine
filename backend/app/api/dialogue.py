"""
Narrator Engine - 对话交互 API

处理对话的流式输出（SSE）和记忆检索：
  - SSE 流式获取 AI 响应
  - 获取对话历史
  - 搜索记忆日志
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import DialogueLog, Memory
from app.engine.narrator import narrator

router = APIRouter()


@router.get("/{session_id}/history", summary="获取对话历史")
async def get_dialogue_history(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定会话的对话历史记录。

    Args:
        session_id: 游戏会话ID
        limit: 返回的最大记录数 (默认50)
        offset: 跳过的记录数 (用于分页)
    """
    stmt = (
        select(DialogueLog)
        .where(DialogueLog.session_id == session_id)
        .order_by(DialogueLog.turn_number.asc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    dialogues = result.scalars().all()

    return {
        "total": len(dialogues),
        "offset": offset,
        "dialogues": [
            {
                "turn_number": d.turn_number,
                "speaker": d.speaker,
                "content": d.content,
                "emotion": d.emotion,
                "action": d.action,
                "choices_offered": d.choices_offered,
                "choice_made": d.choice_made,
                "input_type": d.input_type,
            }
            for d in dialogues
        ],
    }


@router.get("/{session_id}/memories", summary="获取记忆日志")
async def get_memories(
    session_id: str,
    category: str | None = None,
    min_importance: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """
    获取记忆系统中存储的关键事实。

    支持按类别和重要度过滤。
    用于前端的「记忆日志」查看器。
    """
    stmt = (
        select(Memory)
        .where(
            Memory.session_id == session_id,
            Memory.importance >= min_importance,
        )
        .order_by(Memory.importance.desc(), Memory.created_at.desc())
        .limit(limit)
    )

    # 类别过滤
    if category:
        stmt = stmt.where(Memory.category == category)

    result = await db.execute(stmt)
    memories = result.scalars().all()

    return {
        "total": len(memories),
        "memories": [
            {
                "id": m.id,
                "content": m.content,
                "category": m.category,
                "importance": m.importance,
                "related_characters": m.related_characters,
                "chapter": m.chapter,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in memories
        ],
    }


@router.get("/{session_id}/memories/search", summary="搜索记忆")
async def search_memories(
    session_id: str,
    q: str,
    top_k: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """
    通过关键词语义搜索记忆。

    使用 ChromaDB 向量检索，返回最相关的记忆。
    """
    from app.engine.memory import memory_manager

    results = await memory_manager.search_semantic_memory(
        db=db,
        session_id=session_id,
        query=q,
        top_k=top_k,
    )

    return {
        "query": q,
        "results": results,
    }


@router.get("/{session_id}/stream", summary="SSE 流式对话")
async def stream_dialogue(
    session_id: str,
    input_type: str = "choice",
    content: str = "",
    db: AsyncSession = Depends(get_db),
):
    """
    通过 Server-Sent Events (SSE) 流式返回 AI 的对话响应。

    前端可以通过 EventSource 监听此端点，实现打字机效果。

    事件类型:
      - narration: 叙事文本片段
      - dialogue: 角色台词
      - choices: 选项列表
      - state_update: 状态更新 (好感度变化等)
      - done: 响应完成

    注意: 此端点目前使用模拟流式输出。
    完整的流式实现需要 LLM 的流式调用 + 实时解析。
    """
    async def event_generator():
        """SSE 事件生成器"""
        try:
            # 调用叙事引擎
            result = await narrator.advance(
                db=db,
                session_id=session_id,
                input_type=input_type,
                content=content,
            )

            # 发送叙事文本
            if result.get("narration"):
                narration_data = json.dumps(
                    {"text": result["narration"]},
                    ensure_ascii=False,
                )
                yield f"event: narration\ndata: {narration_data}\n\n"

            # 发送角色台词
            for dialogue in result.get("dialogues", []):
                dialogue_data = json.dumps(dialogue, ensure_ascii=False)
                yield f"event: dialogue\ndata: {dialogue_data}\n\n"

            # 发送选项
            if result.get("choices"):
                choices_data = json.dumps(result["choices"], ensure_ascii=False)
                yield f"event: choices\ndata: {choices_data}\n\n"

            # 发送状态更新
            state_update = {
                "scene_state": result.get("scene_state", {}),
                "affection_changes": result.get("affection_changes", []),
            }
            yield f"event: state_update\ndata: {json.dumps(state_update, ensure_ascii=False)}\n\n"

            # 完成信号
            yield "event: done\ndata: {}\n\n"

        except Exception as e:
            error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁止 Nginx 缓冲
        },
    )
