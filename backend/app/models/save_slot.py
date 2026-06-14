"""
Narrator Engine - 存档模型

SaveSlot 存储游戏存档的完整状态快照。
支持 20 个手动存档位 + 3 个自动存档位。
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Boolean, JSON, DateTime, Text, ForeignKey, func
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SaveSlot(Base):
    """
    存档表 —— 游戏状态的完整快照

    存档包含：
      - 游戏会话的所有关键状态（章节、场景、世界状态）
      - 所有角色的好感度状态
      - 玩家画像
      - 记忆系统的指针（引用范围，不复制数据）
    """
    __tablename__ = "save_slots"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: uuid.uuid4().hex
    )
    session_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="所属游戏会话ID"
    )
    user_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="所属用户ID"
    )
    slot_number: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="存档位编号 (1-20手动, 101-103自动)"
    )
    auto_save: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="是否为自动存档"
    )

    # ---- 存档描述 ----
    title: Mapped[str] = mapped_column(
        String(128), nullable=False, default="",
        comment="存档标题 (自动生成的摘要)"
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False, default="",
        comment="存档描述 (如: 黄昏的禁书库 — 初次遇见艾莉西亚)"
    )

    # ---- 状态快照 (完整序列化) ----
    state_snapshot: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=False, default=dict,
        comment=(
            "完整的游戏状态快照，包含:\n"
            "- template_ids: 使用的模板\n"
            "- player_profile: 玩家画像\n"
            "- chapter / scene: 当前进度\n"
            "- world_state: 世界状态\n"
            "- characters_state: 所有角色的好感度\n"
            "- memory_pointers: 记忆系统指针"
        )
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # ---- 关系映射 ----
    session: Mapped["GameSession"] = relationship(
        "GameSession", back_populates="save_slots"
    )

    def __repr__(self) -> str:
        save_type = "AUTO" if self.auto_save else f"SLOT-{self.slot_number}"
        return f"<SaveSlot {save_type} title={self.title}>"
