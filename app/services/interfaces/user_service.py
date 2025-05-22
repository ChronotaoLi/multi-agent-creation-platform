"""
用户服务接口

定义用户相关的业务逻辑接口
"""
from typing import Optional, Protocol, List

from app.models.schemas import UserCreate, UserUpdate, UserDB


class UserService(Protocol):
    """用户服务接口
    
    定义用户相关的业务逻辑方法
    """
    
    async def create_user(self, user_data: UserCreate) -> UserDB:
        """创建新用户
        
        Args:
            user_data: 用户创建数据
            
        Returns:
            UserDB: 创建的用户
            
        Raises:
            ResourceConflictError: 用户名或邮箱已存在
        """
        ...
    
    async def get_user_by_id(self, user_id: int) -> Optional[UserDB]:
        """通过ID获取用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[UserDB]: 找到的用户，如果不存在则返回None
        """
        ...
    
    async def get_user_by_username(self, username: str) -> Optional[UserDB]:
        """通过用户名获取用户
        
        Args:
            username: 用户名
            
        Returns:
            Optional[UserDB]: 找到的用户，如果不存在则返回None
        """
        ...
    
    async def get_user_by_email(self, email: str) -> Optional[UserDB]:
        """通过邮箱获取用户
        
        Args:
            email: 邮箱地址
            
        Returns:
            Optional[UserDB]: 找到的用户，如果不存在则返回None
        """
        ...
    
    async def update_user(self, user_id: int, user_data: UserUpdate) -> UserDB:
        """更新用户信息
        
        Args:
            user_id: 用户ID
            user_data: 用户更新数据
            
        Returns:
            UserDB: 更新后的用户
            
        Raises:
            ResourceNotFoundError: 用户不存在
            ResourceConflictError: 更新的用户名或邮箱已存在
        """
        ...
    
    async def authenticate_user(self, username_or_email: str, password: str) -> Optional[UserDB]:
        """认证用户
        
        Args:
            username_or_email: 用户名或邮箱
            password: 密码
            
        Returns:
            Optional[UserDB]: 认证成功的用户，如果认证失败则返回None
        """
        ...
    
    async def is_active(self, user: UserDB) -> bool:
        """检查用户是否活跃
        
        Args:
            user: 用户
            
        Returns:
            bool: 用户是否活跃
        """
        ...
    
    async def assign_role(self, user_id: int, role_id: int) -> None:
        """分配角色给用户
        
        Args:
            user_id: 用户ID
            role_id: 角色ID
            
        Raises:
            ResourceNotFoundError: 用户或角色不存在
        """
        ...
    
    async def get_user_permissions(self, user_id: int) -> list[str]:
        """获取用户权限
        
        Args:
            user_id: 用户ID
            
        Returns:
            list[str]: 权限列表
            
        Raises:
            ResourceNotFoundError: 用户不存在
        """
        ...
