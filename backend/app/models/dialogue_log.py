"""
Narrator Engine - 对话记录模型

DialogueLog 记录每一轮对话的完整信息：
  - AI 的叙事文本和角色台词
  - 给出的选项列表
  - 玩家的选择或自由输入
  - 附加的情感标签和动作描写

这些记录是「工作记忆」的数据来源，也是存档回溯的基础。
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, JSON, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DialogueLog(Base):
    """
    对话记录表 —— 存储每一轮玩家与 AI 的交互

    字段说明:
      - id: 记录唯一ID
      - session_id: 所属游戏会话
      - turn_number: 对话轮次序号 (从1开始递增)
      - speaker: 说话人 ("narrator"=旁白, 角色名=角色台词, "player"=玩家)
      - content: 对话/叙事文本内容
      - emotion: 情感标签 (如 "警觉", "温柔", "愤怒")
      - action: 动作/表情描写
      - choices_offered: AI 本轮给出的选项列表 (JSON)
      - choice_made: 玩家的选择 (选项ID 或自由输入的文本)
      - input_type: 玩家输入类型 ("choice"=选选项, "free"=自由输入)
      - metadata: 附加元数据 (JSON, 如好感度变化、场景状态更新)
    """
    __tablename__ = "dialogue_logs"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: uuid.uuid4().hex,
        comment="对话记录唯一ID"
    )
    session_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="所属游戏会话ID"
    )
    turn_number: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="对话轮次序号"
    )
    speaker: Mapped[str] = mapped_column(
        String(64), nullable=False, default="narrator",
        comment="说话人: narrator / 角色名 / player"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, default="",
        comment="对话/叙事文本"
    )
    emotion: Mapped[str] = mapped_column(
        String(32), nullable=True,
        comment="情感标签"
    )
    action: Mapped[str] = mapped_column(
        Text, nullable=True,
        comment="动作/表情描写"
    )
    choices_offered: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="AI本轮给出的选项列表"
    )
    choice_made: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="玩家的选择内容"
    )
    input_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="choice",
        comment="输入类型: choice / free"
    )
    metadata_json: Mapped[dict] = mapped_column(
        "metadata", JSON, nullable=False, default=dict,
        comment="附加元数据 (好感度变化等)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(),
        comment="记录创建时间"
    )

    # ---- 关系映射 ----
    session: Mapped["GameSession"] = relationship(
        "GameSession", back_populates="dialogues"
    )

    def __repr__(self) -> str:
        return f"<DialogueLog turn={self.turn_number} speaker={self.speaker}>"
