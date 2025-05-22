"""
用户实体ORM模型

定义用户数据模型、属性和关系
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data_access.db_session import Base


class User(Base):
    """用户实体类
    
    用于存储系统用户信息
    """
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
    
    # 关系定义
    roles: Mapped[List["Role"]] = relationship(back_populates="users", secondary="user_roles")
    
    def __repr__(self) -> str:
        """对象的字符串表示
        
        Returns:
            str: 用户对象的字符串表示
        """
        return f"User(id={self.id}, username={self.username}, email={self.email})" 