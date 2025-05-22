"""
安全模块

提供JWT令牌生成/验证、密码哈希等安全功能。
"""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import get_settings

# 获取应用配置
settings = get_settings()

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2密码Bearer配置
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/token")

# JWT算法
ALGORITHM = "HS256"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码

    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码

    Returns:
        bool: 密码是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希

    Args:
        password: 明文密码

    Returns:
        str: 哈希密码
    """
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """创建JWT访问令牌

    Args:
        data: 令牌数据
        expires_delta: 过期时间增量

    Returns:
        str: 编码后的JWT令牌
    """
    to_encode = data.copy()
    
    # 设置过期时间
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """创建JWT刷新令牌

    Args:
        data: 令牌数据
        expires_delta: 过期时间增量

    Returns:
        str: 编码后的JWT刷新令牌
    """
    to_encode = data.copy()
    
    # 设置过期时间，刷新令牌通常比访问令牌有更长的有效期
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # 默认刷新令牌有效期为7天
        expire = datetime.utcnow() + timedelta(days=7)
    
    # 添加令牌类型标识
    to_encode.update({"exp": expire, "token_type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """解码JWT访问令牌

    Args:
        token: JWT令牌

    Returns:
        Dict[str, Any]: 解码后的令牌数据

    Raises:
        HTTPException: 令牌无效
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )


def decode_refresh_token(token: str) -> Dict[str, Any]:
    """解码JWT刷新令牌

    Args:
        token: JWT刷新令牌

    Returns:
        Dict[str, Any]: 解码后的令牌数据

    Raises:
        HTTPException: 令牌无效或不是刷新令牌
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        
        # 验证令牌类型
        token_type = payload.get("token_type")
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌类型",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_token_from_header(authorization: str) -> str:
    """从授权头中获取令牌

    Args:
        authorization: 授权头

    Returns:
        str: JWT令牌

    Raises:
        HTTPException: 无效的认证方案
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    scheme, token = authorization.split()
    if scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证方案",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token


async def verify_token(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """验证JWT令牌

    Args:
        token: JWT令牌

    Returns:
        Dict[str, Any]: 用户信息

    Raises:
        HTTPException: 令牌无效
    """
    return decode_access_token(token)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """获取当前用户

    Args:
        token: JWT令牌

    Returns:
        Dict[str, Any]: 当前用户信息

    Raises:
        HTTPException: 无效的用户凭据
    """
    payload = decode_access_token(token)
    
    # 提取用户ID
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的用户凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # TODO: 从数据库获取用户信息
    # 此处为示例，实际应该从数据库查询用户信息
    user = {"id": user_id, "username": payload.get("username", "unknown")}
    
    return user


def check_permission(user: Dict[str, Any], required_permission: str) -> bool:
    """检查用户权限

    Args:
        user: 用户信息
        required_permission: 所需权限

    Returns:
        bool: 是否具有权限
    """
    # TODO: 实现实际权限检查逻辑
    # 此处为示例，实际应根据用户角色和权限进行检查
    user_permissions = user.get("permissions", [])
    return required_permission in user_permissions


class RateLimitError(HTTPException):
    """速率限制错误"""
    
    def __init__(self, detail: str = "请求频率过高，请稍后再试"):
        super().__init__(status_code=429, detail=detail)
