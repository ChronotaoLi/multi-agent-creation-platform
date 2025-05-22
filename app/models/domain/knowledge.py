"""
知识库实体ORM模型

定义知识项及其与向量存储、图存储的映射关系
"""
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import String, Text, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data_access.db_session import Base


class KnowledgeItem(Base):
    """知识项实体类
    
    用于存储知识库中的知识条目，并与向量数据库、图数据库中的数据建立关联
    """
    __tablename__ = "knowledge_items"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    # 存储知识项元数据（如来源、标签、关联项目等）
    metadata_json: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON)
    # 向量数据库中的ID
    vector_id: Mapped[Optional[str]] = mapped_column(String(50))
    # 图数据库中的节点ID
    node_id: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    def __repr__(self) -> str:
        """对象的字符串表示
        
        Returns:
            str: 知识项对象的字符串表示
        """
        return f"KnowledgeItem(id={self.id}, title={self.title}, vector_id={self.vector_id})"


class KnowledgeRelation(Base):
    """知识关系实体类
    
    用于存储知识项之间的关系
    """
    __tablename__ = "knowledge_relations"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("knowledge_items.id"))
    target_id: Mapped[int] = mapped_column(ForeignKey("knowledge_items.id"))
    relation_type: Mapped[str] = mapped_column(String(50))
    # 存储关系的元数据
    metadata_json: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON)
    # 图数据库中对应关系的ID
    edge_id: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    
    # 关系定义
    source: Mapped["KnowledgeItem"] = relationship("KnowledgeItem", foreign_keys=[source_id])
    target: Mapped["KnowledgeItem"] = relationship("KnowledgeItem", foreign_keys=[target_id])
    
    def __repr__(self) -> str:
        """对象的字符串表示
        
        Returns:
            str: 知识关系对象的字符串表示
        """
        return f"KnowledgeRelation(id={self.id}, source_id={self.source_id}, target_id={self.target_id}, type={self.relation_type})" 