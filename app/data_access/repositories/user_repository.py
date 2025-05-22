"""
用户数据Repository模块

提供用户相关的数据访问方法
"""
from typing import List, Optional
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.user import User
from app.models.domain.role import Role, UserRole
from app.data_access.repositories.base_repository import BaseRepository
from app.data_access.db_session import get_db


class UserRepository(BaseRepository[User]):
    """用户数据Repository
    
    提供用户相关的数据访问方法
    """
    
    def __init__(self, db: AsyncSession):
        """初始化UserRepository
        
        Args:
            db: 数据库会话
        """
        super().__init__(User, db)
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """通过用户名获取用户
        
        Args:
            username: 用户名
            
        Returns:
            Optional[User]: 找到的用户，如果不存在则返回None
        """
        query = select(User).where(User.username == username)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """通过邮箱获取用户
        
        Args:
            email: 邮箱地址
            
        Returns:
            Optional[User]: 找到的用户，如果不存在则返回None
        """
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_user_roles(self, user_id: int) -> List[Role]:
        """获取用户角色列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[Role]: 角色列表
        """
        # 构建连接查询
        query = (
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def assign_role(self, user_id: int, role_id: int) -> None:
        """分配角色给用户
        
        Args:
            user_id: 用户ID
            role_id: 角色ID
        """
        # 创建用户-角色关联
        user_role = UserRole(user_id=user_id, role_id=role_id)
        self.db.add(user_role)
        await self.db.commit()
    
    async def remove_role(self, user_id: int, role_id: int) -> None:
        """移除用户角色
        
        Args:
            user_id: 用户ID
            role_id: 角色ID
        """
        # 构建删除语句
        stmt = (
            select(UserRole)
            .where(UserRole.user_id == user_id)
            .where(UserRole.role_id == role_id)
        )
        result = await self.db.execute(stmt)
        user_role = result.scalars().first()
        
        if user_role:
            await self.db.delete(user_role)
            await self.db.commit()


# 使用依赖注入模式创建用户仓库
async def get_user_repository() -> UserRepository:
    """获取用户仓库实例
    
    通过依赖注入模式创建UserRepository实例
    
    Returns:
        UserRepository: 用户仓库实例
    """
    async for db in get_db():
        # 为每个请求创建新的仓库实例
        yield UserRepository(db)
