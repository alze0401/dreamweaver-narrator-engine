"""
Narrator Engine - 玩家画像模型

PlayerProfile 记录玩家在游戏中展现出的性格特征和行为偏好。
AI 会根据画像调整叙事风格和选项生成——
例如，偏好诚实选项的玩家，AI 会更多设计道德困境来考验。
"""

import uuid
from datetime import datetime

from sqlalchemy import String, JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PlayerProfile(Base):
    """
    玩家画像表 —— 一个会话对应一条记录

    画像来源：
      - 玩家创建角色时主动填写的信息
      - AI 从对话中观察并提取的性格特征 (自动积累)
    """
    __tablename__ = "player_profiles"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: uuid.uuid4().hex
    )
    session_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
        comment="所属游戏会话ID (一对一关系)"
    )

    # ---- 玩家主动设定的信息 ----
    name: Mapped[str] = mapped_column(
        String(64), nullable=False, default="主角",
        comment="角色名"
    )
    age: Mapped[str] = mapped_column(
        String(16), nullable=True,
        comment="角色年龄"
    )
    background: Mapped[str] = mapped_column(
        String(512), nullable=True,
        comment="角色背景简介"
    )

    # ---- AI 观察到的特征 (自动积累) ----
    observed_traits: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list,
        comment="AI观察到的玩家性格特征 (如: ['诚实', '果断', '好奇心强'])"
    )
    play_style: Mapped[str] = mapped_column(
        String(32), nullable=False, default="unknown",
        comment="游玩风格: balanced/aggressive/cautious/explorer/social"
    )

    # ---- 重要决定记录 ----
    key_decisions: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list,
        comment="玩家做出的重要决定列表 [{chapter, description, impact}]"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # ---- 关系映射 (一对一) ----
    session: Mapped["GameSession"] = relationship(
        "GameSession", back_populates="player_profile"
    )

    def __repr__(self) -> str:
        return f"<PlayerProfile name={self.name} style={self.play_style}>"
