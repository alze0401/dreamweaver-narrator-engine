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
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # relationships
    templates: Mapped[list["Template"]] = relationship("Template", back_populates="creator")
