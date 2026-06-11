"""
Narrator Engine - 语义记忆模型 (记忆 Layer 3)

Memory 存储从对话中提取的关键事实和知识。
每条记忆有重要度评分，重要度高的记忆永不遗忘。
数据会同时向量化存入 ChromaDB 以支持相似度检索。
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Float, JSON, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Memory(Base):
    """
    语义记忆表 —— 关键事实和知识的结构化存储

    记忆类别 (category):
      - character_secret: 角色秘密/隐藏信息
      - world_event: 世界观相关事件
      - relationship: 人物关系变化
      - player_action: 玩家的重要行动/决定
      - other: 其他
    """
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: uuid.uuid4().hex
    )
    session_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="所属游戏会话ID"
    )
    # ---- 记忆内容 ----
    content: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="记忆文本内容"
    )
    category: Mapped[str] = mapped_column(
        String(32), nullable=False, default="other",
        comment="记忆类别: character_secret/world_event/relationship/player_action/other"
    )
    importance: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5,
        comment="重要度 (1-10)，>=6 长期保存，>=8 永不遗忘"
    )

    # ---- 关联信息 ----
    related_characters: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list,
        comment="相关角色名称列表"
    )
    chapter: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1,
        comment="产生此记忆的章节"
    )

    # ---- ChromaDB 向量索引关联 ----
    embedding_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
        comment="ChromaDB 中对应的向量ID"
    )

    # ---- 元数据 ----
    metadata_json: Mapped[dict] = mapped_column(
        "metadata", JSON, nullable=False, default=dict,
        comment="附加元数据 (如来源对话轮次、触发事件等)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Memory imp={self.importance} cat={self.category} content={self.content[:30]}...>"
