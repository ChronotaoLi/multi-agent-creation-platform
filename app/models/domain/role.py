"""
角色实体ORM模型

定义角色、权限及其与用户的关系
"""
from typing import List, Optional

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data_access.db_session import Base
from app.models.domain.user import User


class Permission(Base):
    """权限实体类
    
    用于定义系统权限
    """
    __tablename__ = "permissions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    
    # 关系定义
    roles: Mapped[List["Role"]] = relationship(back_populates="permissions", secondary="role_permissions")
    
    def __repr__(self) -> str:
        """对象的字符串表示
        
        Returns:
            str: 权限对象的字符串表示
        """
        return f"Permission(id={self.id}, name={self.name})"


class Role(Base):
    """角色实体类
    
    用于定义用户角色
    """
    __tablename__ = "roles"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    
    # 关系定义
    permissions: Mapped[List["Permission"]] = relationship(back_populates="roles", secondary="role_permissions")
    users: Mapped[List["User"]] = relationship(back_populates="roles", secondary="user_roles")
    
    def __repr__(self) -> str:
        """对象的字符串表示
        
        Returns:
            str: 角色对象的字符串表示
        """
        return f"Role(id={self.id}, name={self.name})"


class UserRole(Base):
    """用户-角色关联表
    
    用于存储用户与角色的多对多关系
    """
    __tablename__ = "user_roles"
    
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), primary_key=True)


class RolePermission(Base):
    """角色-权限关联表
    
    用于存储角色与权限的多对多关系
    """
    __tablename__ = "role_permissions"
    
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id"), primary_key=True) 