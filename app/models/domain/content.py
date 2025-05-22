"""
内容实体ORM模型

定义内容项、内容版本等
"""
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import String, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data_access.db_session import Base


class ContentItem(Base):
    """内容项实体类
    
    用于存储创作内容信息（如故事、角色、场景等）
    """
    __tablename__ = "content_items"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    # 内容类型（如"story", "character", "scene"等）
    content_type: Mapped[str] = mapped_column(String(50))
    # 使用JSON类型存储结构化内容数据
    content_data: Mapped[Dict[str, Any]] = mapped_column(JSON)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    # 关系定义
    project: Mapped["Project"] = relationship("Project", back_populates="content_items")
    versions: Mapped[List["ContentVersion"]] = relationship(
        "ContentVersion", 
        back_populates="content_item",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        """对象的字符串表示
        
        Returns:
            str: 内容项对象的字符串表示
        """
        return f"ContentItem(id={self.id}, title={self.title}, type={self.content_type})"


class ContentVersion(Base):
    """内容版本实体类
    
    用于存储内容项的历史版本
    """
    __tablename__ = "content_versions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    content_item_id: Mapped[int] = mapped_column(ForeignKey("content_items.id"))
    # 使用JSON类型存储版本数据
    version_data: Mapped[Dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    # 关系定义
    content_item: Mapped["ContentItem"] = relationship("ContentItem", back_populates="versions")
    
    def __repr__(self) -> str:
        """对象的字符串表示
        
        Returns:
            str: 内容版本对象的字符串表示
        """
        return f"ContentVersion(id={self.id}, content_item_id={self.content_item_id}, created_at={self.created_at})" 