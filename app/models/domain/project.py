"""
项目实体ORM模型

定义创作项目、项目用户关系等
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data_access.db_session import Base


class Project(Base):
    """项目实体类
    
    用于存储创作项目信息
    """
    __tablename__ = "projects"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    project_type: Mapped[str] = mapped_column(String(50))  # 如"story", "script", "game"等
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, archived, deleted
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    # 关系定义
    content_items: Mapped[List["ContentItem"]] = relationship(back_populates="project")
    agents: Mapped[List["Agent"]] = relationship(back_populates="project")
    project_users: Mapped[List["ProjectUser"]] = relationship(
        "ProjectUser", 
        back_populates="project", 
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        """对象的字符串表示
        
        Returns:
            str: 项目对象的字符串表示
        """
        return f"Project(id={self.id}, title={self.title}, type={self.project_type})"


class ProjectUser(Base):
    """项目-用户关联表
    
    用于存储项目与用户的多对多关系，并记录用户在项目中的角色
    """
    __tablename__ = "project_users"
    
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20))  # owner, editor, viewer, etc.
    
    # 关系定义
    project: Mapped["Project"] = relationship("Project", back_populates="project_users")
    user: Mapped["User"] = relationship("User")
    
    def __repr__(self) -> str:
        """对象的字符串表示
        
        Returns:
            str: 项目用户关系对象的字符串表示
        """
        return f"ProjectUser(project_id={self.project_id}, user_id={self.user_id}, role={self.role})" 