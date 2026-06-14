"""
织梦绮谭 - 游戏设置 API

提供用户游戏设置的 CRUD 接口：
  - 获取当前用户的游戏设置
  - 更新游戏设置（BGM、背景、音量、文字速度、主题等）
  - 重置为默认设置
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.template_models import User, UserGameSettings
from app.auth import get_current_user
from app.storage import storage

router = APIRouter()


# ---- 请求/响应模型 ----

class GameSettingsResponse(BaseModel):
    """游戏设置响应"""
    bgm_url: Optional[str] = None
    bgm_volume: float = 0.7
    bgm_enabled: bool = True
    sfx_volume: float = 0.8
    bg_url: Optional[str] = None
    text_speed: str = "normal"
    theme: str = "dark"
    font_size: int = 16
    auto_advance: bool = False
    show_affection_popup: bool = True


class GameSettingsUpdate(BaseModel):
    """游戏设置更新（部分更新，仅传需要修改的字段）"""
    bgm_url: Optional[str] = None
    bgm_volume: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    bgm_enabled: Optional[bool] = None
    sfx_volume: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    bg_url: Optional[str] = None
    text_speed: Optional[str] = None
    theme: Optional[str] = None
    font_size: Optional[int] = Field(default=None, ge=10, le=32)
    auto_advance: Optional[bool] = None
    show_affection_popup: Optional[bool] = None


class BgmUploadRequest(BaseModel):
    """通过 URL 设置 BGM（已上传的文件）"""
    bgm_url: str = Field(..., description="已上传的 BGM 文件 URL")


class BgUploadRequest(BaseModel):
    """通过 URL 设置游戏背景（已上传的文件）"""
    bg_url: str = Field(..., description="已上传的背景图 URL")


# ---- 默认值 ----

_DEFAULTS = {
    "bgm_url": None,
    "bgm_volume": 0.7,
    "bgm_enabled": True,
    "sfx_volume": 0.8,
    "bg_url": None,
    "text_speed": "normal",
    "theme": "dark",
    "font_size": 16,
    "auto_advance": False,
    "show_affection_popup": True,
}

_VALID_TEXT_SPEEDS = {"slow", "normal", "fast", "instant"}
_VALID_THEMES = {"dark", "light", "sakura", "ocean", "forest", "sunset"}


# ---- 辅助函数 ----

async def _get_or_create_settings(
    user: User, db: AsyncSession
) -> UserGameSettings:
    """获取用户的游戏设置，不存在则创建默认设置"""
    stmt = select(UserGameSettings).where(UserGameSettings.user_id == user.id)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()

    if settings is None:
        settings = UserGameSettings(user_id=user.id)
        db.add(settings)
        await db.flush()

    return settings


def _settings_to_response(settings: UserGameSettings) -> GameSettingsResponse:
    """ORM 模型转响应模型"""
    return GameSettingsResponse(
        bgm_url=settings.bgm_url,
        bgm_volume=settings.bgm_volume,
        bgm_enabled=settings.bgm_enabled,
        sfx_volume=settings.sfx_volume,
        bg_url=settings.bg_url,
        text_speed=settings.text_speed,
        theme=settings.theme,
        font_size=settings.font_size,
        auto_advance=settings.auto_advance,
        show_affection_popup=settings.show_affection_popup,
    )


# ---- API 端点 ----

@router.get("/", summary="获取游戏设置", response_model=GameSettingsResponse)
async def get_game_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前用户的游戏设置。
    如果用户从未设置过，返回默认值。
    """
    settings = await _get_or_create_settings(user, db)
    return _settings_to_response(settings)


@router.patch("/", summary="更新游戏设置", response_model=GameSettingsResponse)
async def update_game_settings(
    update: GameSettingsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    部分更新游戏设置。
    仅传入需要修改的字段，未传的字段保持不变。
    """
    settings = await _get_or_create_settings(user, db)

    # 逐字段更新（只更新非 None 的值）
    update_data = update.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="未提供任何更新字段")

    # 校验 text_speed
    if "text_speed" in update_data and update_data["text_speed"] not in _VALID_TEXT_SPEEDS:
        raise HTTPException(
            status_code=400,
            detail=f"无效的 text_speed: {update_data['text_speed']}，可选: {list(_VALID_TEXT_SPEEDS)}",
        )

    # 校验 theme
    if "theme" in update_data and update_data["theme"] not in _VALID_THEMES:
        raise HTTPException(
            status_code=400,
            detail=f"无效的 theme: {update_data['theme']}，可选: {list(_VALID_THEMES)}",
        )

    # 应用更新
    for field, value in update_data.items():
        setattr(settings, field, value)

    await db.commit()
    await db.refresh(settings)

    return _settings_to_response(settings)


@router.post("/reset", summary="重置游戏设置为默认值", response_model=GameSettingsResponse)
async def reset_game_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    将游戏设置重置为系统默认值。
    不会删除已上传的 BGM/背景文件，但会清空引用。
    """
    settings = await _get_or_create_settings(user, db)

    for field, default_value in _DEFAULTS.items():
        setattr(settings, field, default_value)

    await db.commit()
    await db.refresh(settings)

    return _settings_to_response(settings)


@router.post("/bgm", summary="设置 BGM（通过已有 URL）", response_model=GameSettingsResponse)
async def set_bgm_url(
    request: BgmUploadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    通过已上传的文件 URL 设置游戏 BGM。
    文件需通过 /api/upload/bgm 接口先行上传。
    """
    settings = await _get_or_create_settings(user, db)

    # 如果旧 BGM 存在且是用户上传的，可以删除旧文件
    if settings.bgm_url and settings.bgm_url != request.bgm_url:
        if f"/user/" in settings.bgm_url and user.id in settings.bgm_url:
            storage.delete_file(settings.bgm_url)

    settings.bgm_url = request.bgm_url
    await db.commit()
    await db.refresh(settings)

    return _settings_to_response(settings)


@router.post("/background", summary="设置游戏背景（通过已有 URL）", response_model=GameSettingsResponse)
async def set_bg_url(
    request: BgUploadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    通过已上传的文件 URL 设置游戏背景图。
    文件需通过 /api/upload/background 接口先行上传。
    """
    settings = await _get_or_create_settings(user, db)

    # 删除旧的用户背景
    if settings.bg_url and settings.bg_url != request.bg_url:
        if f"/user/" in settings.bg_url and user.id in settings.bg_url:
            storage.delete_file(settings.bg_url)

    settings.bg_url = request.bg_url
    await db.commit()
    await db.refresh(settings)

    return _settings_to_response(settings)


@router.delete("/bgm", summary="移除 BGM 设置")
async def remove_bgm(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """移除当前 BGM 设置（不删除文件，仅清空引用）"""
    settings = await _get_or_create_settings(user, db)
    settings.bgm_url = None
    await db.commit()
    return {"message": "BGM 已移除"}


@router.delete("/background", summary="移除背景设置")
async def remove_bg(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """移除当前背景设置（不删除文件，仅清空引用）"""
    settings = await _get_or_create_settings(user, db)
    settings.bg_url = None
    await db.commit()
    return {"message": "背景图已移除"}
