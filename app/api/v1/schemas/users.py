"""
用户相关的请求/响应Pydantic模型

定义用户相关的API请求和响应数据结构
"""
from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, EmailStr, HttpUrl, Field, field_validator


class UserBase(BaseModel):
    """用户基本属性
    
    包含用户的基本信息字段
    """
    username: str = Field(..., description="用户名（唯一）")
    email: EmailStr = Field(..., description="电子邮件（唯一）")
    display_name: Optional[str] = Field(None, description="显示名称")


class UserCreate(UserBase):
    """用于创建用户的输入模型
    
    包含创建用户所需的所有字段
    """
    password: str = Field(..., description="用户密码")
    confirm_password: str = Field(..., description="确认密码")
    
    @field_validator('password')
    def password_must_be_strong(cls, v: str) -> str:
        """验证密码强度
        
        Args:
            v: 密码值
            
        Returns:
            str: 验证通过的密码
            
        Raises:
            ValueError: 密码不符合要求
        """
        if len(v) < 8:
            raise ValueError("密码长度不能少于8个字符")
        return v
    
    @field_validator('confirm_password')
    def passwords_match(cls, v: str, values: Dict[str, Any]) -> str:
        """验证两次输入的密码是否一致
        
        Args:
            v: 确认密码值
            values: 已验证的字段值
            
        Returns:
            str: 验证通过的确认密码
            
        Raises:
            ValueError: 两次密码不一致
        """
        if 'password' in values.data and v != values.data['password']:
            raise ValueError("两次输入的密码不一致")
        return v


class UserUpdate(BaseModel):
    """用于更新用户的输入模型
    
    包含可更新的用户字段
    """
    display_name: Optional[str] = Field(None, description="显示名称")
    avatar_url: Optional[HttpUrl] = Field(None, description="头像URL")
    bio: Optional[str] = Field(None, description="个人简介")
    
    @field_validator('*')
    def at_least_one_field(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """验证至少提供一个更新字段
        
        Args:
            values: 字段值字典
            
        Returns:
            Dict[str, Any]: 验证通过的字段值
            
        Raises:
            ValueError: 没有提供任何更新字段
        """
        if all(v is None for v in values.values()):
            raise ValueError("至少提供一个更新字段")
        return values


class UserResponse(BaseModel):
    """用户信息响应模型
    
    API返回的用户数据结构
    """
    id: str
    username: str
    email: EmailStr
    display_name: str
    is_active: bool
    is_verified: bool = False
    avatar_url: Optional[HttpUrl] = None
    bio: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    role: Optional[str] = "user"
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """身份验证令牌响应模型
    
    包含访问令牌和刷新令牌
    """
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field("bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求模型
    
    用于请求新的访问令牌
    """
    refresh_token: str = Field(..., description="刷新令牌")


class PasswordResetRequest(BaseModel):
    """密码重置请求模型
    
    用于请求密码重置
    """
    email: EmailStr = Field(..., description="用户邮箱")


class PasswordResetConfirm(BaseModel):
    """密码重置确认模型
    
    用于确认密码重置
    """
    token: str = Field(..., description="密码重置令牌")
    new_password: str = Field(..., description="新密码")
    confirm_password: str = Field(..., description="确认新密码")
    
    @field_validator('new_password')
    def password_must_be_strong(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("密码长度不能少于8个字符")
        return v
    
    @field_validator('confirm_password')
    def passwords_match(cls, v: str, values: Dict[str, Any]) -> str:
        if 'new_password' in values.data and v != values.data['new_password']:
            raise ValueError("两次输入的密码不一致")
        return v
