"""
Narrator Engine - 模板管理 API

处理世界观/角色/剧本模板的 CRUD：
  - 列出所有模板（支持按类型/分类过滤 + 分页）
  - 获取模板详情
  - 创建自定义模板
  - 克隆预设模板

数据源: MySQL (通过 SQLAlchemy 2.0 async ORM)
"""

import json
import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from app.database import get_db
from app.models.template_models import Template, TemplateCategory, TemplateCategoryMapping, User
from app.auth import get_optional_user, get_current_user
from app.schemas.schemas import (
    TemplateSummary,
    TemplateDetail,
    TemplateCreateRequest,
    TemplateUpdateRequest,
    AIGenerateRequest,
    MessageResponse,
)
from app.llm.deepseek import get_llm_provider
from app.llm.base import LLMMessage
from app.llm.template_schemas import TEMPLATE_TYPE_TO_MODEL

router = APIRouter()


async def _resolve_categories(db: AsyncSession, category_codes: list[str]) -> list[TemplateCategory]:
    """根据 code 列表查询对应的 TemplateCategory 对象列表"""
    if not category_codes:
        return []
    stmt = select(TemplateCategory).where(TemplateCategory.code.in_(category_codes))
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("", summary="获取模板列表（支持分页）")
async def list_templates(
    template_type: str | None = Query(default=None, description="过滤类型: world/character/scenario"),
    category_code: str | None = Query(default=None, description="按分类 code 过滤"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=50, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """
    获取模板的摘要列表，支持分页。
    - 已登录: 显示公共预设模板 + 用户自定义模板
    - 未登录: 只显示公共预设模板
    """
    base_stmt = select(Template).options(selectinload(Template.categories))

    # 权限过滤：公共预设 OR 当前用户创建
    if current_user:
        base_stmt = base_stmt.where(
            (Template.is_preset == True) | (Template.creator_id == current_user.id)
        )
    else:
        base_stmt = base_stmt.where(Template.is_preset == True)

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
            avatar_url=t.avatar_url,
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
        categories=[{"code": c.code, "name": c.name} for c in t.categories],
        avatar_url=t.avatar_url,
    )


@router.post("", response_model=MessageResponse, summary="创建自定义模板")
async def create_template(
    request: TemplateCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建一个新的自定义模板（需要登录）。
    自定义模板 is_preset=False，归属当前用户。
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
        creator_id=current_user.id,
        data=merged_data,
        tags=[],
    )
    db.add(new_template)
    await db.flush()

    # 关联分类（直接操作映射表，避免 async 懒加载 MissingGreenlet）
    if request.category_codes:
        cats = await _resolve_categories(db, request.category_codes)
        for cat in cats:
            db.add(TemplateCategoryMapping(
                template_id=new_template.id,
                category_id=cat.id,
            ))
        if cats:
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
    current_user: User = Depends(get_current_user),
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
        creator_id=current_user.id,
        data=source.data,
        tags=source.tags or [],
    )
    db.add(cloned)
    await db.flush()

    # 复制源模板的分类关联（直接操作映射表，避免 async 懒加载）
    if source.categories:
        for cat in source.categories:
            db.add(TemplateCategoryMapping(
                template_id=cloned.id,
                category_id=cat.id,
            ))
        await db.flush()

    return MessageResponse(
        success=True,
        message=f"模板已克隆: {clone_template_id}",
        data={"template_id": clone_template_id},
    )


