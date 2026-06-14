"""
织梦绮谭 - 文件上传 API

提供用户头像、角色头像/立绘、背景图、BGM 等文件上传接口。
所有接口均需认证（登录状态），上传后返回可公开访问的 URL。
"""

import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.template_models import User, Template
from app.auth import get_current_user
from app.storage import storage
from loguru import logger

router = APIRouter()


# ---- 辅助函数 ----

def _sanitize_name(name: str) -> str:
    """清理文件名，移除非法字符"""
    name = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', name)
    return name[:80] or "unnamed"


def _ext_from_filename(filename: str) -> str:
    """从文件名中提取扩展名"""
    if '.' in filename:
        return filename.rsplit('.', 1)[-1].lower()
    return ""


# ---- 用户头像上传 ----

@router.post("/avatar", summary="上传用户头像")
async def upload_user_avatar(
    file: UploadFile = File(..., description="头像图片 (PNG/JPEG/WebP, 最大5MB)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    上传当前用户的头像图片。
    如果用户已有头像，旧文件将被替换。
    """
    if not file.content_type or file.content_type not in storage.IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的图片格式: {file.content_type}，仅支持 PNG/JPEG/WebP/GIF",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="文件内容为空")

    try:
        # 上传到 MinIO（UUID 文件名，不会覆盖旧文件）
        url = storage.upload_user_avatar(data, file.content_type, user.id)

        # 只有新旧 URL 不同时才删除旧文件（防止误删刚上传的文件）
        old_url = user.avatar_url
        if old_url and old_url != url:
            try:
                storage.delete_file(old_url)
                logger.info(f"旧头像已删除: {old_url}")
            except Exception as del_err:
                logger.warning(f"旧头像删除失败（不影响使用）: {del_err}")

        # 更新数据库
        user.avatar_url = url
        await db.commit()

        return {"url": url, "message": "头像上传成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {e}")


# ---- 角色头像/立绘上传 ----

@router.post("/character", summary="上传角色头像/立绘")
async def upload_character_avatar(
    template_id: str = Form(..., description="角色模板 ID (如 char_lingxue)"),
    file: UploadFile = File(..., description="角色图片 (PNG/JPEG/WebP, 最大5MB)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    上传角色的头像或立绘图片。
    可以是预设角色（admin）或用户自建角色。
    """
    if not file.content_type or file.content_type not in storage.IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的图片格式: {file.content_type}",
        )

    # 查找模板
    stmt = select(Template).where(Template.template_id == template_id)
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail=f"模板 '{template_id}' 不存在")

    # 权限检查：预设模板只有 admin 可改，自建模板只有创建者可改
    if template.is_preset and user.role != "admin":
        raise HTTPException(status_code=403, detail="预设模板仅管理员可修改")
    if not template.is_preset and template.creator_id != user.id:
        raise HTTPException(status_code=403, detail="无权修改他人创建的模板")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="文件内容为空")

    logger.info(f"角色头像上传: template_id={template_id}, size={len(data)}B, content_type={file.content_type}, user_id={user.id}")

    try:
        is_user_char = not template.is_preset
        uid = user.id if is_user_char else None
        url = storage.upload_character_avatar(data, file.content_type, template_id, user_id=uid)
        logger.info(f"文件已上传到 MinIO: {url}")

        # 先提交数据库，成功后再删除旧文件（避免数据库回滚后旧文件已删）
        old_avatar_url = template.avatar_url
        template.avatar_url = url
        await db.commit()
        logger.info(f"数据库已更新: template={template_id}, avatar_url={url}")

        # 数据库提交成功后才删除旧文件（且新旧 URL 不同时）
        if old_avatar_url and old_avatar_url != url:
            try:
                storage.delete_file(old_avatar_url)
                logger.info(f"旧头像已删除: {old_avatar_url}")
            except Exception as del_err:
                logger.warning(f"旧头像删除失败（不影响使用）: {del_err}")

        return {"url": url, "message": "角色图片上传成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {e}")


# ---- 背景图上传 ----

