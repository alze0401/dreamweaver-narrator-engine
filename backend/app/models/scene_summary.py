"""
Narrator Engine - 场景摘要模型 (情景记忆 Layer 2)

SceneSummary 是对一段对话/一个场景的压缩摘要。
当工作记忆（最近 N 轮对话）超出容量时，旧对话被压缩为摘要保存。
这是三层记忆架构中的第二层：情景记忆。
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, JSON, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SceneSummary(Base):
    """
    场景摘要表 —— 压缩后的对话/场景记忆

    每章/每个场景结束时，AI 会生成一段摘要，记录：
      - 发生了什么 (summary_text)
      - 哪些角色在场 (characters_present)
      - 关键事件 (key_events)
    """
    __tablename__ = "scene_summaries"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: uuid.uuid4().hex
    )
    session_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="所属游戏会话ID"
    )
    chapter: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1,
        comment="所属章节编号"
    )
    scene_name: Mapped[str] = mapped_column(
        String(128), nullable=False, default="",
        comment="场景名称 (如: 禁书库初次相遇)"
    )
    summary_text: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="场景摘要文本 (200-500 tokens)"
    )
    characters_present: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list,
        comment="在场角色名称列表"
    )
    key_events: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list,
        comment="关键事件描述列表"
    )
    # 摘要覆盖的对话轮次范围
    turn_range_start: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="起始轮次"
    )
    turn_range_end: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="结束轮次"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # ---- 关系映射 ----
    session: Mapped["GameSession"] = relationship(
        "GameSession", back_populates="scene_summaries"
    )

    def __repr__(self) -> str:
        return f"<SceneSummary ch={self.chapter} scene={self.scene_name}>"