@router.put("/{template_id}", response_model=MessageResponse, summary="更新自定义模板")
async def update_template(
    template_id: str,
    request: TemplateUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新一个自定义模板（需要登录）。
    仅模板创建者或管理员可以编辑，预设模板不可修改。
    """
    stmt = (
        select(Template)
        .options(selectinload(Template.categories))
        .where(Template.template_id == template_id)
    )
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    if template.is_preset:
        raise HTTPException(status_code=403, detail="预设模板不可修改")

    if template.creator_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权修改此模板")

    # 部分更新：仅覆盖请求中提供的字段
    if request.name is not None:
        template.name = request.name
    if request.description is not None:
        template.description = request.description
    if request.data is not None:
        template.data = request.data

    # 更新分类关联（category_codes 为 None 时不更新，空列表表示清除所有关联）
    if request.category_codes is not None:
        cats = await _resolve_categories(db, request.category_codes)
        template.categories = cats

    await db.flush()

    return MessageResponse(
        success=True,
        message=f"模板已更新: {template_id}",
        data={"template_id": template_id},
    )


@router.delete("/{template_id}", response_model=MessageResponse, summary="删除自定义模板")
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除一个自定义模板（需要登录）。
    仅模板创建者或管理员可以删除，预设模板不可删除。
    """
    stmt = select(Template).where(Template.template_id == template_id)
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    if template.is_preset:
        raise HTTPException(status_code=403, detail="预设模板不可删除")

    if template.creator_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权删除此模板")

    await db.delete(template)
    await db.flush()

    return MessageResponse(
        success=True,
        message=f"模板已删除: {template_id}",
    )


@router.post("/ai-generate", summary="AI 生成模板数据")
async def ai_generate_template(
    request: AIGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    使用 LLM + LangChain 结构化输出生成模板配置数据。
    优先使用 with_structured_output (Pydantic schema 约束)，
    失败时回退到 JSON 模式。
    """
    type_labels = {
        "world": "世界观",
        "character": "角色",
        "scenario": "剧本",
    }
    type_name = type_labels.get(request.template_type, request.template_type)

    # 获取对应的 Pydantic 结构化模型
    output_model = TEMPLATE_TYPE_TO_MODEL.get(request.template_type)
    if not output_model:
        raise HTTPException(status_code=400, detail=f"不支持的模板类型: {request.template_type}")

    system_prompt = (
        "你是一个专业的 Galgame 模板配置生成器。\n"
        "根据用户描述，生成高质量、富有创意的模板配置。\n"
        "所有文本内容请使用中文。\n"
        "description 字段应该是一段简洁但有吸引力的描述，概括模板的核心特色。"
    )

    user_prompt = (
        f"请根据以下描述，生成一个{type_name}类型的 Galgame 模板配置。\n\n"
        f"用户描述: {request.user_prompt}\n\n"
        "要求:\n"
        "- 内容要丰富、有创意，符合 Galgame 的风格\n"
        "- description 用一两句话概括模板特色\n"
        "- 所有字段都要填写，不要留空"
    )

    try:
        provider = get_llm_provider()
        llm = provider._llm

        # 尝试 LangChain 结构化输出
        try:
            structured_llm = llm.with_structured_output(output_model)
            from langchain_core.messages import SystemMessage, HumanMessage

            result = await structured_llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ])

            # result 是一个 Pydantic 模型实例，转为 dict
            data = result.model_dump()
            logger.info(f"AI 结构化生成成功: type={request.template_type}")

            # 提取顶层 name/description，放到外层供前端使用
            output = {
                "name": data.pop("name", ""),
                "description": data.pop("description", ""),
            }
            # world 类型的 Pydantic schema 是扁平字段，需要包装在 "world" 键下
            # character/scenario 类型的数据已经自带嵌套结构 (character: {...}, scenario: {...})
            if request.template_type == "world":
                output["world"] = data
            else:
                output.update(data)
            return {"success": True, "data": output}

        except Exception as struct_err:
            logger.warning(
                f"结构化输出失败，回退到 JSON 模式: {type(struct_err).__name__}: {struct_err}"
            )

        # 回退：JSON 模式（带明确的输出结构要求）
        from langchain_core.messages import SystemMessage, HumanMessage

        schema_hints = {
            "world": '{ "name": "模板名称", "description": "简短描述", "world": { "era": "时代背景", "genre": ["标签1", "标签2"], "setting_description": "详细世界设定", "rules": ["规则1", "规则2"] } }',
            "character": '{ "name": "模板名称", "description": "简短描述", "character": { "full_name": "角色名", "personality": { "archetype": "原型", "mbti": "INTJ", "likes": [...], "dislikes": [...], "speech_style": { "tone": "风格" } }, "relationships": {} }, "affection_config": { "initial_value": 0 } }',
            "scenario": '{ "name": "模板名称", "description": "简短描述", "scenario": { "premise": "故事前提", "opening_scene": { "location": "地点", "time": "时间", "weather": "" }, "chapter_beats": [], "plot_hooks": ["钩子1"], "estimated_chapters": 5 } }',
        }
        schema_hint = schema_hints.get(request.template_type, "")

        fallback_prompt = (
            f"{user_prompt}\n\n"
            f"请以 JSON 格式输出，严格遵循以下结构:\n{schema_hint}\n"
            "所有文本使用中文。"
        )

        raw = await provider.chat_completion(
            messages=[
                LLMMessage(role="system", content=system_prompt + "\n只输出合法 JSON。"),
                LLMMessage(role="user", content=fallback_prompt),
            ],
            temperature=0.85,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)

        data = json.loads(cleaned)
        return {"success": True, "data": data}

    except json.JSONDecodeError as e:
        logger.error(f"AI 生成模板 JSON 解析失败: {e}")
        raise HTTPException(status_code=500, detail="AI 返回的数据格式无法解析")
    except Exception as e:
        logger.error(f"AI 生成模板失败: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"AI 生成失败: {str(e)}")
