"""模板分类 API"""
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database import get_db
from app.models.template_models import TemplateCategory, Template, User
from app.auth import get_optional_user

router = APIRouter()


@router.get("", summary="获取所有分类")
async def list_categories(db: AsyncSession = Depends(get_db)):
    """获取所有模板分类列表，按 sort_order 排序"""
    try:
        stmt = select(TemplateCategory).order_by(TemplateCategory.sort_order)
        result = await db.execute(stmt)
        cats = result.scalars().all()
        return [
            {
                "id": c.id,
                "code": c.code,
                "name": c.name,
                "description": c.description or "",
                "icon": c.icon or "",
                "sort_order": c.sort_order,
            }
            for c in cats
        ]
    except Exception as e:
        logger.error(f"获取分类列表失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"数据库查询失败: {type(e).__name__}: {e}",
        )


@router.get("/{category_code}/templates", summary="获取分类下的模板列表")
async def list_templates_by_category(
    category_code: str,
    template_type: str | None = Query(default=None, description="过滤类型: world/character/scenario"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """获取指定分类下的模板列表（支持类型过滤 + 分页）"""

    try:
        # 先找分类
        cat_stmt = select(TemplateCategory).where(TemplateCategory.code == category_code)
        cat_result = await db.execute(cat_stmt)
        category = cat_result.scalar_one_or_none()
        if not category:
            raise HTTPException(404, detail=f"分类不存在: {category_code}")

        # 通过中间表查模板，预加载 categories 关系避免懒加载
        base_stmt = (
            select(Template)
            .join(Template.categories)
            .where(TemplateCategory.id == category.id)
            .options(selectinload(Template.categories))
        )

        # 权限过滤：公共预设 OR 当前用户创建
        if current_user:
            base_stmt = base_stmt.where(
                (Template.is_preset == True) | (Template.creator_id == current_user.id)
            )
        else:
            base_stmt = base_stmt.where(Template.is_preset == True)

        if template_type:
            base_stmt = base_stmt.where(Template.template_type == template_type)

        # 总数
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0
        total_pages = max(1, math.ceil(total / page_size))

        # 分页
        stmt = base_stmt.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        templates = result.scalars().all()

        return {
            "category": {"id": category.id, "code": category.code, "name": category.name},
            "items": [
                {
                    "template_id": t.template_id,
                    "template_type": t.template_type,
                    "name": t.name,
                    "description": t.description or "",
                    "is_preset": t.is_preset,
                    "tags": t.tags or [],
                    "categories": [{"code": c.code, "name": c.name} for c in t.categories],
                }
                for t in templates
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分类模板列表失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"数据库查询失败: {type(e).__name__}: {e}",
        )
