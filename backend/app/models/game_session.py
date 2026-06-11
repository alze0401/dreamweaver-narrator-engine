"""
Narrator Engine - 游戏会话模型

GameSession 是整个游戏的核心实体，一次完整的游戏流程对应一个 Session。
它持有当前的游戏状态：所选模板、当前章节、场景信息、世界状态标志等。
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, JSON, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def generate_uuid() -> str:
    """生成不带连字符的 UUID，作为会话 ID"""
    return uuid.uuid4().hex


class GameSession(Base):
    """
    游戏会话表 —— 一局游戏的完整生命周期

    字段说明:
      - id: 会话唯一标识 (UUID)
      - world_template_id: 选择的世界观模板 ID
      - scenario_template_id: 选择的剧本模板 ID
      - player_name: 玩家角色名
      - player_data: 玩家自定义信息 (JSON, 包含年龄/背景等)
      - chapter: 当前章节编号
      - current_scene: 当前场景描述
      - world_state: 世界状态标志 (JSON, 如 {"met_alicia": true, ...})
      - created_at / updated_at: 创建/更新时间
    """
    __tablename__ = "game_sessions"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=generate_uuid,
        comment="会话唯一ID"
    )
    world_template_id: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="世界观模板ID"
    )
    scenario_template_id: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="剧本模板ID"
    )
    player_name: Mapped[str] = mapped_column(
        String(64), nullable=False, default="主角",
        comment="玩家角色名"
    )
    player_data: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict,
        comment="玩家自定义数据 (年龄/背景/外观等)"
    )
    chapter: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1,
        comment="当前章节编号"
    )
    total_chapters: Mapped[int] = mapped_column(
        Integer, nullable=False, default=4,
        comment="剧本预估总章节数"
    )
    current_scene: Mapped[str] = mapped_column(
        Text, nullable=False, default="",
        comment="当前场景描述文本"
    )
    world_state: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict,
        comment="世界状态标志 (全局flag、地点、时间等)"
    )
    total_turns: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="总对话轮次计数"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(),
        comment="会话创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now(),
        comment="最后更新时间"
    )

    # ---- 关系映射 ----
    # 一个会话有多条对话记录
    dialogues: Mapped[list["DialogueLog"]] = relationship(
        "DialogueLog", back_populates="session", cascade="all, delete-orphan",
        lazy="selectin"
    )
    # 一个会话有多个角色的好感度状态
    affection_states: Mapped[list["AffectionState"]] = relationship(
        "AffectionState", back_populates="session", cascade="all, delete-orphan",
        lazy="selectin"
    )
    # 一个会话有多条场景摘要（情景记忆）
    scene_summaries: Mapped[list["SceneSummary"]] = relationship(
        "SceneSummary", back_populates="session", cascade="all, delete-orphan",
        lazy="selectin"
    )
    # 一个会话有一条玩家画像
    player_profile: Mapped["PlayerProfile"] = relationship(
        "PlayerProfile", back_populates="session", uselist=False,
        cascade="all, delete-orphan", lazy="selectin"
    )
    # 一个会话有多个存档
    save_slots: Mapped[list["SaveSlot"]] = relationship(
        "SaveSlot", back_populates="session", cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<GameSession id={self.id[:8]}... chapter={self.chapter} player={self.player_name}>"
