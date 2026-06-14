"""模板相关 ORM 模型：分类、模板、多对多映射"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, Boolean, JSON, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class TemplateCategory(Base):
    """模板分类表"""
    __tablename__ = "template_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True, default="")
    icon: Mapped[str] = mapped_column(String(64), nullable=True, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # relationships
    templates: Mapped[list["Template"]] = relationship(
        "Template",
        secondary="template_category_mapping",
        back_populates="categories",
    )


class Template(Base):
    """模板表"""
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    template_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # world/character/scenario
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True, default="")
    tags: Mapped[list] = mapped_column(JSON, nullable=True, default=list)
    is_preset: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    creator_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="角色头像/立绘 或 世界封面图 URL"
    )
    bg_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="背景图 URL（世界观模板的场景背景）"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # relationships
    categories: Mapped[list["TemplateCategory"]] = relationship(
        "TemplateCategory",
        secondary="template_category_mapping",
        back_populates="templates",
    )
    creator: Mapped["User | None"] = relationship("User", back_populates="templates")


class TemplateCategoryMapping(Base):
    """模板-分类 多对多映射表"""
    __tablename__ = "template_category_mapping"

    template_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("templates.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("template_categories.id", ondelete="CASCADE"), primary_key=True
    )


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: uuid.uuid4().hex
    )
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=True)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="user")  # user / admin
    avatar_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="用户头像 URL"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # relationships
    templates: Mapped[list["Template"]] = relationship("Template", back_populates="creator")
    game_settings: Mapped["UserGameSettings | None"] = relationship(
        "UserGameSettings", back_populates="user", uselist=False,
    )


class UserGameSettings(Base):
    """用户游戏设置表（一对一关联用户）"""
    __tablename__ = "user_game_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True, comment="用户ID（一对一）"
    )

    # ---- 音频设置 ----
    bgm_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="自定义 BGM 文件 URL"
    )
    bgm_volume: Mapped[float] = mapped_column(
        default=0.7, comment="BGM 音量 (0.0 ~ 1.0)"
    )
    bgm_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="是否启用 BGM"
    )
    sfx_volume: Mapped[float] = mapped_column(
        default=0.8, comment="音效音量 (0.0 ~ 1.0)"
    )

    # ---- 视觉设置 ----
    bg_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="自定义游戏背景图 URL"
    )
    text_speed: Mapped[str] = mapped_column(
        String(16), default="normal",
        comment="文字显示速度: slow / normal / fast / instant"
    )
    theme: Mapped[str] = mapped_column(
        String(16), default="dark",
        comment="界面主题: dark / light / custom"
    )
    font_size: Mapped[int] = mapped_column(
        Integer, default=16, comment="对话文字字号 (px)"
    )

    # ---- 游戏偏好 ----
    auto_advance: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否自动推进对话"
    )
    show_affection_popup: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="是否显示好感度变化弹窗"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # relationships
    user: Mapped["User"] = relationship("User", back_populates="game_settings")
