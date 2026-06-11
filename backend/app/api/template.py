"""
Narrator Engine - 模板管理 API

处理世界观/角色/剧本模板的 CRUD：
  - 列出所有模板（支持按类型/分类过滤 + 分页）
  - 获取模板详情
  - 创建自定义模板
  - 克隆预设模板

数据源: MySQL (通过 SQLAlchemy 2.0 async ORM)
"""

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.template_models import Template, TemplateCategory
from app.schemas.schemas import (
    TemplateSummary,
    TemplateDetail,
    TemplateCreateRequest,
    MessageResponse,
)

router = APIRouter()


@router.get("", summary="获取模板列表（支持分页）")
async def list_templates(
    template_type: str | None = Query(default=None, description="过滤类型: world/character/scenario"),
    category_code: str | None = Query(default=None, description="按分类 code 过滤"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=50, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取模板的摘要列表，支持分页。
    可通过 template_type 过滤类型: world / character / scenario
    可通过 category_code 按分类过滤。
    """
    base_stmt = select(Template).options(selectinload(Template.categories))

    # 类型过滤
    if template_type:
        base_stmt = base_stmt.where(Template.template_type == template_type)

    # 分类过滤
    if category_code:
        base_stmt = (
            base_stmt
            .join(Template.categories)
            .where(TemplateCategory.code == category_code)
        )

    # 总数
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0
    total_pages = max(1, math.ceil(total / page_size))

    # 分页
    stmt = base_stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    templates = result.scalars().all()

    items = [
        TemplateSummary(
            template_id=t.template_id,
            template_type=t.template_type,
            name=t.name,
            is_preset=t.is_preset,
            description=t.description or "",
            tags=t.tags or [],
        )
        for t in templates
    ]

    return {
        "items": [item.model_dump() for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/{template_id}", response_model=TemplateDetail, summary="获取模板详情")
async def get_template(template_id: str, db: AsyncSession = Depends(get_db)):
    """获取单个模板的完整数据"""
    stmt = (
        select(Template)
        .options(selectinload(Template.categories))
        .where(Template.template_id == template_id)
    )
    result = await db.execute(stmt)
    t = result.scalar_one_or_none()

    if not t:
        raise HTTPException(status_code=404, detail=f"模板不存在: {template_id}")

    return TemplateDetail(
        template_id=t.template_id,
        template_type=t.template_type,
        name=t.name,
        version=t.data.get("version", "1.0") if isinstance(t.data, dict) else "1.0",
        is_preset=t.is_preset,
        description=t.description or "",
        data=t.data,
    )


@router.post("", response_model=MessageResponse, summary="创建自定义模板")
async def create_template(
    request: TemplateCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    创建一个新的自定义模板。
    自定义模板 is_preset=False，存储在 MySQL 中。
    """
    # 如果指定了 clone_from，先加载源模板数据
    source_data = {}
    if request.clone_from:
        src_stmt = select(Template).where(Template.template_id == request.clone_from)
        src_result = await db.execute(src_stmt)
        source = src_result.scalar_one_or_none()
        if source:
            source_data = source.data if isinstance(source.data, dict) else {}

    # 生成唯一 template_id
    new_template_id = f"custom_{request.template_type}_{uuid.uuid4().hex[:8]}"

    # 合并数据：clone_from 的数据作为基底，request.data 覆盖
    merged_data = {**source_data, **request.data}

    new_template = Template(
        template_id=new_template_id,
        template_type=request.template_type,
        name=request.name,
        description=request.description,
        is_preset=False,
        data=merged_data,
        tags=[],
    )
    db.add(new_template)
    await db.flush()

    return MessageResponse(
        success=True,
        message=f"模板已创建: {new_template_id}",
        data={"template_id": new_template_id},
    )


@router.post("/{template_id}/clone", response_model=MessageResponse, summary="克隆模板")
async def clone_template(
    template_id: str,
    new_name: str | None = Query(default=None, description="克隆后的新名称"),
    db: AsyncSession = Depends(get_db),
):
    """
    克隆一个已有模板为自定义版本。
    用户可以在克隆的基础上自由修改。
    """
    # 查找源模板
    src_stmt = (
        select(Template)
        .options(selectinload(Template.categories))
        .where(Template.template_id == template_id)
    )
    src_result = await db.execute(src_stmt)
    source = src_result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="源模板不存在")

    # 创建克隆
    clone_template_id = f"custom_clone_{template_id}_{uuid.uuid4().hex[:6]}"
    cloned = Template(
        template_id=clone_template_id,
        template_type=source.template_type,
        name=new_name or f"{source.name} (副本)",
        description=source.description or "",
        is_preset=False,
        data=source.data,
        tags=source.tags or [],
    )
    db.add(cloned)
    await db.flush()

    return MessageResponse(
        success=True,
        message=f"模板已克隆: {clone_template_id}",
        data={"template_id": clone_template_id},
    )
