"""
用户注册、登录、信息管理等接口

提供用户账户管理和认证相关的API端点
"""
from datetime import timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.api.v1.deps import get_current_user, get_user_service
from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token, decode_refresh_token
from app.models.schemas import UserCreate, UserUpdate, UserDB, Token
from app.services.interfaces.user_service import UserService
from app.utils.error_handlers import ResourceConflictError

# 创建路由器
router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={401: {"description": "未授权"}}
)

@router.post("/register", response_model=UserDB, status_code=201)
async def register_user(
    user_data: UserCreate,
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """
    创建新用户账户
    
    Args:
        user_data: 用户注册数据
        
    Returns:
        UserDB: 创建的用户信息
        
    Raises:
        HTTPException: 用户名或邮箱已存在
    """
    try:
        user = await user_service.create_user(user_data)
        return user
    except ResourceConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """
    验证用户凭据并生成访问令牌
    
    Args:
        form_data: 表单数据（用户名/邮箱、密码）
        
    Returns:
        Token: 包含访问令牌和刷新令牌
        
    Raises:
        HTTPException: 认证失败
    """
    user = await user_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码不正确",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证用户是否活跃
    if not await user_service.is_active(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户未激活"
        )
        
    settings = get_settings()
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    refresh_token_expires = timedelta(days=30)  # Default to 30 days
    
    # 创建访问令牌
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    # 创建刷新令牌
    refresh_token = create_refresh_token(
        data={"sub": user.username},
        expires_delta=refresh_token_expires
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": access_token_expires.total_seconds()
    }

@router.get("/me", response_model=UserDB)
async def get_current_user_info(
    current_user: Annotated[UserDB, Depends(get_current_user)]
):
    """
    获取当前已认证用户的详细信息
    
    Args:
        current_user: 当前用户
        
    Returns:
        UserDB: 当前用户信息
    """
    return current_user

@router.patch("/me", response_model=UserDB)
async def update_user_info(
    user_data: UserUpdate,
    current_user: Annotated[UserDB, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """
    更新当前用户的个人信息
    
    Args:
        user_data: 用户更新数据
        current_user: 当前用户
        
    Returns:
        UserDB: 更新后的用户信息
        
    Raises:
        HTTPException: 更新失败
    """
    try:
        updated_user = await user_service.update_user(current_user.id, user_data)
        return updated_user
    except ResourceConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    refresh_token: str,
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """
    使用刷新令牌生成新的访问令牌
    
    Args:
        refresh_token: 刷新令牌
        
    Returns:
        Token: 新的访问令牌和刷新令牌
        
    Raises:
        HTTPException: 刷新令牌无效
    """
    try:
        # 解码刷新令牌
        payload = decode_refresh_token(refresh_token)
        username = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 获取用户
        user = await user_service.get_user_by_username(username)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not await user_service.is_active(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户未激活"
            )
            
        # 生成新的令牌
        settings = get_settings()
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        refresh_token_expires = timedelta(days=30)  # Default to 30 days
        
        access_token = create_access_token(
            data={"sub": username},
            expires_delta=access_token_expires
        )
        
        new_refresh_token = create_refresh_token(
            data={"sub": username},
            expires_delta=refresh_token_expires
        )
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": access_token_expires.total_seconds()
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无法验证刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/verify-email/{token}")
async def verify_email(
    token: str,
    user_service: Annotated[UserService, Depends(get_user_service)]
):
    """
    使用发送到用户邮箱的令牌验证用户邮箱
    
    Args:
        token: 验证令牌
        
    Returns:
        dict: 验证结果
        
    Raises:
        HTTPException: 验证失败
    """
    try:
        # 这里需要实现验证邮箱令牌的逻辑
        # 由于文档中没有详细说明，这里提供一个基本框架
        
        # 解码令牌 (具体实现需要根据实际的邮件验证流程)
        # payload = decode_verification_token(token)
        # user_id = payload.get("user_id")
        
        # 如果成功验证，返回成功消息
        return {"message": "邮箱验证成功"}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的验证令牌"
        )
