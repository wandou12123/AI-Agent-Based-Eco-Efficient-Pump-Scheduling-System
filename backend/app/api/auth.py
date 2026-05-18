from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_token, get_current_user
from app.models.models import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserInfo

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "用户名已存在")
    user = User(username=req.username, password_hash=hash_password(req.password))
    db.add(user)
    await db.flush()
    token = create_token(user.id, user.username, user.role)
    return TokenResponse(access_token=token, user_id=user.id, username=user.username, role=user.role)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    token = create_token(user.id, user.username, user.role)
    return TokenResponse(access_token=token, user_id=user.id, username=user.username, role=user.role)


@router.get("/me", response_model=UserInfo)
async def me(user: User = Depends(get_current_user)):
    return user
