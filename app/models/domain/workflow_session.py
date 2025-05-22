"""
工作流会话领域模型定义

本模块包含工作流会话相关的领域模型定义
"""
from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime

from pydantic import BaseModel, Field


class WorkflowSessionStatus(str, Enum):
    """工作流会话状态枚举"""
    INITIALIZING = "initializing"
    PLANNING = "planning"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    AWAITING_INTERVENTION = "awaiting_intervention"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class WorkflowInterventionData(BaseModel):
    """工作流干预数据模型"""
    intervention_id: str = Field(..., description="干预ID")
    type: str = Field(..., description="干预类型")
    question: str = Field(..., description="干预问题")
    options: List[Any] = Field(default_factory=list, description="干预选项")
    context: Dict[str, Any] = Field(default_factory=dict, description="干预上下文")


class WorkflowSession(BaseModel):
    """工作流会话模型"""
    session_id: str = Field(..., description="会话ID")
    project_id: str = Field(..., description="项目ID")
    user_id: str = Field(..., description="用户ID")
    workflow_type: str = Field(..., description="工作流类型")
    status: WorkflowSessionStatus = Field(WorkflowSessionStatus.INITIALIZING, description="会话状态")
    current_stage: str = Field("initialization", description="当前阶段")
    progress: float = Field(0.0, description="进度（0-1）")
    config: Dict[str, Any] = Field(default_factory=dict, description="配置数据")
    intervention_data: Optional[WorkflowInterventionData] = Field(None, description="干预数据")
    created_at: str = Field(..., description="创建时间（ISO格式）")
    updated_at: str = Field(..., description="更新时间（ISO格式）") 