@router.post("/background", summary="上传场景背景图")
async def upload_background(
    name: str = Form(..., description="背景图名称（英文或中文，用于路径标识）"),
    file: UploadFile = File(..., description="背景图片 (PNG/JPEG/WebP, 最大5MB)"),
    is_preset: bool = Form(default=False, description="是否为预设背景（仅 admin）"),
    user: User = Depends(get_current_user),
):
    """
    上传场景背景图片。
    预设背景对所有用户可见，用户自定义背景仅自己可见。
    """
    if not file.content_type or file.content_type not in storage.IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的图片格式: {file.content_type}",
        )

    if is_preset and user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可上传预设背景")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="文件内容为空")

    safe_name = _sanitize_name(name)
    try:
        uid = None if is_preset else user.id
        url = storage.upload_background(data, file.content_type, safe_name, user_id=uid)
        return {"url": url, "message": "背景图上传成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {e}")


# ---- BGM 上传 ----

@router.post("/bgm", summary="上传背景音乐")
async def upload_bgm(
    name: str = Form(..., description="BGM 名称（用于路径标识）"),
    file: UploadFile = File(..., description="音频文件 (MP3/OGG/WAV/FLAC, 最大20MB)"),
    is_preset: bool = Form(default=False, description="是否为预设 BGM（仅 admin）"),
    user: User = Depends(get_current_user),
):
    """
    上传背景音乐文件。
    预设 BGM 对所有用户可见，用户上传的 BGM 仅自己可用。
    """
    if not file.content_type or file.content_type not in storage.AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的音频格式: {file.content_type}，仅支持 MP3/OGG/WAV/FLAC",
        )

    if is_preset and user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可上传预设 BGM")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="文件内容为空")

    safe_name = _sanitize_name(name)
    try:
        uid = None if is_preset else user.id
        url = storage.upload_bgm(data, file.content_type, safe_name, user_id=uid)
        return {"url": url, "message": "BGM 上传成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {e}")


# ---- 通用文件上传（高级用法） ----

@router.post("/file", summary="通用文件上传")
async def upload_generic_file(
    category: str = Form(..., description="文件分类: avatar/character/background/bgm"),
    file: UploadFile = File(..., description="上传文件"),
    name: Optional[str] = Form(default=None, description="自定义文件名（可选）"),
    user: User = Depends(get_current_user),
):
    """
    通用文件上传接口，根据 category 自动选择存储目录。
    返回上传后的公开访问 URL。
    """
    category_map = {
        "avatar": (storage.PREFIX_USER_AVATAR, storage.IMAGE_TYPES),
        "character": (storage.PREFIX_USER_CHAR, storage.IMAGE_TYPES),
        "background": (storage.PREFIX_USER_BG, storage.IMAGE_TYPES),
        "bgm": (storage.PREFIX_USER_BGM, storage.AUDIO_TYPES),
    }

    if category not in category_map:
        raise HTTPException(
            status_code=400,
            detail=f"无效的 category: {category}，可选: {list(category_map.keys())}",
        )

    prefix, allowed_types = category_map[category]

    if not file.content_type or file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"文件类型 {file.content_type} 不在 {category} 允许范围内",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="文件内容为空")

    ext = _ext_from_filename(file.filename or "")
    custom = _sanitize_name(name) if name else None

    try:
        url = storage.upload_file(
            data=data,
            content_type=file.content_type,
            prefix=prefix,
            file_ext=ext,
            user_id=user.id,
            custom_name=custom,
        )
        return {"url": url, "message": "文件上传成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {e}")


# ---- 删除文件 ----

@router.delete("/file", summary="删除已上传的文件")
async def delete_uploaded_file(
    url: str = Form(..., description="要删除的文件 URL"),
    user: User = Depends(get_current_user),
):
    """
    删除已上传的文件。
    用户只能删除自己上传的文件（URL 中包含 user_id 路径的文件）。
    管理员可以删除任何文件。
    """
    # 安全检查：确保用户只能删除自己的文件
    if f"/user/" in url and user.id not in url and user.role != "admin":
        raise HTTPException(status_code=403, detail="无权删除他人上传的文件")

    success = storage.delete_file(url)
    if success:
        return {"message": "文件已删除"}
    else:
        raise HTTPException(status_code=404, detail="文件不存在或删除失败")
