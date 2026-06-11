"""
Narrator Engine - 好感度状态模型

AffectionState 追踪每个角色对玩家的多维度好感度。
采用五维模型：亲密度、信任度、尊重度、好奇度、畏惧度。
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Float, JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AffectionState(Base):
    """
    好感度状态表 —— 每个角色在每个会话中有一条记录

    五维好感度模型:
      - intimacy:  亲密度 (情感距离)     0-100
      - trust:     信任度 (可靠性评价)    0-100
      - respect:   尊重度 (能力/品格评价)  0-100
      - curiosity: 好奇度 (兴趣程度)      0-100
      - fear:      畏惧度 (恐惧程度)      0-100

    综合好感度等级由这五个维度的加权值决定。
    """
    __tablename__ = "affection_states"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: uuid.uuid4().hex,
        comment="记录唯一ID"
    )
    session_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="所属游戏会话ID"
    )
    character_id: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="角色模板ID"
    )
    character_name: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="角色显示名称"
    )

    # ---- 五维好感度数值 ----
    intimacy: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="亲密度 (0-100)"
    )
    trust: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="信任度 (0-100)"
    )
    respect: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="尊重度 (0-100)"
    )
    curiosity: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="好奇度 (0-100)"
    )
    fear: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="畏惧度 (0-100)"
    )

    # ---- 状态追踪 ----
    current_rank: Mapped[str] = mapped_column(
        String(32), nullable=False, default="陌生",
        comment="当前好感度等级 (如: 陌生/友好/亲密)"
    )
    triggered_events: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list,
        comment="已触发的好感度事件ID列表"
    )
    known_secrets: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list,
        comment="角色已向玩家揭露的秘密列表"
    )
    relationship_label: Mapped[str] = mapped_column(
        String(128), nullable=False, default="陌生人",
        comment="关系描述文本"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # ---- 关系映射 ----
    session: Mapped["GameSession"] = relationship(
        "GameSession", back_populates="affection_states"
    )

    # ---- 便捷方法 ----
    @property
    def overall_score(self) -> float:
        """
        计算综合好感度分数。
        简单的加权平均（实际使用时角色模板可定义不同权重）。
        """
        return (
            self.intimacy * 0.3 +
            self.trust * 0.25 +
            self.respect * 0.2 +
            self.curiosity * 0.15 +
            self.fear * 0.1
        )

    def apply_delta(self, dimension: str, delta: float) -> float:
        """
        应用好感度变化。

        Args:
            dimension: 维度名称 (intimacy/trust/respect/curiosity/fear)
            delta: 变化量 (正值增加, 负值减少)

        Returns:
            变化后的新值

        Raises:
            ValueError: 维度名称不合法
        """
        valid_dims = {"intimacy", "trust", "respect", "curiosity", "fear"}
        if dimension not in valid_dims:
            raise ValueError(f"未知的好感度维度: {dimension}, 可选: {valid_dims}")

        # 获取当前值，加上变化量，限制在 0-100 范围内
        current = getattr(self, dimension)
        new_value = max(0.0, min(100.0, current + delta))
        setattr(self, dimension, new_value)
        return new_value

    def __repr__(self) -> str:
        return (
            f"<AffectionState char={self.character_name} "
            f"rank={self.current_rank} score={self.overall_score:.1f}>"
        )
