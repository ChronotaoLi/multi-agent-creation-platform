"""
智能体实体ORM模型

定义智能体配置、状态等
"""
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy import String, ForeignKey, JSON, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data_access.db_session import Base


class Agent(Base):
    """智能体实体类
    
    用于存储智能体配置信息
    """
    __tablename__ = "agents"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    # 智能体类型，如"coordinator", "character", "content", "review"等
    agent_type: Mapped[str] = mapped_column(String(50))
    # 使用JSON类型存储智能体配置数据
    config: Mapped[Dict[str, Any]] = mapped_column(JSON)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
    
    # 关系定义
    project: Mapped["Project"] = relationship("Project", back_populates="agents")
    agent_states: Mapped[List["AgentState"]] = relationship(
        "AgentState", 
        back_populates="agent",
        cascade="all, delete-orphan"
    )
    instances: Mapped[List["AgentInstance"]] = relationship(
        "AgentInstance",
        back_populates="agent",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        """对象的字符串表示
        
        Returns:
            str: 智能体对象的字符串表示
        """
        return f"Agent(id={self.id}, name={self.name}, type={self.agent_type})"


class AgentState(Base):
    """智能体状态实体类
    
    用于存储智能体状态的历史记录，支持状态回溯
    """
    __tablename__ = "agent_states"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    # 使用JSON类型存储状态数据
    state_data: Mapped[Dict[str, Any]] = mapped_column(JSON)
    # 状态类型，如"cognitive", "emotional", "memory", "knowledge"等
    state_type: Mapped[str] = mapped_column(String(50))
    checkpoint_id: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    
    # 关系定义
    agent: Mapped["Agent"] = relationship("Agent", back_populates="agent_states")
    
    def __repr__(self) -> str:
        """对象的字符串表示
        
        Returns:
            str: 智能体状态对象的字符串表示
        """
        return f"AgentState(id={self.id}, agent_id={self.agent_id}, type={self.state_type}, created_at={self.created_at})"


class AgentInstance(Base):
    """智能体实例实体类
    
    用于存储智能体实例的运行时信息
    """
    __tablename__ = "agent_instances"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    # 实例状态: "initializing", "running", "paused", "terminated", "failed"
    status: Mapped[str] = mapped_column(String(50), default="initializing")
    # 使用JSON类型存储实例配置
    config: Mapped[Dict[str, Any]] = mapped_column(JSON)
    # 使用JSON类型存储实例运行时数据
    runtime_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default={})
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
    terminated_at: Mapped[Optional[datetime]] = mapped_column()
    
    # 关系定义
    agent: Mapped["Agent"] = relationship("Agent", back_populates="instances")
    user: Mapped["User"] = relationship("User")
    
    def __repr__(self) -> str:
        """对象的字符串表示
        
        Returns:
            str: 智能体实例对象的字符串表示
        """
        return f"AgentInstance(id={self.id}, agent_id={self.agent_id}, status={self.status})"


class AgentTemplate(Base):
    """智能体模板实体类
    
    用于存储预定义的智能体模板
    """
    __tablename__ = "agent_templates"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(String(500))
    # 智能体类型，如"coordinator", "character", "content", "review"等
    agent_type: Mapped[str] = mapped_column(String(50))
    # 使用JSON类型存储模板配置数据
    template_config: Mapped[Dict[str, Any]] = mapped_column(JSON)
    # 模板是否公开
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
    
    # 关系定义
    creator: Mapped["User"] = relationship("User")
    
    def __repr__(self) -> str:
        """对象的字符串表示
        
        Returns:
            str: 智能体模板对象的字符串表示
        """
        return f"AgentTemplate(id={self.id}, name={self.name}, type={self.agent_type})" 