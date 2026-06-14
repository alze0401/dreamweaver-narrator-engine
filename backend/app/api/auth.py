"""
织梦绮谭 - 用户认证 API

提供注册、登录、获取当前用户信息接口。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.template_models import User
from app.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter()


# ---- 请求/响应模型 ----

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    display_name: str = Field(default="", max_length=64, description="显示名称")


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserInfo(BaseModel):
    id: str
    username: str
    display_name: str
    role: str
    avatar_url: str | None = None
    created_at: str


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码")


class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(None, max_length=64, description="显示名称")


class PasswordChangeResponse(BaseModel):
    success: bool = True
    message: str = "密码修改成功"


# ---- API 端点 ----

@router.post("/register", response_model=TokenResponse, summary="用户注册")
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    注册新用户并自动返回 JWT Token。
    用户名必须唯一，密码至少 6 位。
    """
    # 检查用户名是否已存在
    stmt = select(User).where(User.username == request.username)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"用户名 '{request.username}' 已被注册",
        )

    # 创建用户
    user = User(
        username=request.username,
        password_hash=hash_password(request.password),
        display_name=request.display_name or request.username,
        role="user",
    )
    db.add(user)
    await db.flush()

    # 生成 Token
    token = create_access_token({"sub": user.id, "username": user.username})

    return TokenResponse(
        access_token=token,
        user={
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
            "avatar_url": user.avatar_url,
        },
    )


@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    用户登录，验证用户名密码后返回 JWT Token。
    """
    stmt = select(User).where(User.username == request.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 生成 Token
    token = create_access_token({"sub": user.id, "username": user.username})

    return TokenResponse(
        access_token=token,
        user={
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
            "avatar_url": user.avatar_url,
        },
    )


@router.get("/me", response_model=UserInfo, summary="获取当前用户信息")
async def get_me(user: User = Depends(get_current_user)):
    """获取当前已认证用户的详细信息"""
    return UserInfo(
        id=user.id,
        username=user.username,
        display_name=user.display_name or user.username,
        role=user.role,
        avatar_url=user.avatar_url,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


@router.post("/change-password", response_model=PasswordChangeResponse, summary="修改密码")
async def change_password(
    request: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改当前用户的密码，需验证旧密码"""
    if not verify_password(request.old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码不正确",
        )
    user.password_hash = hash_password(request.new_password)
    await db.flush()
    return PasswordChangeResponse()


@router.patch("/profile", response_model=UserInfo, summary="更新个人资料")
async def update_profile(
    request: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新当前用户的个人资料（昵称等）"""
    if request.display_name is not None:
        user.display_name = request.display_name
    await db.flush()
    return UserInfo(
        id=user.id,
        username=user.username,
        display_name=user.display_name or user.username,
        role=user.role,
        avatar_url=user.avatar_url,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )
